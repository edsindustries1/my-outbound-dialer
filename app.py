"""
app.py - Main Flask application for the Voicemail Drop System.
Handles web dashboard, file uploads, webhook processing, and campaign control.
"""

import os
import csv
import io
import re
import logging
import threading
import functools
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for
from werkzeug.utils import secure_filename
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
)
from telnyx_client import (
    transfer_call, play_audio, hangup_call, make_call, validate_connection_id,
    set_webhook_base_url, start_transcription, start_recording,
    search_available_numbers, purchase_number, create_call_control_app,
    assign_number_to_app, list_owned_numbers, release_number,
    list_call_control_apps, get_number_order_status,
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
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

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

APP_PASSWORD = os.environ.get("APP_PASSWORD", "")


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not APP_PASSWORD:
            return f(*args, **kwargs)
        if not session.get("authenticated"):
            if request.is_json or request.headers.get("X-Requested-With"):
                return jsonify({"error": "Not authenticated"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ---- Landing Page ----
@app.route("/")
def landing():
    """Serve the public landing page."""
    _detect_and_set_base_url()
    return render_template("landing.html")


# ---- Lead Capture ----
@app.route("/api/lead", methods=["POST"])
def api_lead():
    """Receive lead form submission and email to owner."""
    try:
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        phone = data.get("phone", "").strip()
        company = data.get("company", "").strip()
        team_size = data.get("team_size", "").strip()

        if not name or not email or not phone:
            return jsonify({"success": False, "error": "Name, email, and phone are required"}), 400

        name = html_module.escape(name)
        email = html_module.escape(email)
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
  <p style="margin:0;font-size:12px;color:#9ca3af;">This lead was captured from your Open Human landing page.<br>&#169; 2026 Open Human &mdash; AI-Powered Sales Dialer</p>
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
        result = send_email(
            to_email="edsindutires1@gmail.com",
            subject="1 Hot Lead Received Just Now",
            html_body=html_body,
            text_body=text_body
        )

        if result:
            logger.info(f"Lead captured and emailed: {name} ({email}, {phone})")
            return jsonify({"success": True})
        else:
            logger.error(f"Lead captured but email failed: {name} ({email})")
            return jsonify({"success": False, "error": "Failed to send notification email"}), 500

    except Exception as e:
        logger.error(f"Lead capture error: {e}")
        return jsonify({"success": False, "error": "Server error"}), 500


# ---- Login Route ----
@app.route("/login", methods=["GET", "POST"])
def login():
    _detect_and_set_base_url()
    if not APP_PASSWORD:
        return redirect(url_for("dashboard"))
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        pw = request.form.get("password", "")
        if pw == APP_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        error = "Incorrect password"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("authenticated", None)
    return redirect(url_for("landing"))


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
        else:
            env_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
            if env_url:
                _detected_base_url = env_url
                set_webhook_base_url(env_url)
    except Exception:
        pass


# ---- Dashboard Route ----
@app.route("/dashboard")
@login_required
def dashboard():
    """Serve the main dashboard page (requires authentication)."""
    _detect_and_set_base_url()
    telnyx_from = os.environ.get("TELNYX_FROM_NUMBER", "Not set")
    return render_template("index.html", telnyx_from=telnyx_from)


# ---- Audio File Serving ----
@app.route("/audio/<filename>")
def serve_audio(filename):
    """Serve uploaded audio files so Telnyx can access them (no auth - Telnyx needs direct access)."""
    response = send_from_directory(UPLOAD_FOLDER, filename)
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/audio/personalized/<filename>")
def serve_personalized_audio(filename):
    """Serve personalized voicemail audio files (no auth - Telnyx needs direct access)."""
    pvm_dir = os.path.join(UPLOAD_FOLDER, "personalized")
    response = send_from_directory(pvm_dir, filename)
    response.headers["Cache-Control"] = "no-cache"
    return response


# ---- Start Campaign ----
@app.route("/start", methods=["POST"])
@login_required
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
        audio_url = get_voicemail_url()
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
    set_campaign(audio_url, transfer_number, numbers, dial_mode=dial_mode, batch_size=batch_size, dial_delay=dial_delay, from_number=campaign_from_number)

    if voicemail_type == "personalized":
        pvm_template_id = request.form.get("pvm_template_id", "").strip()
        pvm_voice_id = request.form.get("pvm_voice_id", "").strip()
        pvm_model_id = request.form.get("pvm_model_id", "eleven_turbo_v2_5").strip()
        pvm_script = ""

        if pvm_template_id:
            from storage import get_vm_templates as _gvt
            templates = _gvt()
            for t in templates:
                if t.get("id") == pvm_template_id and t.get("type") == "script":
                    pvm_script = t.get("content", "")
                    mark_vm_template_used(pvm_template_id)
                    break

        if not pvm_script:
            pvm_script = request.form.get("pvm_script", "").strip()

        if not pvm_script:
            return jsonify({"error": "No personalized voicemail script template selected"}), 400
        if not pvm_voice_id:
            preset = get_voice_preset()
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

    start_dialer()
    return jsonify({"message": f"Campaign started with {len(numbers)} numbers", "voicemail_type": voicemail_type})


# ---- Test Call ----
@app.route("/test_call", methods=["POST"])
@login_required
def test_call():
    """Place a single test call to verify everything is working."""
    _detect_and_set_base_url()
    number = request.form.get("test_number", "").strip()
    if not number:
        return jsonify({"error": "No phone number provided"}), 400

    transfer_number = request.form.get("transfer_number", "").strip()
    vm_url = get_voicemail_url()
    camp = get_campaign()
    transfer_num = transfer_number or camp.get("transfer_number") or ""
    if not transfer_num:
        return jsonify({"error": "Transfer number is required for test calls"}), 400
    audio = camp.get("audio_url") or vm_url
    set_campaign(audio, transfer_num, [number], dial_mode="sequential", batch_size=1)

    logger.info(f"Placing test call to {number}")
    call_control_id = make_call(number)

    if call_control_id:
        create_call_state(call_control_id, number)
        update_call_state(call_control_id, status="test_call_ringing",
                          status_description="Ringing", status_color="blue")
        logger.info(f"Test call placed successfully to {number}")
        return jsonify({"message": f"Test call placed to {number}", "call_control_id": call_control_id})
    else:
        logger.error(f"Test call failed to {number}")
        return jsonify({"error": "Failed to place call. Check your Telnyx credentials."}), 500


# ---- Stop Campaign ----
@app.route("/stop", methods=["POST"])
@login_required
def stop():
    """Stop the current campaign. Active calls will finish but no new calls are placed."""
    stop_campaign()
    resume_after_transfer()
    logger.info("Campaign stopped by user")
    return jsonify({"message": "Campaign stopped"})


# ---- Status Endpoint (polled by frontend) ----
@app.route("/status")
@login_required
def status():
    """Return current call statuses and campaign info for the dashboard."""
    camp = get_campaign()
    return jsonify({
        "active": camp["active"],
        "stop_requested": camp["stop_requested"],
        "total": len(camp["numbers"]),
        "dialed_count": camp["dialed_count"],
        "transfer_paused": is_transfer_paused(),
        "calls": get_all_statuses(),
    })


# ---- Voicemail Settings API ----
@app.route("/api/voicemail_settings", methods=["GET"])
@login_required
def get_vm_settings():
    url = get_voicemail_url()
    return jsonify({"voicemail_url": url})


@app.route("/api/voicemail_settings", methods=["POST"])
@login_required
def save_vm_settings():
    data = request.get_json() or {}
    url = data.get("voicemail_url", "").strip()
    if not url:
        return jsonify({"error": "Voicemail URL is required"}), 400
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "URL must start with http:// or https://"}), 400
    save_voicemail_url(url)
    logger.info(f"Voicemail URL updated: {url}")
    return jsonify({"message": "Voicemail URL saved", "voicemail_url": url})


@app.route("/api/voice-preset", methods=["GET"])
@login_required
def get_voice_preset_api():
    preset = get_voice_preset()
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
    save_voice_preset(preset)
    logger.info(f"Voice preset saved: {preset.get('voice_id')}")
    return jsonify({"message": "Voice preset saved", "preset": preset})


# ---- Clear Call Logs ----
@app.route("/clear_logs", methods=["POST"])
@login_required
def clear_logs():
    from storage import clear_call_states
    camp = get_campaign()
    if camp.get("active"):
        return jsonify({"error": "Cannot clear logs while campaign is active"}), 400
    clear_call_states()
    clear_call_history()
    logger.info("Call logs cleared by user")
    return jsonify({"message": "Call logs cleared"})


# ---- Download Call Report ----
@app.route("/download_report")
@login_required
def download_report():
    """Download call history as CSV with optional date filtering."""
    start_date = request.args.get("start", "")
    end_date = request.args.get("end", "")

    history = get_call_history(start_date=start_date or None, end_date=end_date or None)

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
    return jsonify({"dnc": get_dnc_list()})


@app.route("/api/dnc", methods=["POST"])
@login_required
def api_dnc_add():
    data = request.get_json() or {}
    number = data.get("number", "").strip()
    reason = data.get("reason", "manual")
    if not number:
        return jsonify({"error": "Phone number is required"}), 400
    if add_to_dnc(number, reason):
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
    if remove_from_dnc(number):
        logger.info(f"DNC: Removed {number}")
        return jsonify({"message": f"Removed {number} from DNC list"})
    return jsonify({"error": "Number not found in DNC list"}), 404


# ---- Analytics API ----
@app.route("/api/analytics", methods=["GET"])
@login_required
def api_analytics():
    return jsonify(get_analytics())


# ---- Campaign Scheduling API ----
@app.route("/api/schedules", methods=["GET"])
@login_required
def api_schedules_list():
    return jsonify({"schedules": get_schedules()})


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
        "audio_url": data.get("audio_url", "") or get_voicemail_url(),
        "dial_mode": dial_mode,
        "batch_size": batch_size,
        "timezone": timezone,
        "total_numbers": len(numbers),
    })
    logger.info(f"Schedule created: {schedule['id']} for {scheduled_time} with {len(numbers)} numbers")
    return jsonify({"message": "Campaign scheduled", "schedule": schedule})


