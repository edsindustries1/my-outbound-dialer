"""
app.py - Main Flask application for the Voicemail Drop System.
Handles web dashboard, file uploads, webhook processing, and campaign control.
"""

import os
import csv
import io
import logging
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
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
)
from telnyx_client import transfer_call, play_audio, hangup_call, make_call, validate_connection_id
from call_manager import start_dialer

_amd_timers = {}

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

UPLOAD_FOLDER = "uploads"
ALLOWED_AUDIO = {"mp3", "wav"}
ALLOWED_CSV = {"csv", "txt"}


# ---- Dashboard Route ----
@app.route("/")
def index():
    """Serve the main dashboard page."""
    return render_template("index.html")


# ---- Audio File Serving ----
@app.route("/audio/<filename>")
def serve_audio(filename):
    """Serve uploaded audio files so Telnyx can access them."""
    response = send_from_directory(UPLOAD_FOLDER, filename)
    response.headers["Cache-Control"] = "no-cache"
    return response


# ---- Start Campaign ----
@app.route("/start", methods=["POST"])
def start():
    """
    Start a new calling campaign.
    Accepts: phone numbers (pasted or CSV), audio (file or URL), transfer number.
    """
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
        return jsonify({"error": "No audio file or URL provided"}), 400

    if not transfer_number:
        return jsonify({"error": "Transfer number is required"}), 400

    # ---- Start the campaign ----
    logger.info(f"Starting campaign: {len(numbers)} numbers, transfer to {transfer_number}")
    set_campaign(audio_url, transfer_number, numbers)
    start_dialer()

    return jsonify({"message": f"Campaign started with {len(numbers)} numbers"})


# ---- Test Call ----
@app.route("/test_call", methods=["POST"])
def test_call():
    """Place a single test call to verify everything is working."""
    number = request.form.get("test_number", "").strip()
    if not number:
        return jsonify({"error": "No phone number provided"}), 400

    logger.info(f"Placing test call to {number}")
    call_control_id = make_call(number)

    if call_control_id:
        create_call_state(call_control_id, number)
        update_call_state(call_control_id, status="test_call_ringing")
        logger.info(f"Test call placed successfully to {number}")
        return jsonify({"message": f"Test call placed to {number}"})
    else:
        logger.error(f"Test call failed to {number}")
        return jsonify({"error": "Failed to place call. Check your Telnyx credentials."}), 500


# ---- Stop Campaign ----
@app.route("/stop", methods=["POST"])
def stop():
    """Stop the current campaign. Active calls will finish but no new calls are placed."""
    stop_campaign()
    logger.info("Campaign stopped by user")
    return jsonify({"message": "Campaign stopped"})


# ---- Status Endpoint (polled by frontend) ----
@app.route("/status")
def status():
    """Return current call statuses and campaign info for the dashboard."""
    camp = get_campaign()
    return jsonify({
        "active": camp["active"],
        "stop_requested": camp["stop_requested"],
        "total": len(camp["numbers"]),
        "calls": get_all_statuses(),
    })


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
        return "", 200

    data = body.get("data", {})
    event_type = data.get("event_type", "")
    payload = data.get("payload", {})
    call_control_id = payload.get("call_control_id", "")

    logger.info(f"Webhook received: {event_type} for call {call_control_id}")

    to_number = payload.get("to", "")
    from_number = payload.get("from", "")
    call_number = to_number or from_number

    state = get_call_state(call_control_id)
    if not state and call_control_id and call_number:
        create_call_state(call_control_id, call_number)
        logger.info(f"Auto-created call state for {call_number} (webhook arrived before state)")

    # ---- call.initiated ----
    if event_type == "call.initiated":
        update_call_state(call_control_id, status="ringing")

    # ---- call.answered ----
    elif event_type == "call.answered":
        update_call_state(call_control_id, status="answered", amd_received=False)
        logger.info(f"Call answered: {call_control_id}, waiting for AMD result...")

        def _amd_fallback(ccid):
            """If AMD event never arrives, treat as human and transfer."""
            state = get_call_state(ccid)
            if state and not state.get("amd_received") and state.get("status") == "answered":
                logger.warning(f"AMD timeout on {ccid}, treating as HUMAN and transferring")
                update_call_state(ccid, machine_detected=False, status="human_detected", amd_received=True)
                camp = get_campaign()
                transfer_num = camp.get("transfer_number", "")
                if transfer_num and mark_transferred(ccid):
                    logger.info(f"Fallback transfer {ccid} to {transfer_num}")
                    transfer_call(ccid, transfer_num)
            _amd_timers.pop(ccid, None)

        timer = threading.Timer(8.0, _amd_fallback, args=[call_control_id])
        timer.daemon = True
        _amd_timers[call_control_id] = timer
        timer.start()

    # ---- call.machine.detection.ended ----
    elif event_type == "call.machine.detection.ended":
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
            update_call_state(call_control_id, machine_detected=False, status="human_detected")
            camp = get_campaign()
            transfer_num = camp.get("transfer_number", "")
            if transfer_num and mark_transferred(call_control_id):
                logger.info(f"HUMAN detected - transferring {call_control_id} to {transfer_num}")
                transfer_call(call_control_id, transfer_num)

        elif result in ("machine", "fax", "not_sure"):
            update_call_state(call_control_id, machine_detected=True, status="machine_detected")
            logger.info(f"MACHINE detected on {call_control_id}, playing voicemail immediately")

            if mark_voicemail_dropped(call_control_id):
                camp = get_campaign()
                audio_url = camp.get("audio_url", "")
                if audio_url:
                    logger.info(f"Dropping voicemail NOW on {call_control_id}: {audio_url}")
                    play_audio(call_control_id, audio_url)
                else:
                    logger.error(f"No audio URL configured for voicemail on {call_control_id}")
                    hangup_call(call_control_id)

        else:
            update_call_state(call_control_id, status="no_answer")
            logger.info(f"AMD unknown result on {call_control_id}, hanging up")
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
            audio_url = camp.get("audio_url", "")
            if audio_url and beep_result == "beep_detected":
                logger.info(f"Beep detected! Restarting voicemail from beginning on {call_control_id}")
                play_audio(call_control_id, audio_url)
            else:
                logger.info(f"Greeting ended on {call_control_id}, audio already playing")

    # ---- call.playback.ended ----
    elif event_type == "call.playback.ended":
        state = get_call_state(call_control_id)
        if state and state.get("voicemail_dropped"):
            update_call_state(call_control_id, status="voicemail_complete")
            logger.info(f"Voicemail playback complete on {call_control_id}, hanging up")
            hangup_call(call_control_id)

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

        state = get_call_state(call_control_id)
        if state:
            current_status = state.get("status", "")
            if current_status not in ("transferred", "voicemail_complete"):
                update_call_state(call_control_id, status="hangup")
        logger.info(f"Call ended: {call_control_id} | cause={hangup_cause} source={hangup_source} sip={sip_code}")

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

    app.run(host="0.0.0.0", port=5000, debug=False)
