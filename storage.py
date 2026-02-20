"""
storage.py - In-memory storage for call states and campaign data.
Manages call tracking, campaign configuration, and status reporting.
Persists completed call logs to JSON file for historical reporting.
"""

import os
import json
import threading
from datetime import datetime, timedelta

lock = threading.Lock()

call_states = {}

LOGS_DIR = "logs"
CALL_LOG_FILE = os.path.join(LOGS_DIR, "call_history.json")
SETTINGS_FILE = os.path.join(LOGS_DIR, "app_settings.json")

DEFAULT_VOICEMAIL_URL = "https://res.cloudinary.com/doaojtas6/video/upload/v1770290941/ElevenLabs_2026-01-28T19_39_03_Greg_-_Driving_Tours_App__pvc_sp100_s50_sb75_v3_njgmqy.wav"


def get_voicemail_url():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                return settings.get("voicemail_url", DEFAULT_VOICEMAIL_URL)
    except Exception:
        pass
    return DEFAULT_VOICEMAIL_URL


def save_voicemail_url(url):
    os.makedirs(LOGS_DIR, exist_ok=True)
    settings = {}
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
    except Exception:
        pass
    settings["voicemail_url"] = url
    settings["updated_at"] = datetime.utcnow().isoformat()
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
    return settings


