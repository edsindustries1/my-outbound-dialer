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


# ── DNC (Do Not Call) List ──────────────────────────────────────────────────

DNC_FILE = os.path.join(LOGS_DIR, "dnc_list.json")

def _load_dnc_list():
    """Load DNC list from file."""
    try:
        if os.path.exists(DNC_FILE):
            with open(DNC_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def _save_dnc_list(dnc):
    """Save DNC list to file."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    try:
        with open(DNC_FILE, "w") as f:
            json.dump(dnc, f, indent=2)
    except Exception:
        pass

def get_dnc_list():
    """Get all DNC numbers."""
    with _file_lock:
        return _load_dnc_list()

def add_to_dnc(number, reason="manual"):
    """Add a number to DNC list. Returns True if added, False if already exists."""
    number = number.strip()
    if not number:
        return False
    with _file_lock:
        dnc = _load_dnc_list()
        existing_numbers = [entry["number"] for entry in dnc]
        if number in existing_numbers:
            return False
        dnc.append({
            "number": number,
            "reason": reason,
            "added_at": datetime.utcnow().isoformat()
        })
        _save_dnc_list(dnc)
        return True

def remove_from_dnc(number):
    """Remove a number from DNC list."""
    number = number.strip()
    with _file_lock:
        dnc = _load_dnc_list()
        updated = [entry for entry in dnc if entry["number"] != number]
        if len(updated) < len(dnc):
            _save_dnc_list(updated)
            return True
        return False

def is_dnc(number):
    """Check if a number is on the DNC list."""
    number = number.strip()
    with _file_lock:
        dnc = _load_dnc_list()
        return number in [entry["number"] for entry in dnc]

def clear_dnc_list():
    """Clear the entire DNC list."""
    with _file_lock:
        _save_dnc_list([])


# ── Call Analytics ──────────────────────────────────────────────────────────

def get_analytics():
    """Compute analytics from call history."""
    history = get_call_history()

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

    # AMD breakdown
    amd_counts = {"human": 0, "machine": 0, "fax": 0, "not_sure": 0, "timeout": 0, "unknown": 0}
    for h in history:
        result = h.get("amd_result", "unknown") or "unknown"
        if result in amd_counts:
            amd_counts[result] += 1
        else:
            amd_counts["unknown"] += 1

    # Hourly distribution (best times to call)
    hourly = {str(h): 0 for h in range(24)}
    hourly_success = {str(h): 0 for h in range(24)}
    for h in history:
        ts = _parse_ts(h.get("timestamp", ""))
        if ts:
            hour_key = str(ts.hour)
            hourly[hour_key] = hourly.get(hour_key, 0) + 1
            if h.get("transferred") or h.get("voicemail_dropped"):
                hourly_success[hour_key] = hourly_success.get(hour_key, 0) + 1

    # Daily distribution (last 7 days)
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

    # Status breakdown
    status_counts = {}
    for h in history:
        desc = h.get("status_description", h.get("status", "unknown"))
        status_counts[desc] = status_counts.get(desc, 0) + 1

    # Hangup cause breakdown
    hangup_counts = {}
    for h in history:
        cause = h.get("hangup_cause", "unknown") or "unknown"
        hangup_counts[cause] = hangup_counts.get(cause, 0) + 1

    # Recent success trend (last 10 groups of 5 calls)
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

SCHEDULE_FILE = os.path.join(LOGS_DIR, "scheduled_campaigns.json")

def _load_schedules():
    try:
        if os.path.exists(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def _save_schedules(schedules):
    os.makedirs(LOGS_DIR, exist_ok=True)
    try:
        with open(SCHEDULE_FILE, "w") as f:
            json.dump(schedules, f, indent=2)
    except Exception:
        pass

def add_schedule(schedule_data):
    """Add a scheduled campaign. schedule_data should include: scheduled_time (ISO UTC), numbers, transfer_number, audio_url, dial_mode, batch_size, timezone."""
    import uuid
    schedule_data["id"] = str(uuid.uuid4())[:8]
    schedule_data["status"] = "pending"
    schedule_data["created_at"] = datetime.utcnow().isoformat()
    with _file_lock:
        schedules = _load_schedules()
        schedules.append(schedule_data)
        _save_schedules(schedules)
    return schedule_data

def get_schedules():
    """Get all scheduled campaigns."""
    with _file_lock:
        return _load_schedules()

def cancel_schedule(schedule_id):
    """Cancel a scheduled campaign."""
    with _file_lock:
        schedules = _load_schedules()
        updated = []
        found = False
        for s in schedules:
            if s.get("id") == schedule_id:
                s["status"] = "cancelled"
                found = True
            updated.append(s)
        if found:
            _save_schedules(updated)
        return found

def mark_schedule_executed(schedule_id):
    """Mark a scheduled campaign as executed."""
    with _file_lock:
        schedules = _load_schedules()
        for s in schedules:
            if s.get("id") == schedule_id:
                s["status"] = "executed"
                s["executed_at"] = datetime.utcnow().isoformat()
        _save_schedules(schedules)

def get_due_schedules():
    """Get schedules that are due to execute (scheduled_time <= now and status is pending)."""
    now = datetime.utcnow()
    with _file_lock:
        schedules = _load_schedules()
        due = []
        for s in schedules:
            if s.get("status") != "pending":
                continue
            scheduled_time = _parse_ts(s.get("scheduled_time", ""))
            if scheduled_time and scheduled_time <= now:
                due.append(s)
        return due

def delete_schedule(schedule_id):
    """Delete a scheduled campaign entirely."""
    with _file_lock:
        schedules = _load_schedules()
        updated = [s for s in schedules if s.get("id") != schedule_id]
        if len(updated) < len(schedules):
            _save_schedules(updated)
            return True
        return False


# ── Webhook Status Monitor ────────────────────────────────────────────────

import re

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


# ── Campaign Templates ────────────────────────────────────────────────────

TEMPLATES_FILE = os.path.join(LOGS_DIR, "campaign_templates.json")

def _load_templates():
    try:
        if os.path.exists(TEMPLATES_FILE):
            with open(TEMPLATES_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def _save_templates(templates):
    os.makedirs(LOGS_DIR, exist_ok=True)
    try:
        with open(TEMPLATES_FILE, "w") as f:
            json.dump(templates, f, indent=2)
    except Exception:
        pass

def save_template(name, config):
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
        templates = _load_templates()
        templates.append(template)
        _save_templates(templates)
    return template

def get_templates():
    with _file_lock:
        return _load_templates()

def delete_template(template_id):
    with _file_lock:
        templates = _load_templates()
        updated = [t for t in templates if t.get("id") != template_id]
        if len(updated) < len(templates):
            _save_templates(updated)
            return True
        return False


# ── Number Validation ─────────────────────────────────────────────────────

def validate_phone_numbers(numbers_text):
    lines = [l.strip() for l in numbers_text.strip().split("\n") if l.strip()]
    results = {
        "valid": [],
        "invalid": [],
        "duplicates_removed": 0,
        "dnc_blocked": 0,
        "total_input": len(lines),
    }
    seen = set()
    dnc = get_dnc_list()
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


# ── Email Report Settings ─────────────────────────────────────────────────

REPORT_SETTINGS_FILE = os.path.join(LOGS_DIR, "report_settings.json")

def get_report_settings():
    try:
        if os.path.exists(REPORT_SETTINGS_FILE):
            with open(REPORT_SETTINGS_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "enabled": False,
        "recipient_email": "",
        "send_time": "08:00",
        "last_sent": None,
    }

def save_report_settings(settings):
    os.makedirs(LOGS_DIR, exist_ok=True)
    current = get_report_settings()
    current.update(settings)
    current["updated_at"] = datetime.utcnow().isoformat()
    try:
        with open(REPORT_SETTINGS_FILE, "w") as f:
            json.dump(current, f, indent=2)
    except Exception:
        pass
    return current

def mark_report_sent():
    settings = get_report_settings()
    settings["last_sent"] = datetime.utcnow().isoformat()
    save_report_settings(settings)
    return settings


def get_campaign_history_summary():
    history = get_call_history()
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
