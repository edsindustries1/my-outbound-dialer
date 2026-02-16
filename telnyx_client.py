"""
telnyx_client.py - Wrapper around the Telnyx Call Control REST API.
All outbound call actions go through these functions.
"""

import os
import requests
import logging

logger = logging.getLogger("voicemail_app")

TELNYX_API_BASE = "https://api.telnyx.com/v2"


def _headers():
    """Build authorization headers for Telnyx API."""
    api_key = os.environ.get("TELNYX_API_KEY", "")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def make_call(number):
    """
    Place an outbound call with answering machine detection enabled.
    Returns the call_control_id on success, or None on failure.
    """
    connection_id = os.environ.get("TELNYX_CONNECTION_ID", "")
    from_number = os.environ.get("TELNYX_FROM_NUMBER", "")
    webhook_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/") + "/webhook"

    payload = {
        "connection_id": connection_id,
        "to": number,
        "from": from_number,
        "answering_machine_detection": "detect_beep",
        "webhook_url": webhook_url,
    }

    try:
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


def transfer_call(call_control_id, to_number):
    """Transfer an active call to the specified number."""
    payload = {"to": to_number}
    try:
        resp = requests.post(
            f"{TELNYX_API_BASE}/calls/{call_control_id}/actions/transfer",
            json=payload,
            headers=_headers(),
            timeout=15,
        )
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
