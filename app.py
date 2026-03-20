"""
app.py - Main Flask application for the Voicemail Drop System.
Handles web dashboard, file uploads, webhook processing, and campaign control.
"""

import os
import csv
import io
import re
import json
import time
import logging
import threading
import functools
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from dotenv import load_dotenv
load_dotenv(override=False)

import queue as _queue_mod
from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for, flash
from flask_sock import Sock
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, current_user, login_required as flask_login_required
import html as html_module

from storage import (
    set_campaign,
    stop_campaign,
    pause_campaign,
    resume_campaign,
    is_campaign_active,
    is_campaign_paused,
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
    get_custom_variables,
    save_custom_variables,
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
    claim_call_action,
    set_quick_call_status,
    get_quick_call_statuses,
    get_quick_call_status,
    count_active_calls,
)
from telnyx_client import (
    transfer_call, play_audio, stop_playback, hangup_call, make_call, validate_connection_id,
    set_webhook_base_url, start_transcription, start_recording, start_gather,
    search_available_numbers, purchase_number, create_call_control_app,
    assign_number_to_app, list_owned_numbers, release_number,
    list_call_control_apps, get_number_order_status,
    lookup_number, lookup_numbers_batch,
    auto_configure_outbound,
    fork_start, fork_stop,
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
os.makedirs("uploads/gatekeeper", exist_ok=True)

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
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import timedelta as _td

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

_secret = os.environ.get("SESSION_SECRET")
if not _secret:
    import secrets as _secrets
    _secret = _secrets.token_hex(32)
    logger.warning("SESSION_SECRET not set — generated a temporary key. Sessions will NOT survive restarts. Set SESSION_SECRET in your environment.")
app.secret_key = _secret

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# ---- WebSocket support (flask-sock) ----
sock = Sock(app)

# ---- Real-time call audio relay ----
_audio_subs_lock = threading.Lock()
_audio_subscribers = {}  # call_id -> list of queue.Queue


def _audio_register(call_id):
    """Subscribe a browser listener to a call's audio stream."""
    q = _queue_mod.Queue(maxsize=1000)
    with _audio_subs_lock:
        _audio_subscribers.setdefault(call_id, []).append(q)
    return q


def _audio_unregister(call_id, q):
    """Unsubscribe a browser listener."""
    with _audio_subs_lock:
        subs = _audio_subscribers.get(call_id, [])
        try:
            subs.remove(q)
        except ValueError:
            pass
        if not subs:
            _audio_subscribers.pop(call_id, None)


def _audio_broadcast(call_id, data):
    """Broadcast raw PCM bytes to all browser subscribers for a call."""
    with _audio_subs_lock:
        subs = list(_audio_subscribers.get(call_id, []))
    for q in subs:
        try:
            q.put_nowait(data)
        except _queue_mod.Full:
            pass


def _ulaw2lin(data):
    """Convert G.711 µ-law (PCMU) bytes to 16-bit signed linear PCM bytes (little-endian)."""
    import struct
    result = bytearray(len(data) * 2)
    idx = 0
    for byte in data:
        byte = (~byte) & 0xFF
        sign = byte & 0x80
        exponent = (byte >> 4) & 0x07
        mantissa = byte & 0x0F
        sample = ((mantissa << 3) | 0x84) << exponent
        sample -= 132
        if sign:
            sample = -sample
        sample = max(-32768, min(32767, sample))
        struct.pack_into('<h', result, idx, sample)
        idx += 2
    return bytes(result)


_is_dev = os.environ.get("FLASK_ENV") == "development" or os.environ.get("INSECURE_COOKIES") == "1"
app.config["PERMANENT_SESSION_LIFETIME"] = _td(days=7)
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = not _is_dev
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"
app.config["REMEMBER_COOKIE_SECURE"] = not _is_dev
app.config["REMEMBER_COOKIE_DURATION"] = _td(days=7)

# ---- Database & Auth Setup ----
_db_url = os.environ.get("DATABASE_URL", "sqlite:///app.db")
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = _db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 300}

from models import db, User, UserInstance, ProvisionedNumber, UserAppData, Invitation, AppConfig, NumberSwapLog, UserFeature, ensure_user_instance, init_db
import base64
import requests
init_db(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    if user and not getattr(user, 'is_active_account', True):
        return None
    return user

from google_auth import google_oauth, google_oauth_available
app.register_blueprint(google_oauth)
from humana_voice.routes import humana_voice_bp
from gatekeeper import navigator as gk_navigator
app.register_blueprint(humana_voice_bp)

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
    "starter": {"amount": Decimal("99.00"), "instances": 1, "included_numbers": 1, "max_numbers": 5},
    "business": {"amount": Decimal("399.00"), "instances": 5, "included_numbers": 3, "max_numbers": 20},
}
PLAN_NUMBER_LIMITS = {
    "starter":  {"included": 1, "max": 5},
    "business": {"included": 3, "max": 20},
}
EXTRA_NUMBER_MONTHLY_COST = Decimal("3.00")
DAILY_DIAL_CAP = 150
QUICK_SWAP_COST = Decimal("2.00")
FREE_SWAPS_PER_QUARTER = 1
CALL_COST = Decimal("0.10")
MIN_REFILL = Decimal("10.00")
DEFAULT_REFILL = Decimal("25.00")

_login_attempts = {}
_LOGIN_MAX_ATTEMPTS = 10
_LOGIN_WINDOW_SECS = 300


def _login_rate_limit_check(ip):
    now = time.time()
    entry = _login_attempts.get(ip)
    if entry:
        count, first_time = entry
        if now - first_time > _LOGIN_WINDOW_SECS:
            _login_attempts[ip] = (1, now)
            return True
        if count >= _LOGIN_MAX_ATTEMPTS:
            return False
        _login_attempts[ip] = (count + 1, first_time)
    else:
        _login_attempts[ip] = (1, now)
    return True


def _login_rate_limit_reset(ip):
    _login_attempts.pop(ip, None)


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


PLAN_MAX_CONCURRENT_LINES = {
    "starter": 5,
    "business": 15,
}

# ---- Feature Flag System ----

FEATURE_DEFINITIONS = {
    "live_transfer":      {"label": "Live Call Transfer",           "desc": "Bridge answered calls directly to your phone in real time"},
    "pvm":                {"label": "Personalized Voicemails",      "desc": "AI generates a unique voicemail using each prospect's name/company"},
    "gatekeeper":         {"label": "Gatekeeper Navigator",         "desc": "AI navigates IVRs and receptionists to reach decision-makers"},
    "recording":          {"label": "Call Recording & Transcription","desc": "Record every call and generate searchable transcripts"},
    "multi_campaign":     {"label": "Multiple Campaigns",           "desc": "Run more than one calling campaign simultaneously"},
    "analytics_advanced": {"label": "Advanced Analytics",           "desc": "Detailed call scoring, export, and trend reporting"},
    "voice_cloning":      {"label": "Voice Cloning",                "desc": "Clone your own voice for the AI agent ($19/mo flat fee)"},
    "api_access":         {"label": "API / Webhook Access",         "desc": "Programmatic access to campaigns and call data"},
    "white_label":        {"label": "White-Label Branding",         "desc": "Remove Open Humana branding and use your own"},
}

PLAN_FEATURES = {
    "starter":  ["live_transfer", "pvm", "gatekeeper"],
    "business": ["live_transfer", "pvm", "gatekeeper", "recording", "multi_campaign", "analytics_advanced", "voice_cloning"],
    "agency":   ["live_transfer", "pvm", "gatekeeper", "recording", "multi_campaign", "analytics_advanced", "voice_cloning", "api_access", "white_label"],
}


def _set_feature(user_id, feature_key, enabled, granted_by=None, note=None):
    """Upsert a single feature flag for a user."""
    try:
        rec = UserFeature.query.filter_by(user_id=user_id, feature_key=feature_key).first()
        if rec:
            rec.enabled = enabled
            rec.updated_at = datetime.utcnow()
            if granted_by is not None:
                rec.granted_by = granted_by
            if note is not None:
                rec.note = note
        else:
            rec = UserFeature(
                user_id=user_id,
                feature_key=feature_key,
                enabled=enabled,
                granted_by=granted_by,
                note=note,
            )
            db.session.add(rec)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to set feature {feature_key} for user {user_id}: {e}")


def _provision_plan_features(user_id, plan, granted_by=None):
    """Set all features for a plan, leaving any admin-granted extras intact."""
    plan = (plan or "").lower()
    features_to_enable = set(PLAN_FEATURES.get(plan, []))
    all_keys = set(FEATURE_DEFINITIONS.keys())
    for key in all_keys:
        _set_feature(user_id, key, key in features_to_enable, granted_by=granted_by, note=f"auto:{plan}")
    logger.info(f"Provisioned {plan} features for user {user_id}: {features_to_enable}")


def _get_user_features(user_id):
    """Return a dict of {feature_key: bool} for a user. Missing keys default to False."""
    rows = UserFeature.query.filter_by(user_id=user_id).all()
    result = {key: False for key in FEATURE_DEFINITIONS}
    for row in rows:
        result[row.feature_key] = row.enabled
    return result


def _has_feature(user_id, feature_key):
    """Return True if the user has access to the given feature."""
    rec = UserFeature.query.filter_by(user_id=user_id, feature_key=feature_key).first()
    return bool(rec and rec.enabled)


def _get_user_plan(user_id):
    """Return the user's current plan key ('starter', 'business', or None)."""
    try:
        rec = UserAppData.query.filter_by(user_id=user_id, data_key="active_plan").first()
        if rec:
            val = json.loads(rec.data_value)
            return (val.get("plan") or "").lower() or None
    except Exception:
        pass
    return None


def _get_number_limits(user_id):
    """Return {included, max} number limits for a user based on plan."""
    plan = _get_user_plan(user_id)
    return PLAN_NUMBER_LIMITS.get(plan, {"included": 1, "max": 3})


def _compute_number_health(answer_rate_7d, calls_7d):
    """Return health status string: 'healthy', 'at_risk', 'flagged', or 'new'.

    Logic:
        new       — fewer than 5 calls in 7 days (not enough data)
        flagged   — answer rate < 5% with ≥20 calls (likely spam-flagged)
        at_risk   — answer rate < 15% with ≥10 calls (degrading)
        healthy   — otherwise
    """
    if calls_7d is None or calls_7d < 5:
        return "new"
    if answer_rate_7d is None:
        return "new"
    if answer_rate_7d < 5 and calls_7d >= 20:
        return "flagged"
    if answer_rate_7d < 15 and calls_7d >= 10:
        return "at_risk"
    return "healthy"


def _get_quarterly_swap_key():
    """Return a UserAppData key string for the current quarter."""
    now = datetime.utcnow()
    quarter = (now.month - 1) // 3 + 1
    return f"swap_count_{now.year}_Q{quarter}"


def _get_quarterly_swap_count(user_id):
    """Return the number of Quick Swaps used this quarter."""
    try:
        key = _get_quarterly_swap_key()
        rec = UserAppData.query.filter_by(user_id=user_id, data_key=key).first()
        if rec:
            return int(json.loads(rec.data_value) or 0)
    except Exception:
        pass
    return 0


def _increment_swap_count(user_id):
    """Increment the quarterly swap counter for a user."""
    try:
        key = _get_quarterly_swap_key()
        rec = UserAppData.query.filter_by(user_id=user_id, data_key=key).first()
        if rec:
            current = int(json.loads(rec.data_value) or 0)
            rec.data_value = json.dumps(current + 1)
        else:
            rec = UserAppData(user_id=user_id, data_key=key, data_value=json.dumps(1))
            db.session.add(rec)
        db.session.commit()
    except Exception as e:
        logger.warning(f"Could not increment swap count for user {user_id}: {e}")


def _set_max_concurrent_lines(user_id, limit):
    """Store the user's max concurrent lines in UserAppData."""
    try:
        if not user_id:
            return None
        existing = UserAppData.query.filter_by(user_id=user_id, data_key="max_concurrent_lines").first()
        payload = json.dumps({"limit": int(limit)})
        if existing:
            existing.data_value = payload
        else:
            rec = UserAppData(user_id=user_id, data_key="max_concurrent_lines", data_value=payload)
            db.session.add(rec)
        db.session.commit()
        return limit
    except Exception as e:
        logger.error(f"Failed to set max_concurrent_lines for user {user_id}: {e}")
        return None


def _upsert_user_app_data(user_id, data_key, data_value):
    """Generic upsert for UserAppData key-value pairs."""
    try:
        existing = UserAppData.query.filter_by(user_id=user_id, data_key=data_key).first()
        if existing:
            existing.data_value = data_value
            existing.updated_at = datetime.utcnow()
        else:
            rec = UserAppData(user_id=user_id, data_key=data_key, data_value=data_value)
            db.session.add(rec)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to upsert app data {data_key} for user {user_id}: {e}")


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
                    max_lines = PLAN_MAX_CONCURRENT_LINES.get(plan, 5)
                    _set_max_concurrent_lines(target_user_id, max_lines)
                    credited = _credit_user(target_user_id, amount_val)
                    # Auto-provision feature flags for the purchased plan
                    try:
                        _provision_plan_features(target_user_id, plan)
                        # Record active_plan in UserAppData
                        _upsert_user_app_data(target_user_id, "active_plan", json.dumps({"plan": plan}))
                    except Exception as fe:
                        logger.error(f"Feature provisioning failed for user {target_user_id}: {fe}")
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
    from humana_voice import fish_client as _fc
    fish_ok = _fc.is_configured()
    fish_source = _fc.get_key_source()
    return jsonify({
        "status": "ok",
        "service": "Open Humana",
        "fish_audio_configured": fish_ok,
        "fish_audio_key_source": fish_source,
    }), 200




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
        data = request.get_json(silent=True) or {}
        if not data:
            data = {
                "name": request.form.get("name", ""),
                "email": request.form.get("email", ""),
                "phone": request.form.get("phone", ""),
                "company": request.form.get("company", ""),
                "team_size": request.form.get("team_size", ""),
            }
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


@app.route("/api/demo", methods=["POST"])
def api_demo():
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            data = {
                "name": request.form.get("name", ""),
                "email": request.form.get("email", ""),
                "phone": request.form.get("phone", ""),
                "company": request.form.get("company", ""),
            }
        name_raw = data.get("name", "").strip()
        email_raw = data.get("email", "").strip()
        phone = data.get("phone", "").strip()
        company = data.get("company", "").strip()

        if not name_raw or not email_raw or not phone:
            return jsonify({"success": False, "error": "Name, email, and phone are required"}), 400

        name = html_module.escape(name_raw)
        email = html_module.escape(email_raw)
        phone = html_module.escape(phone)
        company = html_module.escape(company)

        now = datetime.now().strftime("%B %d, %Y at %I:%M %p")

        admin_html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f7;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f7;padding:40px 20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

