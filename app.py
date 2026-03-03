"""
app.py - Main Flask application for the Voicemail Drop System.
Handles web dashboard, file uploads, webhook processing, and campaign control.
"""

import os
import csv
import io
import re
import json
import logging
import threading
import functools
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, current_user, login_required as flask_login_required
import html as html_module

from storage import (
    set_campaign,
    stop_campaign,
    get_all_statuses,
    get_campaign,
    get_call_state,
    update_call_state,
    mark_transferred,
    mark_voicemail_dropped,
    reset_campaign,
    create_call_state,
    signal_call_complete,
    persist_call_log,
    get_call_history,
    clear_call_history,
    get_voicemail_url,
    get_voicemail_script,
    save_voicemail_url,
    get_voice_preset,
    save_voice_preset,
    pause_for_transfer,
    resume_after_transfer,
    is_transfer_paused,
    is_active_transfer,
    call_states_snapshot,
    append_transcript,
    get_dnc_list,
    add_to_dnc,
    remove_from_dnc,
    get_analytics,
    get_schedules,
    add_schedule,
    cancel_schedule,
    delete_schedule,
    get_due_schedules,
    mark_schedule_executed,
    record_webhook_event,
    get_webhook_stats,
    save_template,
    get_templates,
    delete_template,
    save_vm_template,
    get_vm_templates,
    update_vm_template,
    delete_vm_template,
    mark_vm_template_used,
    validate_phone_numbers,
    is_valid_phone_number,
    log_invalid_number,
    get_invalid_numbers,
    log_unreachable_number,
    get_unreachable_numbers,
    get_report_settings,
    save_report_settings,
    mark_report_sent,
    get_contacts,
    add_contacts,
    update_contact,
    delete_contacts,
    get_contact_groups,
    get_contact_tags,
    record_contact_called,
    clear_contacts,
    store_recording_url,
    get_user_for_call,
)
from telnyx_client import (
    transfer_call, play_audio, hangup_call, make_call, validate_connection_id,
    set_webhook_base_url, start_transcription, start_recording,
    search_available_numbers, purchase_number, create_call_control_app,
    assign_number_to_app, list_owned_numbers, release_number,
    list_call_control_apps, get_number_order_status,
    lookup_number, lookup_numbers_batch,
    auto_configure_outbound,
    caller_health_check, caller_health_check_batch,
)
from call_manager import start_dialer
from personalized_vm import (
    parse_csv as pvm_parse_csv,
    render_template as pvm_render_template,
    start_generation as pvm_start_generation,
    get_generation_status as pvm_get_generation_status,
    get_available_voices as pvm_get_voices,
    get_personalized_audio_url,
    get_audio_map as pvm_get_audio_map,
    clear_personalized_audio as pvm_clear,
    generate_preview_audio as pvm_preview_audio,
)

_amd_timers = {}
_detected_base_url = None

# ---- Logging Setup ----
os.makedirs("logs", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/personalized", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/calls.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("voicemail_app")

# ---- Flask App ----
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
from datetime import timedelta as _td
app.config["PERMANENT_SESSION_LIFETIME"] = _td(days=7)
app.config["SESSION_PERMANENT"] = True

# ---- Database & Auth Setup ----
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 300}

from models import db, User, UserInstance, ProvisionedNumber, UserAppData, Invitation, ensure_user_instance, init_db
import base64
import requests
init_db(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if user and not getattr(user, 'is_active_account', True):
        return None
    return user

from google_auth import google_oauth, google_oauth_available
app.register_blueprint(google_oauth)

from supa_auth import supabase_available, supabase_sign_up, supabase_sign_in, supabase_send_otp, supabase_verify_otp

@app.after_request
def add_no_cache_headers(response):
    if "text/html" in response.content_type or "text/css" in response.content_type or "javascript" in response.content_type:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

UPLOAD_FOLDER = "uploads"
ALLOWED_AUDIO = {"mp3", "wav"}
ALLOWED_CSV = {"csv", "txt"}

# Use 'live' as a default so the build daemon doesn't crash
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'live')
PAYPAL_WEBHOOK_ID = os.getenv("WEBHOOK_ID", "")

# Plan definitions for SaaS pricing
PLAN_MATRIX = {
    "starter": {"amount": Decimal("99.00"), "instances": 1},
    "business": {"amount": Decimal("399.00"), "instances": 5},
}
CALL_COST = Decimal("0.10")
MIN_REFILL = Decimal("10.00")
DEFAULT_REFILL = Decimal("25.00")


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_authenticated:
            return f(*args, **kwargs)
        if request.is_json or request.headers.get("X-Requested-With"):
            return jsonify({"error": "Not authenticated"}), 401
        return redirect(url_for("login"))
    return decorated