@app.route("/api/schedules/<schedule_id>", methods=["DELETE"])
@login_required
def api_schedule_delete(schedule_id):
    if delete_schedule(schedule_id):
        logger.info(f"Schedule deleted: {schedule_id}")
        return jsonify({"message": "Schedule deleted"})
    return jsonify({"error": "Schedule not found"}), 404


@app.route("/api/schedules/<schedule_id>/cancel", methods=["POST"])
@login_required
def api_schedule_cancel(schedule_id):
    if cancel_schedule(schedule_id):
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
    return jsonify({"templates": get_templates()})


@app.route("/api/templates", methods=["POST"])
@login_required
def api_template_save():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Template name is required"}), 400
    template = save_template(name, data)
    logger.info(f"Template saved: {name} ({template['id']})")
    return jsonify({"template": template})


@app.route("/api/templates/<template_id>", methods=["DELETE"])
@login_required
def api_template_delete(template_id):
    if delete_template(template_id):
        logger.info(f"Template deleted: {template_id}")
        return jsonify({"message": "Template deleted"})
    return jsonify({"error": "Template not found"}), 404


# ---- Voicemail Templates API ----

@app.route("/api/vm-templates", methods=["GET"])
@login_required
def api_vm_templates_list():
    return jsonify({"templates": get_vm_templates()})


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
    existing = _get_vmt()
    if len(existing) >= 5:
        return jsonify({"error": "Maximum 5 templates allowed. Delete one to create a new one."}), 400
    template = save_vm_template({"name": name, "type": ttype, "content": content})
    logger.info(f"VM template created: {name} ({template['id']})")
    return jsonify({"template": template})