<tr><td style="background:linear-gradient(135deg,#065f46 0%,#059669 100%);padding:36px 40px;text-align:center;">
  <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:800;letter-spacing:-0.5px;">&#127911; Demo Request Received!</h1>
  <p style="margin:8px 0 0;color:rgba(255,255,255,0.7);font-size:14px;">A prospect wants to see Alex in action</p>
</td></tr>

<tr><td style="padding:36px 40px;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;overflow:hidden;">
    <tr>
      <td style="padding:20px 24px;border-bottom:1px solid #d1fae5;">
        <span style="display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#059669;margin-bottom:4px;">Full Name</span>
        <span style="font-size:16px;font-weight:700;color:#111827;">{name}</span>
      </td>
    </tr>
    <tr>
      <td style="padding:20px 24px;border-bottom:1px solid #d1fae5;">
        <span style="display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#059669;margin-bottom:4px;">Email Address</span>
        <a href="mailto:{email}" style="font-size:16px;font-weight:600;color:#065f46;text-decoration:none;">{email}</a>
      </td>
    </tr>
    <tr>
      <td style="padding:20px 24px;border-bottom:1px solid #d1fae5;">
        <span style="display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#059669;margin-bottom:4px;">Phone Number</span>
        <a href="tel:{phone}" style="font-size:16px;font-weight:600;color:#065f46;text-decoration:none;">{phone}</a>
      </td>
    </tr>
    <tr>
      <td style="padding:20px 24px;">
        <span style="display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#059669;margin-bottom:4px;">Company / Industry</span>
        <span style="font-size:16px;font-weight:600;color:#111827;">{company or 'Not provided'}</span>
      </td>
    </tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:28px;">
    <tr>
      <td style="background:#fef3c7;border:1px solid #fde68a;border-radius:10px;padding:16px 20px;">
        <p style="margin:0;font-size:13px;color:#92400e;line-height:1.6;">
          <strong>&#9889; Action Required:</strong> This prospect requested a live demo on {now}. Reach out within the next 5 minutes for the highest conversion rate.
        </p>
      </td>
    </tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
    <tr>
      <td align="center">
        <a href="mailto:{email}" style="display:inline-block;padding:14px 36px;background:#059669;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:700;font-size:14px;">Reply to {name.split()[0] if name else 'Prospect'} Now</a>
      </td>
    </tr>
  </table>
</td></tr>

<tr><td style="background:#f8f9fa;padding:24px 40px;text-align:center;border-top:1px solid #e5e7eb;">
  <p style="margin:0;font-size:12px;color:#9ca3af;">This demo request was captured from your Open Humana landing page.<br>&#169; 2026 Open Humana &mdash; Your Digital Employee Agency</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>
"""

        text_body = f"""
DEMO REQUEST RECEIVED - {now}

Name: {name}
Email: {email}
Phone: {phone}
Company/Industry: {company or 'Not provided'}

