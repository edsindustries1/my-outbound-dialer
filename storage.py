"""
storage.py - In-memory storage for call states and campaign data.
Manages call tracking, campaign configuration, and status reporting.
Persists completed call logs to JSON file for historical reporting.
Supports per-user data isolation via user_id parameter.
"""

import os
import re
import json
import threading
from datetime import datetime, timedelta

lock = threading.Lock()

call_states = {}

LOGS_DIR = "logs"

DEFAULT_VOICEMAIL_URL = "https://res.cloudinary.com/doaojtas6/video/upload/v1770290941/ElevenLabs_2026-01-28T19_39_03_Greg_-_Driving_Tours_App__pvc_sp100_s50_sb75_v3_njgmqy.wav"


def _user_logs_dir(user_id):
    if user_id is None:
        return LOGS_DIR
    return os.path.join(LOGS_DIR, f"user_{user_id}")


def _user_file(user_id, filename):
    d = _user_logs_dir(user_id)
    return os.path.join(d, filename)


_cid_to_user = {}


def get_user_for_call(call_control_id):
    with lock:
        return _cid_to_user.get(call_control_id)


def _default_campaign():
    return {
        "active": False,
        "is_test": False,
        "audio_url": None,
        "transfer_number": None,
        "numbers": [],
        "dialed_count": 0,
        "stop_requested": False,
        "dial_mode": "sequential",
        "batch_size": 5,
    }


_campaigns = {}


def _campaign_key(user_id):
    return user_id if user_id is not None else "global"


def get_voicemail_url(user_id=None):
    settings_file = _user_file(user_id, "app_settings.json")
    try:
        if os.path.exists(settings_file):
            with open(settings_file, "r") as f:
                settings = json.load(f)
                return settings.get("voicemail_url", DEFAULT_VOICEMAIL_URL)
    except Exception:
        pass
    return DEFAULT_VOICEMAIL_URL


def save_voicemail_url(url, user_id=None):
    d = _user_logs_dir(user_id)
    os.makedirs(d, exist_ok=True)
    settings_file = _user_file(user_id, "app_settings.json")
    settings = {}
    try:
        if os.path.exists(settings_file):
            with open(settings_file, "r") as f:
                settings = json.load(f)
    except Exception:
        pass
    settings["voicemail_url"] = url
    settings["updated_at"] = datetime.utcnow().isoformat()
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=2)
    return settings


def get_voice_preset(user_id=None):
    settings_file = _user_file(user_id, "app_settings.json")
    try:
        if os.path.exists(settings_file):
            with open(settings_file, "r") as f:
                settings = json.load(f)
                return settings.get("voice_preset", {})
    except Exception:
        pass
    return {}

def save_voice_preset(preset, user_id=None):
    d = _user_logs_dir(user_id)
    os.makedirs(d, exist_ok=True)
    settings_file = _user_file(user_id, "app_settings.json")
    settings = {}
    try:
        if os.path.exists(settings_file):
            with open(settings_file, "r") as f:
                settings = json.load(f)
    except Exception:
        pass
    settings["voice_preset"] = preset
    settings["updated_at"] = datetime.utcnow().isoformat()
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=2)
    return preset


def _load_call_history(user_id=None):
    call_log_file = _user_file(user_id, "call_history.json")
    try:
        if os.path.exists(call_log_file):
            with open(call_log_file, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_call_history(history, user_id=None):
    d = _user_logs_dir(user_id)
    os.makedirs(d, exist_ok=True)
    call_log_file = _user_file(user_id, "call_history.json")
    try:
        with open(call_log_file, "w") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass


_file_lock = threading.Lock()


def persist_call_log(call_control_id):
    with lock:
        state = call_states.get(call_control_id)
        if not state:
            return
        user_id = state.get("user_id")
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
            "recording_url": state.get("recording_url"),
        }
    cutoff_dt = datetime.utcnow() - timedelta(days=7)
    with _file_lock:
        history = _load_call_history(user_id)
        history.append(entry)
        cleaned = []
        for h in history:
            h_dt = _parse_ts(h.get("timestamp", ""))
            if h_dt and h_dt >= cutoff_dt:
                cleaned.append(h)
        _save_call_history(cleaned, user_id)


def clear_call_history(user_id=None):
    with _file_lock:
        _save_call_history([], user_id)


def _parse_ts(ts_str):
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def get_call_history(start_date=None, end_date=None, user_id=None):
    with _file_lock:
        history = _load_call_history(user_id)
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