def require_credit(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        try:
            bal = Decimal(str(getattr(current_user, "credit_balance", 0) or 0))
        except Exception:
            bal = Decimal("0")
        if bal <= Decimal("0.01"):
            if request.is_json or request.headers.get("X-Requested-With"):
                return jsonify({"error": "Insufficient credits. Please add credits to continue.", "code": "payment_required"}), 402
            return "Payment Required", 402
        return f(*args, **kwargs)
    return wrapped


def _get_user_balance(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return Decimal("0")
    try:
        return Decimal(str(user.credit_balance or 0))
    except Exception:
        return Decimal("0")


def _paypal_base_url():
    return "https://api-m.paypal.com" if PAYPAL_MODE == "live" else "https://api-m.sandbox.paypal.com"


def _paypal_access_token():
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise RuntimeError("PAYPAL credentials missing")
    token_url = f"{_paypal_base_url()}/v1/oauth2/token"
    auth = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()).decode()
    resp = requests.post(token_url, headers={"Authorization": f"Basic {auth}"}, data={"grant_type": "client_credentials"}, timeout=20)
    resp.raise_for_status()
    return resp.json().get("access_token")


def _credit_user(user_id, amount):
    if not user_id or not amount:
        return None
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return None
    bal = Decimal(str(user.credit_balance or 0))
    user.credit_balance = (bal + Decimal(str(amount))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    db.session.commit()
    return user.credit_balance


def _set_employee_instances(user_id, count):
    try:
        if not user_id:
            return None
        existing = UserAppData.query.filter_by(user_id=user_id, data_key="employee_instances").first()
        payload = json.dumps({"unlocked": int(count)})
        if existing:
            existing.data_value = payload
        else:
            rec = UserAppData(user_id=user_id, data_key="employee_instances", data_value=payload)
            db.session.add(rec)
        db.session.commit()
        ensure_user_instance(user_id)
        return count
    except Exception as e:
        logger.error(f"Failed to set employee instances for user {user_id}: {e}")
        return None


def _send_masterpiece_email(to_email, user_name=None):
    try:
        from gmail_client import send_email
    except Exception as e:
        logger.error(f"Email module unavailable: {e}")
        return False
    if not to_email:
        return False
    subject = "Alex is joining your team! 🚀"
    content = (
        "Thank you for choosing Open Humana. Your payment was successful, and Alex is now being provisioned for your team. "
        "You can find your credentials in the dashboard."
    )
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    html_body = f"""
    <html><body style='font-family:Inter,Arial,sans-serif;background:#0b1021;color:#e5e7eb;padding:32px;'>
      <div style='max-width:520px;margin:0 auto;background:#0f172a;border:1px solid rgba(255,255,255,0.08);border-radius:18px;padding:28px;box-shadow:0 30px 80px rgba(0,0,0,0.35);'>
        <h2 style='margin:0 0 12px;font-size:22px;color:#ffffff;'>Alex is joining your team! 🚀</h2>
        <p style='margin:0 0 12px;color:rgba(229,231,235,0.8);line-height:1.6;'>{greeting}</p>
        <p style='margin:0 0 16px;color:rgba(229,231,235,0.8);line-height:1.6;'>{content}</p>
        <div style='margin-top:18px;padding:14px 16px;border-radius:12px;background:rgba(99,102,241,0.08);color:#c7d2fe;'>Payment Verified. Alex is on your way.</div>
      </div>
    </body></html>
    """
    text_body = f"{subject}\n\n{content}"
    try:
        return send_email(to_email=to_email, subject=subject, html_body=html_body, text_body=text_body)
    except Exception as e:
        logger.exception(f"Failed to send masterpiece email to {to_email}: {e}")
        return False


def _set_employee_instances(user_id, count):
    try:
        if not user_id:
            return None
        existing = UserAppData.query.filter_by(user_id=user_id, data_key="employee_instances").first()
        payload = json.dumps({"unlocked": int(count)})
        if existing:
            existing.data_value = payload
        else:
            rec = UserAppData(user_id=user_id, data_key="employee_instances", data_value=payload)
            db.session.add(rec)
        db.session.commit()
        ensure_user_instance(user_id)
        return count
    except Exception as e:
        logger.error(f"Failed to set employee instances for user {user_id}: {e}")
        return None


def _send_masterpiece_email(to_email, user_name=None):
    try:
        from gmail_client import send_email
    except Exception as e:
        logger.error(f"Email module unavailable: {e}")
        return False
    if not to_email:
        return False
    subject = "Alex is joining your team! 🚀"
    content = (
        "Thank you for choosing Open Humana. Your payment was successful, and Alex is now being provisioned for your team. "
        "You can find your credentials in the dashboard."
    )
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    html_body = f"""
    <html><body style='font-family:Inter,Arial,sans-serif;background:#0b1021;color:#e5e7eb;padding:32px;'>
      <div style='max-width:520px;margin:0 auto;background:#0f172a;border:1px solid rgba(255,255,255,0.08);border-radius:18px;padding:28px;box-shadow:0 30px 80px rgba(0,0,0,0.35);'>
        <h2 style='margin:0 0 12px;font-size:22px;color:#ffffff;'>Alex is joining your team! 🚀</h2>
        <p style='margin:0 0 12px;color:rgba(229,231,235,0.8);line-height:1.6;'>{greeting}</p>
        <p style='margin:0 0 16px;color:rgba(229,231,235,0.8);line-height:1.6;'>{content}</p>
        <div style='margin-top:18px;padding:14px 16px;border-radius:12px;background:rgba(99,102,241,0.08);color:#c7d2fe;'>Payment Verified. Alex is on your way.</div>
      </div>
    </body></html>
    """
    text_body = f"{subject}\n\n{content}"
    try:
        return send_email(to_email=to_email, subject=subject, html_body=html_body, text_body=text_body)
    except Exception as e:
        logger.exception(f"Failed to send masterpiece email to {to_email}: {e}")
        return False


def _create_paypal_order(amount, user_id, meta=None):
    access_token = _paypal_access_token()
    url = f"{_paypal_base_url()}/v2/checkout/orders"
    meta = meta or {}
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {"currency_code": "USD", "value": f"{amount:.2f}"},
                "custom_id": str(user_id),
                "description": meta.get("plan") or "credit_refill",
            }
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Prefer": "return=representation",
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _capture_paypal_order(order_id):
    access_token = _paypal_access_token()
    url = f"{_paypal_base_url()}/v2/checkout/orders/{order_id}/capture"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    resp = requests.post(url, headers=headers, json={}, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _verify_webhook(transmission_id, timestamp, webhook_id, event_body, cert_url, auth_algo, transmission_sig):
    access_token = _paypal_access_token()
    url = f"{_paypal_base_url()}/v1/notifications/verify-webhook-signature"
    payload = {
        "transmission_id": transmission_id,
        "transmission_time": timestamp,
        "cert_url": cert_url,
        "auth_algo": auth_algo,
        "transmission_sig": transmission_sig,
        "webhook_id": webhook_id,
        "webhook_event": event_body,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json()


@app.route("/billing")
def billing_page():
    plan = (request.args.get("plan") or "").lower().strip()
    if plan not in PLAN_MATRIX:
        plan = ""
    return render_template(
        "billing.html",
        user=current_user if current_user.is_authenticated else None,
        default_refill=float(DEFAULT_REFILL),
        min_refill=float(MIN_REFILL),
        processor_id=PAYPAL_CLIENT_ID,
        processor_mode=PAYPAL_MODE,
        selected_plan=plan,
    )


@app.route("/pricing")
def pricing():
    logger.info("PRICING ROUTE LOADED")
    return render_template("pricing.html")


@app.route("/api/paypal/create-order", methods=["POST"])
def paypal_create_order():
    data = request.get_json() or {}
    plan = (data.get("plan") or "").lower().strip()
    amount = Decimal(str(data.get("amount", DEFAULT_REFILL)))
    if plan in PLAN_MATRIX:
        amount = PLAN_MATRIX[plan]["amount"]
    if amount < MIN_REFILL and plan not in PLAN_MATRIX:
        return jsonify({"error": f"Minimum refill is ${MIN_REFILL:.2f}"}), 400
    user_id = current_user.id if current_user.is_authenticated else "guest"
    try:
        order = _create_paypal_order(amount, user_id, meta={"plan": plan or "refill"})
        return jsonify(order), 200
    except Exception as e:
        logger.error(f"Create order failed: {e}")
        return jsonify({"error": "Failed to create order"}), 500


def _get_or_create_user_by_email(email):
    email = (email or "").strip().lower()
    if not email:
        return None
    user = User.query.filter_by(email=email).first()
    if not user:
        logger.warning(f"PayPal payment from unknown email {email} — no account created (invite-only)")
        return None
    return user


@app.route("/api/paypal/capture-order", methods=["POST"])
def paypal_capture_order():
    data = request.get_json() or {}
    order_id = data.get("order_id")
    plan = (data.get("plan") or "").lower().strip()
    checkout_email = (data.get("email") or "").strip()
    if not order_id:
        return jsonify({"error": "order_id is required"}), 400
    try:
        resp = _capture_paypal_order(order_id)
        status = resp.get("status") or resp.get("result", {}).get("status")
        purchase_units = resp.get("purchase_units") or resp.get("result", {}).get("purchase_units", [])
        amount_val = Decimal("0")
        custom_id = None
        if purchase_units:
            pu = purchase_units[0]
            amount_val = Decimal(str(pu.get("amount", {}).get("value", "0")))
            custom_id = pu.get("custom_id")
        if status == "COMPLETED":
            target_user_id = custom_id if custom_id and custom_id != "guest" else None

            payer_email = resp.get("payer", {}).get("email_address")
            resolved_email = checkout_email or payer_email
            if not target_user_id and resolved_email:
                guest_user = _get_or_create_user_by_email(resolved_email)
                if guest_user:
                    target_user_id = guest_user.id
                    checkout_email = resolved_email

            if target_user_id:
                if plan in PLAN_MATRIX:
                    matrix = PLAN_MATRIX[plan]
                    amount_val = matrix["amount"]
                    _set_employee_instances(target_user_id, matrix["instances"])
                    credited = _credit_user(target_user_id, amount_val)
                else:
                    credited = _credit_user(target_user_id, amount_val)
            else:
                credited = amount_val

            send_to_email = None
            send_to_name = None
            if current_user.is_authenticated:
                send_to_email = current_user.email
                send_to_name = current_user.profile_name
            elif checkout_email:
                send_to_email = checkout_email
                send_to_name = checkout_email.split("@")[0]

            if send_to_email:
                def _send_masterpiece():
                    try:
                        _send_masterpiece_email(send_to_email, send_to_name)
                    except Exception as e:
                        logger.error(f"Masterpiece email failed: {e}")
                threading.Thread(target=_send_masterpiece, daemon=True).start()

            return jsonify({
                "status": status,
                "credited": float(credited or 0),
                "message": "Payment Verified. Alex is on your way.",
            }), 200
        return jsonify({"status": status, "error": "Payment not completed"}), 400
    except Exception as e:
        logger.error(f"Capture order failed: {e}")
        return jsonify({"error": "Failed to capture order"}), 500


@app.route("/api/paypal/webhook", methods=["POST"])
def paypal_webhook():
    try:
        transmission_id = request.headers.get("PayPal-Transmission-Id", "")
        timestamp = request.headers.get("PayPal-Transmission-Time", "")
        cert_url = request.headers.get("PayPal-Cert-Url", "")
        auth_algo = request.headers.get("PayPal-Auth-Algo", "")
        transmission_sig = request.headers.get("PayPal-Transmission-Sig", "")
        body = request.get_json() or {}
        verify = _verify_webhook(transmission_id, timestamp, PAYPAL_WEBHOOK_ID, body, cert_url, auth_algo, transmission_sig)
        if verify.get("verification_status") != "SUCCESS":
            return "", 400
        event_type = body.get("event_type")
        resource = body.get("resource", {})
        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            amount_val = Decimal(str(resource.get("amount", {}).get("value", "0")))
            custom_id = resource.get("custom_id")
            if custom_id:
                _credit_user(custom_id, amount_val)
        return "", 200
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        return "", 400


def _bill_successful_call(call_control_id, user_id, amount=CALL_COST):
    try:
        if not user_id:
            return
        from storage import get_call_state
        state = get_call_state(call_control_id)
        if not state:
            return
        if state.get("billed"):
            return
        status = state.get("status", "")
        if status not in ("transferred", "voicemail_complete"):
            return
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return
        user.credit_balance = (Decimal(str(user.credit_balance or 0)) - amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if user.credit_balance < 0:
            user.credit_balance = Decimal("0.00")
        db.session.commit()
        from storage import update_call_state
        update_call_state(call_control_id, billed=True)
    except Exception as e:
        logger.error(f"Billing deduction failed for call {call_control_id}: {e}")


# ---- Landing Page ----
@app.route("/")
def landing():
    """Serve the public landing page."""
    _detect_and_set_base_url()
    return render_template("landing.html")


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "service": "Open Humana"}), 200



@app.route("/api/chat", methods=["POST"])
@app.route("/api/chat-alex", methods=["POST"])
def api_chat():
    from alex_chat import stream_chat_response
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])
    if not message:
        return jsonify({"error": "Message is required"}), 400

    def generate():
        for chunk in stream_chat_response(message, history):
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return app.response_class(generate(), mimetype="text/event-stream",
                              headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.errorhandler(500)
def handle_500(e):
    logger.error(f"Internal server error: {e}")
    if request.path.startswith("/api/"):
        return jsonify({"error": "System Configuration in Progress", "details": "A required service is being configured. Please try again shortly."}), 500
    return """<!DOCTYPE html><html><head><meta charset="utf-8"><title>Open Humana</title>
    <style>body{font-family:'Helvetica Neue',Arial,sans-serif;background:#f0f0f3;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;}
    .card{background:#fff;border-radius:16px;padding:48px;text-align:center;max-width:480px;box-shadow:0 4px 24px rgba(0,0,0,0.08);}
    h1{font-size:24px;color:#111;margin:0 0 12px;}p{font-size:15px;color:#666;line-height:1.7;margin:0;}</style></head>
    <body><div class="card"><h1>System Configuration in Progress</h1><p>Open Humana is being set up. This usually takes just a moment. Please refresh the page shortly.</p></div></body></html>""", 500


@app.route("/about")
def about_page():
    return render_template("about.html")

@app.route("/blog-page")
def blog_page_redirect():
    return redirect(url_for("blog_listing"))

@app.route("/blog")
def blog_listing():
    from blog_data import get_all_posts
    all_posts = get_all_posts()
    category = request.args.get("category", "")
    categories = list(dict.fromkeys(p["category"] for p in all_posts))
    if category and category in categories:
        posts = [p for p in all_posts if p["category"] == category]
    else:
        category = ""
        posts = all_posts
    return render_template("blog.html", posts=posts, categories=categories, active_category=category)

@app.route("/blog/<slug>")
def blog_post(slug):
    from blog_data import get_all_posts, get_post_by_slug
    post = get_post_by_slug(slug)
    if not post:
        return redirect(url_for("blog_listing"))
    all_posts = get_all_posts()
    related = [p for p in all_posts if p["slug"] != slug][:3]
    return render_template("blog_post.html", post=post, related=related)

@app.route("/help")
def help_page():
    return render_template("help.html")

@app.route("/compliance")
def compliance_page():
    return render_template("compliance.html")

@app.route("/privacy")
def privacy_page():
    return render_template("privacy.html")

@app.route("/terms")
def terms_page():
    return render_template("terms.html")

@app.route("/contact")
def contact_page():
    return render_template("contact.html")


# ---- Lead Capture ----
@app.route("/api/lead", methods=["POST"])
def api_lead():
    """Receive lead form submission and email to owner."""
    try:
        data = request.get_json() or {}
        name_raw = data.get("name", "").strip()
        email_raw = data.get("email", "").strip()
        phone = data.get("phone", "").strip()
        company = data.get("company", "").strip()
        team_size = data.get("team_size", "").strip()

        if not name_raw or not email_raw or not phone:
            return jsonify({"success": False, "error": "Name, email, and phone are required"}), 400

        name = html_module.escape(name_raw)
        email = html_module.escape(email_raw)
        phone = html_module.escape(phone)
        company = html_module.escape(company)
        team_size = html_module.escape(team_size)

        now = datetime.now().strftime("%B %d, %Y at %I:%M %p")

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f4f4f7;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f7;padding:40px 20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

<tr><td style="background:linear-gradient(135deg,#1e1b4b 0%,#4338ca 100%);padding:36px 40px;text-align:center;">
  <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:800;letter-spacing:-0.5px;">&#128293; Hot Lead Received!</h1>
  <p style="margin:8px 0 0;color:rgba(255,255,255,0.7);font-size:14px;">A new prospect just submitted the demo request form</p>
</td></tr>

<tr><td style="padding:36px 40px;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8f9ff;border:1px solid #e8e8f4;border-radius:10px;overflow:hidden;">
    <tr>
      <td style="padding:20px 24px;border-bottom:1px solid #e8e8f4;">
        <span style="display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#6366f1;margin-bottom:4px;">Full Name</span>
        <span style="font-size:16px;font-weight:700;color:#111827;">{name}</span>
      </td>
    </tr>
    <tr>
      <td style="padding:20px 24px;border-bottom:1px solid #e8e8f4;">
        <span style="display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#6366f1;margin-bottom:4px;">Email Address</span>
        <a href="mailto:{email}" style="font-size:16px;font-weight:600;color:#4338ca;text-decoration:none;">{email}</a>
      </td>
    </tr>
    <tr>
      <td style="padding:20px 24px;border-bottom:1px solid #e8e8f4;">
        <span style="display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#6366f1;margin-bottom:4px;">Phone Number</span>
        <a href="tel:{phone}" style="font-size:16px;font-weight:600;color:#4338ca;text-decoration:none;">{phone}</a>
      </td>
    </tr>
    <tr>
      <td style="padding:20px 24px;border-bottom:1px solid #e8e8f4;">
        <span style="display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#6366f1;margin-bottom:4px;">Company</span>
        <span style="font-size:16px;font-weight:600;color:#111827;">{company or 'Not provided'}</span>
      </td>
    </tr>
    <tr>
      <td style="padding:20px 24px;">
        <span style="display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#6366f1;margin-bottom:4px;">Team Size</span>
        <span style="font-size:16px;font-weight:600;color:#111827;">{team_size or 'Not specified'}</span>
      </td>
    </tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:28px;">
    <tr>
      <td style="background:#fef3c7;border:1px solid #fde68a;border-radius:10px;padding:16px 20px;">
        <p style="margin:0;font-size:13px;color:#92400e;line-height:1.6;">
          <strong>&#9889; Action Required:</strong> This lead submitted a demo request on {now}. Reach out within the next 5 minutes for the highest conversion rate.
        </p>
      </td>
    </tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
    <tr>
      <td align="center">
        <a href="mailto:{email}" style="display:inline-block;padding:14px 36px;background:#6366f1;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:700;font-size:14px;">Reply to {name.split()[0] if name else 'Lead'} Now</a>
      </td>
    </tr>
  </table>
</td></tr>

<tr><td style="background:#f8f9fa;padding:24px 40px;text-align:center;border-top:1px solid #e5e7eb;">
  <p style="margin:0;font-size:12px;color:#9ca3af;">This lead was captured from your Open Humana landing page.<br>&#169; 2026 Open Humana &mdash; Your Digital Employee Agency</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>
"""

        text_body = f"""
HOT LEAD RECEIVED - {now}

Name: {name}
Email: {email}
Phone: {phone}
Company: {company or 'Not provided'}
Team Size: {team_size or 'Not specified'}

ACTION: Reach out within 5 minutes for highest conversion.
"""

        from gmail_client import send_email
        import threading

        def _send_admin_lead_email():
            try:
                result = send_email(
                    to_email=os.environ.get("ADMIN_EMAIL", "openhumana@gmail.com"),
                    subject=f"NEW LEAD: {name_raw or 'Unknown'}",
                    html_body=html_body,
                    text_body=text_body,
                )
                if result:
                    logger.info(f"Lead captured and emailed: {name} ({email}, {phone})")
                else:
                    logger.error(f"Lead captured but admin email failed: {name} ({email})")
            except Exception as e:
                logger.exception(f"Background admin email send failed for {email}: {e}")

        threading.Thread(target=_send_admin_lead_email, daemon=True).start()

        from invite_email import send_lead_confirmation_async
        send_lead_confirmation_async(email_raw, name_raw)

        def _send_telegram_lead_alert():
            try:
                bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
                chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
                if not bot_token or not chat_id:
                    return
                msg = (
                    f"🔥 *New Lead Received*\n\n"
                    f"*Name:* {name_raw}\n"
                    f"*Email:* {email_raw}\n"
                    f"*Phone:* {phone}\n"
                    f"*Company:* {company or 'Not provided'}\n"
                    f"*Team Size:* {team_size or 'Not specified'}\n"
                    f"*Time:* {now}"
                )
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
                    timeout=10,
                )
                logger.info(f"Telegram lead alert sent for {name_raw}")
            except Exception as e:
                logger.error(f"Telegram lead alert failed: {e}")

        threading.Thread(target=_send_telegram_lead_alert, daemon=True).start()

        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"Lead capture error: {e}")
        return jsonify({"success": False, "error": "Server error"}), 500


# ---- Login Route ----
@app.route("/login", methods=["GET", "POST"])
def login():
    _detect_and_set_base_url()
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    error = None
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if request.method == "POST":
        try:
            login_mode = request.form.get("login_mode", "user")
            if login_mode == "admin" and APP_PASSWORD:
                app_password = request.form.get("app_password", "").strip()
                logger.info(f"Admin login attempt (password length: {len(app_password)}, expected length: {len(APP_PASSWORD)})")
                if app_password == APP_PASSWORD:
                    admin = User.query.filter_by(email="admin@openhuman.local").first()
                    if not admin:
                        admin = User(email="admin@openhuman.local", profile_name="Admin")
                        admin.set_password(APP_PASSWORD)
                        db.session.add(admin)
                        db.session.commit()
                        logger.info("Admin account auto-created via APP_PASSWORD login")
                    login_user(admin, remember=True)
                    session.permanent = True
                    logger.info("Admin successfully authenticated")
                    if is_ajax:
                        return jsonify({"success": True, "redirect": url_for("dashboard")})
                    return redirect(url_for("dashboard"))
                else:
                    logger.warning(f"Admin login failed - password mismatch")
                    error = "Invalid admin password"
            else:
                email = request.form.get("email", "").strip().lower()
                password = request.form.get("password", "")
                if not email or not password:
                    error = "Please enter email and password"
                elif supabase_available:
                    result, err = supabase_sign_in(email, password)
                    if result:
                        user = User.query.filter_by(email=email).first()
                        if not user:
                            error = "No account found. Access is by invitation only."
                        elif not getattr(user, 'is_active_account', True):
                            error = "Your account has been deactivated. Please contact the administrator."
                        else:
                            if not user.supabase_id:
                                user.supabase_id = result["user_id"]
                                db.session.commit()
                            login_user(user)
                            session.permanent = True
                            if is_ajax:
                                return jsonify({"success": True, "redirect": url_for("dashboard")})
                            return redirect(url_for("dashboard"))
                    else:
                        error = err or "Invalid email or password"
                else:
                    user = User.query.filter_by(email=email).first()
                    if user and user.check_password(password):
                        if not getattr(user, 'is_active_account', True):
                            error = "Your account has been deactivated. Please contact the administrator."
                        else:
                            login_user(user)
                            session.permanent = True
                            if is_ajax:
                                return jsonify({"success": True, "redirect": url_for("dashboard")})
                            return redirect(url_for("dashboard"))
                    else:
                        error = "Invalid email or password"
            if is_ajax and error:
                return jsonify({"success": False, "error": error}), 401
        except Exception as e:
            logger.exception(f"Login POST handler crashed: {e}")
            if is_ajax:
                return jsonify({"success": False, "error": "Server error, please try again."}), 500
            error = "Something went wrong while logging you in. Please try again."
    return render_template("login.html", error=error, google_oauth=google_oauth_available, app_password_set=bool(APP_PASSWORD))


@app.route("/signup")
@app.route("/register")
def signup():
    return redirect(url_for("login"))


def verify_otp_page():
    email = session.get("pending_verify_email")
    if not email:
        return redirect(url_for("signup"))
    error = None
    if request.method == "POST":
        otp_code = request.form.get("otp_code", "").strip()
        if not otp_code or len(otp_code) != 6:
            error = "Please enter the 6-digit code from your email"
        else:
            result, err = supabase_verify_otp(email, otp_code)
            if result:
                name = session.pop("pending_verify_name", "")
                password = session.pop("pending_verify_password", "")
                supa_id = result["user_id"]
                session.pop("pending_verify_email", None)
                session.pop("pending_verify_supa_id", None)
                if password and result.get("access_token"):
                    try:
                        from supabase import create_client
                        temp_client = create_client(os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_ANON_KEY", ""))
                        temp_client.auth._headers = {
                            **temp_client.auth._headers,
                            "Authorization": f"Bearer {result['access_token']}"
                        }
                        temp_client.auth.update_user({"password": password})
                    except Exception as pw_err:
                        logger.warning(f"Failed to set password for {email}: {pw_err}")
                user = User.query.filter_by(email=email).first()
                if not user:
                    user = User(email=email, profile_name=name or None, supabase_id=supa_id)
                    if password:
                        user.set_password(password)
                    db.session.add(user)
                    db.session.commit()
                else:
                    if not user.supabase_id:
                        user.supabase_id = supa_id
                    if password:
                        user.set_password(password)
                    db.session.commit()
                login_user(user)
                ensure_user_instance(user.id)
                logger.info(f"New user signup via Supabase OTP: {email}")
                from welcome_email import send_welcome_email_async
                send_welcome_email_async(email, name)
                return redirect(url_for("profile_setup"))
            else:
                error = err or "Invalid or expired code"
    return render_template("verify_otp.html", email=email, error=error)


@app.route("/resend-otp", methods=["POST"])
def resend_otp():
    email = session.get("pending_verify_email")
    if not email:
        return jsonify({"success": False, "error": "No pending verification"}), 400
    success, err = supabase_send_otp(email)
    if success:
        return jsonify({"success": True, "message": "A new code has been sent to your email"})
    return jsonify({"success": False, "error": err or "Failed to resend code"}), 400


@app.route("/profile-setup", methods=["GET", "POST"])
@login_required
def profile_setup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            current_user.profile_name = name
        if "profile_image" in request.files:
            file = request.files["profile_image"]
            if file and file.filename:
                filename = secure_filename(f"profile_{current_user.id}_{file.filename}")
                filepath = os.path.join("uploads", filename)
                file.save(filepath)
                current_user.profile_image_url = f"/audio/{filename}"
        db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("profile_setup.html", user=current_user)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("landing"))


@app.route("/api/user/profile")
@login_required
def api_user_profile():
    return jsonify(current_user.to_dict())


@app.route("/api/user/profile", methods=["POST"])
@login_required
def api_update_profile():
    data = request.get_json() or {}
    if "profile_name" in data:
        current_user.profile_name = data["profile_name"].strip() or current_user.profile_name
    db.session.commit()
    return jsonify(current_user.to_dict())


def _detect_and_set_base_url():
    global _detected_base_url
    if _detected_base_url:
        return
    try:
        host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host") or request.host
        proto = request.headers.get("X-Forwarded-Proto", "https")
        if host and "localhost" not in host and "127.0.0.1" not in host:
            detected = f"{proto}://{host}"
            _detected_base_url = detected
            set_webhook_base_url(detected)
            logger.info(f"Auto-detected public base URL from request: {detected}")
            return
    except Exception:
        pass
    env_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if env_url:
        _detected_base_url = env_url
        set_webhook_base_url(env_url)
        return
    domains = os.environ.get("REPLIT_DOMAINS", "")
    if domains:
        domain = domains.split(",")[0].strip()
        if domain:
            _detected_base_url = f"https://{domain}"
            set_webhook_base_url(_detected_base_url)
            logger.info(f"Using REPLIT_DOMAINS for base URL: {_detected_base_url}")


# ---- Dashboard Route ----
@app.route("/dashboard")
@login_required
def dashboard():
    """Serve the main dashboard page (requires authentication)."""
    _detect_and_set_base_url()
    secure_from = os.environ.get("TELNYX_FROM_NUMBER", "Not set")
    user_data = current_user.to_dict() if current_user.is_authenticated else {}
    return render_template("index.html", secure_from=secure_from, user=user_data, processor_id=PAYPAL_CLIENT_ID)


# ---- Audio File Serving ----
@app.route("/audio/<filename>")
def serve_audio(filename):
    """Serve uploaded audio files for call playback (no auth - infrastructure needs direct access)."""
    response = send_from_directory(UPLOAD_FOLDER, filename)
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/audio/personalized/<filename>")
def serve_personalized_audio(filename):
    """Serve personalized voicemail audio files (no auth - infrastructure needs direct access)."""
    pvm_dir = os.path.join(UPLOAD_FOLDER, "personalized")
    response = send_from_directory(pvm_dir, filename)
    response.headers["Cache-Control"] = "no-cache"
    return response


# ---- Start Campaign ----
@app.route("/start", methods=["POST"])
@login_required
@require_credit
def start():
    """
    Start a new calling campaign.
    Accepts: phone numbers (pasted or CSV), audio (file or URL), transfer number.
    """
    _detect_and_set_base_url()
    transfer_number = request.form.get("transfer_number", "").strip()
    pasted_numbers = request.form.get("numbers", "").strip()
    audio_url_input = request.form.get("audio_url", "").strip()

    # ---- Parse phone numbers ----
    numbers = []
    csv_content_for_pvm = ""

    csv_file = request.files.get("csv_file")
    if csv_file and csv_file.filename:
        filename = secure_filename(csv_file.filename)
        content = csv_file.read().decode("utf-8")
        csv_content_for_pvm = content

        reader = csv.DictReader(io.StringIO(content))
        fieldnames = reader.fieldnames or []
        norm_fields = {f: f.strip().lower().replace(" ", "_") for f in fieldnames}
        phone_col = None
        for orig, norm in norm_fields.items():
            if norm in ("phone", "phone_number", "phonenumber", "mobile", "cell", "telephone", "tel", "number"):
                phone_col = orig
                break

        if phone_col:
            for row in reader:
                val = (row.get(phone_col) or "").strip()
                if val:
                    digits = re.sub(r'[^\d+]', '', val)
                    if digits and len(digits) >= 7:
                        if not digits.startswith("+"):
                            if len(digits) == 10:
                                digits = "+1" + digits
                            elif len(digits) == 11 and digits.startswith("1"):
                                digits = "+" + digits
                            else:
                                digits = "+" + digits
                        numbers.append(digits)
        else:
            reader2 = csv.reader(io.StringIO(content))
            header = next(reader2, None)
            for row in reader2:
                for cell in row:
                    cell = cell.strip()
                    cleaned = cell.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
                    if cleaned.isdigit() and len(cleaned) >= 7:
                        numbers.append(cell)

    if pasted_numbers:
        for line in pasted_numbers.split("\n"):
            line = line.strip()
            if line:
                numbers.append(line)

    if not numbers:
        return jsonify({"error": "No phone numbers provided"}), 400

    valid_numbers = []
    invalid_count = 0
    for num in numbers:
        is_valid, reason = is_valid_phone_number(num)
        if is_valid:
            valid_numbers.append(num)
        else:
            invalid_count += 1
            log_invalid_number(num, reason, user_id=current_user.id)
            logger.info(f"Skipping invalid number: {num} ({reason})")

    if not valid_numbers:
        return jsonify({"error": f"All {len(numbers)} numbers are invalid. No valid numbers to dial."}), 400

    if invalid_count > 0:
        logger.info(f"Format validation: {len(valid_numbers)} valid, {invalid_count} invalid (skipped)")

    enable_carrier_check = request.form.get("enable_carrier_check", "false").lower() == "true"
    carrier_check_done = False
    unreachable_count = 0
    reachable_numbers = []
    unknown_numbers = []
    if enable_carrier_check and len(valid_numbers) <= 500:
        logger.info(f"Running carrier lookup on {len(valid_numbers)} numbers...")
        try:
            lookup_results = lookup_numbers_batch(valid_numbers, max_concurrent=5)
            unreachable_count = len(lookup_results.get("unreachable", []))

            for entry in lookup_results.get("unreachable", []):
                log_unreachable_number(
                    entry.get("phone_number", ""),
                    entry.get("reason", "Unreachable"),
                    carrier=entry.get("carrier"),
                    line_type=entry.get("line_type"),
                    user_id=current_user.id,
                )
                logger.info(f"Skipping unreachable number: {entry.get('phone_number', '')} ({entry.get('reason', 'Unreachable')})")

            reachable_numbers = [r.get("phone_number", "") for r in lookup_results.get("reachable", []) if r.get("phone_number")]
            unknown_numbers = [r.get("phone_number", "") for r in lookup_results.get("unknown", []) if r.get("phone_number")]
            valid_numbers = reachable_numbers + unknown_numbers

            if not valid_numbers:
                return jsonify({"error": f"All numbers are unreachable or disconnected. {unreachable_count} numbers filtered out."}), 400

            carrier_check_done = True
            logger.info(f"Carrier validation: {len(reachable_numbers)} reachable, {len(unknown_numbers)} unknown (will dial), {unreachable_count} unreachable (skipped)")
        except Exception as e:
            logger.error(f"Carrier lookup failed, proceeding without it: {e}")
    elif not enable_carrier_check:
        logger.info("Carrier lookup not enabled for this campaign")
    elif len(valid_numbers) > 500:
        logger.info(f"Carrier lookup skipped - too many numbers ({len(valid_numbers)} > 500 limit)")

    numbers = valid_numbers

    # ---- Handle audio ----
    audio_url = None
    audio_file = request.files.get("audio_file")
    public_base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

    if audio_file and audio_file.filename:
        filename = secure_filename(audio_file.filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_AUDIO:
            return jsonify({"error": "Only MP3 and WAV files allowed"}), 400
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)
        audio_url = f"{public_base}/audio/{filename}"
        logger.info(f"Audio uploaded: {filename}, URL: {audio_url}")
    elif audio_url_input:
        audio_url = audio_url_input
        logger.info(f"Using provided audio URL: {audio_url}")
    else:
        audio_url = get_voicemail_url(user_id=current_user.id)
        logger.info(f"Using stored voicemail URL: {audio_url}")

    if not transfer_number:
        return jsonify({"error": "Transfer number is required"}), 400

    dial_mode = request.form.get("dial_mode", "sequential").strip()
    if dial_mode not in ("sequential", "simultaneous"):
        dial_mode = "sequential"
    batch_size = 5
    try:
        batch_size = int(request.form.get("batch_size", "5"))
    except (ValueError, TypeError):
        batch_size = 5
    dial_delay = 2
    try:
        dial_delay = int(request.form.get("dial_delay", "2"))
        dial_delay = max(1, min(10, dial_delay))
    except (ValueError, TypeError):
        dial_delay = 2

    voicemail_type = request.form.get("voicemail_type", "standard").strip()
    campaign_from_number = request.form.get("from_number", "").strip() or None

    # ---- Start the campaign ----
    logger.info(f"Starting campaign: {len(numbers)} numbers, transfer to {transfer_number}, mode={dial_mode}, batch={batch_size}, delay={dial_delay}min, vm_type={voicemail_type}, from={campaign_from_number or 'default'}")
    set_campaign(audio_url, transfer_number, numbers, dial_mode=dial_mode, batch_size=batch_size, dial_delay=dial_delay, from_number=campaign_from_number, user_id=current_user.id)

    if voicemail_type == "personalized":
        pvm_template_id = request.form.get("pvm_template_id", "").strip()
        pvm_voice_id = request.form.get("pvm_voice_id", "").strip()
        pvm_model_id = request.form.get("pvm_model_id", "eleven_turbo_v2_5").strip()
        pvm_script = ""

        if pvm_template_id:
            from storage import get_vm_templates as _gvt
            templates = _gvt(user_id=current_user.id)
            for t in templates:
                if t.get("id") == pvm_template_id and t.get("type") == "script":
                    pvm_script = t.get("content", "")
                    mark_vm_template_used(pvm_template_id, user_id=current_user.id)
                    break

        if not pvm_script:
            pvm_script = request.form.get("pvm_script", "").strip()

        if not pvm_script:
            return jsonify({"error": "No personalized voicemail script template selected"}), 400
        if not pvm_voice_id:
            preset = get_voice_preset(user_id=current_user.id)
            pvm_voice_id = preset.get("voice_id", "")
        if not pvm_voice_id:
            return jsonify({"error": "No voice selected for personalized voicemail"}), 400

        pvm_stability = int(request.form.get("pvm_stability", "35"))
        pvm_similarity = int(request.form.get("pvm_similarity", "80"))
        pvm_style = int(request.form.get("pvm_style", "15"))
        pvm_speed = int(request.form.get("pvm_speed", "82"))
        pvm_humanize = request.form.get("pvm_humanize", "true") == "true"

        _detect_and_set_base_url()
        base_url = _detected_base_url or os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

        contacts = []
        if csv_content_for_pvm:
            parsed = pvm_parse_csv(csv_content_for_pvm)
            contacts = parsed.get("contacts", []) if isinstance(parsed, dict) else parsed
        else:
            for num in numbers:
                contacts.append({"phone": num, "first_name": "", "last_name": ""})

        if contacts:
            voice_settings = {
                "stability": pvm_stability / 100.0,
                "similarity_boost": pvm_similarity / 100.0,
                "style": pvm_style / 100.0,
                "speed": pvm_speed / 100.0,
                "use_speaker_boost": True,
            }
            ok, msg = pvm_start_generation(contacts, pvm_script, pvm_voice_id, base_url, voice_settings=voice_settings, humanize=pvm_humanize, model_id=pvm_model_id)
            if not ok:
                return jsonify({"error": f"Failed to start PVM generation: {msg}"}), 400
            logger.info(f"PVM generation started for {len(contacts)} contacts during campaign launch")

    start_dialer(user_id=current_user.id)

    response_data = {
        "message": f"Campaign started with {len(numbers)} numbers",
        "voicemail_type": voicemail_type,
        "validation": {
            "total_input": len(numbers) + invalid_count,
            "format_invalid": invalid_count,
            "dialing": len(numbers),
        },
    }
    if carrier_check_done:
        response_data["validation"]["carrier_unreachable"] = unreachable_count
        response_data["validation"]["carrier_reachable"] = len(reachable_numbers)
        response_data["validation"]["carrier_unknown"] = len(unknown_numbers)

    return jsonify(response_data)


# ---- Test Call ----
@app.route("/test_call", methods=["POST"])
@login_required
@require_credit
def test_call():
    """Place a single test call to verify everything is working."""
    _detect_and_set_base_url()
    number = request.form.get("test_number", "").strip()
    if not number:
        return jsonify({"error": "No phone number provided"}), 400

    transfer_number = request.form.get("transfer_number", "").strip()
    vm_url = get_voicemail_url(user_id=current_user.id)
    camp = get_campaign(user_id=current_user.id)
    transfer_num = transfer_number or camp.get("transfer_number") or ""
    if not transfer_num:
        return jsonify({"error": "Transfer number is required for test calls"}), 400
    audio = camp.get("audio_url") or vm_url
    set_campaign(audio, transfer_num, [number], dial_mode="sequential", batch_size=1, user_id=current_user.id, is_test=True)

    from_number = request.form.get("from_number", "").strip() or None
    logger.info(f"Placing test call to {number}" + (f" from {from_number}" if from_number else ""))
    call_control_id, call_error = make_call(number, from_number_override=from_number)

    if call_control_id:
        create_call_state(call_control_id, number, user_id=current_user.id)
        update_call_state(call_control_id, status="test_call_ringing",
                          status_description="Ringing", status_color="blue")
        logger.info(f"Test call placed successfully to {number}")
        return jsonify({"message": f"Test call placed to {number}", "call_control_id": call_control_id})
    else:
        logger.error(f"Test call failed to {number}: {call_error}")
        return jsonify({"error": f"Failed to place call: {call_error}"}), 500


@app.route("/api/hangup_call", methods=["POST"])
@login_required
def api_hangup_call():
    data = request.get_json() or {}
    ccid = data.get("call_control_id", "").strip()
    if not ccid:
        snapshot = call_states_snapshot()
        for cid, st in snapshot.items():
            if str(st.get("user_id")) == str(current_user.id) and st.get("status") not in ("hangup", "voicemail_complete", "completed"):
                ccid = cid
                break
    if not ccid:
        return jsonify({"error": "No active call found"}), 404
    state = get_call_state(ccid)
    if not state or str(state.get("user_id")) != str(current_user.id):
        return jsonify({"error": "Call not found or not yours"}), 404
    try:
        hangup_call(ccid)
        update_call_state(ccid, status="hangup", status_description="Ended by user", status_color="yellow")
        logger.info(f"Call {ccid} ended manually by user {current_user.id}")
        return jsonify({"message": "Call ended"})
    except Exception as e:
        logger.error(f"Failed to hangup call {ccid}: {e}")
        return jsonify({"error": str(e)}), 500


# ---- Stop Campaign ----
@app.route("/stop", methods=["POST"])
@login_required
def stop():
    """Stop the current campaign. Active calls will finish but no new calls are placed."""
    stop_campaign(user_id=current_user.id)
    resume_after_transfer(user_id=current_user.id)
    logger.info("Campaign stopped by user")
    return jsonify({"message": "Campaign stopped"})


# ---- Status Endpoint (polled by frontend) ----
@app.route("/status")
@login_required
def status():
    """Return current call statuses and campaign info for the dashboard."""
    camp = get_campaign(user_id=current_user.id)
    is_test = camp.get("is_test", False)
    campaign_active = camp["active"] and not is_test
    return jsonify({
        "active": campaign_active,
        "is_test": is_test,
        "stop_requested": camp["stop_requested"],
        "total": len(camp["numbers"]) if not is_test else 0,
        "dialed_count": camp["dialed_count"] if not is_test else 0,
        "transfer_paused": is_transfer_paused(user_id=current_user.id),
        "calls": get_all_statuses(user_id=current_user.id),
    })


# ---- Voicemail Settings API ----
@app.route("/api/voicemail_settings", methods=["GET"])
@login_required
def get_vm_settings():
    url = get_voicemail_url(user_id=current_user.id)
    script = get_voicemail_script(user_id=current_user.id)
    return jsonify({"voicemail_url": url, "voicemail_script": script})


@app.route("/api/voicemail_settings", methods=["POST"])
@login_required
def save_vm_settings():
    data = request.get_json() or {}
    url = data.get("voicemail_url", "").strip()
    script = data.get("voicemail_script", "").strip()
    if not url:
        return jsonify({"error": "Voicemail URL is required"}), 400
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "URL must start with http:// or https://"}), 400
    save_voicemail_url(url, user_id=current_user.id, script=script)
    logger.info(f"Voicemail URL updated: {url}, script: {script[:50] if script else '(none)'}...")
    return jsonify({"message": "Voicemail URL saved", "voicemail_url": url, "voicemail_script": script})


@app.route("/api/voice-preset", methods=["GET"])
@login_required
def get_voice_preset_api():
    preset = get_voice_preset(user_id=current_user.id)
    return jsonify({"preset": preset})

@app.route("/api/voice-preset", methods=["POST"])
@login_required
def save_voice_preset_api():
    data = request.get_json() or {}
    preset = {
        "voice_id": data.get("voice_id", ""),
        "model_id": data.get("model_id", "eleven_turbo_v2_5"),
        "stability": data.get("stability", 35),
        "similarity": data.get("similarity", 80),
        "style": data.get("style", 15),
        "speed": data.get("speed", 82),
        "humanize": data.get("humanize", True),
        "speaker_boost": data.get("speaker_boost", True),
    }
    save_voice_preset(preset, user_id=current_user.id)
    logger.info(f"Voice preset saved: {preset.get('voice_id')}")
    return jsonify({"message": "Voice preset saved", "preset": preset})


# ---- Clear Call Logs ----
@app.route("/clear_logs", methods=["POST"])
@login_required
def clear_logs():
    from storage import clear_call_states
    camp = get_campaign(user_id=current_user.id)
    if camp.get("active"):
        return jsonify({"error": "Cannot clear logs while campaign is active"}), 400
    clear_call_states()
    clear_call_history(user_id=current_user.id)
    logger.info("Call logs cleared by user")
    return jsonify({"message": "Call logs cleared"})


# ---- Download Call Report ----
@app.route("/download_report")
@login_required
def download_report():
    """Download call history as CSV with optional date filtering."""
    start_date = request.args.get("start", "")
    end_date = request.args.get("end", "")

    history = get_call_history(start_date=start_date or None, end_date=end_date or None, user_id=current_user.id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date/Time", "Destination", "Caller ID", "Status Description", "Ring Duration (s)", "Machine Detected", "Transferred", "Voicemail Dropped", "AMD Result", "Hangup Cause", "Transcript"])

    for entry in history:
        ts = entry.get("timestamp", "")
        try:
            dt_obj = datetime.fromisoformat(ts)
            ts_formatted = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            ts_formatted = ts

        machine = "Yes" if entry.get("machine_detected") else ("No" if entry.get("machine_detected") is False else "-")
        transferred = "Yes" if entry.get("transferred") else "No"
        voicemail = "Yes" if entry.get("voicemail_dropped") else "No"
        ring = entry.get("ring_duration", "-")
        status_desc = entry.get("status_description", "") or entry.get("status", "").replace("_", " ").title()
        amd_result = entry.get("amd_result", "") or ""
        hangup_cause = entry.get("hangup_cause", "") or ""

        transcript_parts = entry.get("transcript", [])
        transcript_text = " | ".join([f"{t.get('track','')}: {t.get('text','')}" for t in transcript_parts]) if transcript_parts else ""

        writer.writerow([ts_formatted, entry.get("number", ""), entry.get("from_number", ""), status_desc, ring, machine, transferred, voicemail, amd_result, hangup_cause, transcript_text])

    csv_content = output.getvalue()
    output.close()

    now_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"open_human_report_{now_str}.csv"

    from flask import Response
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ---- DNC List API ----
@app.route("/api/dnc", methods=["GET"])
@login_required
def api_dnc_list():
    return jsonify({"dnc": get_dnc_list(user_id=current_user.id)})


@app.route("/api/dnc", methods=["POST"])
@login_required
def api_dnc_add():
    data = request.get_json() or {}
    number = data.get("number", "").strip()
    reason = data.get("reason", "manual")
    if not number:
        return jsonify({"error": "Phone number is required"}), 400
    if add_to_dnc(number, reason, user_id=current_user.id):
        logger.info(f"DNC: Added {number} (reason: {reason})")
        return jsonify({"message": f"Added {number} to DNC list"})
    return jsonify({"message": f"{number} is already on the DNC list"})


@app.route("/api/dnc", methods=["DELETE"])
@login_required
def api_dnc_remove():
    data = request.get_json() or {}
    number = data.get("number", "").strip()
    if not number:
        return jsonify({"error": "Phone number is required"}), 400
    if remove_from_dnc(number, user_id=current_user.id):
        logger.info(f"DNC: Removed {number}")
        return jsonify({"message": f"Removed {number} from DNC list"})
    return jsonify({"error": "Number not found in DNC list"}), 404


# ---- Analytics API ----
@app.route("/api/analytics", methods=["GET"])
@login_required
def api_analytics():
    return jsonify(get_analytics(user_id=current_user.id))


# ---- Campaign Scheduling API ----
@app.route("/api/schedules", methods=["GET"])
@login_required
def api_schedules_list():
    return jsonify({"schedules": get_schedules(user_id=current_user.id)})


@app.route("/api/schedules", methods=["POST"])
@login_required
def api_schedule_create():
    data = request.get_json() or {}
    scheduled_time = data.get("scheduled_time", "").strip()
    numbers_text = data.get("numbers", "").strip()
    transfer_number = data.get("transfer_number", "").strip()
    timezone = data.get("timezone", "UTC")
    dial_mode = data.get("dial_mode", "sequential")
    batch_size = data.get("batch_size", 5)

    if not scheduled_time:
        return jsonify({"error": "Scheduled time is required"}), 400
    if not numbers_text:
        return jsonify({"error": "Phone numbers are required"}), 400
    if not transfer_number:
        return jsonify({"error": "Transfer number is required"}), 400

    numbers = [n.strip() for n in numbers_text.split("\n") if n.strip()]
    if not numbers:
        return jsonify({"error": "No valid phone numbers provided"}), 400

    schedule = add_schedule({
        "scheduled_time": scheduled_time,
        "numbers": numbers,
        "transfer_number": transfer_number,
        "audio_url": data.get("audio_url", "") or get_voicemail_url(user_id=current_user.id),
        "dial_mode": dial_mode,
        "batch_size": batch_size,
        "timezone": timezone,
        "total_numbers": len(numbers),
    }, user_id=current_user.id)
    logger.info(f"Schedule created: {schedule['id']} for {scheduled_time} with {len(numbers)} numbers")
    return jsonify({"message": "Campaign scheduled", "schedule": schedule})


@app.route("/api/schedules/<schedule_id>", methods=["DELETE"])
@login_required
def api_schedule_delete(schedule_id):
    if delete_schedule(schedule_id, user_id=current_user.id):
        logger.info(f"Schedule deleted: {schedule_id}")
        return jsonify({"message": "Schedule deleted"})
    return jsonify({"error": "Schedule not found"}), 404


@app.route("/api/schedules/<schedule_id>/cancel", methods=["POST"])
@login_required
def api_schedule_cancel(schedule_id):
    if cancel_schedule(schedule_id, user_id=current_user.id):
        logger.info(f"Schedule cancelled: {schedule_id}")
        return jsonify({"message": "Schedule cancelled"})
    return jsonify({"error": "Schedule not found"}), 404


# ---- Webhook Status Monitor API ----
@app.route("/api/webhook-status", methods=["GET"])
@login_required
def api_webhook_status():
    return jsonify(get_webhook_stats())


# ---- Campaign Templates API ----
@app.route("/api/templates", methods=["GET"])
@login_required
def api_templates_list():
    return jsonify({"templates": get_templates(user_id=current_user.id)})


@app.route("/api/templates", methods=["POST"])
@login_required
def api_template_save():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Template name is required"}), 400
    template = save_template(name, data, user_id=current_user.id)
    logger.info(f"Template saved: {name} ({template['id']})")
    return jsonify({"template": template})


@app.route("/api/templates/<template_id>", methods=["DELETE"])
@login_required
def api_template_delete(template_id):
    if delete_template(template_id, user_id=current_user.id):
        logger.info(f"Template deleted: {template_id}")
        return jsonify({"message": "Template deleted"})
    return jsonify({"error": "Template not found"}), 404


# ---- Voicemail Templates API ----

@app.route("/api/vm-templates", methods=["GET"])
@login_required
def api_vm_templates_list():
    return jsonify({"templates": get_vm_templates(user_id=current_user.id)})


@app.route("/api/vm-templates", methods=["POST"])
@login_required
def api_vm_template_create():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    ttype = data.get("type", "")
    content = data.get("content", "").strip()
    if not name:
        return jsonify({"error": "Template name is required"}), 400
    if ttype not in ("audio_url", "script"):
        return jsonify({"error": "Type must be 'audio_url' or 'script'"}), 400
    if not content:
        return jsonify({"error": "Content is required"}), 400
    from storage import get_vm_templates as _get_vmt
    existing = _get_vmt(user_id=current_user.id)
    if len(existing) >= 5:
        return jsonify({"error": "Maximum 5 templates allowed. Delete one to create a new one."}), 400
    template = save_vm_template({"name": name, "type": ttype, "content": content}, user_id=current_user.id)
    logger.info(f"VM template created: {name} ({template['id']})")
    return jsonify({"template": template})


@app.route("/api/vm-templates/<template_id>", methods=["PUT"])
@login_required
def api_vm_template_update(template_id):
    data = request.get_json() or {}
    updated = update_vm_template(template_id, data, user_id=current_user.id)
    if updated:
        logger.info(f"VM template updated: {template_id}")
        return jsonify({"template": updated})
    return jsonify({"error": "Template not found"}), 404


@app.route("/api/vm-templates/<template_id>", methods=["DELETE"])
@login_required
def api_vm_template_delete(template_id):
    if delete_vm_template(template_id, user_id=current_user.id):
        logger.info(f"VM template deleted: {template_id}")
        return jsonify({"message": "Template deleted"})
    return jsonify({"error": "Template not found"}), 404


@app.route("/api/vm-templates/<template_id>/use", methods=["POST"])
@login_required
def api_vm_template_mark_used(template_id):
    mark_vm_template_used(template_id, user_id=current_user.id)
    return jsonify({"message": "ok"})


# ---- Number Validation API ----
@app.route("/api/validate-numbers", methods=["POST"])
@login_required
def api_validate_numbers():
    data = request.get_json() or {}
    numbers_text = data.get("numbers", "")
    if not numbers_text.strip():
        return jsonify({"error": "No numbers provided"}), 400
    results = validate_phone_numbers(numbers_text, user_id=current_user.id)
    return jsonify(results)


@app.route("/api/lookup-number", methods=["POST"])
@login_required
def api_lookup_number():
    data = request.get_json() or {}
    number = data.get("number", "").strip()
    if not number:
        return jsonify({"error": "No number provided"}), 400
    result = lookup_number(number)
    return jsonify(result)


@app.route("/api/lookup-numbers-batch", methods=["POST"])
@login_required
def api_lookup_numbers_batch():
    data = request.get_json() or {}
    numbers_text = data.get("numbers", "").strip()
    if not numbers_text:
        return jsonify({"error": "No numbers provided"}), 400
    numbers = [n.strip() for n in numbers_text.split("\n") if n.strip()]
    if len(numbers) > 500:
        return jsonify({"error": f"Maximum 500 numbers for batch lookup. You provided {len(numbers)}."}), 400
    results = lookup_numbers_batch(numbers, max_concurrent=5)
    return jsonify(results)


@app.route("/api/caller-health", methods=["POST"])
@login_required
def api_caller_health():
    data = request.get_json() or {}
    number = data.get("number", "").strip()
    if not number:
        return jsonify({"error": "No number provided"}), 400
    result = caller_health_check(number)
    return jsonify(result)


@app.route("/api/caller-health-batch", methods=["POST"])
@login_required
def api_caller_health_batch():
    data = request.get_json() or {}
    numbers = data.get("numbers", [])
    if not numbers:
        return jsonify({"error": "No numbers provided"}), 400
    if len(numbers) > 20:
        return jsonify({"error": "Maximum 20 numbers per batch health check"}), 400
    results = caller_health_check_batch(numbers, max_concurrent=3)
    return jsonify({"results": results})


# ---- Contact Management API ----
@app.route("/api/contacts", methods=["GET"])
@login_required
def api_contacts_list():
    tag = request.args.get("tag", "")
    group = request.args.get("group", "")
    contacts = get_contacts(tag=tag or None, group=group or None, user_id=current_user.id)
    groups = get_contact_groups(user_id=current_user.id)
    tags = get_contact_tags(user_id=current_user.id)
    return jsonify({"contacts": contacts, "groups": groups, "tags": tags, "total": len(contacts)})


@app.route("/api/contacts", methods=["POST"])
@login_required
def api_contacts_add():
    data = request.get_json() or {}
    new_contacts = data.get("contacts", [])
    group = data.get("group", "")
    tags = data.get("tags", [])

    if not new_contacts:
        return jsonify({"error": "No contacts provided"}), 400

    result = add_contacts(new_contacts, group=group, tags=tags, user_id=current_user.id)
    logger.info(f"Contacts added: {result['added']} new, {result['duplicates']} duplicates, {result['total']} total")
    return jsonify(result)


@app.route("/api/contacts/import", methods=["POST"])
@login_required
def api_contacts_import():
    group = request.form.get("group", "")
    tags_str = request.form.get("tags", "")
    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

    csv_file = request.files.get("csv_file")
    if not csv_file:
        return jsonify({"error": "No CSV file provided"}), 400

    content = csv_file.read().decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(content))
    fieldnames = reader.fieldnames or []
    norm_fields = {f: f.strip().lower().replace(" ", "_") for f in fieldnames}

    phone_col = None
    first_name_col = None
    last_name_col = None
    email_col = None
    company_col = None

    for orig, norm in norm_fields.items():
        if norm in ("phone", "phone_number", "phonenumber", "mobile", "cell", "telephone", "tel", "number"):
            phone_col = orig
        elif norm in ("first_name", "firstname", "first", "fname"):
            first_name_col = orig
        elif norm in ("last_name", "lastname", "last", "lname", "surname"):
            last_name_col = orig
        elif norm in ("email", "email_address", "emailaddress"):
            email_col = orig
        elif norm in ("company", "organization", "org", "business"):
            company_col = orig

    if not phone_col:
        return jsonify({"error": "No phone column found in CSV. Expected: phone, phone_number, mobile, cell, etc."}), 400

    contacts = []
    for row in reader:
        phone = (row.get(phone_col) or "").strip()
        if not phone:
            continue
        contact = {"phone": phone}
        if first_name_col:
            contact["first_name"] = (row.get(first_name_col) or "").strip()
        if last_name_col:
            contact["last_name"] = (row.get(last_name_col) or "").strip()
        if email_col:
            contact["email"] = (row.get(email_col) or "").strip()
        if company_col:
            contact["company"] = (row.get(company_col) or "").strip()
        contacts.append(contact)

    if not contacts:
        return jsonify({"error": "No valid contacts found in CSV"}), 400

    result = add_contacts(contacts, group=group, tags=tags, user_id=current_user.id)
    logger.info(f"CSV import: {result['added']} new, {result['duplicates']} duplicates")
    return jsonify(result)


@app.route("/api/contacts/<contact_id>", methods=["PUT"])
@login_required
def api_contact_update(contact_id):
    data = request.get_json() or {}
    updated = update_contact(contact_id, data, user_id=current_user.id)
    if updated:
        return jsonify({"contact": updated})
    return jsonify({"error": "Contact not found"}), 404


@app.route("/api/contacts/delete", methods=["POST"])
@login_required
def api_contacts_delete():
    data = request.get_json() or {}
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"error": "No contact IDs provided"}), 400
    removed = delete_contacts(ids, user_id=current_user.id)
    return jsonify({"removed": removed})


@app.route("/api/contacts/clear", methods=["POST"])
@login_required
def api_contacts_clear():
    clear_contacts(user_id=current_user.id)
    return jsonify({"message": "All contacts cleared"})


# ---- Email Report Settings API ----
@app.route("/api/report-settings", methods=["GET"])
@login_required
def api_report_settings_get():
    settings = get_report_settings(user_id=current_user.id)
    return jsonify(settings)


@app.route("/api/report-settings", methods=["POST"])
@login_required
def api_report_settings_save():
    data = request.get_json() or {}
    allowed_keys = {"enabled", "recipient_email", "send_time"}
    filtered = {k: v for k, v in data.items() if k in allowed_keys}
    if "recipient_email" in filtered:
        email = filtered["recipient_email"].strip()
        if email and "@" not in email:
            return jsonify({"error": "Invalid email address"}), 400
        filtered["recipient_email"] = email
    if "send_time" in filtered:
        send_time = filtered["send_time"].strip()
        try:
            parts = send_time.split(":")
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
        except (ValueError, IndexError):
            return jsonify({"error": "Invalid send time format (use HH:MM)"}), 400
        filtered["send_time"] = send_time
    settings = save_report_settings(filtered, user_id=current_user.id)
    logger.info(f"Report settings updated: enabled={settings.get('enabled')}, recipient={settings.get('recipient_email')}, time={settings.get('send_time')}")
    return jsonify(settings)


@app.route("/api/report-settings/test", methods=["POST"])
@login_required
def api_report_test():
    from daily_report import send_test_report
    data = request.get_json() or {}
    recipient = data.get("recipient_email", "").strip()
    result = send_test_report(recipient_email=recipient if recipient else None)
    if result.get("success"):
        return jsonify({"message": f"Test report sent to {result['recipient']}", "summary": result.get("summary")})
    return jsonify({"error": result.get("error", "Failed to send test report")}), 500


@app.route("/api/gmail-status", methods=["GET"])
@login_required
def api_gmail_status():
    from gmail_client import test_connection
    return jsonify(test_connection())


@app.route("/api/campaign_history")
@login_required
def campaign_history():
    from storage import get_campaign_history_summary
    return jsonify(get_campaign_history_summary(user_id=current_user.id))


# ---- Background Scheduler Thread ----
def _scheduler_worker():
    import time as _time
    while True:
        try:
            due = get_due_schedules()
            for schedule in due:
                camp = get_campaign()
                if camp.get("active"):
                    logger.info(f"Scheduler: Campaign already active, skipping schedule {schedule['id']}")
                    continue

                logger.info(f"Scheduler: Executing scheduled campaign {schedule['id']}")
                numbers = schedule.get("numbers", [])
                transfer_number = schedule.get("transfer_number", "")
                audio_url = schedule.get("audio_url", "") or get_voicemail_url()
                dial_mode = schedule.get("dial_mode", "sequential")
                batch_size = schedule.get("batch_size", 5)

                set_campaign(audio_url, transfer_number, numbers, dial_mode=dial_mode, batch_size=batch_size)
                start_dialer()
                mark_schedule_executed(schedule["id"])
                logger.info(f"Scheduler: Campaign {schedule['id']} started with {len(numbers)} numbers")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        _time.sleep(30)


def _report_scheduler_worker():
    import time as _time
    from daily_report import generate_and_send_report
    logger.info("Daily report scheduler started")
    while True:
        try:
            settings = get_report_settings()
            if settings.get("enabled") and settings.get("recipient_email"):
                send_time = settings.get("send_time", "08:00")
                now = datetime.utcnow()
                current_time = now.strftime("%H:%M")

                send_h, send_m = int(send_time.split(":")[0]), int(send_time.split(":")[1])
                current_h, current_m = now.hour, now.minute
                is_past_send_time = (current_h > send_h) or (current_h == send_h and current_m >= send_m)

                if is_past_send_time:
                    last_sent = settings.get("last_sent")
                    should_send = True
                    if last_sent:
                        from storage import _parse_ts
                        last_dt = _parse_ts(last_sent)
                        if last_dt and (now - last_dt).total_seconds() < 82800:
                            should_send = False

                    if should_send:
                        logger.info(f"Daily report: Sending scheduled report (send_time={send_time}, now={now.strftime('%H:%M')} UTC)")
                        success = generate_and_send_report()
                        if success:
                            mark_report_sent()
                            logger.info("Daily report: Sent successfully")
                        else:
                            logger.error("Daily report: Failed to send")
        except Exception as e:
            logger.error(f"Report scheduler error: {e}")
        _time.sleep(30)


_scheduler_thread = None
_report_thread = None


def start_scheduler():
    global _scheduler_thread, _report_thread
    if not _scheduler_thread or not _scheduler_thread.is_alive():
        _scheduler_thread = threading.Thread(target=_scheduler_worker, daemon=True)
        _scheduler_thread.start()
        logger.info("Background scheduler started")
    if not _report_thread or not _report_thread.is_alive():
        _report_thread = threading.Thread(target=_report_scheduler_worker, daemon=True)
        _report_thread.start()


# ---- Personalized Voicemail API ----
@app.route("/api/pvm/voices", methods=["GET"])
@login_required
def pvm_voices():
    voices = pvm_get_voices()
    return jsonify({"voices": voices})


@app.route("/api/pvm/parse", methods=["POST"])
@login_required
def pvm_parse():
    if "csv_file" not in request.files:
        csv_text = request.form.get("csv_text", "")
        if not csv_text:
            return jsonify({"error": "No CSV data provided"}), 400
    else:
        f = request.files["csv_file"]
        csv_text = f.read().decode("utf-8", errors="replace")

    result = pvm_parse_csv(csv_text)
    return jsonify(result)


@app.route("/api/pvm/preview", methods=["POST"])
@login_required
def pvm_preview():
    data = request.get_json() or {}
    template = data.get("template", "")
    contact = data.get("contact", {})
    if not template:
        return jsonify({"error": "No template provided"}), 400
    humanize = data.get("humanize", True)
    rendered = pvm_render_template(template, contact, humanize=humanize)
    return jsonify({"rendered": rendered})


@app.route("/api/pvm/preview-audio", methods=["POST"])
@login_required
def pvm_preview_audio_endpoint():
    data = request.get_json() or {}
    template = data.get("template", "")
    contact = data.get("contact", {})
    voice_id = data.get("voice_id", "")
    if not template:
        return jsonify({"error": "No template provided"}), 400
    if not voice_id:
        return jsonify({"error": "No voice selected"}), 400

    _detect_and_set_base_url()
    base_url = _detected_base_url or os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

    voice_settings = data.get("voice_settings", None)
    humanize = data.get("humanize", True)

    model_id = data.get("model_id", "eleven_multilingual_v2")
    filename, result = pvm_preview_audio(contact, template, voice_id, voice_settings=voice_settings, humanize=humanize, model_id=model_id)
    if filename:
        audio_url = f"{base_url}/audio/personalized/{filename}"
        return jsonify({"audio_url": audio_url, "script": result})
    else:
        return jsonify({"error": f"Failed to generate preview: {result}"}), 500


@app.route("/api/pvm/generate", methods=["POST"])
@login_required
def pvm_generate():
    data = request.get_json() or {}
    contacts = data.get("contacts", [])
    template = data.get("template", "")
    voice_id = data.get("voice_id", "")
    voice_settings = data.get("voice_settings", None)
    humanize = data.get("humanize", True)

    if not contacts:
        return jsonify({"error": "No contacts provided"}), 400
    if not template:
        return jsonify({"error": "No template provided"}), 400
    if not voice_id:
        return jsonify({"error": "No voice selected"}), 400

    _detect_and_set_base_url()
    base_url = _detected_base_url or os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if not base_url:
        return jsonify({"error": "Could not determine public URL for audio serving"}), 400

    model_id = data.get("model_id", "eleven_multilingual_v2")
    success, msg = pvm_start_generation(contacts, template, voice_id, base_url, voice_settings=voice_settings, humanize=humanize, model_id=model_id)
    if not success:
        return jsonify({"error": msg}), 400
    return jsonify({"message": msg, "total": len(contacts)})


@app.route("/api/pvm/status", methods=["GET"])
@login_required
def pvm_status():
    status = pvm_get_generation_status()
    return jsonify({
        "status": status["status"],
        "total": status["total"],
        "completed": status["completed"],
        "errors": status["errors"],
    })


@app.route("/api/pvm/audio-map", methods=["GET"])
@login_required
def pvm_audio_map():
    audio_map = pvm_get_audio_map()
    return jsonify({"audio_map": audio_map, "count": len(audio_map)})


@app.route("/api/pvm/clear", methods=["POST"])
@login_required
def pvm_clear_all():
    pvm_clear()
    return jsonify({"message": "Personalized audio cleared"})


def _drop_voicemail_now(call_control_id, audio_url, is_personalized, customer_number, user_id):
    """Play voicemail audio and append transcript. Called after beep or timeout."""
    if not mark_voicemail_dropped(call_control_id):
        return
    from datetime import datetime as dt
    update_call_state(call_control_id,
                      status_description="Dropping voicemail..." if not is_personalized else "Dropping personalized voicemail...",
                      status_color="blue",
                      vm_pending_audio_url=None,
                      vm_playback_start=dt.utcnow().timestamp())
    if is_personalized:
        logger.info(f"Using PERSONALIZED voicemail for {customer_number} on {call_control_id}")
    logger.info(f"Dropping voicemail NOW on {call_control_id}: {audio_url}")
    play_audio(call_control_id, audio_url)
    vm_script_text = None
    if is_personalized and customer_number:
        audio_map = pvm_get_audio_map()
        digits = re.sub(r'[^\d+]', '', customer_number)
        for key, val in audio_map.items():
            if key.lstrip("+") == digits.lstrip("+"):
                vm_script_text = val.get("script", "")
                break
    if not vm_script_text:
        vm_script_text = get_voicemail_script(user_id=user_id)
    if vm_script_text:
        append_transcript(call_control_id, vm_script_text, track="outbound", is_final=True)


# ---- Telnyx Webhook Handler ----
@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Receive and process Telnyx webhook events.
    Always returns 200 immediately to avoid timeouts.
    All call logic decisions are made here based on event type.
    """
    try:
        return _handle_webhook()
    except Exception as e:
        logger.error(f"CRITICAL webhook handler error: {e}", exc_info=True)
        return "", 200

def _handle_webhook():
    body = request.json
    if not body:
        logger.warning("Webhook received with empty body")
        return "", 200

    data = body.get("data", {})
    event_type = data.get("event_type", "")
    payload = data.get("payload", {})
    call_control_id = payload.get("call_control_id", "")

    logger.info(f">>> WEBHOOK received: {event_type} for call {call_control_id}")
    record_webhook_event(event_type, call_control_id)

    to_number = payload.get("to") or ""
    from_number = payload.get("from") or ""
    call_number = to_number or from_number

    state = get_call_state(call_control_id)

    webhook_user_id = get_user_for_call(call_control_id)
    camp = get_campaign(user_id=webhook_user_id)
    transfer_num = camp.get("transfer_number") or ""
    is_transfer_leg = False
    if not state and call_control_id and call_number:
        normalized_to = (to_number or "").lstrip("+").replace("-", "").replace(" ", "")
        normalized_transfer = (transfer_num or "").lstrip("+").replace("-", "").replace(" ", "")
        if transfer_num and normalized_transfer and normalized_to and (normalized_transfer in normalized_to or normalized_to in normalized_transfer):
            is_transfer_leg = True
            logger.info(f"Transfer leg detected: {call_control_id} to {to_number} (transfer number: {transfer_num})")
        else:
            create_call_state(call_control_id, call_number, user_id=webhook_user_id)
            logger.info(f"Auto-created call state for {call_number} (webhook arrived before state)")

    if is_transfer_leg or (state and state.get("is_transfer_leg")):
        if event_type == "call.answered":
            logger.info(f"Transfer leg {call_control_id} answered - human connected, speaking now")
            for cid_key, cid_state in list(call_states_snapshot().items()):
                if cid_state.get("transferred") and is_active_transfer(cid_key):
                    update_call_state(cid_key, status="transferred",
                                      status_description="Connected to a human, speaking now", status_color="green")
                    logger.info(f"Updated parent call {cid_key} status to 'Connected to a human, speaking now'")
        elif event_type == "call.hangup":
            logger.info(f"Transfer leg {call_control_id} hung up - call ended, resuming campaign")
            for cid_key, cid_state in list(call_states_snapshot().items()):
                if cid_state.get("transferred") and is_active_transfer(cid_key):
                    update_call_state(cid_key, status="transferred",
                                      status_description="Transfer call ended", status_color="green")
                    resume_after_transfer(cid_key, user_id=get_user_for_call(cid_key))
                    signal_call_complete(cid_key)
                    logger.info(f"Resumed campaign after transfer leg hangup for {cid_key}")
        return "", 200

    # ---- call.initiated ----
    if event_type == "call.initiated":
        from datetime import datetime as dt
        update_call_state(call_control_id, status="ringing", ring_start=dt.utcnow().timestamp(), from_number=from_number,
                          status_description="Ringing", status_color="blue")

    # ---- call.answered ----
    elif event_type == "call.answered":
        state = get_call_state(call_control_id)
        if state and state.get("transferred"):
            logger.info(f"Ignoring call.answered for already-transferred call {call_control_id}")
            update_call_state(call_control_id, status="transferred",
                              status_description="Connected to a human, speaking now", status_color="green")
            return "", 200

        from datetime import datetime as dt
        update_call_state(call_control_id, status="answered", amd_received=False, ring_end=dt.utcnow().timestamp(),
                          status_description="Answered - detecting...", status_color="blue")
        logger.info(f"Call answered: {call_control_id}, waiting for AMD result...")

        try:
            start_transcription(call_control_id)
        except Exception as e:
            logger.error(f"Failed to start transcription: {e}")

        try:
            start_recording(call_control_id)
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")

        def _amd_fallback(ccid):
            """If AMD event never arrives, treat as machine and drop voicemail (safe mode)."""
            state = get_call_state(ccid)
            if state and not state.get("amd_received") and state.get("status") == "answered":
                logger.warning(f"AMD timeout on {ccid}, treating as MACHINE (safe mode) - will drop voicemail")
                update_call_state(ccid, machine_detected=True, status="machine_detected", amd_received=True,
                                  amd_result="timeout", status_description="AMD timeout - dropping voicemail (safe mode)", status_color="yellow")
                uid = get_user_for_call(ccid)
                camp = get_campaign(user_id=uid)
                customer_num = state.get("number", "")
                personalized_url = get_personalized_audio_url(customer_num) if customer_num else None
                audio_url = personalized_url or camp.get("audio_url", "") or get_voicemail_url(user_id=uid)
                is_personalized = bool(personalized_url)

                if audio_url:
                    logger.info(f"AMD timeout fallback: dropping voicemail immediately on {ccid}")
                    _drop_voicemail_now(ccid, audio_url, is_personalized, customer_num, uid)
                else:
                    logger.error(f"AMD timeout on {ccid}, no audio URL, hanging up")
                    update_call_state(ccid, status_description="Voicemail failed - no audio", status_color="red")
                    hangup_call(ccid)
            _amd_timers.pop(ccid, None)

        timer = threading.Timer(8.0, _amd_fallback, args=[call_control_id])
        timer.daemon = True
        _amd_timers[call_control_id] = timer
        timer.start()

    # ---- call.machine.detection.ended ----
    elif event_type == "call.machine.detection.ended":
        state = get_call_state(call_control_id)
        if state and state.get("transferred"):
            logger.info(f"Ignoring AMD event for already-transferred call {call_control_id}")
            return "", 200

        result = payload.get("result", "unknown")
        amd_type = payload.get("type", "unknown")
        logger.info(f"AMD result: {result} (type={amd_type}) for {call_control_id} | payload keys: {list(payload.keys())}")

        timer = _amd_timers.pop(call_control_id, None)
        if timer:
            timer.cancel()

        update_call_state(call_control_id, amd_received=True)

        state = get_call_state(call_control_id)
        if not state:
            return "", 200

        if result == "human":
            update_call_state(call_control_id, machine_detected=False, status="human_detected",
                              amd_result="human", status_description="Human detected", status_color="blue")
            camp = get_campaign(user_id=webhook_user_id)
            transfer_num = camp.get("transfer_number") or ""
            customer_num = (get_call_state(call_control_id) or {}).get("number", "")
            if transfer_num and mark_transferred(call_control_id):
                logger.info(f"HUMAN detected - transferring {call_control_id} to {transfer_num} (caller ID: {customer_num})")
                success = transfer_call(call_control_id, transfer_num, customer_number=customer_num)
                if success:
                    pause_for_transfer(call_control_id, user_id=webhook_user_id)
                    logger.info(f"Campaign paused for transfer on {call_control_id}")
                    update_call_state(call_control_id, status="transferred",
                                      status_description="Answered by human - transferred (campaign paused)", status_color="green")
                else:
                    logger.error(f"Transfer failed for {call_control_id}, hanging up")
                    update_call_state(call_control_id, status="transfer_failed",
                                      status_description="Transfer failed", status_color="red")
                    hangup_call(call_control_id)
            elif not transfer_num:
                logger.warning(f"HUMAN detected on {call_control_id} but no transfer number configured")
                update_call_state(call_control_id, status="human_no_transfer",
                                  status_description="Human answered - no transfer number", status_color="yellow")
                hangup_call(call_control_id)

        elif result == "fax":
            update_call_state(call_control_id, machine_detected=True, status="machine_detected",
                              amd_result="fax", status_description="Fax machine detected", status_color="red")
            logger.info(f"FAX detected on {call_control_id}, hanging up")
            hangup_call(call_control_id)

        elif result == "machine":
            update_call_state(call_control_id, machine_detected=True, status="machine_detected",
                              amd_result="machine", status_description="Machine detected - waiting for beep", status_color="blue")
            logger.info(f"MACHINE detected on {call_control_id}, waiting for greeting to end before playing voicemail")

            camp = get_campaign(user_id=webhook_user_id)
            state = get_call_state(call_control_id)
            customer_number = (state or {}).get("number", "")
            personalized_url = get_personalized_audio_url(customer_number) if customer_number else None
            audio_url = personalized_url or camp.get("audio_url", "") or get_voicemail_url(user_id=webhook_user_id)
            is_personalized = bool(personalized_url)

            update_call_state(call_control_id,
                              vm_pending_audio_url=audio_url,
                              vm_pending_personalized=is_personalized,
                              vm_pending_customer_number=customer_number,
                              vm_pending_user_id=webhook_user_id)

            def _greeting_delay_drop(ccid, aud_url, is_pvm, cust_num, uid):
                st = get_call_state(ccid)
                if st and not st.get("voicemail_dropped") and st.get("vm_pending_audio_url"):
                    logger.info(f"Greeting delay elapsed on {ccid}, dropping voicemail now")
                    _drop_voicemail_now(ccid, aud_url, is_pvm, cust_num, uid)

            if audio_url:
                t = threading.Timer(5, _greeting_delay_drop, args=[call_control_id, audio_url, is_personalized, customer_number, webhook_user_id])
                t.daemon = True
                t.start()
                _amd_timers[f"beep_{call_control_id}"] = t
            else:
                logger.error(f"No audio URL configured for voicemail on {call_control_id}")
                update_call_state(call_control_id, status_description="Voicemail failed - no audio", status_color="red")
                hangup_call(call_control_id)

        elif result == "not_sure":
            update_call_state(call_control_id, machine_detected=True, status="machine_detected",
                              amd_result="not_sure", status_description="Detection unclear - treating as machine (safe mode)", status_color="yellow")
            logger.info(f"AMD not_sure on {call_control_id}, treating as MACHINE (safe) - will drop voicemail")

            camp = get_campaign(user_id=webhook_user_id)
            state = get_call_state(call_control_id)
            customer_number = (state or {}).get("number", "")
            personalized_url = get_personalized_audio_url(customer_number) if customer_number else None
            audio_url = personalized_url or camp.get("audio_url", "") or get_voicemail_url(user_id=webhook_user_id)
            is_personalized = bool(personalized_url)

            update_call_state(call_control_id,
                              vm_pending_audio_url=audio_url,
                              vm_pending_personalized=is_personalized,
                              vm_pending_customer_number=customer_number,
                              vm_pending_user_id=webhook_user_id)

            def _greeting_delay_drop_unsure(ccid, aud_url, is_pvm, cust_num, uid):
                st = get_call_state(ccid)
                if st and not st.get("voicemail_dropped") and st.get("vm_pending_audio_url"):
                    logger.info(f"Greeting delay elapsed on {ccid} (not_sure), dropping voicemail now")
                    _drop_voicemail_now(ccid, aud_url, is_pvm, cust_num, uid)

            if audio_url:
                t = threading.Timer(5, _greeting_delay_drop_unsure, args=[call_control_id, audio_url, is_personalized, customer_number, webhook_user_id])
                t.daemon = True
                t.start()
                _amd_timers[f"beep_{call_control_id}"] = t
            else:
                logger.error(f"No audio URL for voicemail on {call_control_id} (not_sure)")
                update_call_state(call_control_id, status_description="Voicemail failed - no audio", status_color="red")
                hangup_call(call_control_id)

        else:
            update_call_state(call_control_id, status="no_answer",
                              amd_result=result, status_description=f"Unknown AMD result: {result}", status_color="yellow")
            logger.info(f"AMD unknown result '{result}' on {call_control_id}, hanging up")
            hangup_call(call_control_id)

    # ---- call.machine.greeting.ended (beep detected) ----
    elif event_type in ("call.machine.greeting.ended", "call.machine.premium.greeting.ended"):
        state = get_call_state(call_control_id)
        if not state:
            return "", 200

        beep_result = payload.get("result", "unknown")
        logger.info(f"Voicemail greeting ended on {call_control_id}, result: {beep_result}")

        beep_timer = _amd_timers.pop(f"beep_{call_control_id}", None)
        if beep_timer:
            beep_timer.cancel()

        if not state.get("voicemail_dropped") and state.get("vm_pending_audio_url"):
            audio_url = state.get("vm_pending_audio_url")
            is_pvm = state.get("vm_pending_personalized", False)
            cust_num = state.get("vm_pending_customer_number", "")
            uid = state.get("vm_pending_user_id") or get_user_for_call(call_control_id)
            logger.info(f"Greeting ended ({beep_result}) on {call_control_id} — dropping voicemail now (after beep)")
            _drop_voicemail_now(call_control_id, audio_url, is_pvm, cust_num, uid)
        elif state.get("voicemail_dropped"):
            logger.info(f"Greeting ended on {call_control_id}, voicemail already playing")

    # ---- call.playback.ended ----
    elif event_type == "call.playback.ended":
        state = get_call_state(call_control_id)
        if state and state.get("voicemail_dropped"):
            vm_duration = None
            vm_start = state.get("vm_playback_start")
            if vm_start:
                from datetime import datetime as dt
                vm_duration = round(dt.utcnow().timestamp() - vm_start)
            desc = "Voicemail dropped successfully"
            if vm_duration is not None:
                desc = f"Voicemail dropped successfully — {vm_duration}s"
            update_call_state(call_control_id, status="voicemail_complete",
                              status_description=desc, status_color="green",
                              vm_duration=vm_duration)
            logger.info(f"Voicemail playback complete on {call_control_id} ({vm_duration}s), hanging up")
            hangup_call(call_control_id)

    # ---- call.transcription ----
    elif event_type == "call.transcription":
        logger.info(f"RAW transcription payload keys: {list(payload.keys())} for {call_control_id}")
        logger.info(f"RAW transcription payload: {str(payload)[:500]}")
        transcript_text = payload.get("transcript", "")
        if not transcript_text:
            td = payload.get("transcription_data") or payload.get("data") or {}
            if isinstance(td, dict):
                transcript_text = td.get("transcript", "")
        is_final = payload.get("is_final", False)
        if not is_final:
            td2 = payload.get("transcription_data") or payload.get("data") or {}
            if isinstance(td2, dict):
                is_final = td2.get("is_final", False)
        track = payload.get("track", "") or payload.get("transcription_event_type", "") or "inbound"
        logger.info(f"Transcription parsed: is_final={is_final}, track={track}, text='{transcript_text[:120] if transcript_text else '(empty)'}', call={call_control_id}")
        if transcript_text:
            append_transcript(call_control_id, transcript_text, track, is_final=is_final)
            logger.info(f"Transcript stored [{track}] for {call_control_id}: {transcript_text[:100]}")

            state = get_call_state(call_control_id)
            if state and state.get("machine_detected") and not state.get("voicemail_dropped") and state.get("vm_pending_audio_url"):
                vm_keywords = ["leave your message", "leave a message", "after the tone", "after the beep",
                               "at the tone", "press pound", "unavailable", "voicemail", "not available",
                               "can't come to the phone", "record your message"]
                text_lower = transcript_text.lower()
                if any(kw in text_lower for kw in vm_keywords):
                    logger.info(f"Voicemail keywords detected in transcription for {call_control_id}, dropping voicemail NOW")
                    beep_timer = _amd_timers.pop(f"beep_{call_control_id}", None)
                    if beep_timer:
                        beep_timer.cancel()
                    audio_url = state.get("vm_pending_audio_url")
                    is_pvm = state.get("vm_pending_personalized", False)
                    cust_num = state.get("vm_pending_customer_number", "")
                    uid = state.get("vm_pending_user_id") or get_user_for_call(call_control_id)
                    _drop_voicemail_now(call_control_id, audio_url, is_pvm, cust_num, uid)

    # ---- call.recording.saved ----
    elif event_type == "call.recording.saved":
        recording_urls = payload.get("recording_urls", {})
        recording_url = recording_urls.get("mp3") or recording_urls.get("wav") or ""
        if not recording_url:
            public_url = payload.get("public_recording_urls", {})
            recording_url = public_url.get("mp3") or public_url.get("wav") or ""
        if recording_url:
            store_recording_url(call_control_id, recording_url)
            logger.info(f"Recording saved for {call_control_id}: {recording_url[:80]}")
        else:
            logger.warning(f"Recording saved event but no URL found for {call_control_id}")

    # ---- call.hangup ----
    elif event_type == "call.hangup":
        timer = _amd_timers.pop(call_control_id, None)
        if timer:
            timer.cancel()
        beep_timer = _amd_timers.pop(f"beep_{call_control_id}", None)
        if beep_timer:
            beep_timer.cancel()

        hangup_cause = payload.get("hangup_cause", "unknown")
        hangup_source = payload.get("hangup_source", "unknown")
        sip_code = payload.get("sip_hangup_cause", "")

        if is_active_transfer(call_control_id):
            logger.info(f"Transferred call {call_control_id} hung up, resuming campaign")
            resume_after_transfer(call_control_id, user_id=webhook_user_id)

        state = get_call_state(call_control_id)
        if state:
            current_status = state.get("status", "")
            updates = {"hangup_cause": hangup_cause}

            if current_status not in ("transferred", "voicemail_complete"):
                updates["status"] = "hangup"
                ring_dur = ""
                if state.get("ring_start"):
                    from datetime import datetime as dt
                    end_ts = state.get("ring_end") or dt.utcnow().timestamp()
                    ring_dur = f" - rang {round(end_ts - state['ring_start'])}s"

                normal_clearing_desc = "Disconnected by recipient" if hangup_source == "callee" else "Call disconnected"
                hangup_desc_map = {
                    "BUSY": ("Line busy", "red"),
                    "USER_BUSY": ("Line busy", "red"),
                    "NO_ANSWER": (f"No answer{ring_dur}", "red"),
                    "ORIGINATOR_CANCEL": (f"No answer{ring_dur}", "red"),
                    "INVALID_NUMBER": ("Invalid or disconnected number", "red"),
                    "UNALLOCATED_NUMBER": ("Invalid or disconnected number", "red"),
                    "NUMBER_CHANGED": ("Number no longer in service", "red"),
                    "CALL_REJECTED": ("Call rejected", "red"),
                    "NORMAL_TEMPORARY_FAILURE": ("Call failed - network error", "red"),
                    "SERVICE_UNAVAILABLE": ("Call failed - service unavailable", "red"),
                    "NETWORK_OUT_OF_ORDER": ("Call failed - network error", "red"),
                    "RECOVERY_ON_TIMER_EXPIRE": (f"No voicemail system detected{ring_dur}", "yellow"),
                    "NORMAL_CLEARING": (normal_clearing_desc, "yellow"),
                }

                if hangup_cause in hangup_desc_map:
                    desc, color = hangup_desc_map[hangup_cause]
                    updates["status_description"] = desc
                    updates["status_color"] = color
                elif current_status in ("ringing", "initiated"):
                    updates["status_description"] = f"Call failed ({hangup_cause})"
                    updates["status_color"] = "red"
                elif not state.get("status_description") or state.get("status_color") == "blue":
                    updates["status_description"] = f"Call ended ({hangup_cause})"
                    updates["status_color"] = "yellow"

            if not state.get("ring_end"):
                from datetime import datetime as dt
                updates["ring_end"] = dt.utcnow().timestamp()
            update_call_state(call_control_id, **updates)
        logger.info(f"Call ended: {call_control_id} | cause={hangup_cause} source={hangup_source} sip={sip_code}")
        persist_call_log(call_control_id)
        signal_call_complete(call_control_id)

        if state:
            try:
                result_desc = state.get("status_description", state.get("status", "unknown"))
                record_contact_called(state.get("number", ""), result_desc)
            except Exception:
                pass

    return "", 200


# ---- Phone Number Management API ----
@app.route("/api/numbers/search", methods=["GET"])
@login_required
def api_numbers_search():
    country = request.args.get("country", "US")
    area_code = request.args.get("area_code", "").strip() or None
    state = request.args.get("state", "").strip() or None
    city = request.args.get("city", "").strip() or None
    number_type = request.args.get("number_type", "local")
    limit = int(request.args.get("limit", 20))
    result = search_available_numbers(country, area_code, state, city, number_type, limit)
    if result.get("success"):
        return jsonify(result)
    return jsonify(result), 400


@app.route("/api/numbers/buy", methods=["POST"])
@login_required
def api_numbers_buy():
    """Purchase a number — enforces one-number governance per user."""
    user_id = current_user.id

    # One Number Governance: check if user already has an active number
    existing_active = ProvisionedNumber.query.filter_by(user_id=user_id, status='active').first()
    if existing_active:
        return jsonify({
            "error": "You already have an active line. Use 'Request Additional Line' to request more.",
            "has_active": True,
            "active_number": existing_active.phone_number
        }), 403

    data = request.get_json() or {}
    phone_number = data.get("phone_number", "").strip()
    if not phone_number:
        return jsonify({"error": "Phone number is required"}), 400

    auto_setup = data.get("auto_setup", True)
    app_name = data.get("app_name", "Open Human Dialer")

    webhook_url = _get_current_webhook_url()

    connection_id = None
    created_app = None
    if auto_setup:
        apps_result = list_call_control_apps()
        if apps_result.get("success") and apps_result.get("apps"):
            connection_id = apps_result["apps"][0]["id"]
            created_app = apps_result["apps"][0]
        else:
            app_result = create_call_control_app(app_name, webhook_url)
            if not app_result.get("success"):
                return jsonify({"error": f"Failed to create voice app: {app_result.get('error')}"}), 400
            connection_id = app_result["app_id"]
            created_app = app_result

    order_result = purchase_number(phone_number, connection_id)
    if not order_result.get("success"):
        return jsonify({"error": f"Failed to purchase number: {order_result.get('error')}"}), 400

    # Record the provisioned number for this user
    pn = ProvisionedNumber(user_id=user_id, phone_number=phone_number, status='active')
    pn.telnyx_order_id = order_result.get("order_id")
    pn.telnyx_connection_id = connection_id
    db.session.add(pn)
    db.session.commit()

    if auto_setup and connection_id and not data.get("skip_assign"):
        import time
        time.sleep(2)
        assign_result = assign_number_to_app(phone_number, connection_id)
        if not assign_result.get("success"):
            logger.warning(f"Number purchased but assignment failed: {assign_result.get('error')}")

    return jsonify({
        "success": True,
        "order": order_result,
        "voice_app": created_app,
        "message": f"Number {phone_number} purchased and configured successfully",
    })


@app.route("/api/numbers/owned", methods=["GET"])
@login_required
def api_numbers_owned():
    """Return only numbers belonging to the current user (strict isolation)."""
    user_id = current_user.id
    user_numbers = ProvisionedNumber.query.filter_by(user_id=user_id).all()
    user_phone_set = {pn.phone_number for pn in user_numbers}

    # If user has provisioned numbers, filter the Telnyx list to only theirs
    result = list_owned_numbers()
    if result.get("success") and user_phone_set:
        filtered = [n for n in result.get("numbers", []) if n.get("phone_number") in user_phone_set]
        result["numbers"] = filtered
        result["total"] = len(filtered)
    elif result.get("success") and not user_phone_set:
        # User has no provisioned numbers — show empty list
        result["numbers"] = []
        result["total"] = 0

    # Include governance info
    active_count = sum(1 for pn in user_numbers if pn.status == 'active')
    result["active_count"] = active_count
    result["can_purchase"] = active_count < 1

    return jsonify(result)


@app.route("/api/request-additional-line", methods=["POST"])
@login_required
def api_request_additional_line():
    """Send a Telegram alert to admin requesting line limit increase. No number is purchased."""
    user_id = current_user.id
    user_email = current_user.email if hasattr(current_user, 'email') else 'Unknown'
    user_name = current_user.profile_name if hasattr(current_user, 'profile_name') else 'Unknown'
    data = request.get_json() or {}
    reason = data.get("reason", "No reason provided")

    active_numbers = ProvisionedNumber.query.filter_by(user_id=user_id, status='active').all()
    active_list = ", ".join([pn.phone_number for pn in active_numbers]) or "None"

    # Send Telegram notification to admin
    import requests as req_lib
    bot_token = os.environ.get("BOT_TOKEN", "").strip()
    admin_chat_id = os.environ.get("ADMIN_CHAT_ID", "").strip()
    if bot_token and admin_chat_id:
        try:
            msg = (
                f"📞 **Additional Line Request**\n\n"
                f"User: {user_name}\n"
                f"Email: {user_email}\n"
                f"User ID: {user_id}\n"
                f"Current Lines: {active_list}\n"
                f"Reason: {reason}\n\n"
                f"Reply /approve_{user_id} to increase their limit."
            )
            req_lib.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": admin_chat_id, "text": msg, "parse_mode": "Markdown"}
            )
        except Exception as e:
            logger.error(f"Telegram request-line alert failed: {e}")

    return jsonify({
        "success": True,
        "message": "Your request has been sent to the admin. You'll be notified when approved."
    })