ACTION: Reach out within 5 minutes for highest conversion.
"""

        from gmail_client import send_email
        import threading

        def _send_admin_demo_email():
            try:
                result = send_email(
                    to_email=os.environ.get("ADMIN_EMAIL", "openhumana@gmail.com"),
                    subject=f"NEW DEMO REQUEST: {name_raw or 'Unknown'}",
                    html_body=admin_html,
                    text_body=text_body,
                )
                if result:
                    logger.info(f"Demo request emailed: {name} ({email}, {phone})")
                else:
                    logger.error(f"Demo captured but admin email failed: {name} ({email})")
            except Exception as e:
                logger.exception(f"Background admin demo email failed for {email}: {e}")

        threading.Thread(target=_send_admin_demo_email, daemon=True).start()

        from invite_email import send_demo_confirmation_async
        send_demo_confirmation_async(email_raw, name_raw)

        def _send_telegram_demo_alert():
            try:
                bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
                chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
                if not bot_token or not chat_id:
                    return
                msg = (
                    f"🎯 *Demo Request Received*\n\n"
                    f"*Name:* {name_raw}\n"
                    f"*Email:* {email_raw}\n"
                    f"*Phone:* {phone}\n"
                    f"*Company:* {company or 'Not provided'}\n"
                    f"*Time:* {now}"
                )
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
                    timeout=10,
                )
                logger.info(f"Telegram demo alert sent for {name_raw}")
            except Exception as e:
                logger.error(f"Telegram demo alert failed: {e}")

        threading.Thread(target=_send_telegram_demo_alert, daemon=True).start()

        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"Demo capture error: {e}")
        return jsonify({"success": False, "error": "Server error"}), 500


# ---- Login Route ----
@app.route("/login", methods=["GET", "POST"])
def login():
    _detect_and_set_base_url()
    show_admin = bool(request.args.get("_oh"))
    if current_user.is_authenticated:
        if show_admin:
            logout_user()
            session.clear()
        else:
            return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        wants_json = "application/json" in request.headers.get("Accept", "")
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
        if not _login_rate_limit_check(client_ip):
            if wants_json:
                return jsonify({"success": False, "error": "Too many login attempts. Please wait 5 minutes."}), 429
            error = "Too many login attempts. Please wait 5 minutes before trying again."
            return render_template("login.html", error=error, show_admin=show_admin), 429
        try:
            login_mode = request.form.get("login_mode", "user")
            if login_mode in ("admin", "super_admin"):
                show_admin = True
            if login_mode in ("admin", "super_admin") and APP_PASSWORD:
                app_password = request.form.get("app_password", "").strip()
                logger.info(f"Admin login attempt (password length: {len(app_password)}, expected length: {len(APP_PASSWORD)})")
                if app_password == APP_PASSWORD:
                    admin = User.query.filter_by(email="admin@openhuman.local").first()
                    if not admin:
                        admin = User(email="admin@openhuman.local", profile_name="Admin", role='admin')
                        admin.set_password(APP_PASSWORD)
                        db.session.add(admin)
                        db.session.commit()
                        logger.info("Admin account auto-created via APP_PASSWORD login")
                    elif admin.role != 'admin':
                        admin.role = 'admin'
                        db.session.commit()
                    _login_rate_limit_reset(client_ip)
                    login_user(admin, remember=True)
                    session.permanent = True
                    redirect_target = url_for("super_admin") if login_mode == "super_admin" else url_for("dashboard")
                    logger.info(f"Admin successfully authenticated, redirecting to {redirect_target}")
                    if wants_json:
                        return jsonify({"success": True, "redirect": redirect_target})
                    return redirect(redirect_target)
                else:
                    logger.warning(f"Admin login failed - password mismatch")
                    if wants_json:
                        return jsonify({"success": False, "error": "Invalid admin password"}), 401
                    error = "Invalid admin password"
            else:
                email = request.form.get("email", "").strip().lower()
                password = request.form.get("password", "")
                if not email or not password:
                    if wants_json:
                        return jsonify({"success": False, "error": "Please enter email and password"}), 400
                    error = "Please enter email and password"
                else:
                    authenticated = False
                    user = User.query.filter_by(email=email).first()
                    if not user:
                        if wants_json:
                            return jsonify({"success": False, "error": "No account found. Access is by invitation only."}), 401
                        error = "No account found. Access is by invitation only."
                    elif not getattr(user, 'is_active_account', True):
                        if wants_json:
                            return jsonify({"success": False, "error": "Your account has been deactivated. Please contact the administrator."}), 403
                        error = "Your account has been deactivated. Please contact the administrator."
                    else:
                        if supabase_available:
                            result, err = supabase_sign_in(email, password)
                            if result:
                                if not user.supabase_id:
                                    user.supabase_id = result["user_id"]
                                    db.session.commit()
                                authenticated = True
                        if not authenticated and user.check_password(password):
                            authenticated = True
                        if authenticated:
                            _login_rate_limit_reset(client_ip)
                            login_user(user)
                            session.permanent = True
                            if wants_json:
                                return jsonify({"success": True, "redirect": url_for("dashboard")})
                            return redirect(url_for("dashboard"))
                        else:
                            if wants_json:
                                return jsonify({"success": False, "error": "Invalid email or password"}), 401
                            error = "Invalid email or password"
        except Exception as e:
            logger.exception(f"Login POST handler crashed: {e}")
            if wants_json:
                return jsonify({"success": False, "error": "Server error, please try again."}), 500
            error = "Server error, please try again."
    login_mode_post = request.form.get("login_mode", "") if request.method == "POST" else ""
    return render_template("login.html", error=error, google_oauth=google_oauth_available, app_password_set=bool(APP_PASSWORD), show_admin=show_admin, login_mode_post=login_mode_post)


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
    session.clear()
    next_url = request.args.get("next")
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
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
    domains = os.environ.get("REPLIT_DOMAINS", "")
    if domains:
        domain = domains.split(",")[0].strip()
        if domain:
            _detected_base_url = f"https://{domain}"
            set_webhook_base_url(_detected_base_url)
            logger.info(f"Using REPLIT_DOMAINS for base URL: {_detected_base_url}")
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


# ---- Dashboard Route ----
@app.route("/dashboard")
@login_required
def dashboard():
    """Serve the main dashboard page (requires authentication)."""
    _detect_and_set_base_url()
    user_default_number = None
    try:
        user_pn = ProvisionedNumber.query.filter_by(user_id=current_user.id, status="active").first()
        if user_pn:
            user_default_number = user_pn.phone_number
    except Exception:
        pass
    secure_from = user_default_number or os.environ.get("TELNYX_FROM_NUMBER", "Not set")
    user_data = current_user.to_dict() if current_user.is_authenticated else {}
    is_admin = getattr(current_user, 'role', 'user') == 'admin'
    user_plan = _get_user_plan(current_user.id) or "none"
    user_features = _get_user_features(current_user.id)
    return render_template(
        "index.html",
        secure_from=secure_from,
        user=user_data,
        processor_id=PAYPAL_CLIENT_ID,
        is_admin=is_admin,
        user_plan=user_plan,
        user_features=user_features,
    )


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


@app.route("/audio/gatekeeper/<filename>")
def serve_gatekeeper_audio(filename):
    """Serve gatekeeper navigator TTS audio (no auth - Telnyx needs direct access)."""
    gk_dir = os.path.join(UPLOAD_FOLDER, "gatekeeper")
    response = send_from_directory(gk_dir, filename)
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
    # ---- Pre-flight: reject if calling service is not configured ----
    if not os.environ.get("TELNYX_API_KEY", "").strip():
        return jsonify({"error": "Calling service is not configured. Please add your Telnyx API key in Settings before launching a campaign."}), 400

    # ---- Pre-flight: reject if a campaign is already running ----
    if is_campaign_active(user_id=current_user.id):
        return jsonify({"error": "A campaign is already running. Stop it before starting a new one."}), 400

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

    if not campaign_from_number:
        try:
            user_pn = ProvisionedNumber.query.filter_by(user_id=current_user.id, status="active").first()
            if user_pn:
                campaign_from_number = user_pn.phone_number
        except Exception:
            pass

    gk_enabled = request.form.get("gatekeeper_navigator_enabled") == "1"
    gk_prospect_name = request.form.get("prospect_name", "").strip()
    gk_prospect_company = request.form.get("prospect_company", "").strip()
    gk_voice_id = request.form.get("navigator_voice_id", "").strip() or None
    gk_persona = request.form.get("navigator_persona", "").strip()
    gk_knowledge_base = request.form.get("navigator_knowledge_base", "").strip()
    if gk_persona or gk_knowledge_base:
        try:
            if gk_persona:
                current_user.navigator_persona = gk_persona
            if gk_knowledge_base:
                current_user.navigator_knowledge_base = gk_knowledge_base
            db.session.commit()
        except Exception:
            db.session.rollback()

    # ---- Check concurrent line limit ----
    user_id_for_campaign = current_user.id
    try:
        max_lines_rec = UserAppData.query.filter_by(user_id=user_id_for_campaign, data_key="max_concurrent_lines").first()
        user_max_lines = int(json.loads(max_lines_rec.data_value).get("limit", 5)) if max_lines_rec else 5
    except Exception:
        user_max_lines = 5
    active_now = count_active_calls(user_id=user_id_for_campaign)
    if active_now >= user_max_lines:
        return jsonify({
            "error": f"Line limit reached: {active_now} of {user_max_lines} lines are currently active. Wait for calls to complete or upgrade your plan.",
            "active_lines": active_now,
            "max_lines": user_max_lines,
        }), 429
    if dial_mode == "simultaneous" and batch_size > user_max_lines:
        batch_size = user_max_lines
        logger.info(f"Capping batch_size to user max_concurrent_lines={user_max_lines}")

    # ---- Start the campaign ----
    logger.info(f"Starting campaign: {len(numbers)} numbers, transfer to {transfer_number}, mode={dial_mode}, batch={batch_size}, delay={dial_delay}min, vm_type={voicemail_type}, from={campaign_from_number or 'default'}, gk={gk_enabled}")
    set_campaign(audio_url, transfer_number, numbers, dial_mode=dial_mode, batch_size=batch_size, dial_delay=dial_delay, from_number=campaign_from_number, user_id=current_user.id,
                 gatekeeper_navigator_enabled=gk_enabled, prospect_name=gk_prospect_name,
                 prospect_company=gk_prospect_company, navigator_voice_id=gk_voice_id,
                 navigator_knowledge_base=gk_knowledge_base)

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

    try:
        ml_rec = UserAppData.query.filter_by(user_id=current_user.id, data_key="max_concurrent_lines").first()
        _test_max_lines = int(json.loads(ml_rec.data_value).get("limit", 5)) if ml_rec else 5
    except Exception:
        _test_max_lines = 5
    _test_active = count_active_calls(user_id=current_user.id)
    if _test_active >= _test_max_lines:
        return jsonify({"error": f"Line limit reached: {_test_active} of {_test_max_lines} lines are currently active."}), 429

    if not from_number:
        from call_manager import _get_lru_from_number as _lru_num
        from_number = _lru_num(current_user.id, fallback=None) or os.environ.get("TELNYX_FROM_NUMBER", "")
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


# ---- Pause Campaign ----
@app.route("/pause", methods=["POST"])
@login_required
def pause():
    """Pause the current campaign. No new calls will be placed until resumed."""
    pause_campaign(user_id=current_user.id)
    logger.info("Campaign paused by user")
    return jsonify({"message": "Campaign paused"})


# ---- Resume Campaign ----
@app.route("/resume", methods=["POST"])
@login_required
def resume():
    """Resume a paused campaign."""
    resume_campaign(user_id=current_user.id)
    logger.info("Campaign resumed by user")
    return jsonify({"message": "Campaign resumed"})


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
        "paused": camp.get("paused", False),
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


@app.route("/api/fish-audio-key", methods=["GET"])
@login_required
def get_fish_audio_key():
    from humana_voice import fish_client as _fc
    db_key = AppConfig.get("fish_audio_api_key", "")
    env_source = _fc.get_key_source()
    is_db = env_source == "database_config"
    return jsonify({
        "configured": _fc.is_configured(),
        "source": env_source,
        "has_db_key": bool(db_key),
        "masked_key": ("*" * (len(db_key) - 4) + db_key[-4:]) if len(db_key) > 4 else ("*" * len(db_key)),
    })


@app.route("/api/fish-audio-key", methods=["POST"])
@login_required
def set_fish_audio_key():
    if getattr(current_user, "role", "user") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    data = request.get_json() or {}
    key = (data.get("api_key") or "").strip().strip('"').strip("'").strip()
    if not key:
        AppConfig.set("fish_audio_api_key", "")
        logger.info("Fish Audio API key cleared from database")
        return jsonify({"message": "Fish Audio API key cleared"})
    AppConfig.set("fish_audio_api_key", key)
    logger.info(f"Fish Audio API key saved to database (length={len(key)})")
    return jsonify({"message": "Fish Audio API key saved successfully", "length": len(key)})


# ── Real-time Call Audio Monitoring ────────────────────────────────────────────

@sock.route("/ws/fork")
def ws_fork(ws):
    """Telnyx connects here and streams forked raw PCMU audio."""
    call_id = request.args.get("call_id", "").strip()
    if not call_id:
        return
    logger.info(f"[fork] Telnyx audio fork connected for call {call_id}")
    try:
        while True:
            data = ws.receive()
            if data is None:
                break
            if isinstance(data, bytes) and data:
                pcm = _ulaw2lin(data)
                _audio_broadcast(call_id, pcm)
    except Exception as e:
        logger.debug(f"[fork] WebSocket closed for call {call_id}: {e}")
    finally:
        logger.info(f"[fork] Telnyx audio fork disconnected for call {call_id}")


@sock.route("/ws/listen/<call_id>")
def ws_listen(ws, call_id):
    """Browser connects here to receive 16-bit PCM audio for a call."""
    if not current_user.is_authenticated:
        return
    call_id = call_id.strip()
    q = _audio_register(call_id)
    logger.info(f"[listen] Browser connected to monitor call {call_id}")
    try:
        while True:
            try:
                chunk = q.get(timeout=20)
                ws.send(chunk)
            except _queue_mod.Empty:
                ws.send(b"")
    except Exception as e:
        logger.debug(f"[listen] Browser WebSocket closed for call {call_id}: {e}")
    finally:
        _audio_unregister(call_id, q)
        logger.info(f"[listen] Browser disconnected from call {call_id}")


@app.route("/api/monitor/start", methods=["POST"])
@login_required
def api_monitor_start():
    """Start Telnyx audio fork so admin can listen to the active call."""
    data = request.get_json() or {}
    call_id = (data.get("call_id") or "").strip()
    if not call_id:
        return jsonify({"error": "call_id required"}), 400
    base = _detected_base_url or ""
    if not base:
        return jsonify({"error": "Public base URL not configured — app is not yet reachable from the internet"}), 503
    ws_url = base.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
    ws_url = f"{ws_url}/ws/fork?call_id={call_id}"
    ok = fork_start(call_id, ws_url)
    if ok:
        return jsonify({"message": "Audio monitoring started", "ws_url": ws_url})
    return jsonify({"error": "Failed to start audio fork — call may have already ended"}), 500


@app.route("/api/monitor/stop", methods=["POST"])
@login_required
def api_monitor_stop():
    """Stop Telnyx audio fork."""
    data = request.get_json() or {}
    call_id = (data.get("call_id") or "").strip()
    if not call_id:
        return jsonify({"error": "call_id required"}), 400
    fork_stop(call_id)
    with _audio_subs_lock:
        _audio_subscribers.pop(call_id, None)
    return jsonify({"message": "Audio monitoring stopped"})


@app.route("/api/custom-variables", methods=["GET"])
@login_required
def api_get_custom_variables():
    variables = get_custom_variables(user_id=current_user.id)
    return jsonify({"variables": variables})


@app.route("/api/custom-variables", methods=["POST"])
@login_required
def api_save_custom_variables():
    data = request.get_json() or {}
    variables = data.get("variables", [])
    import re
    cleaned = []
    seen = set()
    for v in variables:
        if not isinstance(v, str):
            continue
        v = v.strip().lower()
        v = re.sub(r'[^a-z0-9_]', '', v.replace(' ', '_'))
        if v and v not in seen and len(v) <= 50:
            cleaned.append(v)
            seen.add(v)
    save_custom_variables(cleaned, user_id=current_user.id)
    return jsonify({"variables": cleaned})


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


# ═══════════════════════════════════════════════════════════════════════════════
# CRM INTEGRATIONS — Webhooks, HubSpot, Google Sheets
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/integrations/status", methods=["GET"])
@login_required
def api_integrations_status():
    from integrations import integration_status
    return jsonify(integration_status(current_user.id))


# ── Outbound Webhooks ──────────────────────────────────────────────────────────

@app.route("/api/integrations/webhook", methods=["GET"])
@login_required
def api_integrations_webhook_get():
    from integrations import get_integration_config, KEY_WEBHOOK
    cfg = get_integration_config(current_user.id, KEY_WEBHOOK)
    return jsonify({
        "url":        cfg.get("url", ""),
        "has_secret": bool(cfg.get("secret")),
        "enabled":    bool(cfg.get("enabled")),
    })


@app.route("/api/integrations/webhook", methods=["POST"])
@login_required
def api_integrations_webhook_save():
    from integrations import get_integration_config, set_integration_config, KEY_WEBHOOK
    data = request.get_json() or {}
    cfg  = get_integration_config(current_user.id, KEY_WEBHOOK)
    url  = data.get("url", "").strip()
    if "url" in data:
        cfg["url"] = url
    if "secret" in data and data["secret"]:
        cfg["secret"] = data["secret"].strip()
    if "clear_secret" in data and data["clear_secret"]:
        cfg.pop("secret", None)
    if "enabled" in data:
        cfg["enabled"] = bool(data["enabled"])
    set_integration_config(current_user.id, KEY_WEBHOOK, cfg)
    return jsonify({"ok": True})


@app.route("/api/integrations/webhook/test", methods=["POST"])
@login_required
def api_integrations_webhook_test():
    from integrations import fire_webhook
    test_record = {
        "call_id": "test-0000",
        "timestamp": datetime.utcnow().isoformat(),
        "number": "+15550001234",
        "from_number": "+15559998888",
        "status": "voicemail_complete",
        "status_description": "Voicemail dropped",
        "transferred": False,
        "voicemail_dropped": True,
        "machine_detected": True,
        "amd_result": "machine_start",
        "ring_duration": 18,
        "hangup_cause": "NORMAL_CLEARING",
    }
    try:
        fire_webhook(current_user.id, test_record)
        return jsonify({"ok": True, "message": "Test webhook fired"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── HubSpot (Private App token — no OAuth needed) ─────────────────────────────

@app.route("/api/integrations/hubspot", methods=["POST"])
@login_required
def api_integrations_hubspot_save():
    """Save/verify a HubSpot Private App access token."""
    from integrations import get_integration_config, set_integration_config, KEY_HUBSPOT, hubspot_verify_token
    data  = request.get_json() or {}
    cfg   = get_integration_config(current_user.id, KEY_HUBSPOT)
    token = data.get("access_token", "").strip()
    if token:
        ok, result = hubspot_verify_token(token)
        if not ok:
            return jsonify({"error": f"Invalid token: {result}"}), 400
        cfg["access_token"] = token
        cfg["portal_id"]    = result
        cfg["enabled"]      = True
    if "enabled" in data:
        cfg["enabled"] = bool(data["enabled"])
    if data.get("disconnect"):
        cfg = {}
    set_integration_config(current_user.id, KEY_HUBSPOT, cfg)
    return jsonify({"ok": True, "portal_id": cfg.get("portal_id", "")})


@app.route("/api/integrations/hubspot", methods=["GET"])
@login_required
def api_integrations_hubspot_get():
    from integrations import get_integration_config, KEY_HUBSPOT
    cfg = get_integration_config(current_user.id, KEY_HUBSPOT)
    return jsonify({
        "connected": bool(cfg.get("access_token")),
        "enabled":   bool(cfg.get("enabled")),
        "portal_id": cfg.get("portal_id", ""),
    })


# ── Google Sheets (Service Account) ───────────────────────────────────────────

@app.route("/api/integrations/google-sheets", methods=["GET"])
@login_required
def api_integrations_gsheets_get():
    from integrations import get_integration_config, KEY_GSHEETS_CFG, integration_status
    st  = integration_status(current_user.id)
    cfg = get_integration_config(current_user.id, KEY_GSHEETS_CFG)
    gs  = st.get("google_sheets", {})
    return jsonify({
        "service_account_configured": gs.get("service_account_configured", False),
        "service_account_email":      gs.get("service_account_email", ""),
        "connected":                  bool(cfg.get("sheet_id")),
        "enabled":                    bool(cfg.get("enabled")),
        "sheet_id":                   cfg.get("sheet_id", ""),
        "sheet_name":                 cfg.get("sheet_name", "Call Log"),
    })


@app.route("/api/integrations/google-sheets", methods=["POST"])
@login_required
def api_integrations_gsheets_save():
    from integrations import get_integration_config, set_integration_config, KEY_GSHEETS_CFG
    import re as _re
    data = request.get_json() or {}
    cfg  = get_integration_config(current_user.id, KEY_GSHEETS_CFG)
    if "sheet_id" in data:
        raw = data["sheet_id"].strip()
        m   = _re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', raw)
        cfg["sheet_id"] = m.group(1) if m else raw
    if "sheet_name" in data:
        cfg["sheet_name"] = data["sheet_name"].strip() or "Call Log"
    if "enabled" in data:
        cfg["enabled"] = bool(data["enabled"])
    if data.get("disconnect"):
        cfg = {}
    set_integration_config(current_user.id, KEY_GSHEETS_CFG, cfg)
    return jsonify({"ok": True})


@app.route("/api/integrations/google-sheets/test", methods=["POST"])
@login_required
def api_integrations_gsheets_test():
    from integrations import get_integration_config, KEY_GSHEETS_CFG, google_sheets_test_connection
    cfg      = get_integration_config(current_user.id, KEY_GSHEETS_CFG)
    sheet_id = cfg.get("sheet_id", "").strip()
    if not sheet_id:
        return jsonify({"error": "No Sheet ID saved yet"}), 400
    ok, result = google_sheets_test_connection(sheet_id, cfg.get("sheet_name", "Call Log"))
    if ok:
        return jsonify({"ok": True, "title": result})
    return jsonify({"error": result}), 400


# ── GoHighLevel (Location API Key) ────────────────────────────────────────────

@app.route("/api/integrations/ghl", methods=["GET"])
@login_required
def api_integrations_ghl_get():
    from integrations import get_integration_config, KEY_GHL
    cfg = get_integration_config(current_user.id, KEY_GHL)
    return jsonify({
        "connected":   bool(cfg.get("api_key")),
        "enabled":     bool(cfg.get("enabled")),
        "location_id": cfg.get("location_id", ""),
    })


@app.route("/api/integrations/ghl", methods=["POST"])
@login_required
def api_integrations_ghl_save():
    from integrations import get_integration_config, set_integration_config, KEY_GHL, ghl_verify_token
    data    = request.get_json() or {}
    cfg     = get_integration_config(current_user.id, KEY_GHL)
    api_key = data.get("api_key", "").strip()
    if api_key:
        ok, result = ghl_verify_token(api_key)
        if not ok:
            return jsonify({"error": f"Invalid API key: {result}"}), 400
        cfg["api_key"]     = api_key
        cfg["location_id"] = result
        cfg["enabled"]     = True
    if "enabled" in data:
        cfg["enabled"] = bool(data["enabled"])
    if data.get("disconnect"):
        cfg = {}
    set_integration_config(current_user.id, KEY_GHL, cfg)
    return jsonify({"ok": True, "location_id": cfg.get("location_id", "")})


# ── Pipedrive (API Token) ──────────────────────────────────────────────────────

@app.route("/api/integrations/pipedrive", methods=["GET"])
@login_required
def api_integrations_pipedrive_get():
    from integrations import get_integration_config, KEY_PIPEDRIVE
    cfg = get_integration_config(current_user.id, KEY_PIPEDRIVE)
    return jsonify({
        "connected": bool(cfg.get("api_token")),
        "enabled":   bool(cfg.get("enabled")),
        "company":   cfg.get("company_domain", ""),
    })


@app.route("/api/integrations/pipedrive", methods=["POST"])
@login_required
def api_integrations_pipedrive_save():
    from integrations import get_integration_config, set_integration_config, KEY_PIPEDRIVE, pipedrive_verify_token
    data      = request.get_json() or {}
    cfg       = get_integration_config(current_user.id, KEY_PIPEDRIVE)
    api_token = data.get("api_token", "").strip()
    if api_token:
        ok, result = pipedrive_verify_token(api_token)
        if not ok:
            return jsonify({"error": f"Invalid API token: {result}"}), 400
        cfg["api_token"]      = api_token
        cfg["company_domain"] = result
        cfg["enabled"]        = True
    if "enabled" in data:
        cfg["enabled"] = bool(data["enabled"])
    if data.get("disconnect"):
        cfg = {}
    set_integration_config(current_user.id, KEY_PIPEDRIVE, cfg)
    return jsonify({"ok": True, "company": cfg.get("company_domain", "")})


@app.route("/api/crm-contacts", methods=["GET"])
@login_required
def api_crm_contacts():
    """Return paginated, searchable contacts from the user's connected CRM(s)."""
    from integrations import (
        get_integration_config, KEY_HUBSPOT, KEY_GHL, KEY_PIPEDRIVE,
        list_contacts_hubspot, list_contacts_ghl, list_contacts_pipedrive,
        PER_PAGE,
    )
    user_id = current_user.id
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid page parameter"}), 400
    search  = (request.args.get("search", "") or "").strip()
    _VALID_SOURCES = {"", "hubspot", "gohighlevel", "pipedrive"}
    source  = (request.args.get("source", "") or "").strip()
    if source not in _VALID_SOURCES:
        return jsonify({"error": "Invalid source parameter"}), 400
    # HubSpot cursor token for cursor-based paging (passed from frontend)
    hs_cursor = (request.args.get("hs_cursor", "") or "").strip() or None

    all_contacts = []
    has_more     = False
    next_hs_cursor = None

    hs_cfg = get_integration_config(user_id, KEY_HUBSPOT)
    if (not source or source == "hubspot") and hs_cfg.get("enabled") and hs_cfg.get("access_token"):
        try:
            contacts, cursor = list_contacts_hubspot(
                hs_cfg["access_token"], page=page, search=search, after_cursor=hs_cursor
            )
            all_contacts.extend(contacts)
            if cursor:
                has_more = True
                next_hs_cursor = cursor
        except Exception as e:
            logger.error(f"[QUICK CALL] HubSpot list error: {e}")

    ghl_cfg = get_integration_config(user_id, KEY_GHL)
    if (not source or source == "gohighlevel") and ghl_cfg.get("enabled") and ghl_cfg.get("api_key"):
        try:
            contacts, more = list_contacts_ghl(ghl_cfg["api_key"], page=page, search=search)
            all_contacts.extend(contacts)
            if more:
                has_more = True
        except Exception as e:
            logger.error(f"[QUICK CALL] GHL list error: {e}")

    pd_cfg = get_integration_config(user_id, KEY_PIPEDRIVE)
    if (not source or source == "pipedrive") and pd_cfg.get("enabled") and pd_cfg.get("api_token"):
        try:
            contacts, more = list_contacts_pipedrive(
                pd_cfg["api_token"],
                company_domain=pd_cfg.get("company_domain", ""),
                page=page,
                search=search,
            )
            all_contacts.extend(contacts)
            if more:
                has_more = True
        except Exception as e:
            logger.error(f"[QUICK CALL] Pipedrive list error: {e}")

    from storage import _qc_key as _mk_qc_key
    statuses = get_quick_call_statuses(user_id)
    for c in all_contacts:
        cid = str(c.get("id", ""))
        csrc = c.get("crm_source", "")
        rec = statuses.get(_mk_qc_key(csrc, cid))
        c["last_call_status"] = rec.get("status") if rec else None
        c["last_call_updated"] = rec.get("updated_at") if rec else None

    return jsonify({
        "contacts": all_contacts,
        "page": page,
        "per_page": PER_PAGE,
        "has_more": has_more,
        "next_hs_cursor": next_hs_cursor,
        "search": search,
    })