def reset_campaign(user_id=None):
    resume_after_transfer(user_id=user_id)
    key = _campaign_key(user_id)
    with lock:
        _campaigns[key] = _default_campaign()
        if user_id is None:
            call_states.clear()
            _cid_to_user.clear()
        else:
            cids_to_remove = [cid for cid, st in call_states.items() if st.get("user_id") == user_id]
            for cid in cids_to_remove:
                del call_states[cid]
                _cid_to_user.pop(cid, None)


def set_campaign(audio_url, transfer_number, numbers, dial_mode="sequential", batch_size=5, dial_delay=2, from_number=None, user_id=None, is_test=False):
    key = _campaign_key(user_id)
    with lock:
        camp = _default_campaign()
        camp["active"] = True
        camp["is_test"] = is_test
        camp["audio_url"] = audio_url
        camp["transfer_number"] = transfer_number
        camp["numbers"] = list(numbers)
        camp["dialed_count"] = 0
        camp["stop_requested"] = False
        camp["dial_mode"] = dial_mode
        camp["batch_size"] = max(1, min(int(batch_size), 50))
        camp["dial_delay"] = max(1, min(10, int(dial_delay)))
        camp["from_number"] = from_number
        _campaigns[key] = camp
        if user_id is None:
            call_states.clear()
            _cid_to_user.clear()
        else:
            cids_to_remove = [cid for cid, st in call_states.items() if st.get("user_id") == user_id]
            for cid in cids_to_remove:
                del call_states[cid]
                _cid_to_user.pop(cid, None)


def stop_campaign(user_id=None):
    key = _campaign_key(user_id)
    with lock:
        camp = _campaigns.get(key)
        if camp:
            camp["stop_requested"] = True
            camp["active"] = False


def mark_campaign_complete(user_id=None):
    key = _campaign_key(user_id)
    with lock:
        camp = _campaigns.get(key)
        if camp:
            camp["active"] = False


def increment_dialed(user_id=None):
    key = _campaign_key(user_id)
    with lock:
        camp = _campaigns.get(key)
        if camp:
            camp["dialed_count"] += 1


def is_campaign_active(user_id=None):
    key = _campaign_key(user_id)
    with lock:
        camp = _campaigns.get(key)
        if camp:
            return camp["active"] and not camp["stop_requested"]
        return False


def get_campaign(user_id=None):
    key = _campaign_key(user_id)
    with lock:
        camp = _campaigns.get(key)
        if camp:
            return dict(camp)
        return dict(_default_campaign())


def create_call_state(call_control_id, number, user_id=None):
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
            "user_id": user_id,
        }
        if user_id is not None:
            _cid_to_user[call_control_id] = user_id


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
        _cid_to_user.clear()


_transfer_pause_events = {}
_active_transfer_cids_per_user = {}

def _get_transfer_event(user_id=None):
    key = _campaign_key(user_id)
    if key not in _transfer_pause_events:
        evt = threading.Event()
        evt.set()
        _transfer_pause_events[key] = evt
    return _transfer_pause_events[key]

def _get_active_transfer_cids(user_id=None):
    key = _campaign_key(user_id)
    if key not in _active_transfer_cids_per_user:
        _active_transfer_cids_per_user[key] = set()
    return _active_transfer_cids_per_user[key]

def pause_for_transfer(call_control_id, user_id=None):
    with lock:
        cids = _get_active_transfer_cids(user_id)
        cids.add(call_control_id)
    _get_transfer_event(user_id).clear()

def resume_after_transfer(call_control_id=None, user_id=None):
    with lock:
        cids = _get_active_transfer_cids(user_id)
        if call_control_id:
            cids.discard(call_control_id)
        else:
            cids.clear()
        if not cids:
            _get_transfer_event(user_id).set()

def is_transfer_paused(user_id=None):
    with lock:
        cids = _get_active_transfer_cids(user_id)
        return len(cids) > 0

def is_active_transfer(call_control_id):
    with lock:
        for cids in _active_transfer_cids_per_user.values():
            if call_control_id in cids:
                return True
        return False

def wait_if_transfer_paused(timeout=None, user_id=None):
    _get_transfer_event(user_id).wait(timeout=timeout)

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