@app.route("/api/numbers/release", methods=["POST"])
@login_required
def api_numbers_release():
    data = request.get_json() or {}
    phone_number_id = data.get("phone_number_id", "").strip()
    if not phone_number_id:
        return jsonify({"error": "Phone number ID is required"}), 400
    result = release_number(phone_number_id)
    if result.get("success"):
        return jsonify({"success": True, "message": "Number released"})
    return jsonify(result), 400


@app.route("/api/numbers/apps", methods=["GET"])
@login_required
def api_numbers_apps():
    result = list_call_control_apps()
    if result.get("success"):
        return jsonify(result)
    return jsonify(result), 400


@app.route("/api/numbers/assign", methods=["POST"])
@login_required
def api_numbers_assign():
    data = request.get_json() or {}
    phone_number = data.get("phone_number", "").strip()
    connection_id = data.get("connection_id", "").strip()
    if not phone_number or not connection_id:
        return jsonify({"error": "Phone number and connection ID are required"}), 400
    result = assign_number_to_app(phone_number, connection_id)
    if result.get("success"):
        return jsonify(result)
    return jsonify(result), 400


@app.route("/api/numbers/create-app", methods=["POST"])
@login_required
def api_numbers_create_app():
    data = request.get_json() or {}
    app_name = data.get("app_name", "Open Human Dialer").strip()
    webhook_url = data.get("webhook_url", "").strip() or _get_current_webhook_url()
    result = create_call_control_app(app_name, webhook_url)
    if result.get("success"):
        return jsonify(result)
    return jsonify(result), 400