@app.route("/api/quick-call", methods=["POST"])
@login_required
def api_quick_call():
    """Initiate a quick outbound call to a CRM contact."""
    data           = request.get_json() or {}
    phone          = (data.get("phone") or "").strip()
    contact_name   = (data.get("contact_name") or "").strip()
    crm_contact_id = str(data.get("crm_contact_id") or "")
    crm_source     = (data.get("crm_source") or "").strip()

    _VALID_CRM_SOURCES = {"hubspot", "gohighlevel", "pipedrive"}
    if not phone:
        return jsonify({"error": "Phone number is required"}), 400
    if not crm_contact_id:
        return jsonify({"error": "crm_contact_id is required"}), 400
    if crm_source and crm_source not in _VALID_CRM_SOURCES:
        return jsonify({"error": "Invalid crm_source"}), 400

    user_id = current_user.id

    from call_manager import _get_lru_from_number as _lru_num
    from_number = _lru_num(user_id, fallback=None)
    if not from_number:
        user_pn = ProvisionedNumber.query.filter_by(user_id=user_id, status="active").first()
        from_number = (user_pn.phone_number if user_pn else None) or os.environ.get("TELNYX_FROM_NUMBER", "")
    if not from_number:
        return jsonify({"error": "No caller ID configured. Please provision a phone number first."}), 400

    camp = get_campaign(user_id=user_id)
    transfer_number = camp.get("transfer_number") or ""
    if not transfer_number:
        return jsonify({"error": "No transfer number configured. Please start or configure a campaign with a transfer number."}), 400

    try:
        _qc_ml_rec = UserAppData.query.filter_by(user_id=user_id, data_key="max_concurrent_lines").first()
        _qc_max_lines = int(json.loads(_qc_ml_rec.data_value).get("limit", 5)) if _qc_ml_rec else 5
    except Exception:
        _qc_max_lines = 5
    _qc_active = count_active_calls(user_id=user_id)
    if _qc_active >= _qc_max_lines:
        return jsonify({"error": f"Line limit reached: {_qc_active} of {_qc_max_lines} lines are currently active."}), 429

    call_control_id, err = make_call(phone, from_number_override=from_number)
    if err or not call_control_id:
        return jsonify({"error": err or "Failed to place call"}), 500

    create_call_state(call_control_id, phone, user_id=user_id)
    update_call_state(
        call_control_id,
        quick_call=True,
        quick_call_contact_name=contact_name,
        quick_call_crm_contact_id=crm_contact_id,
        quick_call_crm_source=crm_source,
        from_number=from_number,
    )

    set_quick_call_status(
        user_id, crm_contact_id, "calling",
        call_control_id=call_control_id,
        crm_source=crm_source,
        extra={"contact_name": contact_name, "phone": phone},
    )

    logger.info(f"[QUICK CALL] user={user_id} contact_id={crm_contact_id} phone={phone} ccid={call_control_id}")
    return jsonify({"ok": True, "call_control_id": call_control_id})


@app.route("/api/quick-call-status", methods=["GET"])
@login_required
def api_quick_call_status():
    """Return all quick call statuses for the current user."""
    user_id  = current_user.id
    statuses = get_quick_call_statuses(user_id)
    return jsonify({"statuses": statuses})


@app.route("/api/campaign_history")
@login_required
def campaign_history():
    from storage import get_campaign_history_summary
    return jsonify(get_campaign_history_summary(user_id=current_user.id))


