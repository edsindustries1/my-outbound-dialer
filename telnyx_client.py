"""
telnyx_client.py - Wrapper around the Telnyx Call Control REST API.
All outbound call actions go through these functions.
"""

import os
import requests
import logging

logger = logging.getLogger("voicemail_app")

TELNYX_API_BASE = "https://api.telnyx.com/v2"

_resolved_connection_id = None


def _headers():
    """Build authorization headers for Telnyx API."""
    api_key = os.environ.get("TELNYX_API_KEY", "")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _get_connection_id():
    """
    Get the correct connection ID. First tries the env var,
    then auto-detects from the Telnyx account if it fails.
    """
    global _resolved_connection_id
    if _resolved_connection_id:
        return _resolved_connection_id

    env_id = os.environ.get("TELNYX_CONNECTION_ID", "")
    if env_id:
        _resolved_connection_id = env_id
        return env_id

    try:
        resp = requests.get(
            f"{TELNYX_API_BASE}/call_control_applications",
            headers=_headers(),
            timeout=15,
        )
        if resp.status_code == 200:
            apps = resp.json().get("data", [])
            if apps:
                auto_id = apps[0].get("id", "")
                logger.info(f"Auto-detected connection_id: {auto_id}")
                _resolved_connection_id = auto_id
                return auto_id
    except Exception as e:
        logger.error(f"Failed to auto-detect connection_id: {e}")

    return env_id


def validate_connection_id():
    """
    Check if the stored connection_id is valid by comparing
    with what Telnyx actually has. Auto-corrects if needed.
    """
    global _resolved_connection_id
    env_id = os.environ.get("TELNYX_CONNECTION_ID", "")

    try:
        resp = requests.get(
            f"{TELNYX_API_BASE}/call_control_applications",
            headers=_headers(),
            timeout=15,
        )
        if resp.status_code == 200:
            apps = resp.json().get("data", [])
            valid_ids = [app.get("id", "") for app in apps]

            if env_id in valid_ids:
                _resolved_connection_id = env_id
                logger.info(f"Connection ID {env_id} is valid")
                return env_id

            if valid_ids:
                correct_id = valid_ids[0]
                logger.warning(f"Connection ID {env_id} invalid, using {correct_id}")
                _resolved_connection_id = correct_id
                return correct_id
    except Exception as e:
        logger.error(f"Could not validate connection_id: {e}")

    return env_id


def make_call(number):
    """
    Place an outbound call with answering machine detection enabled.
    Returns the call_control_id on success, or None on failure.
    """
    connection_id = _get_connection_id()
    from_number = os.environ.get("TELNYX_FROM_NUMBER", "")
    webhook_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/") + "/webhook"

    payload = {
        "connection_id": connection_id,
        "to": number,
        "from": from_number,
        "answering_machine_detection": "detect_words",
        "answering_machine_detection_config": {
            "after_greeting_silence_millis": 800,
            "between_words_silence_millis": 50,
            "greeting_duration_millis": 3500,
            "greeting_silence_duration_millis": 2000,
            "greeting_total_analysis_time_millis": 50000,
            "initial_silence_millis": 3500,
            "maximum_number_of_words": 5,
            "maximum_word_length_millis": 3500,
            "silence_threshold": 256,
            "total_analysis_time_millis": 5000,
        },
        "timeout_secs": 60,
        "time_limit_secs": 180,
        "webhook_url": webhook_url,
    }

    try:
        resp = requests.post(
            f"{TELNYX_API_BASE}/calls",
            json=payload,
            headers=_headers(),
            timeout=15,
        )
        if resp.status_code == 422 and "connection_id" in resp.text:
            logger.warning("Connection ID rejected, auto-correcting...")
            _resolved_connection_id_reset()
            correct_id = validate_connection_id()
            if correct_id and correct_id != connection_id:
                payload["connection_id"] = correct_id
                resp = requests.post(
                    f"{TELNYX_API_BASE}/calls",
                    json=payload,
                    headers=_headers(),
                    timeout=15,
                )
        if resp.status_code != 200:
            logger.error(f"Telnyx API error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        data = resp.json().get("data", {})
        call_control_id = data.get("call_control_id")
        logger.info(f"Call placed to {number}, call_control_id={call_control_id}")
        return call_control_id
    except Exception as e:
        logger.error(f"Failed to place call to {number}: {e}")
        return None


def _resolved_connection_id_reset():
    """Reset the cached connection ID so it gets re-fetched."""
    global _resolved_connection_id
    _resolved_connection_id = None


def transfer_call(call_control_id, to_number):
    """Transfer an active call to the specified number."""
    from_number = os.environ.get("TELNYX_FROM_NUMBER", "")
    webhook_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/") + "/webhook"
    payload = {
        "to": to_number,
        "from": from_number,
        "timeout_secs": 30,
        "webhook_url": webhook_url,
    }
    try:
        resp = requests.post(
            f"{TELNYX_API_BASE}/calls/{call_control_id}/actions/transfer",
            json=payload,
            headers=_headers(),
            timeout=15,
        )
        logger.info(f"Transfer API response {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()
        logger.info(f"Call {call_control_id} transferred to {to_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to transfer call {call_control_id}: {e}")
        return False


def play_audio(call_control_id, audio_url):
    """Play an audio file on an active call."""
    payload = {"audio_url": audio_url}
    try:
        resp = requests.post(
            f"{TELNYX_API_BASE}/calls/{call_control_id}/actions/playback_start",
            json=payload,
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"Playing audio on call {call_control_id}: {audio_url}")
        return True
    except Exception as e:
        logger.error(f"Failed to play audio on call {call_control_id}: {e}")
        return False


def hangup_call(call_control_id):
    """Hang up an active call."""
    try:
        resp = requests.post(
            f"{TELNYX_API_BASE}/calls/{call_control_id}/actions/hangup",
            json={},
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"Hangup call {call_control_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to hangup call {call_control_id}: {e}")
        return False