@app.route("/api/numbers/order-status/<order_id>", methods=["GET"])
@login_required
def api_numbers_order_status(order_id):
    result = get_number_order_status(order_id)
    if result.get("success"):
        return jsonify(result)
    return jsonify(result), 400


def _get_current_webhook_url():
    global _detected_base_url
    if _detected_base_url:
        return _detected_base_url.rstrip("/") + "/webhook"
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if base:
        return base + "/webhook"
    return "https://example.com/webhook"


# ---- Automated Line Provisioning ----
@app.route("/api/provision-line", methods=["POST"])
@login_required
def api_provision_line():
    """Automated number provisioning: search, purchase, assign to user."""
    user_id = current_user.id
    existing = ProvisionedNumber.query.filter_by(user_id=user_id, status='active').first()
    if existing:
        return jsonify({"success": True, "status": "ready", "phone_number": existing.phone_number,
                         "message": "Alex already has a local line assigned."})

    pending = ProvisionedNumber.query.filter_by(user_id=user_id, status='provisioning').first()
    if pending:
        return jsonify({"success": True, "status": "provisioning",
                         "message": "A line is currently being provisioned. Please wait..."})

    try:
        search_result = search_available_numbers(country_code="US", number_type="local", limit=5)
        if not search_result.get("success") or not search_result.get("numbers"):
            return jsonify({"success": False, "error": "No local numbers available. Please try again later."}), 400

        chosen = search_result["numbers"][0]
        phone_number = chosen["phone_number"]

        pn = ProvisionedNumber(user_id=user_id, phone_number=phone_number, status='provisioning')
        db.session.add(pn)
        db.session.commit()

        webhook_url = _get_current_webhook_url()
        app_name = f"Alex-{user_id}"
        existing_apps = list_call_control_apps()
        connection_id = None
        if existing_apps.get("success"):
            for a in existing_apps.get("apps", []):
                if a.get("app_name") == app_name:
                    connection_id = a.get("id")
                    break
        if not connection_id:
            app_result = create_call_control_app(app_name, webhook_url)
            if not app_result.get("success"):
                pn.status = 'failed'
                db.session.commit()
                return jsonify({"success": False, "error": "Failed to create call control app."}), 500
            connection_id = app_result["app_id"]

        purchase_result = purchase_number(phone_number, connection_id=connection_id)
        if not purchase_result.get("success"):
            pn.status = 'failed'
            db.session.commit()
            return jsonify({"success": False, "error": purchase_result.get("error", "Failed to purchase number.")}), 500

        pn.telnyx_order_id = purchase_result.get("order_id")
        pn.telnyx_connection_id = connection_id
        pn.status = 'active'
        db.session.commit()

        instance = ensure_user_instance(user_id)
        instance.telnyx_connection_id = connection_id
        db.session.commit()

        logger.info(f"Line provisioned for user {user_id}: {phone_number}")
        return jsonify({"success": True, "status": "ready", "phone_number": phone_number,
                         "message": "Alex is Ready."})

    except Exception as e:
        logger.error(f"Provisioning error for user {user_id}: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": "An unexpected error occurred during provisioning."}), 500


