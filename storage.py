"""
storage.py - In-memory storage for call states and campaign data.
Manages call tracking, campaign configuration, and status reporting.
"""

import os
import threading
from datetime import datetime

lock = threading.Lock()

call_states = {}

campaign = {
    "active": False,
    "audio_url": None,
    "transfer_number": None,
    "numbers": [],
    "dialed_count": 0,
    "stop_requested": False,
}


def reset_campaign():
    with lock:
        campaign["active"] = False
        campaign["audio_url"] = None
        campaign["transfer_number"] = None
        campaign["numbers"] = []
        campaign["dialed_count"] = 0
        campaign["stop_requested"] = False
        call_states.clear()


def set_campaign(audio_url, transfer_number, numbers):
    with lock:
        campaign["active"] = True
        campaign["audio_url"] = audio_url
        campaign["transfer_number"] = transfer_number
        campaign["numbers"] = list(numbers)
        campaign["dialed_count"] = 0
        campaign["stop_requested"] = False
        call_states.clear()


def stop_campaign():
    with lock:
        campaign["stop_requested"] = True
        campaign["active"] = False


def mark_campaign_complete():
    with lock:
        campaign["active"] = False


def increment_dialed():
    with lock:
        campaign["dialed_count"] += 1


def is_campaign_active():
    with lock:
        return campaign["active"] and not campaign["stop_requested"]


def get_campaign():
    with lock:
        return dict(campaign)


def create_call_state(call_control_id, number):
    from_number = os.environ.get("TELNYX_FROM_NUMBER", "")
    with lock:
        call_states[call_control_id] = {
            "number": number,
            "from_number": from_number,
            "status": "initiated",
            "machine_detected": None,
            "transferred": False,
            "voicemail_dropped": False,
            "playback_started": False,
            "created_at": datetime.utcnow().isoformat(),
            "ring_start": datetime.utcnow().timestamp(),
            "ring_end": None,
        }


def get_call_state(call_control_id):
    with lock:
        state = call_states.get(call_control_id)
        if state:
            return dict(state)
        return None


def update_call_state(call_control_id, **kwargs):
    with lock:
        if call_control_id in call_states:
            call_states[call_control_id].update(kwargs)
            return True
        return False


def mark_transferred(call_control_id):
    with lock:
        state = call_states.get(call_control_id)
        if state and not state["transferred"]:
            state["transferred"] = True
            state["status"] = "transferred"
            return True
        return False


def mark_voicemail_dropped(call_control_id):
    with lock:
        state = call_states.get(call_control_id)
        if state and not state["voicemail_dropped"]:
            state["voicemail_dropped"] = True
            state["playback_started"] = True
            state["status"] = "voicemail_playing"
            return True
        return False


def clear_call_states():
    with lock:
        call_states.clear()


def get_all_statuses():
    now = datetime.utcnow().timestamp()
    with lock:
        results = []
        for cid, state in call_states.items():
            ring_duration = None
            if state.get("ring_start"):
                end = state.get("ring_end") or now
                ring_duration = round(end - state["ring_start"])
            results.append({
                "call_id": cid[:12] + "...",
                "number": state["number"],
                "from_number": state.get("from_number", ""),
                "status": state["status"],
                "machine_detected": state["machine_detected"],
                "transferred": state["transferred"],
                "voicemail_dropped": state["voicemail_dropped"],
                "ring_duration": ring_duration,
            })
        return results