def get_all_statuses(user_id=None):
    now = datetime.utcnow()
    now_ts = now.timestamp()

    with lock:
        live_results = []
        live_cids = set()
        for cid, state in call_states.items():
            if user_id is not None and state.get("user_id") != user_id:
                continue
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
                "recording_url": state.get("recording_url"),
            })
            live_cids.add(cid)

    cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
    history = get_call_history(start_date=cutoff, user_id=user_id)

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
            "recording_url": entry.get("recording_url"),
        })

    combined = live_results + history_results

    def _sort_key(x):
        dt = _parse_ts(x.get("timestamp", ""))
        return dt if dt else datetime.min

    combined.sort(key=_sort_key, reverse=True)
    return combined


# ── DNC (Do Not Call) List ──────────────────────────────────────────────────

def _load_dnc_list(user_id=None):
    dnc_file = _user_file(user_id, "dnc_list.json")
    try:
        if os.path.exists(dnc_file):
            with open(dnc_file, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def _save_dnc_list(dnc, user_id=None):
    d = _user_logs_dir(user_id)
    os.makedirs(d, exist_ok=True)
    dnc_file = _user_file(user_id, "dnc_list.json")
    try:
        with open(dnc_file, "w") as f:
            json.dump(dnc, f, indent=2)
    except Exception:
        pass

def get_dnc_list(user_id=None):
    with _file_lock:
        return _load_dnc_list(user_id)

def add_to_dnc(number, reason="manual", user_id=None):
    number = number.strip()
    if not number:
        return False
    with _file_lock:
        dnc = _load_dnc_list(user_id)
        existing_numbers = [entry["number"] for entry in dnc]
        if number in existing_numbers:
            return False
        dnc.append({
            "number": number,
            "reason": reason,
            "added_at": datetime.utcnow().isoformat()
        })
        _save_dnc_list(dnc, user_id)
        return True

def remove_from_dnc(number, user_id=None):
    number = number.strip()
    with _file_lock:
        dnc = _load_dnc_list(user_id)
        updated = [entry for entry in dnc if entry["number"] != number]
        if len(updated) < len(dnc):
            _save_dnc_list(updated, user_id)
            return True
        return False

def is_dnc(number, user_id=None):
    number = number.strip()
    with _file_lock:
        dnc = _load_dnc_list(user_id)
        return number in [entry["number"] for entry in dnc]

def clear_dnc_list(user_id=None):
    with _file_lock:
        _save_dnc_list([], user_id)


# ── Call Analytics ──────────────────────────────────────────────────────────

def get_analytics(user_id=None):
    history = get_call_history(user_id=user_id)

    total_calls = len(history)
    if total_calls == 0:
        return {
            "total_calls": 0,
            "success_rate": 0,
            "transfer_rate": 0,
            "voicemail_rate": 0,
            "avg_ring_duration": 0,
            "amd_accuracy": {"human": 0, "machine": 0, "fax": 0, "not_sure": 0, "timeout": 0, "unknown": 0},
            "hourly_distribution": {str(h): 0 for h in range(24)},
            "daily_distribution": {},
            "status_breakdown": {},
            "hangup_causes": {},
            "recent_success_trend": [],
        }

    transferred = sum(1 for h in history if h.get("transferred"))
    voicemail_dropped = sum(1 for h in history if h.get("voicemail_dropped"))
    successful = transferred + voicemail_dropped

    ring_durations = [h["ring_duration"] for h in history if h.get("ring_duration") is not None and h["ring_duration"] > 0]
    avg_ring = round(sum(ring_durations) / len(ring_durations), 1) if ring_durations else 0

    amd_counts = {"human": 0, "machine": 0, "fax": 0, "not_sure": 0, "timeout": 0, "unknown": 0}
    for h in history:
        result = h.get("amd_result", "unknown") or "unknown"
        if result in amd_counts:
            amd_counts[result] += 1
        else:
            amd_counts["unknown"] += 1

    hourly = {str(h): 0 for h in range(24)}
    hourly_success = {str(h): 0 for h in range(24)}
    for h in history:
        ts = _parse_ts(h.get("timestamp", ""))
        if ts:
            hour_key = str(ts.hour)
            hourly[hour_key] = hourly.get(hour_key, 0) + 1
            if h.get("transferred") or h.get("voicemail_dropped"):
                hourly_success[hour_key] = hourly_success.get(hour_key, 0) + 1

    daily = {}
    for h in history:
        ts = _parse_ts(h.get("timestamp", ""))
        if ts:
            day_key = ts.strftime("%Y-%m-%d")
            if day_key not in daily:
                daily[day_key] = {"total": 0, "success": 0}
            daily[day_key]["total"] += 1
            if h.get("transferred") or h.get("voicemail_dropped"):
                daily[day_key]["success"] += 1

    status_counts = {}
    for h in history:
        desc = h.get("status_description", h.get("status", "unknown"))
        status_counts[desc] = status_counts.get(desc, 0) + 1

    hangup_counts = {}
    for h in history:
        cause = h.get("hangup_cause", "unknown") or "unknown"
        hangup_counts[cause] = hangup_counts.get(cause, 0) + 1

    trend = []
    chunk_size = max(1, total_calls // 10) if total_calls >= 10 else total_calls
    sorted_history = sorted(history, key=lambda x: x.get("timestamp", ""))
    for i in range(0, len(sorted_history), chunk_size):
        chunk = sorted_history[i:i+chunk_size]
        chunk_success = sum(1 for c in chunk if c.get("transferred") or c.get("voicemail_dropped"))
        rate = round((chunk_success / len(chunk)) * 100, 1) if chunk else 0
        ts = chunk[0].get("timestamp", "") if chunk else ""
        trend.append({"timestamp": ts, "rate": rate, "count": len(chunk)})

    return {
        "total_calls": total_calls,
        "success_rate": round((successful / total_calls) * 100, 1),
        "transfer_rate": round((transferred / total_calls) * 100, 1),
        "voicemail_rate": round((voicemail_dropped / total_calls) * 100, 1),
        "avg_ring_duration": avg_ring,
        "amd_accuracy": amd_counts,
        "hourly_distribution": hourly,
        "hourly_success": hourly_success,
        "daily_distribution": daily,
        "status_breakdown": status_counts,
        "hangup_causes": hangup_counts,
        "recent_success_trend": trend,
    }


# ── Campaign Scheduling ────────────────────────────────────────────────────

def _load_schedules(user_id=None):
    schedule_file = _user_file(user_id, "scheduled_campaigns.json")
    try:
        if os.path.exists(schedule_file):
            with open(schedule_file, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def _save_schedules(schedules, user_id=None):
    d = _user_logs_dir(user_id)
    os.makedirs(d, exist_ok=True)
    schedule_file = _user_file(user_id, "scheduled_campaigns.json")
    try:
        with open(schedule_file, "w") as f:
            json.dump(schedules, f, indent=2)
    except Exception:
        pass

def add_schedule(schedule_data, user_id=None):
    import uuid
    schedule_data["id"] = str(uuid.uuid4())[:8]
    schedule_data["status"] = "pending"
    schedule_data["created_at"] = datetime.utcnow().isoformat()
    with _file_lock:
        schedules = _load_schedules(user_id)
        schedules.append(schedule_data)
        _save_schedules(schedules, user_id)
    return schedule_data

def get_schedules(user_id=None):
    with _file_lock:
        return _load_schedules(user_id)

def cancel_schedule(schedule_id, user_id=None):
    with _file_lock:
        schedules = _load_schedules(user_id)
        updated = []
        found = False
        for s in schedules:
            if s.get("id") == schedule_id:
                s["status"] = "cancelled"
                found = True
            updated.append(s)
        if found:
            _save_schedules(updated, user_id)
        return found

def mark_schedule_executed(schedule_id, user_id=None):
    with _file_lock:
        schedules = _load_schedules(user_id)
        for s in schedules:
            if s.get("id") == schedule_id:
                s["status"] = "executed"
                s["executed_at"] = datetime.utcnow().isoformat()
        _save_schedules(schedules, user_id)

def get_due_schedules(user_id=None):
    now = datetime.utcnow()
    with _file_lock:
        schedules = _load_schedules(user_id)
        due = []
        for s in schedules:
            if s.get("status") != "pending":
                continue
            scheduled_time = _parse_ts(s.get("scheduled_time", ""))
            if scheduled_time and scheduled_time <= now:
                due.append(s)
        return due

def delete_schedule(schedule_id, user_id=None):
    with _file_lock:
        schedules = _load_schedules(user_id)
        updated = [s for s in schedules if s.get("id") != schedule_id]
        if len(updated) < len(schedules):
            _save_schedules(updated, user_id)
            return True
        return False


# ── Webhook Status Monitor ────────────────────────────────────────────────

_webhook_stats = {
    "total_received": 0,
    "last_received_at": None,
    "last_event_type": None,
    "events_by_type": {},
    "errors": [],
    "recent_events": [],
}
_webhook_lock = threading.Lock()

def record_webhook_event(event_type, call_control_id="", success=True, error_msg=None):
    with _webhook_lock:
        _webhook_stats["total_received"] += 1
        _webhook_stats["last_received_at"] = datetime.utcnow().isoformat()
        _webhook_stats["last_event_type"] = event_type
        _webhook_stats["events_by_type"][event_type] = _webhook_stats["events_by_type"].get(event_type, 0) + 1
        entry = {
            "time": datetime.utcnow().isoformat(),
            "event": event_type,
            "call_id": call_control_id[:12] if call_control_id else "",
            "success": success,
        }
        if error_msg:
            entry["error"] = str(error_msg)[:200]
            _webhook_stats["errors"].append({
                "time": datetime.utcnow().isoformat(),
                "event": event_type,
                "error": str(error_msg)[:200]
            })
            _webhook_stats["errors"] = _webhook_stats["errors"][-20:]
        _webhook_stats["recent_events"].append(entry)
        _webhook_stats["recent_events"] = _webhook_stats["recent_events"][-50:]

def get_webhook_stats():
    with _webhook_lock:
        import copy
        stats = copy.deepcopy(_webhook_stats)
        uptime = None
        if stats["last_received_at"]:
            last = _parse_ts(stats["last_received_at"])
            if last:
                diff = (datetime.utcnow() - last).total_seconds()
                if diff < 60:
                    uptime = f"{int(diff)}s ago"
                elif diff < 3600:
                    uptime = f"{int(diff/60)}m ago"
                else:
                    uptime = f"{int(diff/3600)}h ago"
        stats["last_received_ago"] = uptime
        stats["health"] = "healthy" if stats["total_received"] > 0 and len(stats["errors"]) < 5 else ("warning" if stats["total_received"] > 0 else "unknown")
        return stats


# ── Voicemail Templates ──────────────────────────────────────────────────

def _load_vm_templates(user_id=None):
    vm_file = _user_file(user_id, "vm_templates.json")
    try:
        if os.path.exists(vm_file):
            with open(vm_file, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def _save_vm_templates(templates, user_id=None):
    d = _user_logs_dir(user_id)
    os.makedirs(d, exist_ok=True)
    vm_file = _user_file(user_id, "vm_templates.json")
    try:
        with open(vm_file, "w") as f:
            json.dump(templates, f, indent=2)
    except Exception:
        pass

def save_vm_template(data, user_id=None):
    import uuid
    template = {
        "id": str(uuid.uuid4())[:8],
        "name": data.get("name", "Untitled"),
        "type": data.get("type", "audio_url"),
        "content": data.get("content", ""),
        "created_at": datetime.utcnow().isoformat(),
        "last_used": None,
    }
    with _file_lock:
        templates = _load_vm_templates(user_id)
        templates.append(template)
        _save_vm_templates(templates, user_id)
    return template

def get_vm_templates(user_id=None):
    with _file_lock:
        return _load_vm_templates(user_id)

def update_vm_template(template_id, data, user_id=None):
    with _file_lock:
        templates = _load_vm_templates(user_id)
        for t in templates:
            if t.get("id") == template_id:
                if "name" in data:
                    t["name"] = data["name"]
                if "type" in data:
                    t["type"] = data["type"]
                if "content" in data:
                    t["content"] = data["content"]
                _save_vm_templates(templates, user_id)
                return t
    return None

def delete_vm_template(template_id, user_id=None):
    with _file_lock:
        templates = _load_vm_templates(user_id)
        updated = [t for t in templates if t.get("id") != template_id]
        if len(updated) < len(templates):
            _save_vm_templates(updated, user_id)
            return True
        return False

def mark_vm_template_used(template_id, user_id=None):
    with _file_lock:
        templates = _load_vm_templates(user_id)
        for t in templates:
            if t.get("id") == template_id:
                t["last_used"] = datetime.utcnow().isoformat()
                _save_vm_templates(templates, user_id)
                return True
    return False


# ── Campaign Templates ────────────────────────────────────────────────────

def _load_templates(user_id=None):
    templates_file = _user_file(user_id, "campaign_templates.json")
    try:
        if os.path.exists(templates_file):
            with open(templates_file, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def _save_templates(templates, user_id=None):
    d = _user_logs_dir(user_id)
    os.makedirs(d, exist_ok=True)
    templates_file = _user_file(user_id, "campaign_templates.json")
    try:
        with open(templates_file, "w") as f:
            json.dump(templates, f, indent=2)
    except Exception:
        pass

def save_template(name, config, user_id=None):
    import uuid
    template = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "transfer_number": config.get("transfer_number", ""),
        "dial_mode": config.get("dial_mode", "sequential"),
        "batch_size": config.get("batch_size", 5),
        "dial_delay": config.get("dial_delay", 2),
        "audio_url": config.get("audio_url", ""),
        "created_at": datetime.utcnow().isoformat(),
    }
    with _file_lock:
        templates = _load_templates(user_id)
        templates.append(template)
        _save_templates(templates, user_id)
    return template

def get_templates(user_id=None):
    with _file_lock:
        return _load_templates(user_id)

def delete_template(template_id, user_id=None):
    with _file_lock:
        templates = _load_templates(user_id)
        updated = [t for t in templates if t.get("id") != template_id]
        if len(updated) < len(templates):
            _save_templates(updated, user_id)
            return True
        return False


# ── Number Validation ─────────────────────────────────────────────────────

def validate_phone_numbers(numbers_text, user_id=None):
    lines = [l.strip() for l in numbers_text.strip().split("\n") if l.strip()]
    results = {
        "valid": [],
        "invalid": [],
        "duplicates_removed": 0,
        "dnc_blocked": 0,
        "total_input": len(lines),
    }
    seen = set()
    dnc = get_dnc_list(user_id)
    dnc_numbers = set()
    for d in dnc:
        n = d.get("number", "").lstrip("+").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        if n:
            dnc_numbers.add(n)

    e164_pattern = re.compile(r'^\+?1?\d{10,15}$')

    for line in lines:
        raw = line.strip()
        cleaned = raw.lstrip("+").replace("-", "").replace(" ", "").replace("(", "").replace(")", "").replace(".", "")
        if not cleaned:
            continue

        if not e164_pattern.match(cleaned) and not e164_pattern.match("+" + cleaned):
            results["invalid"].append({"number": raw, "reason": "Invalid format"})
            continue

        if len(cleaned) < 10:
            results["invalid"].append({"number": raw, "reason": "Too short"})
            continue

        if len(cleaned) > 15:
            results["invalid"].append({"number": raw, "reason": "Too long"})
            continue

        normalized = cleaned
        if normalized in seen:
            results["duplicates_removed"] += 1
            continue
        seen.add(normalized)

        if normalized in dnc_numbers:
            results["dnc_blocked"] += 1
            results["invalid"].append({"number": raw, "reason": "On DNC list"})
            continue

        formatted = "+" + cleaned if not raw.startswith("+") else raw
        results["valid"].append(formatted)

    results["total_valid"] = len(results["valid"])
    results["total_invalid"] = len(results["invalid"])
    return results


_E164_PATTERN = re.compile(r'^\+?1?\d{10,15}$')

INVALID_NANP_AREA_CODES = {
    "000", "100", "200", "211", "311", "411", "511", "611", "711", "811", "911",
    "555",
}

def is_valid_phone_number(number):
    cleaned = number.lstrip("+").replace("-", "").replace(" ", "").replace("(", "").replace(")", "").replace(".", "")
    if not cleaned or not cleaned.isdigit():
        return False, "Invalid format - contains non-numeric characters"
    if len(cleaned) < 10:
        return False, "Too short - must be at least 10 digits"
    if len(cleaned) > 15:
        return False, "Too long - exceeds 15 digits"
    if not _E164_PATTERN.match(cleaned) and not _E164_PATTERN.match("+" + cleaned):
        return False, "Invalid phone number format"
    if cleaned.startswith("1") and len(cleaned) == 11:
        area_code = cleaned[1:4]
    elif len(cleaned) == 10:
        area_code = cleaned[0:3]
    else:
        area_code = None
    if area_code and area_code in INVALID_NANP_AREA_CODES:
        return False, f"Invalid area code ({area_code})"
    if area_code and area_code[0] in ("0", "1"):
        return False, f"Invalid area code ({area_code}) - cannot start with 0 or 1"
    return True, "Valid"


def log_invalid_number(number, reason, campaign_name="", user_id=None):
    entry = {
        "call_id": f"invalid_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{number}",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        "number": number,
        "from_number": "",
        "status": "skipped",
        "machine_detected": False,
        "transferred": False,
        "voicemail_dropped": False,
        "ring_duration": None,
        "status_description": f"Invalid number - {reason}",
        "status_color": "red",
        "amd_result": None,
        "hangup_cause": "INVALID_NUMBER_FORMAT",
        "transcript": [],
        "recording_url": None,
        "invalid_reason": reason,
        "campaign_name": campaign_name,
    }
    cutoff_dt = datetime.utcnow() - timedelta(days=7)
    with _file_lock:
        history = _load_call_history(user_id)
        history.append(entry)
        cleaned = []
        for h in history:
            h_dt = _parse_ts(h.get("timestamp", ""))
            if h_dt is None or h_dt >= cutoff_dt:
                cleaned.append(h)
        _save_call_history(cleaned, user_id)
    return entry


def log_unreachable_number(number, reason, carrier=None, line_type=None, campaign_name="", user_id=None):
    entry = {
        "call_id": f"unreachable_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{number}",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        "number": number,
        "from_number": "",
        "status": "skipped",
        "machine_detected": False,
        "transferred": False,
        "voicemail_dropped": False,
        "ring_duration": None,
        "status_description": f"Unreachable - {reason}",
        "status_color": "amber",
        "amd_result": None,
        "hangup_cause": "NUMBER_UNREACHABLE",
        "transcript": [],
        "recording_url": None,
        "invalid_reason": reason,
        "carrier": carrier,
        "line_type": line_type,
        "campaign_name": campaign_name,
    }
    cutoff_dt = datetime.utcnow() - timedelta(days=7)
    with _file_lock:
        history = _load_call_history(user_id)
        history.append(entry)
        cleaned = []
        for h in history:
            h_dt = _parse_ts(h.get("timestamp", ""))
            if h_dt is None or h_dt >= cutoff_dt:
                cleaned.append(h)
        _save_call_history(cleaned, user_id)
    return entry


def get_unreachable_numbers(hours=24):
    history = _load_call_history()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")
    unreachable = []
    for entry in history:
        if entry.get("hangup_cause") == "NUMBER_UNREACHABLE" and entry.get("status") == "skipped":
            ts = entry.get("timestamp", "")
            if ts >= cutoff:
                unreachable.append(entry)
    return unreachable


def get_invalid_numbers(hours=24):
    history = _load_call_history()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")
    invalid = []
    for entry in history:
        if entry.get("hangup_cause") == "INVALID_NUMBER_FORMAT" and entry.get("status") == "skipped":
            ts = entry.get("timestamp", "")
            if ts >= cutoff:
                invalid.append(entry)
    return invalid


# ── Email Report Settings ─────────────────────────────────────────────────

def get_report_settings(user_id=None):
    report_file = _user_file(user_id, "report_settings.json")
    try:
        if os.path.exists(report_file):
            with open(report_file, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "enabled": False,
        "recipient_email": "",
        "send_time": "08:00",
        "last_sent": None,
    }

def save_report_settings(settings, user_id=None):
    d = _user_logs_dir(user_id)
    os.makedirs(d, exist_ok=True)
    current = get_report_settings(user_id)
    current.update(settings)
    current["updated_at"] = datetime.utcnow().isoformat()
    report_file = _user_file(user_id, "report_settings.json")
    try:
        with open(report_file, "w") as f:
            json.dump(current, f, indent=2)
    except Exception:
        pass
    return current

def mark_report_sent(user_id=None):
    settings = get_report_settings(user_id)
    settings["last_sent"] = datetime.utcnow().isoformat()
    save_report_settings(settings, user_id)
    return settings


def get_campaign_history_summary(user_id=None):
    history = get_call_history(user_id=user_id)
    if not history:
        return []

    campaigns = {}
    for h in history:
        date = h.get("timestamp", "")[:10]
        if not date:
            continue
        if date not in campaigns:
            campaigns[date] = {"date": date, "total": 0, "transferred": 0, "voicemail": 0, "failed": 0}
        campaigns[date]["total"] += 1
        if h.get("transferred"):
            campaigns[date]["transferred"] += 1
        elif h.get("voicemail_dropped"):
            campaigns[date]["voicemail"] += 1
        else:
            campaigns[date]["failed"] += 1

    result = sorted(campaigns.values(), key=lambda x: x["date"], reverse=True)
    for r in result:
        r["success_rate"] = round(((r["transferred"] + r["voicemail"]) / r["total"]) * 100, 1) if r["total"] > 0 else 0
    return result


# ── Contact List Management ──────────────────────────────────────────────

def _load_contacts(user_id=None):
    contacts_file = _user_file(user_id, "contacts.json")
    try:
        if os.path.exists(contacts_file):
            with open(contacts_file, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def _save_contacts(contacts, user_id=None):
    d = _user_logs_dir(user_id)
    os.makedirs(d, exist_ok=True)
    contacts_file = _user_file(user_id, "contacts.json")
    try:
        with open(contacts_file, "w") as f:
            json.dump(contacts, f, indent=2)
    except Exception:
        pass

def _normalize_phone(number):
    digits = re.sub(r'[^\d+]', '', number.strip())
    if not digits.startswith("+"):
        if len(digits) == 10:
            digits = "+1" + digits
        elif len(digits) == 11 and digits.startswith("1"):
            digits = "+" + digits
        else:
            digits = "+" + digits
    return digits

def get_contacts(tag=None, group=None, user_id=None):
    with _file_lock:
        contacts = _load_contacts(user_id)
    if tag:
        contacts = [c for c in contacts if tag in c.get("tags", [])]
    if group:
        contacts = [c for c in contacts if c.get("group", "") == group]
    return contacts

def add_contacts(new_contacts, group="", tags=None, user_id=None):
    import uuid
    with _file_lock:
        existing = _load_contacts(user_id)
        existing_phones = {}
        for c in existing:
            existing_phones[c.get("phone_normalized", "")] = c

        added = 0
        duplicates = 0
        for nc in new_contacts:
            phone = nc.get("phone", "").strip()
            if not phone:
                continue
            normalized = _normalize_phone(phone)
            if normalized in existing_phones:
                duplicates += 1
                continue

            contact = {
                "id": str(uuid.uuid4())[:8],
                "phone": phone,
                "phone_normalized": normalized,
                "first_name": nc.get("first_name", ""),
                "last_name": nc.get("last_name", ""),
                "email": nc.get("email", ""),
                "company": nc.get("company", ""),
                "group": group or nc.get("group", ""),
                "tags": tags or nc.get("tags", []),
                "added_at": datetime.utcnow().isoformat(),
                "call_count": 0,
                "last_called": None,
                "last_result": None,
                "campaigns_included": 0,
            }
            existing.append(contact)
            existing_phones[normalized] = contact
            added += 1

        _save_contacts(existing, user_id)
        return {"added": added, "duplicates": duplicates, "total": len(existing)}

def update_contact(contact_id, updates, user_id=None):
    with _file_lock:
        contacts = _load_contacts(user_id)
        for c in contacts:
            if c.get("id") == contact_id:
                for key in ("first_name", "last_name", "email", "company", "group", "tags"):
                    if key in updates:
                        c[key] = updates[key]
                _save_contacts(contacts, user_id)
                return c
    return None

def delete_contacts(contact_ids, user_id=None):
    with _file_lock:
        contacts = _load_contacts(user_id)
        id_set = set(contact_ids)
        updated = [c for c in contacts if c.get("id") not in id_set]
        removed = len(contacts) - len(updated)
        _save_contacts(updated, user_id)
        return removed

def get_contact_groups(user_id=None):
    with _file_lock:
        contacts = _load_contacts(user_id)
    groups = {}
    for c in contacts:
        g = c.get("group", "") or "Ungrouped"
        if g not in groups:
            groups[g] = 0
        groups[g] += 1
    return groups

def get_contact_tags(user_id=None):
    with _file_lock:
        contacts = _load_contacts(user_id)
    tags = {}
    for c in contacts:
        for t in c.get("tags", []):
            tags[t] = tags.get(t, 0) + 1
    return tags

def record_contact_called(phone, result, user_id=None):
    normalized = _normalize_phone(phone)
    with _file_lock:
        contacts = _load_contacts(user_id)
        for c in contacts:
            if c.get("phone_normalized", "") == normalized:
                c["call_count"] = c.get("call_count", 0) + 1
                c["last_called"] = datetime.utcnow().isoformat()
                c["last_result"] = result
                break
        _save_contacts(contacts, user_id)

def clear_contacts(user_id=None):
    with _file_lock:
        _save_contacts([], user_id)


# ── Call Recording URLs ──────────────────────────────────────────────────

def store_recording_url(call_control_id, recording_url):
    with lock:
        state = call_states.get(call_control_id)
        if state:
            state["recording_url"] = recording_url

def get_recording_urls():
    history = get_call_history()
    recordings = []
    for h in history:
        if h.get("recording_url"):
            recordings.append({
                "call_id": h.get("call_id", ""),
                "number": h.get("number", ""),
                "timestamp": h.get("timestamp", ""),
                "recording_url": h["recording_url"],
                "status": h.get("status", ""),
            })
    return recordings