@app.route("/api/provision-status", methods=["GET"])
@login_required
def api_provision_status():
    """Check the current provisioning status for the logged-in user."""
    pn = ProvisionedNumber.query.filter_by(user_id=current_user.id).order_by(ProvisionedNumber.created_at.desc()).first()
    if not pn:
        return jsonify({"provisioned": False, "status": "none"})
    return jsonify({
        "provisioned": pn.status == 'active',
        "status": pn.status,
        "phone_number": pn.phone_number if pn.status == 'active' else None,
    })


# ---- Super Admin Portal ----
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")


def admin_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))
        is_admin = False
        if ADMIN_EMAIL and current_user.email.lower() == ADMIN_EMAIL.lower():
            is_admin = True
        if getattr(current_user, 'role', 'user') == 'admin':
            is_admin = True
        if not is_admin:
            return "Not Found", 404
        return f(*args, **kwargs)
    return decorated


@app.route("/admin")
@admin_required
def admin_panel():
    success_msg = request.args.get("success")
    error_msg = request.args.get("error")
    users = User.query.order_by(User.created_at.desc()).all()
    user_data = []
    for u in users:
        user_data.append({
            "id": u.id,
            "email": u.email,
            "name": u.profile_name or u.email.split("@")[0],
            "role": u.role or "user",
            "active": getattr(u, 'is_active_account', True),
            "created_at": u.created_at.strftime("%b %d, %Y") if u.created_at else "N/A",
        })
    pending_invites = Invitation.query.filter_by(used=False).order_by(Invitation.created_at.desc()).all()
    return render_template("admin.html", users=user_data, pending_invites=pending_invites,
                           success_msg=success_msg, error_msg=error_msg)