@app.route("/api/campaign_history/<date>")
@login_required
def campaign_history_detail(date):
    import re
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        return jsonify({"error": "Invalid date format"}), 400
    start_date = date + "T00:00:00"
    end_date = date + "T23:59:59"
    calls = get_call_history(start_date=start_date, end_date=end_date, user_id=current_user.id)
    calls.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    summary = {"total": len(calls), "transferred": 0, "voicemail": 0, "failed": 0}
    for c in calls:
        if c.get("transferred"):
            summary["transferred"] += 1
        elif c.get("voicemail_dropped"):
            summary["voicemail"] += 1
        else:
            summary["failed"] += 1
    return jsonify({"date": date, "summary": summary, "calls": calls})


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
    state = get_call_state(call_control_id)
    if state and state.get("silence_playing"):
        try:
            stop_playback(call_control_id)
            logger.info(f"[SILENCE STOP] {call_control_id} | Stopped silence keepalive before dropping voicemail")
            update_call_state(call_control_id, silence_playing=False)
            import time
            time.sleep(0.3)
        except Exception as e:
            logger.error(f"[SILENCE STOP ERROR] {call_control_id} | {e}")
    from datetime import datetime as dt
    update_call_state(call_control_id,
                      status_description="Dropping voicemail..." if not is_personalized else "Dropping personalized voicemail...",
                      status_color="blue",
                      vm_pending_audio_url=None,
                      vm_playback_start=dt.utcnow().timestamp())
    if is_personalized:
        logger.info(f"Using PERSONALIZED voicemail for {customer_number} on {call_control_id}")
    logger.info(f"Dropping voicemail NOW on {call_control_id}: {audio_url}")
    play_audio(call_control_id, audio_url, client_state="voicemail_drop")
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
        logger.info(f"[CALL ANSWERED] {call_control_id} | to: {to_number} | from: {from_number}")

        def _amd_fallback(ccid):
            """If AMD event never arrives within 8s, default to transfer (treat as human)."""
            state = get_call_state(ccid)
            if state and not state.get("amd_received") and state.get("status") == "answered":
                logger.warning(f"[AMD TIMEOUT] {ccid} | No AMD result in 8s, defaulting to HUMAN (transfer)")
                update_call_state(ccid, amd_received=True, amd_result="timeout",
                                  status_description="AMD timeout - treating as human", status_color="blue")
                try:
                    start_transcription(ccid)
                except Exception as e:
                    logger.error(f"Failed to start transcription on AMD timeout: {e}")
                try:
                    start_recording(ccid)
                except Exception as e:
                    logger.error(f"Failed to start recording on AMD timeout: {e}")
                uid = get_user_for_call(ccid)
                camp = get_campaign(user_id=uid)
                t_num = camp.get("transfer_number") or ""
                customer_num = state.get("number", "")
                if t_num and not state.get("voicemail_dropped") and claim_call_action(ccid, "transfer") and mark_transferred(ccid):
                    logger.info(f"[TRANSFER] {ccid} | AMD timeout fallback transfer to {t_num}")
                    success = transfer_call(ccid, t_num, customer_number=customer_num)
                    if success:
                        pause_for_transfer(ccid, user_id=uid)
                        update_call_state(ccid, status="transferred",
                                          status_description="AMD timeout - transferred to human", status_color="green")
                    else:
                        update_call_state(ccid, status_description="Transfer failed", status_color="red")
                        hangup_call(ccid)
                elif not t_num:
                    logger.warning(f"[AMD TIMEOUT] {ccid} | No transfer number, hanging up")
                    update_call_state(ccid, status_description="No transfer number configured", status_color="yellow")
                    hangup_call(ccid)
            _amd_timers.pop(ccid, None)

        timer = threading.Timer(20.0, _amd_fallback, args=[call_control_id])
        timer.daemon = True
        _amd_timers[call_control_id] = timer
        timer.start()

        def _safety_timeout(ccid):
            """Rule 4: If call lasts 120s with no action, hang up gracefully."""
            st = get_call_state(ccid)
            if st and not st.get("transferred") and not st.get("voicemail_dropped") and st.get("status") not in ("hangup", "voicemail_complete", "transferred"):
                logger.warning(f"[SAFETY TIMEOUT] {ccid} | 120s with no action taken, hanging up")
                update_call_state(ccid, status_description="Safety timeout - no action taken in 120s", status_color="yellow")
                hangup_call(ccid)
            _amd_timers.pop(f"safety_{ccid}", None)

        safety_timer = threading.Timer(120.0, _safety_timeout, args=[call_control_id])
        safety_timer.daemon = True
        _amd_timers[f"safety_{call_control_id}"] = safety_timer
        safety_timer.start()

    # ---- AMD Detection (standard + premium) ----
    elif event_type in ("call.machine.detection.ended", "call.machine.premium.detection.ended"):
        state = get_call_state(call_control_id)
        if state and state.get("transferred"):
            logger.info(f"Ignoring AMD event for already-transferred call {call_control_id}")
            return "", 200

        result = payload.get("result", "unknown")
        amd_type = payload.get("type", "unknown")
        logger.info(f"[AMD RESULT] {call_control_id} | result: {result} | type: {amd_type} | event: {event_type}")

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
            try:
                start_transcription(call_control_id)
            except Exception as e:
                logger.error(f"Failed to start transcription on human detection: {e}")
            try:
                start_recording(call_control_id)
            except Exception as e:
                logger.error(f"Failed to start recording on human detection: {e}")
            camp = get_campaign(user_id=webhook_user_id)
            transfer_num = camp.get("transfer_number") or ""
            customer_num = (get_call_state(call_control_id) or {}).get("number", "")

            # ---- Gatekeeper Navigator ----
            if camp.get("gatekeeper_navigator_enabled") and not state.get("gatekeeper_mode_active"):
                nav_voice_id = camp.get("navigator_voice_id")
                update_call_state(
                    call_control_id,
                    gatekeeper_mode_active=True,
                    navigator_voice_id=nav_voice_id,
                    status="gatekeeper_active",
                    status_description="Gatekeeper Navigator active — listening...",
                    status_color="blue",
                )
                logger.info(f"[GATEKEEPER] {call_control_id} | Navigator activated (voice_id={nav_voice_id})")
                return "", 200
            # ---- End Gatekeeper Navigator ----

            if transfer_num and not state.get("transferred") and not state.get("voicemail_dropped") and claim_call_action(call_control_id, "transfer") and mark_transferred(call_control_id):
                logger.info(f"[TRANSFER] {call_control_id} | HUMAN detected, transferring to {transfer_num} (caller ID: {customer_num})")
                if state.get("quick_call") and webhook_user_id:
                    _qc_cid = state.get("quick_call_crm_contact_id", "")
                    if _qc_cid:
                        set_quick_call_status(webhook_user_id, _qc_cid, "connected",
                                              call_control_id=call_control_id,
                                              crm_source=state.get("quick_call_crm_source", ""))
                try:
                    success = transfer_call(call_control_id, transfer_num, customer_number=customer_num)
                except Exception as e:
                    logger.error(f"[TRANSFER ERROR] {call_control_id} | {e}")
                    success = False
                if success:
                    pause_for_transfer(call_control_id, user_id=webhook_user_id)
                    update_call_state(call_control_id, status="transferred",
                                      status_description="Answered by human - transferred (campaign paused)", status_color="green")
                else:
                    logger.error(f"[TRANSFER FAILED] {call_control_id} | hanging up")
                    update_call_state(call_control_id, status="transfer_failed",
                                      status_description="Transfer failed", status_color="red")
                    hangup_call(call_control_id)
            elif not transfer_num:
                logger.warning(f"[NO TRANSFER] {call_control_id} | HUMAN detected but no transfer number configured")
                update_call_state(call_control_id, status="human_no_transfer",
                                  status_description="Human answered - no transfer number", status_color="yellow")
                hangup_call(call_control_id)

        elif result == "fax":
            update_call_state(call_control_id, machine_detected=True, status="machine_detected",
                              amd_result="fax", status_description="Fax machine detected", status_color="red")
            logger.info(f"[FAX] {call_control_id} | Fax detected, hanging up")
            hangup_call(call_control_id)

        elif result == "machine":
            update_call_state(call_control_id, machine_detected=True, status="machine_detected",
                              amd_result="machine", status_description="Machine detected - waiting for beep", status_color="blue")
            logger.info(f"[AMD RESULT] {call_control_id} | MACHINE detected, waiting for beep only (120s timeout)")

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

            if audio_url:
                silence_url = f"{_detected_base_url or os.environ.get('PUBLIC_BASE_URL', '').rstrip('/')}/static/silence_60s.wav"
                try:
                    play_audio(call_control_id, silence_url, client_state="silence_keepalive")
                    import time as _time_mod
                    update_call_state(call_control_id, silence_playing=True, silence_start_time=_time_mod.time())
                    logger.info(f"[SILENCE PLAY] {call_control_id} | Playing 60s silence to keep RTP alive while waiting for beep")
                except Exception as e:
                    logger.error(f"[SILENCE PLAY ERROR] {call_control_id} | {e}")

                # ── LAYER 2: start transcription so Alex can hear the voicemail greeting ──
                try:
                    start_transcription(call_control_id)
                    logger.info(f"[LAYER2] {call_control_id} | Transcription started on machine — Alex is listening for VM keywords")
                except Exception as e:
                    logger.error(f"[LAYER2] {call_control_id} | Failed to start transcription on machine: {e}")

                # ── LAYER 3: 22-second safety-net timer ──
                # If neither beep event nor keyword detection fires within 22s,
                # the greeting has almost certainly ended — drop the voicemail anyway.
                _vm_safe_url = audio_url
                _vm_safe_pvm = is_personalized
                _vm_safe_cust = customer_number
                _vm_safe_uid = webhook_user_id
                _vm_safe_cid = call_control_id

                _TERMINAL_STATUSES = {"transferred", "voicemail_complete", "hangup", "voicemail_playing"}

                def _vm_safety_fallback(ccid, aurl, ispvm, custnum, uid):
                    _amd_timers.pop(f"vm_safety_{ccid}", None)
                    st = get_call_state(ccid)
                    if (st
                            and not st.get("voicemail_dropped")
                            and not st.get("transferred")
                            and st.get("machine_detected")
                            and st.get("status") not in _TERMINAL_STATUSES):
                        logger.info(f"[LAYER3] {ccid} | 22s safety timer — no beep/keyword received, dropping voicemail now")
                        update_call_state(ccid, status_description="Dropping voicemail (safety timer)", status_color="blue")
                        _drop_voicemail_now(ccid, aurl, ispvm, custnum, uid)
                    else:
                        logger.info(f"[LAYER3] {ccid} | Safety timer fired but call already handled (status={st.get('status') if st else 'gone'}), skipping")

                # Cancel any prior safety timer for this call before registering new one
                _prev_safe = _amd_timers.pop(f"vm_safety_{call_control_id}", None)
                if _prev_safe:
                    _prev_safe.cancel()
                vm_safety_t = threading.Timer(22.0, _vm_safety_fallback,
                                              args=[_vm_safe_cid, _vm_safe_url, _vm_safe_pvm, _vm_safe_cust, _vm_safe_uid])
                vm_safety_t.daemon = True
                # Store in dict BEFORE start() so hangup cleanup can always find and cancel it
                _amd_timers[f"vm_safety_{call_control_id}"] = vm_safety_t
                vm_safety_t.start()
                logger.info(f"[LAYER3] {call_control_id} | 22s safety fallback timer started")
            else:
                logger.error(f"[NO AUDIO] {call_control_id} | No voicemail audio URL configured")
                update_call_state(call_control_id, status_description="Voicemail failed - no audio", status_color="red")
                hangup_call(call_control_id)

        elif result == "not_sure":
            camp = get_campaign(user_id=webhook_user_id)
            transfer_num = camp.get("transfer_number") or ""
            customer_num = (get_call_state(call_control_id) or {}).get("number", "")
            logger.info(f"[AMD RESULT] {call_control_id} | NOT_SURE, treating as human (transferring)")
            update_call_state(call_control_id, amd_result="not_sure",
                              status_description="Detection unclear - treating as human", status_color="blue")
            try:
                start_transcription(call_control_id)
            except Exception as e:
                logger.error(f"Failed to start transcription on not_sure detection: {e}")
            try:
                start_recording(call_control_id)
            except Exception as e:
                logger.error(f"Failed to start recording on not_sure detection: {e}")
            if transfer_num and not state.get("transferred") and not state.get("voicemail_dropped") and claim_call_action(call_control_id, "transfer") and mark_transferred(call_control_id):
                logger.info(f"[TRANSFER] {call_control_id} | not_sure -> transferring to {transfer_num}")
                _ns_state = get_call_state(call_control_id) or {}
                if _ns_state.get("quick_call") and webhook_user_id:
                    _qc_cid2 = _ns_state.get("quick_call_crm_contact_id", "")
                    if _qc_cid2:
                        set_quick_call_status(webhook_user_id, _qc_cid2, "connected",
                                              call_control_id=call_control_id,
                                              crm_source=_ns_state.get("quick_call_crm_source", ""))
                try:
                    success = transfer_call(call_control_id, transfer_num, customer_number=customer_num)
                except Exception as e:
                    logger.error(f"[TRANSFER ERROR] {call_control_id} | {e}")
                    success = False
                if success:
                    pause_for_transfer(call_control_id, user_id=webhook_user_id)
                    update_call_state(call_control_id, status="transferred",
                                      status_description="Detection unclear - transferred to human", status_color="green")
                else:
                    update_call_state(call_control_id, status_description="Transfer failed", status_color="red")
                    hangup_call(call_control_id)
            elif not transfer_num:
                logger.warning(f"[NO TRANSFER] {call_control_id} | not_sure, no transfer number, hanging up")
                update_call_state(call_control_id, status_description="No transfer number configured", status_color="yellow")
                hangup_call(call_control_id)

        elif result == "silence":
            camp = get_campaign(user_id=webhook_user_id)
            transfer_num = camp.get("transfer_number") or ""
            customer_num = (get_call_state(call_control_id) or {}).get("number", "")
            logger.info(f"[AMD RESULT] {call_control_id} | SILENCE detected, treating as human (transferring)")
            update_call_state(call_control_id, amd_result="silence",
                              status_description="Silence detected - treating as human", status_color="blue")
            try:
                start_transcription(call_control_id)
            except Exception:
                pass
            try:
                start_recording(call_control_id)
            except Exception:
                pass
            _sil_state = get_call_state(call_control_id) or {}
            if transfer_num and not _sil_state.get("transferred") and not _sil_state.get("voicemail_dropped") and claim_call_action(call_control_id, "transfer") and mark_transferred(call_control_id):
                logger.info(f"[TRANSFER] {call_control_id} | silence -> transferring to {transfer_num}")
                if _sil_state.get("quick_call") and webhook_user_id:
                    _qc_cid3 = _sil_state.get("quick_call_crm_contact_id", "")
                    if _qc_cid3:
                        set_quick_call_status(webhook_user_id, _qc_cid3, "connected",
                                              call_control_id=call_control_id,
                                              crm_source=_sil_state.get("quick_call_crm_source", ""))
                try:
                    success = transfer_call(call_control_id, transfer_num, customer_number=customer_num)
                except Exception as e:
                    logger.error(f"[TRANSFER ERROR] {call_control_id} | {e}")
                    success = False
                if success:
                    pause_for_transfer(call_control_id, user_id=webhook_user_id)
                    update_call_state(call_control_id, status="transferred",
                                      status_description="Silence - transferred as human", status_color="green")
                else:
                    update_call_state(call_control_id, status_description="Transfer failed", status_color="red")
                    hangup_call(call_control_id)
            elif not transfer_num:
                logger.warning(f"[NO TRANSFER] {call_control_id} | silence, no transfer number, hanging up")
                update_call_state(call_control_id, status_description="No transfer number configured", status_color="yellow")
                hangup_call(call_control_id)

        else:
            update_call_state(call_control_id, status="no_answer",
                              amd_result=result, status_description=f"Unknown AMD result: {result}", status_color="yellow")
            logger.info(f"[AMD UNKNOWN] {call_control_id} | result='{result}', hanging up")
            hangup_call(call_control_id)

    # ---- call.machine.greeting.ended (beep/no-beep) ----
    elif event_type in ("call.machine.greeting.ended", "call.machine.premium.greeting.ended"):
        state = get_call_state(call_control_id)
        if not state:
            return "", 200

        beep_result = payload.get("result", "unknown")
        logger.info(f"[GREETING ENDED] {call_control_id} | result: {beep_result}")

        # Cancel Layer 2/3 timers based on result:
        # - beep_detected: cancel both (Layer 1 is dropping, nothing else needed)
        # - no_beep: cancel safety timer only; preserve keyword timer so Layer 2
        #   can still fire if keywords were already heard during the greeting
        _prefixes_to_cancel = ["vm_safety_", "vm_kw_"] if beep_result == "beep_detected" else ["vm_safety_"]
        for _prefix in _prefixes_to_cancel:
            _t = _amd_timers.pop(f"{_prefix}{call_control_id}", None)
            if _t:
                _t.cancel()

        if state.get("voicemail_dropped") or state.get("transferred"):
            logger.info(f"[GREETING ENDED] {call_control_id} | Already handled (vm={state.get('voicemail_dropped')}, transfer={state.get('transferred')}), ignoring")
        elif state.get("vm_pending_audio_url") and beep_result == "beep_detected":
            audio_url = state.get("vm_pending_audio_url")
            is_pvm = state.get("vm_pending_personalized", False)
            cust_num = state.get("vm_pending_customer_number", "")
            uid = state.get("vm_pending_user_id") or get_user_for_call(call_control_id)
            logger.info(f"[BEEP DETECTED] {call_control_id} | Confirmed voicemail, dropping immediately")
            update_call_state(call_control_id, beep_detected=True, voicemail_confirmed=True)
            _drop_voicemail_now(call_control_id, audio_url, is_pvm, cust_num, uid)
        else:
            logger.info(f"[NO BEEP] {call_control_id} | No beep — listening silently for beep or human (120s timeout)")
            update_call_state(call_control_id, beep_detected=False,
                              status_description="No beep — listening silently for beep or human", status_color="blue")

    # ---- call.gather.ended (from keep-alive gather after no-beep) ----
    elif event_type == "call.gather.ended":
        state = get_call_state(call_control_id)
        if state:
            digits = payload.get("digits", "")
            status = payload.get("status", "")
            logger.info(f"[GATHER ENDED] {call_control_id} | status={status}, digits={digits}")
            if not state.get("voicemail_dropped") and not state.get("transferred") and state.get("machine_detected"):
                logger.info(f"[GATHER TIMEOUT] {call_control_id} | Gather ended with no action taken, safety timeout will handle hangup")

    # ---- call.playback.ended ----
    elif event_type == "call.playback.ended":
        import base64 as b64module
        raw_cs = payload.get("client_state", "") or ""
        try:
            client_state_str = b64module.b64decode(raw_cs).decode() if raw_cs else ""
        except Exception:
            client_state_str = ""

        state = get_call_state(call_control_id)

        if client_state_str == "voicemail_drop":
            # Voicemail audio finished playing — hang up immediately
            vm_duration = None
            vm_start = state.get("vm_playback_start") if state else None
            if vm_start:
                from datetime import datetime as dt
                vm_duration = round(dt.utcnow().timestamp() - vm_start)
            desc = f"Voicemail dropped successfully — {vm_duration}s" if vm_duration is not None else "Voicemail dropped successfully"
            update_call_state(call_control_id, status="voicemail_complete",
                              status_description=desc, status_color="green",
                              vm_duration=vm_duration)
            logger.info(f"[VM COMPLETE] {call_control_id} | Voicemail playback finished ({vm_duration}s), hanging up")
            hangup_call(call_control_id)

        elif client_state_str == "silence_keepalive":
            if state and not state.get("voicemail_dropped") and not state.get("transferred"):
                import time as _time_mod2
                silence_start = state.get("silence_start_time", 0)
                elapsed = _time_mod2.time() - silence_start if silence_start else 0
                if elapsed < 110:
                    logger.info(f"[SILENCE REPLAY] {call_control_id} | Silence ended early ({elapsed:.1f}s), replaying to keep line alive while waiting for beep")
                    silence_url = f"{_detected_base_url or os.environ.get('PUBLIC_BASE_URL', '').rstrip('/')}/static/silence_60s.wav"
                    try:
                        play_audio(call_control_id, silence_url, client_state="silence_keepalive")
                    except Exception as e:
                        logger.error(f"[SILENCE REPLAY ERROR] {call_control_id} | {e}")
                else:
                    logger.info(f"[SILENCE END] {call_control_id} | Full silence wait completed ({elapsed:.1f}s), no beep detected — hanging up")
                    update_call_state(call_control_id, silence_playing=False, status="no_voicemail",
                                      status_description="120s wait — no beep detected, hanging up", status_color="yellow")
                    hangup_call(call_control_id)
            else:
                update_call_state(call_control_id, silence_playing=False)
                logger.info(f"[SILENCE END] {call_control_id} | Silence playback ended (already handled: vm={state.get('voicemail_dropped') if state else '?'}, xfer={state.get('transferred') if state else '?'})")

        elif state and state.get("voicemail_dropped"):
            # Fallback: voicemail ended but client_state wasn't tagged — still hang up
            vm_duration = None
            vm_start = state.get("vm_playback_start")
            if vm_start:
                from datetime import datetime as dt
                vm_duration = round(dt.utcnow().timestamp() - vm_start)
            desc = f"Voicemail dropped successfully — {vm_duration}s" if vm_duration is not None else "Voicemail dropped successfully"
            update_call_state(call_control_id, status="voicemail_complete",
                              status_description=desc, status_color="green",
                              vm_duration=vm_duration)
            logger.info(f"[VM COMPLETE fallback] {call_control_id} | Voicemail playback finished ({vm_duration}s), hanging up")
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
            if state and state.get("machine_detected") and not state.get("voicemail_dropped") and not state.get("transferred"):
                text_lower = transcript_text.lower()

                # High-confidence phrases spoken at the END of a voicemail greeting
                # (right before the beep). Hearing any of these means the greeting
                # is finishing and recording is about to start.
                vm_keywords_high = [
                    "leave your message", "leave a message", "leave me a message",
                    "after the tone", "after the beep", "at the tone", "at the beep",
                    "record your message", "record a message", "start recording",
                    "press pound when done", "hang up when done", "hang up when finished",
                    "begin your message", "begin recording",
                ]
                # Medium-confidence phrases (heard during the greeting body)
                vm_keywords_medium = [
                    "can't come to the phone", "cannot come to the phone",
                    "can't take your call", "cannot take your call",
                    "not available", "currently unavailable",
                    "you have reached voicemail", "you've reached voicemail",
                    "please leave", "not in at the moment",
                ]

                is_high_confidence = any(kw in text_lower for kw in vm_keywords_high)
                is_medium_confidence = any(kw in text_lower for kw in vm_keywords_medium)

                if (is_high_confidence or is_medium_confidence) and state.get("vm_pending_audio_url") and not state.get("voicemail_confirmed"):
                    confidence = "HIGH" if is_high_confidence else "MEDIUM"
                    delay = 2.0 if is_high_confidence else 4.0
                    logger.info(f"[LAYER2] {call_control_id} | VM keywords [{confidence}] heard: '{transcript_text[:100]}' — dropping in {delay}s if no beep fires")
                    update_call_state(call_control_id, voicemail_confirmed=True,
                                      status_description=f"Voicemail keywords heard [{confidence}] — dropping in {delay:.0f}s", status_color="blue")

                    # Cancel the slower Layer 3 safety timer — Layer 2 has a better signal
                    existing_safe = _amd_timers.pop(f"vm_safety_{call_control_id}", None)
                    if existing_safe:
                        existing_safe.cancel()

                    # Cancel any existing keyword timer to avoid double-drop
                    existing_kw = _amd_timers.pop(f"vm_kw_{call_control_id}", None)
                    if existing_kw:
                        existing_kw.cancel()

                    _vm_kw_cid = call_control_id
                    _KW_TERMINAL = {"transferred", "voicemail_complete", "hangup", "voicemail_playing"}

                    def _vm_keyword_fallback(ccid):
                        _amd_timers.pop(f"vm_kw_{ccid}", None)
                        st = get_call_state(ccid)
                        if (st
                                and not st.get("voicemail_dropped")
                                and not st.get("transferred")
                                and st.get("voicemail_confirmed")
                                and st.get("status") not in _KW_TERMINAL):
                            aurl = st.get("vm_pending_audio_url", "")
                            ispvm = st.get("vm_pending_personalized", False)
                            custnum = st.get("vm_pending_customer_number", "")
                            uid = st.get("vm_pending_user_id")
                            logger.info(f"[LAYER2] {ccid} | Keyword timer fired — beep event never arrived, dropping voicemail now")
                            _drop_voicemail_now(ccid, aurl, ispvm, custnum, uid)
                        else:
                            logger.info(f"[LAYER2] {ccid} | Keyword timer fired but call already handled (status={st.get('status') if st else 'gone'}), skipping")

                    # Store in dict BEFORE start() so hangup cleanup can always cancel it
                    vm_kw_t = threading.Timer(delay, _vm_keyword_fallback, args=[_vm_kw_cid])
                    vm_kw_t.daemon = True
                    _amd_timers[f"vm_kw_{call_control_id}"] = vm_kw_t
                    vm_kw_t.start()

            # ---- Gatekeeper Navigator logic ----
            if (state and state.get("gatekeeper_mode_active")
                    and is_final
                    and not state.get("gatekeeper_resolved")
                    and not state.get("transferred")
                    and not state.get("voicemail_dropped")):
                try:
                    gk_camp = get_campaign(user_id=webhook_user_id)
                    gk_category = gk_navigator.classify_gatekeeper(transcript_text)
                    turn = state.get("gatekeeper_turn_count", 0)
                    logger.info(f"[GATEKEEPER] {call_control_id} | turn={turn} category={gk_category} text='{transcript_text[:80]}'")
                    update_call_state(call_control_id, gatekeeper_type=gk_category)

                    if gk_category == "human_prospect" or turn >= 4:
                        update_call_state(call_control_id, gatekeeper_resolved=True,
                                          status_description="Prospect reached — transferring",
                                          status_color="green")
                        gk_transfer_num = gk_camp.get("transfer_number") or ""
                        gk_customer_num = state.get("number", "")
                        if gk_transfer_num and claim_call_action(call_control_id, "transfer") and mark_transferred(call_control_id):
                            logger.info(f"[GATEKEEPER] {call_control_id} | Prospect reached — transferring to {gk_transfer_num}")
                            try:
                                gk_success = transfer_call(call_control_id, gk_transfer_num, customer_number=gk_customer_num)
                            except Exception as te:
                                logger.error(f"[GATEKEEPER TRANSFER ERROR] {call_control_id} | {te}")
                                gk_success = False
                            if gk_success:
                                pause_for_transfer(call_control_id, user_id=webhook_user_id)
                                update_call_state(call_control_id, status="transferred",
                                                  status_description="Transferred after gatekeeper navigation", status_color="green")
                            else:
                                update_call_state(call_control_id, status="transfer_failed",
                                                  status_description="Transfer failed after navigation", status_color="red")
                                hangup_call(call_control_id)
                        else:
                            hangup_call(call_control_id)
                    else:
                        prospect_name = gk_camp.get("prospect_name") or "the decision maker"
                        prospect_company = gk_camp.get("prospect_company") or "their company"
                        nav_voice_id = state.get("navigator_voice_id") or gk_camp.get("navigator_voice_id")
                        agent_persona = "Alex, a friendly business development representative"
                        gk_knowledge_base = gk_camp.get("navigator_knowledge_base", "")
                        if webhook_user_id:
                            try:
                                gk_user = User.query.get(webhook_user_id)
                                if gk_user:
                                    if gk_user.navigator_persona:
                                        agent_persona = gk_user.navigator_persona
                                    if not gk_knowledge_base and gk_user.navigator_knowledge_base:
                                        gk_knowledge_base = gk_user.navigator_knowledge_base
                            except Exception:
                                pass
                        response_text = gk_navigator.build_navigator_response(
                            gk_category, transcript_text, prospect_name, prospect_company,
                            agent_persona, knowledge_base=gk_knowledge_base
                        )
                        logger.info(f"[GATEKEEPER] {call_control_id} | Response: '{response_text[:100]}'")
                        base_url = _detected_base_url or os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
                        if nav_voice_id and response_text:
                            gk_navigator.speak_response(call_control_id, response_text, nav_voice_id, base_url)
                        update_call_state(call_control_id,
                                          gatekeeper_turn_count=turn + 1,
                                          status_description=f"Gatekeeper turn {turn + 1} — {gk_category}",
                                          status_color="blue")
                except Exception as gke:
                    logger.error(f"[GATEKEEPER ERROR] {call_control_id} | {gke}")
            # ---- End Gatekeeper Navigator logic ----

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
        for prefix in ["", "beep_", "nobeep_", "safety_", "vm_safety_", "vm_kw_"]:
            t = _amd_timers.pop(f"{prefix}{call_control_id}", None)
            if t:
                t.cancel()

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

        if state and webhook_user_id:
            try:
                from datetime import datetime as _dt
                _ring_start = state.get("ring_start")
                _ring_end   = state.get("ring_end") or _dt.utcnow().timestamp()
                _ring_dur   = round(_ring_end - _ring_start) if _ring_start else None
                _call_record = {
                    "call_id":           call_control_id,
                    "timestamp":         state.get("created_at", _dt.utcnow().isoformat()),
                    "number":            state.get("number", ""),
                    "from_number":       state.get("from_number", ""),
                    "status":            state.get("status", ""),
                    "status_description": state.get("status_description", ""),
                    "transferred":       bool(state.get("transferred")),
                    "voicemail_dropped": bool(state.get("voicemail_dropped")),
                    "machine_detected":  bool(state.get("machine_detected")),
                    "amd_result":        state.get("amd_result"),
                    "ring_duration":     _ring_dur,
                    "hangup_cause":      hangup_cause,
                }
                is_quick = bool(state.get("quick_call"))
                _qc_crm_src = state.get("quick_call_crm_source", "") if is_quick else ""
                if is_quick and _qc_crm_src:
                    # Quick calls: targeted writeback to the specific CRM only
                    # (plus webhook and Google Sheets which are not CRM-specific)
                    from integrations import (
                        fire_webhook, sync_to_hubspot, sync_to_ghl,
                        sync_to_pipedrive, sync_to_google_sheets,
                    )
                    import threading as _threading
                    _qc_rec = dict(_call_record)
                    _qc_rec["contact_id"] = state.get("quick_call_crm_contact_id", "")
                    _qc_rec["contact_name"] = state.get("quick_call_contact_name", "")
                    _qc_crm_fn_map = {
                        "hubspot": sync_to_hubspot,
                        "gohighlevel": sync_to_ghl,
                        "pipedrive": sync_to_pipedrive,
                    }
                    _qc_crm_fn = _qc_crm_fn_map.get(_qc_crm_src)
                    def _run_quick_writeback(_uid=webhook_user_id, _rec=_qc_rec, _fn=_qc_crm_fn):
                        for _name, _fn2 in [("webhook", fire_webhook), ("gsheets", sync_to_google_sheets)]:
                            try:
                                _fn2(_uid, _rec)
                            except Exception as _e:
                                logger.error(f"[INTEGRATIONS] quick-call {_name}: {_e}")
                        if _fn:
                            try:
                                _fn(_uid, _rec)
                            except Exception as _e:
                                logger.error(f"[INTEGRATIONS] quick-call crm ({_qc_crm_src}): {_e}")
                    _threading.Thread(target=_run_quick_writeback, daemon=True).start()
                else:
                    from integrations import fire_all_integrations
                    fire_all_integrations(webhook_user_id, _call_record)
            except Exception as _ie:
                logger.error(f"[INTEGRATIONS] Hook error: {_ie}")

        if state and state.get("quick_call") and webhook_user_id:
            try:
                cid = state.get("quick_call_crm_contact_id", "")
                crm_src = state.get("quick_call_crm_source", "")
                if cid:
                    if state.get("transferred"):
                        qc_status = "connected"
                    elif state.get("voicemail_dropped"):
                        qc_status = "voicemail_left"
                    elif hangup_cause in ("NO_ANSWER", "ORIGINATOR_CANCEL"):
                        qc_status = "no_answer"
                    elif hangup_cause in ("BUSY", "USER_BUSY", "CALL_REJECTED"):
                        qc_status = "failed"
                    else:
                        qc_status = "no_answer"
                    set_quick_call_status(
                        webhook_user_id, cid, qc_status,
                        call_control_id=call_control_id,
                        crm_source=crm_src,
                        extra={"hangup_cause": hangup_cause},
                    )
                    logger.info(f"[QUICK CALL] Contact {cid} status -> {qc_status}")
            except Exception as _qce:
                logger.error(f"[QUICK CALL] Status update error: {_qce}")

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
    """Purchase a phone number for the current user. Enforces plan-based limits."""
    user_id = current_user.id

    data = request.get_json() or {}
    phone_number = data.get("phone_number", "").strip()
    if not phone_number:
        return jsonify({"error": "Phone number is required"}), 400

    limits = _get_number_limits(user_id)
    current_count = ProvisionedNumber.query.filter_by(user_id=user_id, status='active').count()
    if current_count >= limits["max"]:
        plan = _get_user_plan(user_id) or "starter"
        if plan == "starter":
            return jsonify({"error": f"You've reached your Starter plan limit of {limits['max']} numbers. Upgrade to Business for up to 20 numbers."}), 400
        return jsonify({"error": f"You've reached your plan limit of {limits['max']} numbers. Contact support to increase your limit."}), 400

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
    limits = _get_number_limits(user_id)
    pn.is_included = (current_count < limits["included"])
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
    """Return numbers belonging to the current user with plan limits and dial health data."""
    user_id = current_user.id
    user_numbers = ProvisionedNumber.query.filter_by(user_id=user_id).all()
    user_phone_set = {pn.phone_number for pn in user_numbers}

    # Build DB number map for fast lookup
    db_number_map = {pn.phone_number: pn for pn in user_numbers}

    # Pull 7-day call history for answer rate calculation
    calls_7d_map = {}
    answered_7d_map = {}
    try:
        from storage import get_call_history as _gch
        from datetime import timedelta
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
        week_history = _gch(start_date=week_ago, user_id=user_id)
        for entry in week_history:
            fn = entry.get("from_number", "")
            if fn:
                calls_7d_map[fn] = calls_7d_map.get(fn, 0) + 1
                if entry.get("amd_result") == "human" or entry.get("status") in ("transferred", "human_answered"):
                    answered_7d_map[fn] = answered_7d_map.get(fn, 0) + 1
    except Exception:
        pass

    # If user has provisioned numbers, filter the Telnyx list to only theirs
    result = list_owned_numbers()
    if result.get("success") and user_phone_set:
        filtered = [n for n in result.get("numbers", []) if n.get("phone_number") in user_phone_set]
        result["numbers"] = filtered
        result["total"] = len(filtered)
    elif result.get("success") and not user_phone_set:
        result["numbers"] = []
        result["total"] = 0

    active_count = sum(1 for pn in user_numbers if pn.status == 'active')

    # Limits and billing
    limits = _get_number_limits(user_id)
    plan = _get_user_plan(user_id)
    extra_count = max(0, active_count - limits["included"])
    monthly_extra_cost = float(EXTRA_NUMBER_MONTHLY_COST) * extra_count

    # Recommended number count: based on 7-day average daily volume
    total_7d = sum(calls_7d_map.values())
    avg_daily = total_7d / 7.0
    import math
    recommended = max(1, math.ceil(avg_daily / DAILY_DIAL_CAP)) if avg_daily > 0 else 1

    result["active_count"] = active_count
    result["can_purchase"] = active_count < limits["max"]
    result["plan"] = plan or "none"
    result["plan_limits"] = limits
    result["extra_count"] = extra_count
    result["monthly_extra_cost"] = monthly_extra_cost
    result["recommended"] = recommended

    # Enrich numbers with DB health data
    if result.get("success"):
        existing_phones = {n.get("phone_number") for n in result.get("numbers", [])}
        for pn in user_numbers:
            if pn.phone_number not in existing_phones:
                result["numbers"].append({
                    "phone_number": pn.phone_number,
                    "status": pn.status,
                    "id": pn.telnyx_number_id or str(pn.id),
                    "connection_id": pn.telnyx_connection_id,
                    "connection_name": None,
                    "number_type": "local",
                })
        from datetime import date as _date
        today = datetime.utcnow().date()
        for n in result["numbers"]:
            ph = n.get("phone_number", "")
            db_pn = db_number_map.get(ph)
            if db_pn:
                # Reset stale daily count
                if db_pn.last_dial_date and db_pn.last_dial_date < today:
                    daily = 0
                else:
                    daily = db_pn.daily_dial_count or 0
                n["daily_dial_count"] = daily
                n["daily_cap"] = DAILY_DIAL_CAP
                n["is_cooling"] = (daily >= DAILY_DIAL_CAP)
                n["is_included"] = db_pn.is_included
            else:
                n["daily_dial_count"] = 0
                n["daily_cap"] = DAILY_DIAL_CAP
                n["is_cooling"] = False
                n["is_included"] = False
            n["calls_7d"] = calls_7d_map.get(ph, 0)
            answered = answered_7d_map.get(ph, 0)
            total = calls_7d_map.get(ph, 0)
            ar = round(answered / total * 100, 1) if total > 0 else None
            n["answer_rate_7d"] = ar
            n["health"] = _compute_number_health(ar, n["calls_7d"])

    # Swap status
    swap_count = _get_quarterly_swap_count(user_id)
    free_remaining = max(0, FREE_SWAPS_PER_QUARTER - swap_count)
    result["swap_free_remaining"] = free_remaining
    result["swap_cost"] = float(QUICK_SWAP_COST) if free_remaining == 0 else 0.0

    return jsonify(result)