def _load_call_history():
    try:
        if os.path.exists(CALL_LOG_FILE):
            with open(CALL_LOG_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_call_history(history):
    os.makedirs(LOGS_DIR, exist_ok=True)
    try:
        with open(CALL_LOG_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass


_file_lock = threading.Lock()


def persist_call_log(call_control_id):
    with lock:
        state = call_states.get(call_control_id)
        if not state:
            return
        now = datetime.utcnow()
        ring_duration = None
        if state.get("ring_start"):
            end = state.get("ring_end") or now.timestamp()
            ring_duration = round(end - state["ring_start"])
        ts = state.get("created_at", now.strftime("%Y-%m-%dT%H:%M:%S"))
        entry = {
            "call_id": call_control_id,
            "timestamp": ts,
            "number": state["number"],
            "from_number": state.get("from_number", ""),
            "status": state["status"],
            "machine_detected": state["machine_detected"],
            "transferred": state["transferred"],
            "voicemail_dropped": state["voicemail_dropped"],
            "ring_duration": ring_duration,
            "status_description": state.get("status_description", ""),
            "status_color": state.get("status_color", "blue"),
            "amd_result": state.get("amd_result"),
            "hangup_cause": state.get("hangup_cause"),
            "transcript": state.get("transcript", []),
        }
    cutoff_dt = datetime.utcnow() - timedelta(days=7)
    with _file_lock:
        history = _load_call_history()
        history.append(entry)
        cleaned = []
        for h in history:
            h_dt = _parse_ts(h.get("timestamp", ""))
            if h_dt and h_dt >= cutoff_dt:
                cleaned.append(h)
        _save_call_history(cleaned)


def clear_call_history():
    with _file_lock:
        _save_call_history([])


def _parse_ts(ts_str):
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def get_call_history(start_date=None, end_date=None):
    with _file_lock:
        history = _load_call_history()
    if not start_date and not end_date:
        return history

    start_dt = _parse_ts(start_date) if start_date else None
    end_dt = _parse_ts(end_date) if end_date else None

    filtered = []
    for entry in history:
        ts_dt = _parse_ts(entry.get("timestamp", ""))
        if ts_dt is None:
            continue
        if start_dt and ts_dt < start_dt:
            continue
        if end_dt and ts_dt > end_dt:
            continue
        filtered.append(entry)
    return filtered

campaign = {
    "active": False,
    "audio_url": None,
    "transfer_number": None,
    "numbers": [],
    "dialed_count": 0,
    "stop_requested": False,
    "dial_mode": "sequential",
    "batch_size": 5,
}


def reset_campaign():
    resume_after_transfer()
    with lock:
        campaign["active"] = False
        campaign["audio_url"] = None
        campaign["transfer_number"] = None
        campaign["numbers"] = []
        campaign["dialed_count"] = 0
        campaign["stop_requested"] = False
        campaign["dial_mode"] = "sequential"
        campaign["batch_size"] = 5
        call_states.clear()


def set_campaign(audio_url, transfer_number, numbers, dial_mode="sequential", batch_size=5, dial_delay=2):
    with lock:
        campaign["active"] = True
        campaign["audio_url"] = audio_url
        campaign["transfer_number"] = transfer_number
        campaign["numbers"] = list(numbers)
        campaign["dialed_count"] = 0
        campaign["stop_requested"] = False
        campaign["dial_mode"] = dial_mode
        campaign["batch_size"] = max(1, min(int(batch_size), 50))
        campaign["dial_delay"] = max(1, min(10, int(dial_delay)))
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
            "status_description": "Call initiated",
            "status_color": "blue",
            "amd_result": None,
            "hangup_cause": None,
            "transcript": [],
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


def append_transcript(call_control_id, text, track="inbound", is_final=True):
    with lock:
        state = call_states.get(call_control_id)
        if state:
            if "transcript" not in state:
                state["transcript"] = []
            state["transcript"].append({"text": text, "track": track, "is_final": is_final})
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


def call_states_snapshot():
    with lock:
        return dict(call_states)

def clear_call_states():
    with lock:
        call_states.clear()


_transfer_pause_event = threading.Event()
_transfer_pause_event.set()
_active_transfer_cids = set()

def pause_for_transfer(call_control_id):
    with lock:
        _active_transfer_cids.add(call_control_id)
    _transfer_pause_event.clear()

def resume_after_transfer(call_control_id=None):
    with lock:
        if call_control_id:
            _active_transfer_cids.discard(call_control_id)
        else:
            _active_transfer_cids.clear()
        if not _active_transfer_cids:
            _transfer_pause_event.set()

def is_transfer_paused():
    with lock:
        return len(_active_transfer_cids) > 0

def is_active_transfer(call_control_id):
    with lock:
        return call_control_id in _active_transfer_cids

def wait_if_transfer_paused(timeout=None):
    _transfer_pause_event.wait(timeout=timeout)

_call_complete_events = {}
_call_complete_lock = threading.Lock()


def register_call_complete_event(call_control_id):
    with _call_complete_lock:
        event = threading.Event()
        _call_complete_events[call_control_id] = event
        return event


def signal_call_complete(call_control_id):
    with _call_complete_lock:
        event = _call_complete_events.pop(call_control_id, None)
        if event:
            event.set()


def get_all_statuses():
    now = datetime.utcnow()
    now_ts = now.timestamp()

    with lock:
        live_results = []
        live_cids = set()
        for cid, state in call_states.items():
            ring_duration = None
            if state.get("ring_start"):
                end = state.get("ring_end") or now_ts
                ring_duration = round(end - state["ring_start"])
            live_results.append({
                "call_id": cid[:12] + "...",
                "number": state["number"],
                "from_number": state.get("from_number", ""),
                "status": state["status"],
                "machine_detected": state["machine_detected"],
                "transferred": state["transferred"],
                "voicemail_dropped": state["voicemail_dropped"],
                "ring_duration": ring_duration,
                "timestamp": state.get("created_at", ""),
                "is_live": True,
                "status_description": state.get("status_description", ""),
                "status_color": state.get("status_color", "blue"),
                "amd_result": state.get("amd_result"),
                "hangup_cause": state.get("hangup_cause"),
                "transcript": state.get("transcript", []),
            })
            live_cids.add(cid)

    cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
    history = get_call_history(start_date=cutoff)

    history_results = []
    for entry in history:
        if entry.get("call_id", "") in live_cids:
            continue
        history_results.append({
            "call_id": "hist",
            "number": entry.get("number", ""),
            "from_number": entry.get("from_number", ""),
            "status": entry.get("status", "unknown"),
            "machine_detected": entry.get("machine_detected"),
            "transferred": entry.get("transferred", False),
            "voicemail_dropped": entry.get("voicemail_dropped", False),
            "ring_duration": entry.get("ring_duration"),
            "timestamp": entry.get("timestamp", ""),
            "is_live": False,
            "status_description": entry.get("status_description", ""),
            "status_color": entry.get("status_color", ""),
            "amd_result": entry.get("amd_result"),
            "hangup_cause": entry.get("hangup_cause"),
            "transcript": entry.get("transcript", []),
        })

    combined = live_results + history_results

    def _sort_key(x):
        dt = _parse_ts(x.get("timestamp", ""))
        return dt if dt else datetime.min

    combined.sort(key=_sort_key, reverse=True)
    return combined