@app.route("/admin/invite", methods=["POST"])
@admin_required
def admin_invite():
    email = request.form.get("email", "").strip().lower()
    grant_free = request.form.get("grant_free_access") == "1"
    if not email:
        return redirect(url_for("admin_panel", error="Email is required"))
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return redirect(url_for("admin_panel", error=f"User {email} already has an account"))
    existing_invite = Invitation.query.filter_by(email=email, used=False).first()
    if existing_invite:
        return redirect(url_for("admin_panel", error=f"An invite is already pending for {email}"))
    invitation = Invitation(
        email=email,
        invited_by=current_user.id,
        grant_free_access=grant_free,
    )
    db.session.add(invitation)
    db.session.commit()
    from invite_email import send_invite_email_async
    send_invite_email_async(email, invitation.token, grant_free)
    logger.info(f"Admin invited {email} (free_access={grant_free})")
    return redirect(url_for("admin_panel", success=f"Invite sent to {email}"))


@app.route("/admin/revoke", methods=["POST"])
@admin_required
def admin_revoke():
    user_id = request.form.get("user_id", type=int)
    target = User.query.get(user_id)
    if not target:
        return redirect(url_for("admin_panel", error="User not found"))
    if target.role == "admin":
        return redirect(url_for("admin_panel", error="Cannot revoke admin access"))
    target.is_active_account = False
    db.session.commit()
    logger.info(f"Admin revoked access for {target.email}")
    return redirect(url_for("admin_panel", success=f"Access revoked for {target.email}"))