@app.route("/api/active-lines", methods=["GET"])
@login_required
def api_active_lines():
    """Return current active call count and user's max concurrent lines limit."""
    user_id = current_user.id
    active = count_active_calls(user_id=user_id)
    max_lines = 5
    try:
        rec = UserAppData.query.filter_by(user_id=user_id, data_key="max_concurrent_lines").first()
        if rec:
            val = json.loads(rec.data_value)
            max_lines = int(val.get("limit", 5))
    except Exception:
        pass
    return jsonify({"active": active, "max": max_lines})


@app.route("/api/campaign/interrupted", methods=["GET"])
@login_required
def api_campaign_interrupted():
    from models import Campaign
    user_id = current_user.id
    interrupted = Campaign.query.filter_by(user_id=user_id, status='interrupted').order_by(Campaign.updated_at.desc()).first()
    if not interrupted:
        return jsonify({"has_interrupted": False})
    return jsonify({
        "has_interrupted": True,
        "campaign": interrupted.to_dict(),
        "remaining": interrupted.total_count - interrupted.dialed_count,
    })


@app.route("/api/campaign/resume/<int:campaign_id>", methods=["POST"])
@login_required
def api_campaign_resume(campaign_id):
    from models import Campaign
    from storage import _campaign_db_ids, _campaign_key
    user_id = current_user.id
    camp = Campaign.query.filter_by(id=campaign_id, user_id=user_id, status='interrupted').first()
    if not camp:
        return jsonify({"error": "No interrupted campaign found"}), 404

    try:
        all_numbers = json.loads(camp.numbers)
    except Exception:
        return jsonify({"error": "Could not read campaign numbers"}), 500

    remaining_numbers = all_numbers[camp.dialed_count:]
    if not remaining_numbers:
        camp.status = 'completed'
        camp.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"error": "No remaining numbers to dial", "completed": True}), 400

    camp.status = 'active'
    camp.updated_at = datetime.utcnow()
    db.session.commit()

    key = _campaign_key(user_id)
    _campaign_db_ids[key] = camp.id

    set_campaign(
        camp.audio_url,
        camp.transfer_number,
        remaining_numbers,
        dial_mode=camp.dial_mode,
        batch_size=camp.batch_size,
        dial_delay=camp.dial_delay,
        from_number=camp.from_number,
        user_id=user_id,
        is_test=camp.is_test,
        gatekeeper_navigator_enabled=camp.gatekeeper_navigator_enabled,
        prospect_name=camp.prospect_name,
        prospect_company=camp.prospect_company,
        navigator_voice_id=camp.navigator_voice_id,
        navigator_knowledge_base=camp.navigator_knowledge_base,
    )

    start_dialer(user_id=user_id)

    logger.info(f"Resumed campaign {campaign_id} for user {user_id} with {len(remaining_numbers)} remaining numbers")
    return jsonify({
        "success": True,
        "campaign_id": campaign_id,
        "remaining_numbers": len(remaining_numbers),
        "total_numbers": camp.total_count,
        "already_dialed": camp.dialed_count,
    })