@app.route("/api/vm-templates/<template_id>", methods=["PUT"])
@login_required
def api_vm_template_update(template_id):
    data = request.get_json() or {}
    updated = update_vm_template(template_id, data)
    if updated:
        logger.info(f"VM template updated: {template_id}")
        return jsonify({"template": updated})
    return jsonify({"error": "Template not found"}), 404


@app.route("/api/vm-templates/<template_id>", methods=["DELETE"])
@login_required
def api_vm_template_delete(template_id):
    if delete_vm_template(template_id):
        logger.info(f"VM template deleted: {template_id}")
        return jsonify({"message": "Template deleted"})
    return jsonify({"error": "Template not found"}), 404


@app.route("/api/vm-templates/<template_id>/use", methods=["POST"])
@login_required
def api_vm_template_mark_used(template_id):
    mark_vm_template_used(template_id)
    return jsonify({"message": "ok"})


# ---- Number Validation API ----
@app.route("/api/validate-numbers", methods=["POST"])
@login_required
def api_validate_numbers():
    data = request.get_json() or {}
    numbers_text = data.get("numbers", "")
    if not numbers_text.strip():
        return jsonify({"error": "No numbers provided"}), 400
    results = validate_phone_numbers(numbers_text)
    return jsonify(results)


# ---- Contact Management API ----
@app.route("/api/contacts", methods=["GET"])
@login_required
def api_contacts_list():
    tag = request.args.get("tag", "")
    group = request.args.get("group", "")
    contacts = get_contacts(tag=tag or None, group=group or None)
    groups = get_contact_groups()
    tags = get_contact_tags()
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

    result = add_contacts(new_contacts, group=group, tags=tags)
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

    result = add_contacts(contacts, group=group, tags=tags)
    logger.info(f"CSV import: {result['added']} new, {result['duplicates']} duplicates")
    return jsonify(result)