@app.route("/admin/restore", methods=["POST"])
@admin_required
def admin_restore():
    user_id = request.form.get("user_id", type=int)
    target = User.query.get(user_id)
    if not target:
        return redirect(url_for("admin_panel", error="User not found"))
    target.is_active_account = True
    db.session.commit()
    logger.info(f"Admin restored access for {target.email}")
    return redirect(url_for("admin_panel", success=f"Access restored for {target.email}"))


@app.route("/setup-account", methods=["GET", "POST"])
def setup_account():
    token = request.args.get("token") or request.form.get("token", "")
    if not token:
        return redirect(url_for("login"))
    invitation = Invitation.query.filter_by(token=token, used=False).first()
    if not invitation:
        return render_template("setup_account.html", token=token, email="",
                               error="This invitation link is invalid or has already been used.",
                               grant_free_access=False)
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not username or not password:
            error = "Username and password are required"
        elif len(password) < 8:
            error = "Password must be at least 8 characters"
        elif password != confirm:
            error = "Passwords do not match"
        else:
            existing = User.query.filter_by(email=invitation.email).first()
            if existing:
                error = "An account with this email already exists. Please log in instead."
            else:
                user = User(
                    email=invitation.email,
                    profile_name=username,
                    role='user',
                    credit_balance=Decimal("5.00"),
                )
                user.set_password(password)
                db.session.add(user)
                invitation.used = True
                invitation.used_at = datetime.utcnow()
                db.session.commit()
                ensure_user_instance(user.id)
                login_user(user)
                session.permanent = True
                logger.info(f"New user created via invite: {invitation.email}")
                return redirect(url_for("profile_setup"))
    return render_template("setup_account.html", token=token, email=invitation.email,
                           error=error, grant_free_access=invitation.grant_free_access)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    error = None
    success = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            error = "Please enter your email address"
        else:
            user = User.query.filter_by(email=email).first()
            if user:
                import uuid
                token = str(uuid.uuid4())
                user.reset_token = token
                user.reset_token_expires = datetime.utcnow() + _td(hours=1)
                db.session.commit()
                from invite_email import send_password_reset_async
                send_password_reset_async(email, token)
                logger.info(f"Password reset requested for {email}")
            success = "If an account exists with that email, we've sent a reset link."
    return render_template("forgot_password.html", error=error, success=success)


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    token = request.args.get("token") or request.form.get("token", "")
    if not token:
        return redirect(url_for("forgot_password"))
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        return render_template("reset_password.html", token=token,
                               error="This reset link is invalid or has expired. Please request a new one.")
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not password or len(password) < 8:
            error = "Password must be at least 8 characters"
        elif password != confirm:
            error = "Passwords do not match"
        else:
            user.set_password(password)
            user.reset_token = None
            user.reset_token_expires = None
            db.session.commit()
            logger.info(f"Password reset completed for {user.email}")
            return redirect(url_for("login"))
    return render_template("reset_password.html", token=token, error=error)


