import os
import requests

FISH_AUDIO_BASE_URL = "https://api.fish.audio/v1"


def _get_headers(extra=None):
    key = os.environ.get("FISH_AUDIO_API_KEY", "")
    h = {"Authorization": f"Bearer {key}"}
    if extra:
        h.update(extra)
    return h


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
        data={"title": name, "type": "svc", "train_mode": "fast"},
        files={"voices": (filename, audio_bytes, "audio/mpeg")},
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
        "emotion": emotion,
    }
    resp = requests.post(
        f"{FISH_AUDIO_BASE_URL}/tts",
        headers=_get_headers({"Content-Type": "application/json"}),
        json=payload,
        stream=True,
        timeout=30,
    )
    if not resp.ok:
        raise Exception(f"Humana Voice TTS error {resp.status_code}: {resp.text}")
    return resp
