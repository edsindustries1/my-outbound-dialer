"""
app.py - Main Flask application for the Voicemail Drop System.
Handles web dashboard, file uploads, webhook processing, and campaign control.
"""

import os
import csv
import io
import logging
import threading
import functools
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for
from werkzeug.utils import secure_filename

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
)
from telnyx_client import transfer_call, play_audio, hangup_call, make_call, validate_connection_id, set_webhook_base_url, start_transcription
from call_manager import start_dialer

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


# ---- Login Route ----
@app.route("/login", methods=["GET", "POST"])
def login():
    _detect_and_set_base_url()
    if not APP_PASSWORD:
        return redirect(url_for("index"))
    if session.get("authenticated"):
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        pw = request.form.get("password", "")
        if pw == APP_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("index"))
        error = "Incorrect password"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("authenticated", None)
    return redirect(url_for("login"))


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
@app.route("/")
@login_required
def index():
    """Serve the main dashboard page."""
    _detect_and_set_base_url()
    return render_template("index.html")


# ---- Audio File Serving ----
@app.route("/audio/<filename>")
def serve_audio(filename):
    """Serve uploaded audio files so Telnyx can access them (no auth - Telnyx needs direct access)."""
    response = send_from_directory(UPLOAD_FOLDER, filename)
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

    csv_file = request.files.get("csv_file")
    if csv_file and csv_file.filename:
        filename = secure_filename(csv_file.filename)
        content = csv_file.read().decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        for row in reader:
            for cell in row:
                cell = cell.strip()
                if cell and cell.replace("+", "").replace("-", "").replace(" ", "").isdigit():
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

    # ---- Start the campaign ----
    logger.info(f"Starting campaign: {len(numbers)} numbers, transfer to {transfer_number}, mode={dial_mode}, batch={batch_size}, delay={dial_delay}min")
    set_campaign(audio_url, transfer_number, numbers, dial_mode=dial_mode, batch_size=batch_size, dial_delay=dial_delay)
    start_dialer()

    return jsonify({"message": f"Campaign started with {len(numbers)} numbers"})


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


# ---- Background Scheduler Thread ----
def _scheduler_worker():
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
        import time
        time.sleep(30)


_scheduler_thread = None


def start_scheduler():
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _scheduler_thread = threading.Thread(target=_scheduler_worker, daemon=True)
    _scheduler_thread.start()
    logger.info("Background scheduler started")


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
                audio_url = camp.get("audio_url", "") or get_voicemail_url()
                if audio_url:
                    logger.info(f"Dropping voicemail NOW on {call_control_id}: {audio_url}")
                    play_audio(call_control_id, audio_url)
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
            audio_url = camp.get("audio_url", "") or get_voicemail_url()
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

    return "", 200


# ---- Main Entry Point ----
if __name__ == "__main__":
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

    app.run(host="0.0.0.0", port=5000, debug=False)