@app.route("/super-admin")
@admin_required
def super_admin():
    users = User.query.order_by(User.created_at.desc()).all()
    user_data = []
    for u in users:
        from storage import _load_call_history, get_contacts
        leads_count = len(get_contacts(user_id=u.id))
        call_count = len(_load_call_history(user_id=u.id))
        active_number = ProvisionedNumber.query.filter_by(user_id=u.id, status='active').first()
        user_data.append({
            "id": u.id,
            "email": u.email,
            "name": u.profile_name or u.email.split("@")[0],
            "leads": leads_count,
            "calls": call_count,
            "active_number": active_number.phone_number if active_number else "None",
            "created_at": u.created_at.strftime("%b %d, %Y") if u.created_at else "N/A",
        })
    return render_template("super_admin.html", users=user_data)


@app.route("/api/admin/user-activity/<int:uid>")
@admin_required
def api_admin_user_activity(uid):
    target_user = User.query.get(uid)
    if not target_user:
        return jsonify({"error": "User not found"}), 404
    from storage import _load_call_history, get_contacts
    calls = _load_call_history(user_id=uid)
    contacts = get_contacts(user_id=uid)
    numbers = ProvisionedNumber.query.filter_by(user_id=uid).all()
    return jsonify({
        "user": {"id": uid, "email": target_user.email, "name": target_user.profile_name or ""},
        "total_calls": len(calls),
        "total_leads": len(contacts),
        "numbers": [{"phone": n.phone_number, "status": n.status} for n in numbers],
        "recent_calls": calls[-20:] if calls else [],
    })


# ---- Startup initialization (runs for both direct and gunicorn) ----
def _init_app():
    print("=" * 60)
    print("  VOICEMAIL DROP SYSTEM - Starting Up")
    print("=" * 60)
    print(f"  Dashboard: http://0.0.0.0:5000")
    print(f"  Webhook URL: <PUBLIC_BASE_URL>/webhook")
    print("=" * 60)
    conn_id = validate_connection_id()
    print(f"  Using Connection ID: {conn_id}")
    print("=" * 60)
    if auto_configure_outbound():
        print("  Outbound voice profile: Configured")
    else:
        print("  Outbound voice profile: Not configured (outbound calls may fail)")
    print("=" * 60)
    start_scheduler()

_init_app()

# ---- Main Entry Point ----
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