@app.route("/api/campaign/dismiss/<int:campaign_id>", methods=["POST"])
@login_required
def api_campaign_dismiss(campaign_id):
    from models import Campaign
    user_id = current_user.id
    camp = Campaign.query.filter_by(id=campaign_id, user_id=user_id, status='interrupted').first()
    if not camp:
        return jsonify({"error": "No interrupted campaign found"}), 404
    camp.status = 'dismissed'
    camp.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/campaign/history", methods=["GET"])
@login_required
def api_campaign_list():
    from models import Campaign
    user_id = current_user.id
    campaigns = Campaign.query.filter_by(user_id=user_id).order_by(Campaign.created_at.desc()).limit(20).all()
    return jsonify({"campaigns": [c.to_dict() for c in campaigns]})


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
    phone_number = data.get("phone_number", "").strip()
    if not phone_number_id:
        return jsonify({"error": "Phone number ID is required"}), 400
    result = release_number(phone_number_id)
    if result.get("success"):
        try:
            pn = None
            if phone_number:
                pn = ProvisionedNumber.query.filter_by(phone_number=phone_number, user_id=current_user.id).first()
            if not pn:
                pn = ProvisionedNumber.query.filter_by(telnyx_number_id=phone_number_id, user_id=current_user.id).first()
            if pn:
                pn.status = 'released'
                db.session.commit()
        except Exception as e:
            logger.warning(f"Could not update DB record on release: {e}")
        return jsonify({"success": True, "message": "Number released"})
    return jsonify(result), 400


@app.route("/api/numbers/swap-status", methods=["GET"])
@login_required
def api_numbers_swap_status():
    """Return quick-swap eligibility for the current user."""
    user_id = current_user.id
    swap_count = _get_quarterly_swap_count(user_id)
    free_remaining = max(0, FREE_SWAPS_PER_QUARTER - swap_count)
    balance = float(getattr(current_user, "credit_balance", 0) or 0)
    can_afford = free_remaining > 0 or balance >= float(QUICK_SWAP_COST)
    return jsonify({
        "success": True,
        "quarterly_swaps_used": swap_count,
        "free_swaps_remaining": free_remaining,
        "swap_cost": float(QUICK_SWAP_COST) if free_remaining == 0 else 0.0,
        "balance": balance,
        "can_afford": can_afford,
    })


@app.route("/api/numbers/quick-swap", methods=["POST"])
@login_required
def api_numbers_quick_swap():
    """Swap a number for a fresh one in the same area code.
    - 1st swap per quarter is free; subsequent swaps cost $2.00.
    - Purchases a new number, copies configuration, releases the old one.
    """
    user_id = current_user.id
    data = request.get_json() or {}
    old_number = data.get("phone_number", "").strip()
    if not old_number:
        return jsonify({"error": "phone_number is required"}), 400

    # Find the DB record for the old number
    pn_old = ProvisionedNumber.query.filter_by(phone_number=old_number, user_id=user_id, status="active").first()
    if not pn_old:
        return jsonify({"error": "Number not found or not active"}), 404

    # Determine cost
    swap_count = _get_quarterly_swap_count(user_id)
    is_free = swap_count < FREE_SWAPS_PER_QUARTER
    cost = Decimal("0.00") if is_free else QUICK_SWAP_COST

    # Check balance
    if not is_free:
        balance = Decimal(str(getattr(current_user, "credit_balance", 0) or 0))
        if balance < cost:
            return jsonify({
                "error": f"Insufficient balance. Quick Swap costs ${float(cost):.2f}. "
                         f"Your balance is ${float(balance):.2f}. Please add credits.",
                "code": "payment_required"
            }), 402

    # Extract area code from old number (strip +1 country code for US numbers)
    area_code = None
    cleaned = old_number.lstrip("+")
    if cleaned.startswith("1") and len(cleaned) == 11:
        area_code = cleaned[1:4]
    elif len(cleaned) == 10:
        area_code = cleaned[:3]

    if not area_code:
        return jsonify({"error": "Could not determine area code from number"}), 400

    # Search for a fresh number in the same area code
    search_result = search_available_numbers(area_code=area_code, limit=5)
    if not search_result.get("success") or not search_result.get("numbers"):
        return jsonify({"error": f"No replacement numbers available in area code {area_code}. Try releasing the number and searching manually."}), 400

    # Filter out the old number itself
    candidates = [n for n in search_result["numbers"] if n["phone_number"] != old_number]
    if not candidates:
        return jsonify({"error": f"No replacement numbers available in area code {area_code}."}), 400
    new_phone = candidates[0]["phone_number"]

    # Purchase the new number with the same connection
    connection_id = pn_old.telnyx_connection_id
    order_result = purchase_number(new_phone, connection_id)
    if not order_result.get("success"):
        return jsonify({"error": f"Failed to purchase replacement: {order_result.get('error')}"}), 400

    # Create DB record for new number, inherit is_included from old
    pn_new = ProvisionedNumber(
        user_id=user_id,
        phone_number=new_phone,
        status="active",
        telnyx_order_id=order_result.get("order_id"),
        telnyx_connection_id=connection_id,
        is_included=pn_old.is_included,
    )
    db.session.add(pn_new)

    # Release old number from Telnyx
    old_telnyx_id = pn_old.telnyx_number_id or pn_old.phone_number
    release_result = release_number(old_telnyx_id)
    if not release_result.get("success"):
        logger.warning(f"Quick swap: could not release {old_number} from Telnyx: {release_result.get('error')}")

    # Mark old number released in DB
    pn_old.status = "released"

    # Charge if not free
    if not is_free:
        user = current_user._get_current_object()
        user.credit_balance = (Decimal(str(user.credit_balance or 0)) - cost).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if user.credit_balance < 0:
            user.credit_balance = Decimal("0.00")

    # Log the swap
    swap_log = NumberSwapLog(
        user_id=user_id,
        old_number=old_number,
        new_number=new_phone,
        swap_cost=float(cost),
        was_free=is_free,
        swap_reason=data.get("reason", "manual"),
    )
    db.session.add(swap_log)
    db.session.commit()

    # Increment quarterly swap counter
    _increment_swap_count(user_id)

    logger.info(
        f"Quick swap for user {user_id}: {old_number} → {new_phone} "
        f"({'free' if is_free else f'${float(cost):.2f}'})"
    )

    return jsonify({
        "success": True,
        "old_number": old_number,
        "new_number": new_phone,
        "was_free": is_free,
        "cost": float(cost),
        "message": f"Successfully swapped {old_number} for {new_phone}."
                   + (" This swap was free." if is_free else f" ${float(cost):.2f} charged to your account."),
    })