@app.route("/api/contacts/<contact_id>", methods=["PUT"])
@login_required
def api_contact_update(contact_id):
    data = request.get_json() or {}
    updated = update_contact(contact_id, data)
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
    removed = delete_contacts(ids)
    return jsonify({"removed": removed})


@app.route("/api/contacts/clear", methods=["POST"])
@login_required
def api_contacts_clear():
    clear_contacts()
    return jsonify({"message": "All contacts cleared"})


# ---- Email Report Settings API ----
@app.route("/api/report-settings", methods=["GET"])
@login_required
def api_report_settings_get():
    settings = get_report_settings()
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
    settings = save_report_settings(filtered)
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
    return jsonify(get_campaign_history_summary())


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


# ---- Telnyx Webhook Handler ----
@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Receive and process Telnyx webhook events.
    Always returns 200 immediately to avoid timeouts.
    All call logic decisions are made here based on event type.
    """
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

    to_number = payload.get("to", "")
    from_number = payload.get("from", "")
    call_number = to_number or from_number

    state = get_call_state(call_control_id)

    camp = get_campaign()
    transfer_num = camp.get("transfer_number", "")
    is_transfer_leg = False
    if not state and call_control_id and call_number:
        normalized_to = to_number.lstrip("+").replace("-", "").replace(" ", "")
        normalized_transfer = transfer_num.lstrip("+").replace("-", "").replace(" ", "")
        if transfer_num and normalized_transfer and normalized_to and (normalized_transfer in normalized_to or normalized_to in normalized_transfer):
            is_transfer_leg = True
            logger.info(f"Transfer leg detected: {call_control_id} to {to_number} (transfer number: {transfer_num})")
        else:
            create_call_state(call_control_id, call_number)
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
                    resume_after_transfer(cid_key)
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
            """If AMD event never arrives, treat as human and transfer."""
            state = get_call_state(ccid)
            if state and not state.get("amd_received") and state.get("status") == "answered":
                logger.warning(f"AMD timeout on {ccid}, treating as HUMAN and transferring")
                update_call_state(ccid, machine_detected=False, status="human_detected", amd_received=True,
                                  amd_result="timeout", status_description="AMD detection timeout", status_color="yellow")
                camp = get_campaign()
                transfer_num = camp.get("transfer_number", "")
                customer_num = state.get("number", "")
                if transfer_num and mark_transferred(ccid):
                    logger.info(f"Fallback transfer {ccid} to {transfer_num} (caller ID: {customer_num})")
                    success = transfer_call(ccid, transfer_num, customer_number=customer_num)
                    if success:
                        pause_for_transfer(ccid)
                        logger.info(f"Campaign paused for transfer on {ccid}")
                        update_call_state(ccid, status="transferred",
                                          status_description="Answered by human - transferred (campaign paused)", status_color="green")
                    else:
                        logger.error(f"Fallback transfer failed for {ccid}, hanging up")
                        update_call_state(ccid, status="transfer_failed",
                                          status_description="Transfer failed", status_color="red")
                        hangup_call(ccid)
                else:
                    logger.warning(f"AMD timeout on {ccid}, no transfer number configured, hanging up")
                    update_call_state(ccid, status="human_no_transfer",
                                      status_description="Human answered - no transfer number", status_color="yellow")
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
        logger.info(f"AMD result: {result} for {call_control_id}")

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
            camp = get_campaign()
            transfer_num = camp.get("transfer_number", "")
            customer_num = (get_call_state(call_control_id) or {}).get("number", "")
            if transfer_num and mark_transferred(call_control_id):
                logger.info(f"HUMAN detected - transferring {call_control_id} to {transfer_num} (caller ID: {customer_num})")
                success = transfer_call(call_control_id, transfer_num, customer_number=customer_num)
                if success:
                    pause_for_transfer(call_control_id)
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
                              amd_result="machine", status_description="Machine detected - dropping voicemail", status_color="blue")
            logger.info(f"MACHINE detected on {call_control_id}, playing voicemail immediately")

            if mark_voicemail_dropped(call_control_id):
                update_call_state(call_control_id, status_description="Dropping voicemail...", status_color="blue")
                camp = get_campaign()
                state = get_call_state(call_control_id)
                customer_number = (state or {}).get("number", "")
                personalized_url = get_personalized_audio_url(customer_number) if customer_number else None
                audio_url = personalized_url or camp.get("audio_url", "") or get_voicemail_url()
                if personalized_url:
                    logger.info(f"Using PERSONALIZED voicemail for {customer_number} on {call_control_id}")
                    update_call_state(call_control_id, status_description="Dropping personalized voicemail...", status_color="blue")
                if audio_url:
                    logger.info(f"Dropping voicemail NOW on {call_control_id}: {audio_url}")
                    play_audio(call_control_id, audio_url)
                    pvm_script_text = None
                    if personalized_url and customer_number:
                        audio_map = pvm_get_audio_map()
                        digits = re.sub(r'[^\d+]', '', customer_number)
                        for key, val in audio_map.items():
                            if key.lstrip("+") == digits.lstrip("+"):
                                pvm_script_text = val.get("script", "")
                                break
                    if pvm_script_text:
                        append_transcript(call_control_id, pvm_script_text, track="outbound", is_final=True)
                    else:
                        append_transcript(call_control_id, "[Voicemail audio playing]", track="outbound", is_final=True)
                else:
                    logger.error(f"No audio URL configured for voicemail on {call_control_id}")
                    update_call_state(call_control_id, status_description="Voicemail failed - no audio", status_color="red")
                    hangup_call(call_control_id)

        elif result == "not_sure":
            update_call_state(call_control_id, machine_detected=False, status="human_detected",
                              amd_result="not_sure", status_description="Detection unclear - treating as human", status_color="yellow")
            camp = get_campaign()
            transfer_num = camp.get("transfer_number", "")
            customer_num = (get_call_state(call_control_id) or {}).get("number", "")
            if transfer_num and mark_transferred(call_control_id):
                logger.info(f"AMD not_sure on {call_control_id}, treating as HUMAN - transferring to {transfer_num} (caller ID: {customer_num})")
                success = transfer_call(call_control_id, transfer_num, customer_number=customer_num)
                if success:
                    pause_for_transfer(call_control_id)
                    logger.info(f"Campaign paused for transfer on {call_control_id}")
                    update_call_state(call_control_id, status="transferred",
                                      status_description="Answered by human - transferred (campaign paused)", status_color="green")
                else:
                    logger.error(f"Transfer failed for {call_control_id} (not_sure), hanging up")
                    update_call_state(call_control_id, status="transfer_failed",
                                      status_description="Transfer failed", status_color="red")
                    hangup_call(call_control_id)
            else:
                logger.warning(f"AMD not_sure on {call_control_id}, no transfer number, hanging up")
                update_call_state(call_control_id, status_description="No transfer number configured", status_color="yellow")
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

        if state.get("voicemail_dropped"):
            camp = get_campaign()
            customer_number = state.get("number", "")
            personalized_url = get_personalized_audio_url(customer_number) if customer_number else None
            audio_url = personalized_url or camp.get("audio_url", "") or get_voicemail_url()
            if audio_url and beep_result == "beep_detected":
                logger.info(f"Beep detected! Restarting voicemail from beginning on {call_control_id}")
                play_audio(call_control_id, audio_url)
            else:
                logger.info(f"Greeting ended on {call_control_id}, audio already playing")

    # ---- call.playback.ended ----
    elif event_type == "call.playback.ended":
        state = get_call_state(call_control_id)
        if state and state.get("voicemail_dropped"):
            update_call_state(call_control_id, status="voicemail_complete",
                              status_description="Voicemail dropped successfully", status_color="green")
            logger.info(f"Voicemail playback complete on {call_control_id}, hanging up")
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
            resume_after_transfer(call_control_id)

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
    result = list_owned_numbers()
    if result.get("success"):
        return jsonify(result)
    return jsonify(result), 400


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
    start_scheduler()

_init_app()

# ---- Main Entry Point ----
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
