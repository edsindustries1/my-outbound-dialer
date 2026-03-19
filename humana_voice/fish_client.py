import os
import logging
import requests

logger = logging.getLogger("voicemail_app")

FISH_AUDIO_BASE_URL = "https://api.fish.audio"
FISH_AUDIO_CDN = "https://api.fish.audio"

_KEY_CANDIDATES = [
    "FISH_AUDIO_API_KEY",
    "FISH_AUDIO_KEY",
    "FISHAUDIO_API_KEY",
    "FISHAUDIO_KEY",
    "FISH_API_KEY",
    "FISH_KEY",
    "fish_audio_api_key",
    "fish_audio_key",
    "fishaudio_api_key",
    "fishaudio_key",
]

_db_key_fetcher = None


def register_db_key_fetcher(fn):
    """Register a callable that returns the Fish Audio API key from the database.
    Called at app startup so fish_client can retrieve keys stored via the Settings UI."""
    global _db_key_fetcher
    _db_key_fetcher = fn


def _read_api_key():
    """Read Fish Audio API key. Priority: DB config → environment variables.
    Strips surrounding whitespace and accidental quote characters."""
    if _db_key_fetcher:
        try:
            db_key = _db_key_fetcher()
            if db_key:
                db_key = db_key.strip().strip('"').strip("'").strip()
                if db_key:
                    return db_key, "database_config"
        except Exception:
            pass

    for name in _KEY_CANDIDATES:
        val = os.environ.get(name, "")
        if val:
            val = val.strip().strip('"').strip("'").strip()
            if val:
                return val, name
    return "", None


def get_api_key():
    key, _ = _read_api_key()
    return key


def get_key_source():
    """Return the source that provided the key ('database_config', env var name, or None)."""
    _, name = _read_api_key()
    return name


def is_configured():
    key, _ = _read_api_key()
    return bool(key)


def log_startup_status():
    """Log Fish Audio key detection result at startup — useful for Railway debugging."""
    key, name = _read_api_key()
    if key:
        logger.info(f"[Fish Audio] API key loaded from: {name} (length={len(key)})")
    else:
        checked = ", ".join(_KEY_CANDIDATES[:5]) + " …"
        logger.warning(
            f"[Fish Audio] API key NOT found in environment. Checked: {checked}. "
            f"Set it via the Settings page in the dashboard, or add FISH_AUDIO_API_KEY to Railway Variables."
        )


def _get_headers(extra=None):
    key, _ = _read_api_key()
    h = {"Authorization": f"Bearer {key}"}
    if extra:
        h.update(extra)
    return h


def resolve_cover_image(raw):
    """Turn a relative cover_image path into a full URL."""
    if not raw:
        return ""
    if raw.startswith("http"):
        return raw
    return f"{FISH_AUDIO_CDN}/{raw}"


def list_voices(query="", page=1):
    params = {"page_size": 20, "page_number": page}
    if query:
        params["title"] = query
    resp = requests.get(
        f"{FISH_AUDIO_BASE_URL}/model",
        headers=_get_headers(),
        params=params,
        timeout=15,
    )
    if not resp.ok:
        raise Exception(f"Humana Voice library error {resp.status_code}: {resp.text}")
    return resp.json()


def create_voice_model(audio_bytes, filename, name):
    resp = requests.post(
        f"{FISH_AUDIO_BASE_URL}/model",
        headers=_get_headers(),
        data={"title": name, "type": "tts", "train_mode": "fast", "visibility": "private"},
        files={"voices": (filename, audio_bytes)},
        timeout=120,
    )
    if not resp.ok:
        raise Exception(f"Humana Voice clone error {resp.status_code}: {resp.text}")
    return resp.json()


def delete_voice_model(voice_id):
    resp = requests.delete(
        f"{FISH_AUDIO_BASE_URL}/model/{voice_id}",
        headers=_get_headers(),
        timeout=15,
    )
    if not resp.ok:
        raise Exception(f"Humana Voice delete error {resp.status_code}: {resp.text}")
    return resp.json() if resp.content else {}


def text_to_speech(voice_id, text, speed=1.0, emotion="neutral"):
    payload = {
        "reference_id": voice_id,
        "text": text,
        "format": "mp3",
        "speed": speed,
    }
    resp = requests.post(
        f"{FISH_AUDIO_BASE_URL}/v1/tts",
        headers=_get_headers({"Content-Type": "application/json"}),
        json=payload,
        stream=True,
        timeout=30,
    )
    if not resp.ok:
        raise Exception(f"Humana Voice TTS error {resp.status_code}: {resp.text}")
    return resp
