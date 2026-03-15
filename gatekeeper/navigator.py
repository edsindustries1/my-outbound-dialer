"""
gatekeeper/navigator.py - AI Gatekeeper Navigator
Classifies what answered a call (AI screener, IVR, receptionist, prospect)
and generates spoken responses via Groq LLM + Fish Audio TTS to navigate
past gatekeepers and reach the actual prospect.
"""

import os
import uuid
import logging
import requests

logger = logging.getLogger("voicemail_app")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-70b-8192"

VALID_CATEGORIES = {"human_prospect", "human_receptionist", "ai_screener", "ivr_menu"}

GATEKEEPER_DIR = os.path.join("uploads", "gatekeeper")
os.makedirs(GATEKEEPER_DIR, exist_ok=True)


def _groq_chat(system_prompt: str, user_message: str, max_tokens: int = 200) -> str:
    if not GROQ_API_KEY:
        logger.warning("[Navigator] GROQ_API_KEY not set — skipping LLM call")
        return ""
    try:
        resp = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"[Navigator] Groq API error: {e}")
        return ""


def classify_gatekeeper(transcript_text: str) -> str:
    """
    Classify what answered the call into one of four categories.
    Returns: 'human_prospect' | 'human_receptionist' | 'ai_screener' | 'ivr_menu'
    Defaults to 'human_prospect' on failure (safe: triggers immediate transfer).
    """
    system_prompt = (
        "You are a call classification engine. You receive the first spoken words from "
        "a phone call that was answered. Classify what answered the call into exactly "
        "one of these four categories:\n\n"
        "- \"human_prospect\": A real person who is likely the intended contact "
        "(answers with their name, says hello informally, sounds like an individual)\n"
        "- \"human_receptionist\": A real person acting as a gatekeeper or front desk "
        "(says company name, asks \"how can I direct your call\", \"who are you holding for\")\n"
        "- \"ai_screener\": An automated AI or robocall screening system "
        "(says \"please state your name\", \"who is calling\", \"what is this regarding\", "
        "\"I'll connect you if you\", Google Call Screen style prompts)\n"
        "- \"ivr_menu\": A touch-tone or voice IVR menu "
        "(says \"press 1 for\", \"para español\", \"say the name of the person\")\n\n"
        "Reply with ONLY the category string, nothing else."
    )
    result = _groq_chat(system_prompt, transcript_text or "(silence)", max_tokens=20)
    result = result.strip().lower().strip('"').strip("'")
    if result in VALID_CATEGORIES:
        return result
    logger.warning(f"[Navigator] Unexpected classification result: '{result}' — defaulting to human_prospect")
    return "human_prospect"


def build_navigator_response(
    category: str,
    transcript_text: str,
    prospect_name: str,
    prospect_company: str,
    agent_persona: str,
) -> str:
    """
    Generate a short spoken response appropriate for the gatekeeper type.
    Returns the text the AI agent should say out loud.
    """
    system_prompt = (
        f"You are {agent_persona}\n\n"
        f"You are on a live phone call trying to reach {prospect_name} at "
        f"{prospect_company}. Something answered the call before you reached them. "
        "Your job is to navigate past it naturally and get connected to the prospect.\n\n"
        "Rules:\n"
        "- Speak like a real human, naturally and confidently\n"
        "- Keep responses SHORT — maximum 2 sentences\n"
        "- Never say you are an AI or automated system\n"
        "- Never read out punctuation\n"
        "- For ai_screener: state your name from the persona and give a brief genuine "
        "reason for calling\n"
        "- For human_receptionist: greet warmly, ask for the prospect by name, give "
        "one short reason\n"
        "- For ivr_menu: you cannot press buttons, so say \"representative\" or \"agent\" "
        "to try to reach a human\n"
        "- For human_prospect: this is the person — greet them and introduce yourself "
        "briefly, handoff is about to happen\n\n"
        f"Current gatekeeper type: {category}\n"
        f"What they just said: \"{transcript_text}\"\n\n"
        "Respond with ONLY what the agent should say out loud, nothing else. "
        "No quotes, no labels, no explanation."
    )
    response = _groq_chat(system_prompt, transcript_text or "(silence)", max_tokens=120)
    if not response:
        if category == "ivr_menu":
            return "Representative."
        elif category == "ai_screener":
            return "This is Alex calling. I'd like to speak with someone regarding a business matter."
        elif category == "human_receptionist":
            return f"Hi, this is Alex. I'm hoping to speak with {prospect_name}."
        else:
            return f"Hi, this is Alex. Is this {prospect_name}?"
    return response


def speak_response(call_control_id: str, text: str, voice_id: str, base_url: str) -> bool:
    """
    Convert text to speech via Fish Audio TTS, save to disk, and play via Telnyx.
    Returns True on success, False on any failure.
    """
    if not text or not voice_id:
        logger.warning(f"[Navigator] speak_response called with empty text or voice_id for {call_control_id}")
        return False

    try:
        from humana_voice.fish_client import text_to_speech
        tts_resp = text_to_speech(voice_id, text)
    except Exception as e:
        logger.error(f"[Navigator] Fish Audio TTS error for {call_control_id}: {e}")
        return False

    try:
        filename = f"gk_{uuid.uuid4().hex}.mp3"
        filepath = os.path.join(GATEKEEPER_DIR, filename)
        with open(filepath, "wb") as f:
            for chunk in tts_resp.iter_content(chunk_size=4096):
                if chunk:
                    f.write(chunk)
        logger.info(f"[Navigator] TTS audio saved: {filepath}")
    except Exception as e:
        logger.error(f"[Navigator] Failed to save TTS audio for {call_control_id}: {e}")
        return False

    try:
        audio_url = f"{base_url.rstrip('/')}/audio/gatekeeper/{filename}"
        from telnyx_client import play_audio
        play_audio(call_control_id, audio_url, client_state="gatekeeper_response")
        logger.info(f"[Navigator] Playing gatekeeper response on {call_control_id}: {audio_url}")
        return True
    except Exception as e:
        logger.error(f"[Navigator] Telnyx play_audio error for {call_control_id}: {e}")
        return False