@app.route("/api/numbers/apps", methods=["GET"])
@login_required
def api_numbers_apps():
    result = list_call_control_apps()
    if result.get("success"):
        is_role_admin = getattr(current_user, 'role', 'user') == 'admin'
        if not is_role_admin:
            user_conn_ids = set()
            user_numbers = ProvisionedNumber.query.filter_by(user_id=current_user.id).all()
            for pn in user_numbers:
                if pn.telnyx_connection_id:
                    user_conn_ids.add(pn.telnyx_connection_id)
            if user_conn_ids:
                filtered = [a for a in result.get("apps", []) if a.get("id") in user_conn_ids]
                result["apps"] = [{"name": "Your Line", "status": "active"} for _ in filtered]
            else:
                result["apps"] = []
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
    if getattr(current_user, 'role', 'user') != 'admin':
        return jsonify({"error": "Line profiles are configured automatically when you purchase a number."}), 403
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

        pn = ProvisionedNumber(user_id=user_id, phone_number=phone_number, status='provisioning', is_included=True)
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
        expires_at=datetime.utcnow() + _td(days=7),
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
    target = db.session.get(User, user_id)
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
    target = db.session.get(User, user_id)
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
    if invitation.is_expired:
        return render_template("setup_account.html", token=token, email="",
                               error="This invitation link has expired. Please contact the administrator for a new invite.",
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
            flash("Your password has been reset successfully. Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("reset_password.html", token=token, error=error)


@app.route("/super-admin")
@admin_required
def super_admin():
    from storage import _load_call_history, get_contacts
    from decimal import Decimal

    users = User.query.order_by(User.created_at.desc()).all()
    user_data = []
    all_calls = []
    total_credit_balance = Decimal("0.00")
    active_users_count = 0
    revoked_users_count = 0
    paused_users = []

    now = datetime.utcnow()
    today = now.date()
    today_str = now.strftime("%Y-%m-%d")
    week_ago_str = (now - _td(days=7)).strftime("%Y-%m-%dT")

    # 7-day chart buckets (ascending order)
    chart_dates = [(now - _td(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    chart_labels = [(now - _td(days=i)).strftime("%a") for i in range(6, -1, -1)]
    chart_counts = {d: 0 for d in chart_dates}

    # Platform health flags
    any_flagged = False
    any_at_risk = False
    any_capped = False

    for u in users:
        calls = _load_call_history(user_id=u.id)
        leads_count = len(get_contacts(user_id=u.id))
        numbers = ProvisionedNumber.query.filter_by(user_id=u.id, status='active').all()
        bal = Decimal(str(u.credit_balance or 0))
        total_credit_balance += bal

        if getattr(u, 'is_active_account', True):
            active_users_count += 1
        else:
            revoked_users_count += 1

        user_calls_today = 0
        user_vm_count = 0
        user_transfer_count = 0
        user_calls_week = 0
        last_call_time = None
        calls_7d_by_number = {}
        answered_7d_by_number = {}

        for c in calls:
            ts = c.get("timestamp", "")
            ts_date = ts[:10]
            if ts.startswith(today_str):
                user_calls_today += 1
            if ts >= week_ago_str:
                user_calls_week += 1
                fn = c.get("from_number", "")
                if fn:
                    calls_7d_by_number[fn] = calls_7d_by_number.get(fn, 0) + 1
                    if (c.get("amd_result") == "human" or
                            c.get("status") in ("transferred", "human_answered") or
                            c.get("transferred")):
                        answered_7d_by_number[fn] = answered_7d_by_number.get(fn, 0) + 1
            if c.get("voicemail_dropped"):
                user_vm_count += 1
            if c.get("transferred"):
                user_transfer_count += 1
            if ts and (last_call_time is None or ts > last_call_time):
                last_call_time = ts
            if ts_date in chart_counts:
                chart_counts[ts_date] += 1

        all_calls.extend(calls)

        # Number health summary
        health_counts = {"healthy": 0, "at_risk": 0, "flagged": 0, "new": 0}
        cooling_numbers = []
        all_numbers_capped = len(numbers) > 0

        for n in numbers:
            if n.last_dial_date and n.last_dial_date < today:
                daily = 0
            else:
                daily = n.daily_dial_count or 0
            is_cooling = daily >= DAILY_DIAL_CAP
            if not is_cooling:
                all_numbers_capped = False
            else:
                cooling_numbers.append(n.phone_number)

            calls_7d = calls_7d_by_number.get(n.phone_number, 0)
            answered_7d = answered_7d_by_number.get(n.phone_number, 0)
            ar = round(answered_7d / calls_7d * 100, 1) if calls_7d > 0 else None
            health = _compute_number_health(ar, calls_7d)
            health_counts[health] = health_counts.get(health, 0) + 1

        if len(numbers) == 0:
            all_numbers_capped = False

        if health_counts.get("flagged", 0) > 0:
            any_flagged = True
        if health_counts.get("at_risk", 0) > 0:
            any_at_risk = True
        if all_numbers_capped:
            any_capped = True
            paused_users.append({
                "name": u.profile_name or u.email.split("@")[0],
                "email": u.email,
                "cooling_count": len(cooling_numbers),
                "total_numbers": len(numbers),
            })

        user_data.append({
            "id": u.id,
            "email": u.email,
            "name": u.profile_name or u.email.split("@")[0],
            "leads": leads_count,
            "calls": len(calls),
            "calls_today": user_calls_today,
            "calls_week": user_calls_week,
            "voicemails": user_vm_count,
            "transfers": user_transfer_count,
            "number_count": len(numbers),
            "health_counts": health_counts,
            "all_numbers_capped": all_numbers_capped,
            "credit_balance": float(bal),
            "role": u.role or "user",
            "active": getattr(u, 'is_active_account', True),
            "created_at": u.created_at.strftime("%b %d, %Y") if u.created_at else "N/A",
            "last_activity": last_call_time[:16].replace("T", " ") if last_call_time else "Never",
        })

    platform_calls_today = sum(1 for c in all_calls if c.get("timestamp", "").startswith(today_str))
    platform_calls_week = sum(1 for c in all_calls if c.get("timestamp", "") >= week_ago_str)
    platform_vm_total = sum(1 for c in all_calls if c.get("voicemail_dropped"))
    platform_transfers_total = sum(1 for c in all_calls if c.get("transferred"))
    platform_vm_rate = round((platform_vm_total / len(all_calls) * 100), 1) if all_calls else 0
    platform_transfer_rate = round((platform_transfers_total / len(all_calls) * 100), 1) if all_calls else 0

    # Compute platform health
    if any_flagged:
        platform_health = "red"
        platform_health_text = "Numbers flagged as spam — some users' calls not being answered"
    elif any_capped:
        platform_health = "yellow"
        platform_health_text = "Some users paused — daily dial cap reached"
    elif any_at_risk:
        platform_health = "yellow"
        platform_health_text = "Some numbers showing declining answer rates"
    else:
        platform_health = "green"
        platform_health_text = "All systems running normally"

    total_numbers = ProvisionedNumber.query.filter_by(status='active').count()
    pending_invites = Invitation.query.filter_by(used=False).count()

    stats = {
        "total_users": len(users),
        "active_users": active_users_count,
        "revoked_users": revoked_users_count,
        "total_credit_balance": float(total_credit_balance),
        "total_calls": len(all_calls),
        "calls_today": platform_calls_today,
        "calls_week": platform_calls_week,
        "voicemails_total": platform_vm_total,
        "transfers_total": platform_transfers_total,
        "vm_rate": platform_vm_rate,
        "transfer_rate": platform_transfer_rate,
        "active_lines": total_numbers,
        "pending_invites": pending_invites,
        "platform_health": platform_health,
        "platform_health_text": platform_health_text,
        "paused_users": paused_users,
        "chart_labels": chart_labels,
        "chart_values": [chart_counts[d] for d in chart_dates],
    }

    return render_template("super_admin.html", users=user_data, stats=stats)


@app.route("/api/admin/cost-usage")
@admin_required
def api_admin_cost_usage():
    from storage import _load_call_history
    from decimal import Decimal, ROUND_HALF_UP

    AMD_COST = Decimal("0.00625")
    VOICE_RATE = Decimal("0.004")
    NO_ANSWER_MINS = Decimal("0.58")
    MACHINE_MINS = Decimal("1.5")
    HUMAN_MINS = Decimal("2.0")
    TRANSCRIPTION_RATE = Decimal("0.05")
    TRANSCRIPTION_MINS = Decimal("2.0")
    RECORDING_RATE = Decimal("0.002")
    RECORDING_MINS = Decimal("2.0")
    TRANSFER_BRIDGE_RATE = Decimal("0.004")
    TRANSFER_BRIDGE_MINS = Decimal("4.0")
    PHONE_NUMBER_MONTHLY = Decimal("1.00")
    ELEVENLABS_CHARS_PER_VM = 350
    ELEVENLABS_PER_1K_CHARS = Decimal("0.30")
    REPLIT_MONTHLY = Decimal("25.00")
    SUBSCRIPTION_MONTHLY = Decimal("99.00")
    CREDIT_PER_CALL = Decimal("0.10")

    users_list = User.query.order_by(User.created_at.desc()).all()
    active_user_count = max(1, sum(1 for u in users_list if getattr(u, 'is_active_account', True)))

    infra_share = (REPLIT_MONTHLY / Decimal(str(active_user_count))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    user_costs = []
    platform_total_cost = Decimal("0")
    platform_total_revenue = Decimal("0")

    for u in users_list:
        calls = _load_call_history(user_id=u.id)
        active_numbers = ProvisionedNumber.query.filter_by(user_id=u.id, status='active').count()

        calls_total = len(calls)
        voicemails_dropped = sum(1 for c in calls if c.get("voicemail_dropped"))
        transfers_done = sum(1 for c in calls if c.get("transferred"))
        machines_detected = sum(1 for c in calls if c.get("machine_detected"))
        humans_detected = transfers_done
        no_answers = max(0, calls_total - machines_detected - humans_detected)

        telnyx_amd = AMD_COST * calls_total
        voice_no_answer = VOICE_RATE * NO_ANSWER_MINS * no_answers
        voice_machine = VOICE_RATE * MACHINE_MINS * machines_detected
        voice_human = VOICE_RATE * HUMAN_MINS * humans_detected
        telnyx_voice = (voice_no_answer + voice_machine + voice_human).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        telnyx_transcription = (TRANSCRIPTION_RATE * TRANSCRIPTION_MINS * humans_detected).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        telnyx_recording = (RECORDING_RATE * RECORDING_MINS * humans_detected).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        telnyx_transfer_bridge = (TRANSFER_BRIDGE_RATE * TRANSFER_BRIDGE_MINS * transfers_done).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        telnyx_phone = PHONE_NUMBER_MONTHLY * active_numbers
        telnyx_total = (telnyx_amd + telnyx_voice + telnyx_transcription + telnyx_recording + telnyx_transfer_bridge + telnyx_phone).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        el_chars = voicemails_dropped * ELEVENLABS_CHARS_PER_VM
        elevenlabs_cost = (Decimal(str(el_chars)) * ELEVENLABS_PER_1K_CHARS / Decimal("1000")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        total_cost = (telnyx_total + elevenlabs_cost + infra_share).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        revenue_credits = (CREDIT_PER_CALL * calls_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        revenue_total = (SUBSCRIPTION_MONTHLY + revenue_credits).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if calls_total > 0 else Decimal("0")

        gross_profit = revenue_total - total_cost
        margin_pct = round(float(gross_profit / revenue_total * 100), 1) if revenue_total > 0 else 0

        platform_total_cost += total_cost
        platform_total_revenue += revenue_total

        user_costs.append({
            "id": u.id,
            "name": u.profile_name or u.email.split("@")[0],
            "email": u.email,
            "calls_total": calls_total,
            "voicemails_dropped": voicemails_dropped,
            "transfers_done": transfers_done,
            "machines_detected": machines_detected,
            "telnyx_amd": float(telnyx_amd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "telnyx_voice": float(telnyx_voice),
            "telnyx_transcription": float(telnyx_transcription),
            "telnyx_recording": float(telnyx_recording),
            "telnyx_transfer_bridge": float(telnyx_transfer_bridge),
            "telnyx_phone": float(telnyx_phone),
            "telnyx_total": float(telnyx_total),
            "elevenlabs_cost": float(elevenlabs_cost),
            "infra_share": float(infra_share),
            "total_cost": float(total_cost),
            "revenue_credits": float(revenue_credits),
            "revenue_total": float(revenue_total),
            "gross_profit": float(gross_profit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "margin_pct": margin_pct,
        })

    platform_gross_profit = platform_total_revenue - platform_total_cost
    platform_margin = round(float(platform_gross_profit / platform_total_revenue * 100), 1) if platform_total_revenue > 0 else 0

    return jsonify({
        "users": user_costs,
        "platform": {
            "total_cost": float(platform_total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "total_revenue": float(platform_total_revenue.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "gross_profit": float(platform_gross_profit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "margin_pct": platform_margin,
            "replit_cost": float(REPLIT_MONTHLY),
            "active_users": active_user_count,
        },
        "rates": {
            "amd_per_call": float(AMD_COST),
            "voice_per_min": float(VOICE_RATE),
            "transcription_per_min": float(TRANSCRIPTION_RATE),
            "recording_per_min": float(RECORDING_RATE),
            "transfer_bridge_per_min": float(TRANSFER_BRIDGE_RATE),
            "phone_monthly": float(PHONE_NUMBER_MONTHLY),
            "elevenlabs_per_1k_chars": float(ELEVENLABS_PER_1K_CHARS),
            "credit_per_call": float(CREDIT_PER_CALL),
        }
    })


@app.route("/api/admin/user-activity/<int:uid>")
@admin_required
def api_admin_user_activity(uid):
    target_user = db.session.get(User, uid)
    if not target_user:
        return jsonify({"error": "User not found"}), 404
    from storage import _load_call_history, get_contacts
    from decimal import Decimal
    calls = _load_call_history(user_id=uid)
    contacts = get_contacts(user_id=uid)
    numbers = ProvisionedNumber.query.filter_by(user_id=uid).all()

    vm_count = sum(1 for c in calls if c.get("voicemail_dropped"))
    transfer_count = sum(1 for c in calls if c.get("transferred"))
    failed_count = len(calls) - vm_count - transfer_count
    vm_rate = round((vm_count / len(calls) * 100), 1) if calls else 0
    transfer_rate = round((transfer_count / len(calls) * 100), 1) if calls else 0

    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")
    week_ago = (now - _td(days=7)).strftime("%Y-%m-%dT")
    calls_today = sum(1 for c in calls if c.get("timestamp", "").startswith(today_str))
    calls_week = sum(1 for c in calls if c.get("timestamp", "") >= week_ago)

    recent = []
    for c in (calls[-30:] if calls else []):
        recent.append({
            "number": c.get("number", "Unknown"),
            "status": c.get("status", "unknown"),
            "transferred": c.get("transferred", False),
            "voicemail_dropped": c.get("voicemail_dropped", False),
            "timestamp": c.get("timestamp", ""),
            "amd_result": c.get("amd_result", ""),
        })

    return jsonify({
        "user": {
            "id": uid,
            "email": target_user.email,
            "name": target_user.profile_name or "",
            "role": target_user.role or "user",
            "active": getattr(target_user, 'is_active_account', True),
            "credit_balance": float(Decimal(str(target_user.credit_balance or 0))),
            "joined": target_user.created_at.strftime("%b %d, %Y") if target_user.created_at else "N/A",
        },
        "total_calls": len(calls),
        "total_leads": len(contacts),
        "calls_today": calls_today,
        "calls_week": calls_week,
        "voicemails": vm_count,
        "transfers": transfer_count,
        "failed": failed_count,
        "vm_rate": vm_rate,
        "transfer_rate": transfer_rate,
        "numbers": [{"phone": n.phone_number, "status": n.status} for n in numbers],
        "recent_calls": recent,
    })


@app.route("/api/admin/features/<int:uid>", methods=["GET"])
@admin_required
def api_admin_get_features(uid):
    """Return all feature flags for a user, including plan info and feature definitions."""
    target = db.session.get(User, uid)
    if not target:
        return jsonify({"success": False, "error": "User not found"}), 404
    plan = _get_user_plan(uid) or "none"
    features = _get_user_features(uid)
    rows = {r.feature_key: r for r in UserFeature.query.filter_by(user_id=uid).all()}
    result = []
    for key, meta in FEATURE_DEFINITIONS.items():
        row = rows.get(key)
        result.append({
            "key": key,
            "label": meta["label"],
            "desc": meta["desc"],
            "enabled": features.get(key, False),
            "plan_includes": key in PLAN_FEATURES.get(plan, []),
            "note": row.note if row else None,
            "updated_at": row.updated_at.strftime("%b %d, %Y %H:%M") if row and row.updated_at else None,
        })
    return jsonify({
        "success": True,
        "user_id": uid,
        "user_name": target.profile_name or target.email.split("@")[0],
        "plan": plan,
        "features": result,
        "plan_definitions": {k: list(v) for k, v in PLAN_FEATURES.items()},
    })


@app.route("/api/admin/features/<int:uid>", methods=["POST"])
@admin_required
def api_admin_set_features(uid):
    """Bulk-update feature flags for a user. Body: {features: {key: bool}, note: str}"""
    target = db.session.get(User, uid)
    if not target:
        return jsonify({"success": False, "error": "User not found"}), 404
    data = request.get_json() or {}
    updates = data.get("features", {})
    note = (data.get("note") or "").strip() or "admin:manual"
    if not isinstance(updates, dict):
        return jsonify({"success": False, "error": "features must be an object"}), 400
    admin_id = current_user.id if current_user.is_authenticated else None
    changed = []
    for key, enabled in updates.items():
        if key in FEATURE_DEFINITIONS:
            _set_feature(uid, key, bool(enabled), granted_by=admin_id, note=note)
            changed.append(key)
    logger.info(f"Admin {admin_id} updated features for user {uid}: {changed}")
    return jsonify({"success": True, "updated": changed, "features": _get_user_features(uid)})


@app.route("/api/admin/features/<int:uid>/provision", methods=["POST"])
@admin_required
def api_admin_provision_features(uid):
    """Set all features for a given plan (resets to plan defaults)."""
    target = db.session.get(User, uid)
    if not target:
        return jsonify({"success": False, "error": "User not found"}), 404
    data = request.get_json() or {}
    plan = (data.get("plan") or "").lower().strip()
    if plan not in PLAN_FEATURES and plan != "none":
        return jsonify({"success": False, "error": f"Unknown plan: {plan}"}), 400
    admin_id = current_user.id if current_user.is_authenticated else None
    if plan == "none":
        for key in FEATURE_DEFINITIONS:
            _set_feature(uid, key, False, granted_by=admin_id, note="admin:reset")
    else:
        _provision_plan_features(uid, plan, granted_by=admin_id)
        _upsert_user_app_data(uid, "active_plan", json.dumps({"plan": plan}))
    return jsonify({"success": True, "plan": plan, "features": _get_user_features(uid)})


@app.route("/api/admin/swap-log")
@admin_required
def api_admin_swap_log():
    """Return all Quick Swap records for super admin visibility."""
    try:
        swaps = NumberSwapLog.query.order_by(NumberSwapLog.swapped_at.desc()).limit(200).all()
        user_map = {}
        for s in swaps:
            if s.user_id not in user_map:
                u = db.session.get(User, s.user_id)
                user_map[s.user_id] = (u.profile_name or u.email.split("@")[0]) if u else f"User {s.user_id}"
        return jsonify({
            "success": True,
            "swaps": [{
                "id": s.id,
                "user_id": s.user_id,
                "user_name": user_map.get(s.user_id, f"User {s.user_id}"),
                "old_number": s.old_number,
                "new_number": s.new_number,
                "swap_cost": float(s.swap_cost),
                "was_free": s.was_free,
                "swap_reason": s.swap_reason or "manual",
                "swapped_at": s.swapped_at.strftime("%b %d, %Y %H:%M UTC") if s.swapped_at else "",
            } for s in swaps]
        })
    except Exception as e:
        logger.error(f"Error loading swap log: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/request-feature", methods=["POST"])
@login_required
def request_feature_access():
    """User requests access to a locked feature — fires a Telegram notification to the owner."""
    try:
        data = request.get_json() or {}
        feature_key = str(data.get("feature_key", ""))[:64]
        feature_label = str(data.get("feature_label", feature_key))[:128]
        user_plan = _get_user_plan(current_user.id) or "none"

        def _notify():
            try:
                bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
                chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
                if not bot_token or not chat_id:
                    return
                msg = (
                    f"\U0001f511 *Feature Access Request*\n\n"
                    f"*User:* {current_user.email} (ID: {current_user.id})\n"
                    f"*Feature:* {feature_label} (`{feature_key}`)\n"
                    f"*Current Plan:* {user_plan}"
                )
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
                    timeout=10,
                )
                logger.info(f"Feature request notification sent: {feature_key} by {current_user.email}")
            except Exception as e:
                logger.error(f"Feature request Telegram notify failed: {e}")

        threading.Thread(target=_notify, daemon=True).start()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Request feature error: {e}")
        return jsonify({"success": False, "error": "Server error"}), 500


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
    from humana_voice import fish_client as _fc
    def _fetch_fish_key_from_db():
        try:
            return AppConfig.get("fish_audio_api_key", "")
        except Exception:
            return ""
    _fc.register_db_key_fetcher(_fetch_fish_key_from_db)
    _fc.log_startup_status()
    _fish_key_name = _fc.get_key_source()
    if _fish_key_name:
        print(f"  Fish Audio: CONFIGURED (source: {_fish_key_name})")
    else:
        print("  Fish Audio: NOT CONFIGURED — enter key in dashboard Settings or set FISH_AUDIO_API_KEY env var")
    print("=" * 60)

_init_app()

from telegram_bot import start_telegram_bot
start_telegram_bot(app)

# ---- Main Entry Point ----
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
