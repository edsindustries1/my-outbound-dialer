"""
storage.py - In-memory storage for call states and campaign data.
Manages call tracking, campaign configuration, and status reporting.
"""

import threading
from datetime import datetime

# Thread lock for safe concurrent access
lock = threading.Lock()

# ---- Call State Storage ----
# Maps call_control_id -> call info dict
call_states = {}

# ---- Campaign Configuration ----
campaign = {
    "active": False,
    "audio_url": None,
    "transfer_number": None,
    "numbers": [],
    "dialed_count": 0,
    "stop_requested": False,
}


def reset_campaign():
    """Reset campaign to default state."""
    with lock:
        campaign["active"] = False
        campaign["audio_url"] = None
        campaign["transfer_number"] = None
        campaign["numbers"] = []
        campaign["dialed_count"] = 0
        campaign["stop_requested"] = False
        call_states.clear()


def set_campaign(audio_url, transfer_number, numbers):
    """Configure a new campaign with audio, transfer number, and phone list."""
    with lock:
        campaign["active"] = True
        campaign["audio_url"] = audio_url
        campaign["transfer_number"] = transfer_number
        campaign["numbers"] = list(numbers)
        campaign["dialed_count"] = 0
        campaign["stop_requested"] = False
        call_states.clear()


def stop_campaign():
    """Signal the campaign to stop dialing new numbers."""
    with lock:
        campaign["stop_requested"] = True
        campaign["active"] = False


def mark_campaign_complete():
    """Mark campaign as finished after all numbers are dialed."""
    with lock:
        campaign["active"] = False


def increment_dialed():
    """Increment the dialed count."""
    with lock:
        campaign["dialed_count"] += 1


def is_campaign_active():
    """Check if campaign is still running."""
    with lock:
        return campaign["active"] and not campaign["stop_requested"]


def get_campaign():
    """Return a copy of current campaign config."""
    with lock:
        return dict(campaign)


# ---- Call State Functions ----

def create_call_state(call_control_id, number):
    """Register a new call in the state tracker."""
    with lock:
        call_states[call_control_id] = {
            "number": number,
            "status": "initiated",
            "machine_detected": None,
            "transferred": False,
            "voicemail_dropped": False,
            "playback_started": False,
            "created_at": datetime.utcnow().isoformat(),
        }


def get_call_state(call_control_id):
    """Get state for a specific call. Returns None if not found."""
    with lock:
        state = call_states.get(call_control_id)
        if state:
            return dict(state)
        return None


def update_call_state(call_control_id, **kwargs):
    """Update one or more fields on a call state."""
    with lock:
        if call_control_id in call_states:
            call_states[call_control_id].update(kwargs)
            return True
        return False


def mark_transferred(call_control_id):
    """Mark a call as transferred. Returns False if already transferred."""
    with lock:
        state = call_states.get(call_control_id)
        if state and not state["transferred"]:
            state["transferred"] = True
            state["status"] = "transferred"
            return True
        return False


def mark_voicemail_dropped(call_control_id):
    """Mark a call as voicemail dropped. Returns False if already dropped."""
    with lock:
        state = call_states.get(call_control_id)
        if state and not state["voicemail_dropped"]:
            state["voicemail_dropped"] = True
            state["playback_started"] = True
            state["status"] = "voicemail_playing"
            return True
        return False


def get_all_statuses():
    """Return a list of all call states for the dashboard."""
    with lock:
        results = []
        for cid, state in call_states.items():
            results.append({
                "call_id": cid[:12] + "...",
                "number": state["number"],
                "status": state["status"],
                "machine_detected": state["machine_detected"],
                "transferred": state["transferred"],
                "voicemail_dropped": state["voicemail_dropped"],
            })
        return results
