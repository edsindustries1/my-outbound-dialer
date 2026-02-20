"""
personalized_vm.py - Personalized voicemail generation using ElevenLabs TTS.
Handles CSV parsing, template rendering, and audio generation for per-contact voicemails.
"""

import os
import csv
import io
import re
import time
import json
import logging
import threading
import requests
from datetime import datetime

logger = logging.getLogger("voicemail_app")

UPLOAD_DIR = "uploads"
PVM_DIR = os.path.join(UPLOAD_DIR, "personalized")
PVM_STATE_FILE = os.path.join("logs", "pvm_state.json")

ALLOWED_PLACEHOLDERS = {
    "name", "first_name", "last_name", "phone", "email",
    "address", "payment_date", "amount", "company"
}

ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"

_generation_state = {
    "status": "idle",
    "total": 0,
    "completed": 0,
    "errors": [],
    "contacts": [],
    "template": "",
    "voice_id": "",
}
_state_lock = threading.Lock()


def _get_elevenlabs_api_key():
    hostname = os.environ.get("REPLIT_CONNECTORS_HOSTNAME", "")
    repl_identity = os.environ.get("REPL_IDENTITY", "")
    web_repl_renewal = os.environ.get("WEB_REPL_RENEWAL", "")

    if repl_identity:
        token = "repl " + repl_identity
    elif web_repl_renewal:
        token = "depl " + web_repl_renewal
    else:
        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if api_key:
            return api_key
        raise RuntimeError("No ElevenLabs credentials found")

    if not hostname:
        raise RuntimeError("REPLIT_CONNECTORS_HOSTNAME not set")

    resp = requests.get(
        f"https://{hostname}/api/v2/connection?include_secrets=true&connector_names=elevenlabs",
        headers={
            "Accept": "application/json",
            "X_REPLIT_TOKEN": token,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    if not items:
        raise RuntimeError("ElevenLabs connector not found")

    api_key = items[0].get("settings", {}).get("api_key", "")
    if not api_key:
        raise RuntimeError("ElevenLabs API key not found in connector")
    return api_key


def get_available_voices():
    try:
        api_key = _get_elevenlabs_api_key()
        resp = requests.get(
            f"{ELEVENLABS_API_BASE}/voices",
            headers={"xi-api-key": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        voices = resp.json().get("voices", [])
        return [{"voice_id": v["voice_id"], "name": v["name"], "category": v.get("category", "")} for v in voices]
    except Exception as e:
        logger.error(f"Failed to fetch ElevenLabs voices: {e}")
        return []


def parse_csv(file_content):
    reader = csv.DictReader(io.StringIO(file_content))
    contacts = []
    errors = []

    fieldnames = reader.fieldnames or []
    normalized_fields = {}
    for f in fieldnames:
        clean = f.strip().lower().replace(" ", "_")
        clean = re.sub(r'[^a-z0-9_]', '', clean)
        normalized_fields[f] = clean

    for i, row in enumerate(reader, start=2):
        contact = {}
        for orig, norm in normalized_fields.items():
            contact[norm] = row.get(orig, "").strip()

        if "name" in contact and contact["name"] and "first_name" not in contact:
            parts = contact["name"].split(None, 1)
            contact["first_name"] = parts[0]
            contact["last_name"] = parts[1] if len(parts) > 1 else ""

        if not contact.get("phone"):
            errors.append(f"Row {i}: missing phone number")
            continue

        phone = contact["phone"].strip()
        digits = re.sub(r'[^\d+]', '', phone)
        if not digits:
            errors.append(f"Row {i}: invalid phone '{phone}'")
            continue
        if not digits.startswith("+"):
            if len(digits) == 10:
                digits = "+1" + digits
            elif len(digits) == 11 and digits.startswith("1"):
                digits = "+" + digits
            else:
                digits = "+" + digits
        contact["phone"] = digits

        contacts.append(contact)

    return {
        "contacts": contacts,
        "fields": list(set(normalized_fields.values())),
        "errors": errors,
        "total": len(contacts),
    }


def render_template(template, contact):
    def replace_placeholder(match):
        key = match.group(1).strip().lower()
        return contact.get(key, match.group(0))

    return re.sub(r'\{(\w+)\}', replace_placeholder, template)


def generate_audio_for_contact(api_key, contact, template, voice_id, model_id="eleven_multilingual_v2"):
    script = render_template(template, contact)
    phone = contact.get("phone", "unknown")
    safe_phone = re.sub(r'[^\d]', '', phone)
    filename = f"pvm_{safe_phone}_{int(time.time())}.mp3"
    filepath = os.path.join(PVM_DIR, filename)

    try:
        resp = requests.post(
            f"{ELEVENLABS_API_BASE}/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": script,
                "model_id": model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "use_speaker_boost": True,
                },
            },
            timeout=60,
        )
        resp.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(resp.content)

        return {
            "phone": phone,
            "filename": filename,
            "script": script,
            "success": True,
        }
    except Exception as e:
        logger.error(f"TTS failed for {phone}: {e}")
        return {
            "phone": phone,
            "filename": None,
            "script": script,
            "success": False,
            "error": str(e),
        }


def start_generation(contacts, template, voice_id, base_url):
    with _state_lock:
        if _generation_state["status"] == "generating":
            return False, "Generation already in progress"

        _generation_state["status"] = "generating"
        _generation_state["total"] = len(contacts)
        _generation_state["completed"] = 0
        _generation_state["errors"] = []
        _generation_state["contacts"] = contacts
        _generation_state["template"] = template
        _generation_state["voice_id"] = voice_id

    os.makedirs(PVM_DIR, exist_ok=True)

    t = threading.Thread(
        target=_generation_worker,
        args=(contacts, template, voice_id, base_url),
        daemon=True,
    )
    t.start()
    return True, "Generation started"


def _generation_worker(contacts, template, voice_id, base_url):
    try:
        api_key = _get_elevenlabs_api_key()
    except Exception as e:
        with _state_lock:
            _generation_state["status"] = "error"
            _generation_state["errors"].append(f"Auth failed: {e}")
        return

    audio_map = {}

    for i, contact in enumerate(contacts):
        result = generate_audio_for_contact(api_key, contact, template, voice_id)

        with _state_lock:
            _generation_state["completed"] = i + 1

        if result["success"]:
            audio_url = f"{base_url}/audio/personalized/{result['filename']}"
            audio_map[result["phone"]] = {
                "audio_url": audio_url,
                "script": result["script"],
                "filename": result["filename"],
            }
        else:
            with _state_lock:
                _generation_state["errors"].append(f"{result['phone']}: {result.get('error', 'Unknown error')}")

        if i < len(contacts) - 1:
            time.sleep(0.5)

    _save_audio_map(audio_map)

    with _state_lock:
        _generation_state["status"] = "complete"

    logger.info(f"Personalized VM generation complete: {len(audio_map)}/{len(contacts)} successful")


def _save_audio_map(audio_map):
    os.makedirs("logs", exist_ok=True)
    data = {
        "audio_map": audio_map,
        "generated_at": datetime.utcnow().isoformat(),
        "count": len(audio_map),
    }
    with open(PVM_STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_audio_map():
    try:
        if os.path.exists(PVM_STATE_FILE):
            with open(PVM_STATE_FILE, "r") as f:
                data = json.load(f)
                return data.get("audio_map", {})
    except Exception:
        pass
    return {}


def get_personalized_audio_url(phone_number):
    audio_map = get_audio_map()
    digits = re.sub(r'[^\d+]', '', phone_number)
    if digits in audio_map:
        return audio_map[digits].get("audio_url")
    without_plus = digits.lstrip("+")
    for key, val in audio_map.items():
        if key.lstrip("+") == without_plus:
            return val.get("audio_url")
    return None


def get_generation_status():
    with _state_lock:
        return dict(_generation_state)


def clear_personalized_audio():
    if os.path.exists(PVM_DIR):
        for f in os.listdir(PVM_DIR):
            try:
                os.remove(os.path.join(PVM_DIR, f))
            except Exception:
                pass
    if os.path.exists(PVM_STATE_FILE):
        try:
            os.remove(PVM_STATE_FILE)
        except Exception:
            pass
    with _state_lock:
        _generation_state["status"] = "idle"
        _generation_state["total"] = 0
        _generation_state["completed"] = 0
        _generation_state["errors"] = []
        _generation_state["contacts"] = []
