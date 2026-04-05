"""
personalized_vm.py - Personalized voicemail generation.
Handles CSV parsing, template rendering, and audio generation for per-contact voicemails.
Supports Fish Audio (default, cheap) and ElevenLabs (legacy/premium) as TTS providers.
"""

import os
import csv
import io
import re
import time
import json
import shutil
import hashlib
import logging
import threading
import requests
from datetime import datetime, timedelta

logger = logging.getLogger("voicemail_app")

UPLOAD_DIR = "uploads"
PVM_DIR = os.path.join(UPLOAD_DIR, "personalized")
PVM_STATE_FILE = os.path.join("logs", "pvm_state.json")
CACHE_DIR = os.path.join(PVM_DIR, "cache")
CACHE_INDEX_FILE = os.path.join(CACHE_DIR, "cache_index.json")
CACHE_TTL_DAYS = 30

ALLOWED_PLACEHOLDERS = {
    "name", "first_name", "last_name", "phone", "email",
    "address", "payment_date", "amount", "company", "date"
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
_cache_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Audio cache helpers — content-addressed, 30-day TTL
# ---------------------------------------------------------------------------

def _cache_key(script, voice_id, provider, voice_settings=None, model_id=""):
    """SHA-256 hash of the rendered script + voice + provider + model + voice settings.

    model_id is a first-class cache-key component so callers that pass model_id
    separately (without embedding it inside voice_settings) still get distinct
    cache entries per model.  voice_settings is also fully included (minus voice_id
    which is already a top-level key) to cover preset, fillers, pauses, emphasis, etc.
    """
    settings_str = ""
    if voice_settings:
        try:
            settings_str = json.dumps(
                {k: voice_settings[k] for k in sorted(voice_settings) if k != "voice_id"},
                sort_keys=True
            )
        except Exception:
            pass
    # Use voice_settings.model_id when present, fall back to the explicit arg
    effective_model = (voice_settings or {}).get("model_id") or model_id
    raw = f"{script}|{voice_id}|{provider}|{effective_model}|{settings_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_cache_index():
    if os.path.exists(CACHE_INDEX_FILE):
        try:
            with open(CACHE_INDEX_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache_index(index):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)


def _cache_lookup(script, voice_id, provider, voice_settings=None, model_id=""):
    """Return path to a cached audio file if it exists and is not expired, else None."""
    key = _cache_key(script, voice_id, provider, voice_settings, model_id=model_id)
    with _cache_lock:
        index = _load_cache_index()
        entry = index.get(key)
        if not entry:
            return None
        cached_path = entry.get("filepath", "")
        if not os.path.exists(cached_path):
            return None
        created_at = datetime.fromisoformat(entry.get("created_at", "2000-01-01"))
        if datetime.utcnow() - created_at > timedelta(days=CACHE_TTL_DAYS):
            return None
        return cached_path


def _cache_store(script, voice_id, provider, source_filepath, voice_settings=None, model_id=""):
    """Copy a freshly-generated audio file into the cache. Returns cached filepath."""
    key = _cache_key(script, voice_id, provider, voice_settings, model_id=model_id)
    os.makedirs(CACHE_DIR, exist_ok=True)
    cached_filename = f"c_{key[:16]}.mp3"
    cached_path = os.path.join(CACHE_DIR, cached_filename)
    with _cache_lock:
        if not os.path.exists(cached_path):
            shutil.copy2(source_filepath, cached_path)
        index = _load_cache_index()
        index[key] = {
            "filepath": cached_path,
            "created_at": datetime.utcnow().isoformat(),
            "script_preview": script[:80],
            "voice_id": voice_id,
            "provider": provider,
        }
        _save_cache_index(index)
    return cached_path


def cache_cleanup():
    """Remove cache entries and files older than CACHE_TTL_DAYS. Returns (kept, removed) counts."""
    with _cache_lock:
        index = _load_cache_index()
        cutoff = datetime.utcnow() - timedelta(days=CACHE_TTL_DAYS)
        keep, remove = {}, []
        for key, entry in index.items():
            created_at = datetime.fromisoformat(entry.get("created_at", "2000-01-01"))
            if created_at < cutoff:
                remove.append(entry.get("filepath", ""))
            else:
                keep[key] = entry
        for fp in remove:
            try:
                if fp and os.path.exists(fp):
                    os.remove(fp)
            except Exception:
                pass
        _save_cache_index(keep)
        return len(keep), len(remove)


def get_cache_stats():
    """Return summary stats about the audio cache."""
    with _cache_lock:
        index = _load_cache_index()
    total = len(index)
    size_bytes = 0
    expired = 0
    cutoff = datetime.utcnow() - timedelta(days=CACHE_TTL_DAYS)
    for entry in index.values():
        fp = entry.get("filepath", "")
        if os.path.exists(fp):
            size_bytes += os.path.getsize(fp)
        created_at = datetime.fromisoformat(entry.get("created_at", "2000-01-01"))
        if created_at < cutoff:
            expired += 1
    return {
        "total_entries": total,
        "expired_entries": expired,
        "active_entries": total - expired,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
    }


# ---------------------------------------------------------------------------

def _get_elevenlabs_api_key():
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if api_key:
        return api_key

    hostname = os.environ.get("REPLIT_CONNECTORS_HOSTNAME", "")
    repl_identity = os.environ.get("REPL_IDENTITY", "")
    web_repl_renewal = os.environ.get("WEB_REPL_RENEWAL", "")

    if repl_identity:
        token = "repl " + repl_identity
    elif web_repl_renewal:
        token = "depl " + web_repl_renewal
    else:
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


US_STATE_ABBREVIATIONS = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}

ADDRESS_ABBREVIATIONS = [
    # Street types — match at word boundary before comma, space, or end
    (r'\bSt\.?(?=[\s,]|$)', 'Street'),
    (r'\bAve\.?(?=[\s,]|$)', 'Avenue'),
    (r'\bBlvd\.?(?=[\s,]|$)', 'Boulevard'),
    (r'\bDr\.?(?=[\s,]|$)', 'Drive'),
    (r'\bLn\.?(?=[\s,]|$)', 'Lane'),
    (r'\bRd\.?(?=[\s,]|$)', 'Road'),
    (r'\bCt\.?(?=[\s,]|$)', 'Court'),
    (r'\bPl\.?(?=[\s,]|$)', 'Place'),
    (r'\bCir\.?(?=[\s,]|$)', 'Circle'),
    (r'\bPkwy\.?(?=[\s,]|$)', 'Parkway'),
    (r'\bHwy\.?(?=[\s,]|$)', 'Highway'),
    (r'\bTpke\.?(?=[\s,]|$)', 'Turnpike'),
    (r'\bTer\.?(?=[\s,]|$)', 'Terrace'),
    (r'\bSq\.?(?=[\s,]|$)', 'Square'),
    (r'\bTrl\.?(?=[\s,]|$)', 'Trail'),
    (r'\bExpy\.?(?=[\s,]|$)', 'Expressway'),
    (r'\bFwy\.?(?=[\s,]|$)', 'Freeway'),
    (r'\bCres\.?(?=[\s,]|$)', 'Crescent'),
    (r'\bXing\.?(?=[\s,]|$)', 'Crossing'),
    (r'\bJct\.?(?=[\s,]|$)', 'Junction'),
    (r'\bRdg\.?(?=[\s,]|$)', 'Ridge'),
    (r'\bHolw\.?(?=[\s,]|$)', 'Hollow'),
    (r'\bMdw\.?(?=[\s,]|$)', 'Meadow'),
    (r'\bMdws\.?(?=[\s,]|$)', 'Meadows'),
    (r'\bGln\.?(?=[\s,]|$)', 'Glen'),
    (r'\bKnl\.?(?=[\s,]|$)', 'Knoll'),
    (r'\bKnls\.?(?=[\s,]|$)', 'Knolls'),
    (r'\bSpg\.?(?=[\s,]|$)', 'Spring'),
    (r'\bSpgs\.?(?=[\s,]|$)', 'Springs'),
    (r'\bVlg\.?(?=[\s,]|$)', 'Village'),
    (r'\bVis\.?(?=[\s,]|$)', 'Vista'),
    (r'\bAlly?\.?(?=[\s,]|$)', 'Alley'),
    (r'\bBrg\.?(?=[\s,]|$)', 'Bridge'),
    (r'\bCmn\.?(?=[\s,]|$)', 'Common'),
    (r'\bLndg\.?(?=[\s,]|$)', 'Landing'),
    (r'\bMnr\.?(?=[\s,]|$)', 'Manor'),
    (r'\bPt\.?(?=[\s,]|$)', 'Point'),
    (r'\bVw\.?(?=[\s,]|$)', 'View'),
    (r'\bSta\.?(?=[\s,]|$)', 'Station'),
    (r'\bTrce\.?(?=[\s,]|$)', 'Trace'),
    (r'\bWy\.?(?=[\s,]|$)', 'Way'),
    (r'\bGtwy\.?(?=[\s,]|$)', 'Gateway'),
    (r'\bLgt\.?(?=[\s,]|$)', 'Light'),
    (r'\bMt\.?(?=\s+[A-Za-z])', 'Mount'),
    (r'\bMtn\.?(?=[\s,]|$)', 'Mountain'),
    (r'\bFt\.?(?=[\s,]|$)', 'Fort'),
    # Unit designators — require digit or # after (prevents matching state abbreviations like FL)
    (r'\bApt\.?(?=\s*[#\d])', 'Apartment'),
    (r'\bSte\.?(?=\s*[#\d])', 'Suite'),
    (r'\bBldg\.?(?=\s*[#\dA-Za-z])', 'Building'),
    (r'\bFl\.(?=\s*[#\d])', 'Floor'),
    # Directionals — match before letters/digits, and also at end of string or before comma
    (r'(?<!\w)N\.?(?=\s+[\w])', 'North'),
    (r'(?<!\w)S\.?(?=\s+[\w])', 'South'),
    (r'(?<!\w)E\.?(?=\s+[\w])', 'East'),
    (r'(?<!\w)W\.?(?=\s+[\w])', 'West'),
    (r'\bNE\b\.?(?=[\s,]|$)', 'Northeast'),
    (r'\bNW\b\.?(?=[\s,]|$)', 'Northwest'),
    (r'\bSE\b\.?(?=[\s,]|$)', 'Southeast'),
    (r'\bSW\b\.?(?=[\s,]|$)', 'Southwest'),
]

ORDINAL_WORDS = {
    '1st': 'First', '2nd': 'Second', '3rd': 'Third', '4th': 'Fourth',
    '5th': 'Fifth', '6th': 'Sixth', '7th': 'Seventh', '8th': 'Eighth',
    '9th': 'Ninth', '10th': 'Tenth', '11th': 'Eleventh', '12th': 'Twelfth',
    '13th': 'Thirteenth', '14th': 'Fourteenth', '15th': 'Fifteenth',
    '16th': 'Sixteenth', '17th': 'Seventeenth', '18th': 'Eighteenth',
    '19th': 'Nineteenth', '20th': 'Twentieth', '21st': 'Twenty-first',
    '22nd': 'Twenty-second', '23rd': 'Twenty-third', '24th': 'Twenty-fourth',
    '25th': 'Twenty-fifth', '26th': 'Twenty-sixth', '27th': 'Twenty-seventh',
    '28th': 'Twenty-eighth', '29th': 'Twenty-ninth', '30th': 'Thirtieth',
    '31st': 'Thirty-first', '40th': 'Fortieth', '41st': 'Forty-first',
    '50th': 'Fiftieth', '51st': 'Fifty-first', '60th': 'Sixtieth',
    '70th': 'Seventieth', '80th': 'Eightieth', '90th': 'Ninetieth',
    '100th': 'One hundredth', '101st': 'One hundred first',
}

DIGIT_WORDS = {
    '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
    '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine',
}

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

ONES = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
        'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
        'seventeen', 'eighteen', 'nineteen']
TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']


def _number_to_words(n):
    if n < 0:
        return "negative " + _number_to_words(-n)
    if n == 0:
        return "zero"
    if n < 20:
        return ONES[n]
    if n < 100:
        t = TENS[n // 10]
        o = ONES[n % 10]
        return f"{t} {o}".strip() if o else t
    if n < 1000:
        h = ONES[n // 100] + " hundred"
        rem = n % 100
        if rem == 0:
            return h
        return f"{h} {_number_to_words(rem)}"
    if n < 10000:
        thousands = n // 1000
        rem = n % 1000
        if rem == 0:
            return _number_to_words(thousands) + " thousand"
        if rem < 100:
            return _number_to_words(thousands) + " thousand " + _number_to_words(rem)
        return _number_to_words(thousands) + " thousand " + _number_to_words(rem)
    if n < 1000000:
        thousands = n // 1000
        rem = n % 1000
        if rem == 0:
            return _number_to_words(thousands) + " thousand"
        return _number_to_words(thousands) + " thousand " + _number_to_words(rem)
    if n < 1000000000:
        millions = n // 1000000
        rem = n % 1000000
        if rem == 0:
            return _number_to_words(millions) + " million"
        return _number_to_words(millions) + " million " + _number_to_words(rem)
    return str(n)


def _speak_year(year):
    if year < 100:
        return _number_to_words(year)
    if year < 2000:
        first = year // 100
        second = year % 100
        if second == 0:
            return _number_to_words(first) + " hundred"
        return _number_to_words(first) + " " + _number_to_words(second)
    if year < 2010:
        return "two thousand " + (_number_to_words(year % 100) if year % 100 else "")
    first = year // 100
    second = year % 100
    return _number_to_words(first) + " " + _number_to_words(second)


def _speak_amount(val):
    val = int(round(val))
    if val == 0:
        return "zero dollars"
    if val < 0:
        return "negative " + _speak_amount(-val)
    if val >= 1100 and val < 10000:
        hundreds = val // 100
        rem = val % 100
        spoken = _number_to_words(hundreds) + " hundred"
        if rem > 0:
            spoken += " " + _number_to_words(rem)
        return spoken + " dollars"
    return _number_to_words(val) + " dollars"


ORDINAL_MAP = {
    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
    6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
    11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth",
    15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth",
    19: "nineteenth", 20: "twentieth", 21: "twenty first", 22: "twenty second",
    23: "twenty third", 24: "twenty fourth", 25: "twenty fifth",
    26: "twenty sixth", 27: "twenty seventh", 28: "twenty eighth",
    29: "twenty ninth", 30: "thirtieth", 31: "thirty first",
}


def _ordinal_spoken(n):
    n = int(n)
    if n in ORDINAL_MAP:
        return ORDINAL_MAP[n]
    return _number_to_words(n)


def _humanize_date(text):
    def replace_date(match):
        raw = match.group(0)
        try:
            for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%m/%d/%y", "%m-%d-%y",
                        "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
                        "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
                        "%B %d %Y", "%b %d %Y"):
                try:
                    dt = datetime.strptime(raw.strip(), fmt)
                    day = _ordinal_spoken(dt.day)
                    month = MONTH_NAMES[dt.month]
                    year = _speak_year(dt.year)
                    return f"{month} {day}... {year}"
                except ValueError:
                    continue
        except Exception:
            pass
        return raw

    text = re.sub(
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})\b',
        replace_date, text, flags=re.IGNORECASE
    )
    return text


def _humanize_phone(text):
    def replace_phone(match):
        raw = match.group(0)
        digits = re.sub(r'[^\d]', '', raw)
        if len(digits) == 11 and digits.startswith('1'):
            digits = digits[1:]
        if len(digits) == 10:
            p1 = ' '.join(DIGIT_WORDS[d] for d in digits[0:3])
            p2 = ' '.join(DIGIT_WORDS[d] for d in digits[3:6])
            p3 = ' '.join(DIGIT_WORDS[d] for d in digits[6:10])
            return f"{p1}... {p2}... {p3}"
        return raw

    text = re.sub(
        r'(?<!\w)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})(?!\w)',
        replace_phone, text
    )
    return text


def _humanize_amount(text):
    def replace_amount(match):
        raw = match.group(0)
        cleaned = raw.replace('$', '').replace(',', '').strip()
        try:
            val = float(cleaned)
            cents = round((val % 1) * 100)
            whole = int(val)
            spoken = _speak_amount(whole)
            if cents > 0:
                spoken = spoken.replace(" dollars", "") + f" and {_number_to_words(cents)} cents"
            return "about " + spoken
        except (ValueError, TypeError):
            return raw

    text = re.sub(
        r'\$[\d,]+(?:\.\d{1,2})?',
        replace_amount, text
    )
    return text


def _speak_street_number(num_str):
    """Speak a street number the way humans naturally say it.

    Humans say addresses as pairs, not as full numbers:
      9         → "nine"
      42        → "forty two"
      100       → "one hundred"
      123       → "one twenty three"
      1000      → "ten hundred"
      1100      → "eleven hundred"
      1234      → "twelve thirty four"
      2500      → "twenty five hundred"
      8001      → "eighty oh one"   (zero preserved as "oh")
      12345+    → digit by digit "one two three four five"
    """
    digits = num_str.strip()
    if not digits or not digits.isdigit():
        return num_str
    n = len(digits)
    if n <= 2:
        return _number_to_words(int(digits))
    elif n == 3:
        first = int(digits[0])
        rest_str = digits[1:]
        rest = int(rest_str)
        if rest == 0:
            return _number_to_words(first) + " hundred"
        if rest < 10:
            # e.g. "102" → "one oh two"
            return _number_to_words(first) + " oh " + _number_to_words(rest)
        return _number_to_words(first) + " " + _number_to_words(rest)
    elif n == 4:
        first_pair = int(digits[:2])
        second_str = digits[2:]
        second_pair = int(second_str)
        if second_pair == 0:
            # e.g. "2500" → "twenty five hundred"
            return _number_to_words(first_pair) + " hundred"
        if second_pair < 10:
            # e.g. "8001" → "eighty oh one", "1005" → "ten oh five"
            return _number_to_words(first_pair) + " oh " + _number_to_words(second_pair)
        return _number_to_words(first_pair) + " " + _number_to_words(second_pair)
    else:
        return " ".join(DIGIT_WORDS.get(d, d) for d in digits)


def _ordinal_to_word(token):
    """Convert ordinal like '3rd', '21st', '101st' to spoken word."""
    key = token.lower()
    if key in ORDINAL_WORDS:
        return ORDINAL_WORDS[key]
    # Fallback: parse the number and build spoken form
    m = re.match(r'^(\d+)(st|nd|rd|th)$', key)
    if not m:
        return token
    n = int(m.group(1))
    base = _number_to_words(n)
    suffix_map = {1: 'first', 2: 'second', 3: 'third'}
    last_two = n % 100
    last_one = n % 10
    if 11 <= last_two <= 13:
        spoken = base + 'th'
    elif last_one == 1:
        spoken = base.rstrip('e').rstrip('n') if base.endswith('one') else base
        spoken = base[:-3] + 'first' if base.endswith('one') else base + 'th'
    elif last_one == 2:
        spoken = base[:-3] + 'second' if base.endswith('two') else base + 'th'
    elif last_one == 3:
        spoken = base[:-5] + 'third' if base.endswith('three') else base + 'th'
    else:
        spoken = base + 'th'
    return spoken.capitalize()


def _humanize_address(text):
    """Transform a US property address into naturally spoken form.

    Processing order is critical — each step depends on the previous:
      1. PO Box (before any digit processing)
      2. Route / Highway / Interstate numbers
      3. Fractional house numbers (234 1/2)
      4. Leading house / street number → spoken pairs (anchored to start of string)
      5. Abbreviation expansion (street types, unit designators, directionals)
      6. Ordinal street names (3rd → Third)
      7. Unit numbers after expansion (Apartment 4B → Apartment four B)
      8. Hash-style unit numbers (#4B → number four B)
      9. State code → full name; zip code stripped
     10. Commas → brief spoken pause
     11. Final whitespace cleanup
    """
    if not text or not text.strip():
        return text

    text = text.strip()

    # 1. PO Box — must be first; converts box number to spoken form
    text = re.sub(
        r'\b(?:P\.?\s*O\.?\s*Box|Post\s+Office\s+Box)\s+(\d+)\b',
        lambda m: 'P O Box ' + _speak_street_number(m.group(1)),
        text, flags=re.IGNORECASE
    )

    # 2. Route / Highway / Interstate numbers — normalize before digit-processing
    text = re.sub(
        r'\b(?:IH|I)-(\d+)\b',
        lambda m: 'Interstate ' + _number_to_words(int(m.group(1))),
        text
    )
    text = re.sub(
        r'\bUS-?(\d+)\b',
        lambda m: 'US Route ' + _number_to_words(int(m.group(1))),
        text, flags=re.IGNORECASE
    )
    text = re.sub(
        r'\b(?:SR|SH|CR|FM|PR|Hwy|Hwys?)-?\s*(\d+)\b',
        lambda m: 'Route ' + _number_to_words(int(m.group(1))),
        text, flags=re.IGNORECASE
    )
    text = re.sub(
        r'\b(?:Rt|Rte|Route)\.?\s+#?(\d+)\b',
        lambda m: 'Route ' + _number_to_words(int(m.group(1))),
        text, flags=re.IGNORECASE
    )

    # 3. Fractional house numbers like "234 1/2 Oak St"
    text = re.sub(
        r'^(\d{1,5})\s+1/2\b',
        lambda m: _speak_street_number(m.group(1)) + ' and a half',
        text
    )

    # 4. Leading house / street number — anchored to the very start of the string.
    #    This is the most important step; using a simple '^' anchor (not lookbehind)
    #    avoids fixed-width lookbehind issues and reliably processes the house number.
    #    e.g. "1234 Oak St" → "twelve thirty four Oak St"
    #    e.g. "42 Maple Lane" → "forty two Maple Lane"
    text = re.sub(
        r'^(\d{1,6})(?=\s)',
        lambda m: _speak_street_number(m.group(1)),
        text
    )

    # 5a. Pre-pass: expand 'St'/'Ft' as proper-noun prefixes (Saint/Fort)
    #     BEFORE the main abbreviations loop, which would incorrectly expand them
    #     as street types.  Rule: St/Ft followed by a Title-Case word that is NOT
    #     itself a known street-type abbreviation → it's a Saint/Fort prefix.
    #     Examples: "St John" → "Saint John"; "Ft Hamilton" → "Fort Hamilton"
    #     Remaining 'St'/'Ft' tokens (those before comma/end) are handled below.
    _STREET_TYPE_ABBRS = {
        'st', 'ave', 'blvd', 'dr', 'ln', 'rd', 'ct', 'pl', 'cir', 'pkwy',
        'hwy', 'tpke', 'ter', 'sq', 'trl', 'expy', 'fwy', 'cres', 'xing',
        'jct', 'rdg', 'holw', 'mdw', 'mdws', 'gln', 'knl', 'knls', 'spg',
        'spgs', 'vlg', 'vis', 'aly', 'ally', 'brg', 'cmn', 'lndg', 'mnr',
        'pt', 'vw', 'sta', 'trce', 'wy', 'gtwy', 'lgt', 'mt', 'mtn', 'ft',
        'way', 'street', 'avenue', 'boulevard', 'drive', 'lane', 'road',
        'court', 'place', 'circle', 'parkway', 'highway', 'terrace',
    }

    def _prefix_expand(m, expansion):
        following = m.group(2)
        if following.lower() in _STREET_TYPE_ABBRS:
            return m.group(0)
        return expansion + m.group(1) + following

    text = re.sub(
        r'\bSt\.?(\s+)([A-Z][a-z]+)\b',
        lambda m: _prefix_expand(m, 'Saint'),
        text
    )
    text = re.sub(
        r'\bFt\.?(\s+)([A-Z][a-z]+)\b',
        lambda m: _prefix_expand(m, 'Fort'),
        text
    )

    # 5. Expand abbreviations — street types, unit designators, directionals.
    #    Applied AFTER step 4 so abbreviation expansion doesn't interfere with
    #    the leading number detection.
    for abbr, full in ADDRESS_ABBREVIATIONS:
        text = re.sub(abbr, full, text, flags=re.IGNORECASE)

    # 6. Ordinal street names: "3rd Avenue" → "Third Avenue"
    text = re.sub(
        r'\b(\d{1,3}(?:st|nd|rd|th))\b',
        lambda m: _ordinal_to_word(m.group(1)),
        text, flags=re.IGNORECASE
    )

    # 7. Unit / apartment / lot numbers after abbreviation expansion.
    #    "Apartment 4B" → "Apartment four B"
    #    "Suite 100" → "Suite one hundred"
    #    Captures optional trailing letter for alphanumeric units like "4B".
    def _speak_unit(match):
        label = match.group(1)
        num = match.group(2)
        letter = match.group(3) or ''
        spoken_num = _number_to_words(int(num))
        return label + ' ' + spoken_num + (' ' + letter.upper() if letter else '')

    text = re.sub(
        r'\b(Apartment|Suite|Unit|Lot|Floor|Building|Space|Room|Box)\s+#?(\d{1,4})([A-Za-z]?)\b',
        _speak_unit, text, flags=re.IGNORECASE
    )

    # 8. Hash-style unit numbers: "#4B" → "number four B"
    text = re.sub(
        r'#\s*(\d{1,4})([A-Za-z]?)\b',
        lambda m: 'number ' + _number_to_words(int(m.group(1))) + (' ' + m.group(2).upper() if m.group(2) else ''),
        text
    )

    # 9. State abbreviation → full name, then strip ZIP code.
    #    Only replaces known US state codes (via dict lookup) so random two-letter
    #    combos in city names are never misidentified as states.
    #    Matches state codes appearing before an optional zip at the end of the string.
    text = re.sub(
        r'(?:,\s*|\s+)([A-Z]{2})(?=\s*(?:\d{5}(?:-\d{4})?)?(?:\s*[,.\n]|\s*$))',
        lambda m: ', ' + (US_STATE_ABBREVIATIONS.get(m.group(1).upper()) or m.group(1)),
        text
    )

    # Strip trailing ZIP code (5-digit or ZIP+4)
    text = re.sub(r',?\s*\d{5}(?:-\d{4})?\s*$', '', text)

    # 10. Convert commas to a spoken-pause rhythm that sounds natural
    #     "123 Oak Street, Houston, Texas" → "123 Oak Street,  Houston,  Texas"
    #     (double space after comma gives TTS engines a breath cue)
    text = re.sub(r',\s*', ',  ', text)

    # 11. Final cleanup
    text = re.sub(r'\s{3,}', '  ', text)   # collapse excess spaces, keep doubles
    text = re.sub(r',\s*$', '', text).strip()

    return text


def _humanize_email(text):
    def speak_number_in_email(m):
        num = int(m.group(0))
        if num < 100:
            return _number_to_words(num)
        return ' '.join(DIGIT_WORDS[d] for d in m.group(0))

    def replace_email(match):
        raw = match.group(0)
        local, domain = raw.split('@', 1)
        local_spoken = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', local)
        local_spoken = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', local_spoken)
        local_spoken = re.sub(r'(\d+)', speak_number_in_email, local_spoken)
        local_spoken = re.sub(r'([a-z])([A-Z])', r'\1 \2', local_spoken)
        local_spoken = re.sub(r'[._-]', ' ', local_spoken)
        parts = domain.split('.')
        domain_spoken = ' dot '.join(parts)
        return f"{local_spoken} at {domain_spoken}"

    text = re.sub(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        replace_email, text
    )
    return text


def _add_micro_hesitations(text):
    text = re.sub(
        r'(?i)\b(I was just|I was|I\'m just|I\'m)\b(?!\.)',
        lambda m: m.group(0) + '...',
        text, count=2
    )
    text = re.sub(
        r'(?i)\b(looks like|it looks like|it seems like)\b(?!\.)',
        lambda m: m.group(0) + '...',
        text, count=2
    )
    return text


def _add_breath_pauses(text):
    text = re.sub(r',\s*(?=(?:but|so|because|since|actually|honestly)\b)', ' — ', text, flags=re.IGNORECASE)
    return text


def _conversational_smoothing(text):
    text = re.sub(r'\.{4,}', '...', text)
    text = re.sub(r'\.\.\.\s*\.\.\.', '...', text)
    text = re.sub(r'—\s*—', '—', text)
    text = re.sub(r'\s*—\s*', ' — ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def humanize_text(text):
    text = _humanize_date(text)
    text = _humanize_phone(text)
    text = _humanize_amount(text)
    text = _humanize_email(text)
    text = _add_micro_hesitations(text)
    text = _add_breath_pauses(text)
    text = _conversational_smoothing(text)
    return text


def render_template(template, contact, humanize=True):
    def replace_placeholder(match):
        key = match.group(1).strip().lower()
        val = contact.get(key, match.group(0))
        if humanize:
            if key in ("first_name", "name"):
                val = val.strip()
                if val:
                    val = val + "..."
            if key == "address":
                val = _humanize_address(val)
        return val

    result = re.sub(r'\{(\w+)\}', replace_placeholder, template)

    if humanize:
        result = humanize_text(result)

    return result


# ---------------------------------------------------------------------------
# VoiceStyle Engine — per-template voice personality
# ---------------------------------------------------------------------------

STYLE_PRESETS = {
    "professional": {
        "preset": "professional",
        "stability": 0.40,
        "similarity_boost": 0.82,
        "style": 0.12,
        "speed": 0.82,
        "use_speaker_boost": True,
        "fish_speed": 0.92,
        "fish_emotion": "neutral",
        "fillers": "none",
        "pause_style": "light",
        "emphasis_mode": "auto",
    },
    "friendly": {
        "preset": "friendly",
        "stability": 0.22,
        "similarity_boost": 0.84,
        "style": 0.28,
        "speed": 0.92,
        "use_speaker_boost": True,
        "fish_speed": 1.0,
        "fish_emotion": "happy",
        "fillers": "light",
        "pause_style": "light",
        "emphasis_mode": "auto",
    },
    "urgent": {
        "preset": "urgent",
        "stability": 0.35,
        "similarity_boost": 0.80,
        "style": 0.18,
        "speed": 1.05,
        "use_speaker_boost": True,
        "fish_speed": 1.08,
        "fish_emotion": "neutral",
        "fillers": "none",
        "pause_style": "minimal",
        "emphasis_mode": "strong",
    },
    "empathetic": {
        "preset": "empathetic",
        "stability": 0.18,
        "similarity_boost": 0.85,
        "style": 0.35,
        "speed": 0.75,
        "use_speaker_boost": True,
        "fish_speed": 0.88,
        "fish_emotion": "empathetic",
        "fillers": "light",
        "pause_style": "full",
        "emphasis_mode": "moderate",
    },
    "conversational": {
        "preset": "conversational",
        "stability": 0.20,
        "similarity_boost": 0.82,
        "style": 0.25,
        "speed": 0.88,
        "use_speaker_boost": True,
        "fish_speed": 0.97,
        "fish_emotion": "neutral",
        "fillers": "natural",
        "pause_style": "natural",
        "emphasis_mode": "auto",
    },
}


def _get_style_preset(name):
    """Return a full settings dict for a named style preset (or 'professional' as default)."""
    return dict(STYLE_PRESETS.get(name or "professional", STYLE_PRESETS["professional"]))


import random as _random

_FILLERS_STARTERS = ["So, ", "Well, ", "Hey — ", "Hi, so "]
_FILLERS_LIGHT = ["So, ", "Well, "]
_FILLERS_NATURAL_MID = ["um, ", "uh, ", "you know, ", "I mean, "]


def _inject_fillers(script, level, _rng=None):
    """Inject natural filler words into the script at appropriate points.

    level: 'none' | 'light' | 'natural'
    - none: return unchanged
    - light: prepend a soft starter to the first line only
    - natural: add mid-sentence fillers at some sentence breaks too

    _rng: optional random.Random instance for reproducible output. When None,
          a deterministic seed derived from the script content is used so that
          build_processed_script() and _apply_voice_enhancements() produce the
          same filler choices for the same script.
    """
    if not level or level == "none":
        return script

    script = script.strip()
    if not script:
        return script

    if _rng is None:
        seed = int(hashlib.sha256(script.encode("utf-8")).hexdigest()[:8], 16)
        _rng = _random.Random(seed)

    if level == "light":
        starter = _FILLERS_LIGHT[_rng.randint(0, len(_FILLERS_LIGHT) - 1)]
        lower = script[0].lower()
        rest = script[1:]
        return starter + lower + rest

    if level == "natural":
        starter = _FILLERS_STARTERS[_rng.randint(0, len(_FILLERS_STARTERS) - 1)]
        lower = script[0].lower()
        rest = script[1:]
        script = starter + lower + rest
        sentences = re.split(r'(?<=[.!?])\s+', script)
        result = []
        for i, sent in enumerate(sentences):
            if i > 0 and i < len(sentences) - 1 and _rng.random() < 0.30:
                filler = _FILLERS_NATURAL_MID[_rng.randint(0, len(_FILLERS_NATURAL_MID) - 1)]
                first_char = sent[0].lower() if sent else ""
                rest_sent = sent[1:] if sent else ""
                sent = filler + first_char + rest_sent
            result.append(sent)
        return " ".join(result)

    return script


def _inject_pauses(script, style, provider):
    """Inject pause markers into the script.

    style: 'minimal' | 'light' | 'natural' | 'full'
    provider: 'elevenlabs' | 'fish_audio' | '_el_plain'

    For ElevenLabs with SSML-capable models: uses <break time="Xs"/>
    For Fish Audio and non-SSML ElevenLabs ('_el_plain'): uses comma/ellipsis punctuation
    """
    if not style or style == "minimal":
        return script

    # Only emit SSML tags for ElevenLabs when the model supports SSML
    is_el_ssml = (provider == "elevenlabs")

    def _pause(sec):
        if is_el_ssml:
            return f' <break time="{sec}s"/> '
        return ", "

    def _long_pause(sec):
        if is_el_ssml:
            return f' <break time="{sec}s"/> '
        return "... "

    if style in ("light", "natural", "full"):
        script = re.sub(
            r'(\b(?:call|reach|text|contact)\s+(?:me|us)\s+(?:at|back\s+at|on)\b)',
            lambda m: _long_pause(0.35) + m.group(0),
            script, flags=re.IGNORECASE
        )
        script = re.sub(
            r'(\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b)',
            lambda m: m.group(0) + _pause(0.25),
            script
        )

    if style in ("natural", "full"):
        script = re.sub(r'(?<=[.!?])\s+(?=[A-Z])', lambda m: _pause(0.3), script)

    if style == "full":
        script = re.sub(
            r'(\b(?:I wanted to reach out|I\'m reaching out|Just wanted to|I was hoping)\b)',
            lambda m: m.group(0) + _pause(0.25),
            script, flags=re.IGNORECASE
        )
        script = re.sub(r'\.\.\.',
                        _long_pause(0.4) if is_el_ssml else "... ",
                        script)

    return script


def _inject_emphasis(script, mode, provider):
    """Wrap phone numbers and key CTAs with emphasis hints.

    mode: 'off' | 'auto' | 'moderate' | 'strong'
    provider: 'elevenlabs' | 'fish_audio' | '_el_plain'

    ElevenLabs SSML-capable models: wraps in <emphasis level="..."> tags.
    Fish Audio / non-SSML ElevenLabs: uses light UPPER-CASE capitalization
    on key words so TTS naturally stresses them.
    """
    if not mode or mode == "off":
        return script

    is_el_ssml = (provider == "elevenlabs")

    level_map = {
        "auto": "moderate",
        "moderate": "moderate",
        "strong": "strong",
    }
    el_level = level_map.get(mode, "moderate")

    def _emph(text):
        if is_el_ssml:
            return f'<emphasis level="{el_level}">{text}</emphasis>'
        # Fish Audio / plain EL: capitalize key words for natural stress
        return text.upper()

    # Phone numbers
    script = re.sub(
        r'(\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b)',
        lambda m: _emph(m.group(0)),
        script
    )

    # Call-to-action phrases
    cta_pattern = r'\b(call\s+(?:me|us)(?:\s+(?:at|back))?|(?:reach|contact)\s+(?:me|us)|text\s+(?:me|us)|give\s+(?:me|us)\s+a\s+(?:call|ring))\b'
    script = re.sub(cta_pattern,
                    lambda m: _emph(m.group(0)),
                    script, flags=re.IGNORECASE)

    return script


def _apply_voice_enhancements(script, settings, provider, model_id=""):
    """Apply all VoiceStyle Engine enhancements to a script.

    settings: the full voice_settings dict (may include preset, fillers, pause_style, emphasis_mode)
    provider: 'fish_audio' | 'elevenlabs'
    model_id: used to gate SSML injection for ElevenLabs; only inject SSML tags for SSML_MODELS.

    Default for each key is the no-op value so legacy templates (those without a VoiceStyle
    preset stored in voice_settings) pass through this pipeline unchanged.
    """
    if not settings:
        return script

    # Explicit no-ops when keys are absent — legacy templates must be unaffected
    fillers = settings.get("fillers") or "none"
    pause_style = settings.get("pause_style") or "minimal"
    emphasis_mode = settings.get("emphasis_mode") or "off"

    # For ElevenLabs, only use SSML markup when the model actually supports it.
    # When the model is not in SSML_MODELS, use a sentinel that suppresses tags.
    effective_provider = provider
    if provider == "elevenlabs" and model_id and model_id not in SSML_MODELS:
        effective_provider = "_el_plain"  # EL without SSML capability

    script = _inject_fillers(script, fillers)
    script = _inject_pauses(script, pause_style, effective_provider)
    script = _inject_emphasis(script, emphasis_mode, effective_provider)

    return script


def build_processed_script(script, settings, provider):
    """Return a human-readable annotated version of the script for UI display.

    Shows injected fillers, [⏸] pause markers, and **emphasized** text
    so users can see exactly what the AI will say.
    """
    if not settings:
        return script

    # No-op defaults so legacy templates (without VoiceStyle keys) render unchanged
    fillers = settings.get("fillers") or "none"
    pause_style = settings.get("pause_style") or "minimal"
    emphasis_mode = settings.get("emphasis_mode") or "off"

    processed = _inject_fillers(script, fillers)

    def _pause_marker(sec):
        return f" [⏸] "

    def _long_pause_marker(sec):
        return f" [⏸⏸] "

    if pause_style in ("light", "natural", "full"):
        processed = re.sub(
            r'(\b(?:call|reach|text|contact)\s+(?:me|us)\s+(?:at|back\s+at|on)\b)',
            lambda m: _long_pause_marker(0.35) + m.group(0),
            processed, flags=re.IGNORECASE
        )
        processed = re.sub(
            r'(\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b)',
            lambda m: m.group(0) + _pause_marker(0.25),
            processed
        )

    if pause_style in ("natural", "full"):
        processed = re.sub(r'(?<=[.!?])\s+(?=[A-Z])', " [⏸] ", processed)

    if pause_style == "full":
        processed = re.sub(
            r'(\b(?:I wanted to reach out|I\'m reaching out|Just wanted to|I was hoping)\b)',
            lambda m: m.group(0) + _pause_marker(0.25),
            processed, flags=re.IGNORECASE
        )

    if emphasis_mode and emphasis_mode != "off":
        processed = re.sub(
            r'(\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b)',
            lambda m: f"**{m.group(0)}**",
            processed
        )
        cta_pattern = r'\b(call\s+(?:me|us)(?:\s+(?:at|back))?|(?:reach|contact)\s+(?:me|us)|text\s+(?:me|us)|give\s+(?:me|us)\s+a\s+(?:call|ring))\b'
        processed = re.sub(cta_pattern,
                           lambda m: f"**{m.group(0)}**",
                           processed, flags=re.IGNORECASE)

    return processed


def build_processed_script_html(script, settings, provider):
    """Return a safe HTML version of the processed script for in-browser display.

    Fillers are highlighted in blue, pause markers in muted grey, and emphasized
    text in bold primary-color. The output is sanitized so it is safe to render
    as innerHTML.
    """
    import html as _html_mod

    plain = build_processed_script(script, settings, provider)
    safe = _html_mod.escape(plain)

    # Bold emphasis markers (**text**) → colored <strong>
    safe = re.sub(
        r'\*\*(.+?)\*\*',
        r'<strong style="color:var(--gads-primary,#4f46e5);">\1</strong>',
        safe
    )

    # Long pause [⏸⏸]
    safe = safe.replace(
        '[⏸⏸]',
        '<span style="color:#9ca3af;font-size:11px;font-weight:600;" title="Long pause">[⏸⏸]</span>'
    )

    # Short pause [⏸]
    safe = safe.replace(
        '[⏸]',
        '<span style="color:#9ca3af;font-size:11px;font-weight:600;" title="Pause">[⏸]</span>'
    )

    # Filler words — highlight common starter fillers in blue
    _FILLER_RE = re.compile(
        r'(^(?:So, |Well, |Hey — |Hi, so )|(?:um, |uh, |you know, |I mean, ))',
        re.IGNORECASE
    )
    safe = _FILLER_RE.sub(
        r'<span style="color:#2563eb;font-style:italic;">\1</span>',
        safe
    )

    return safe


DEFAULT_VOICE_SETTINGS = {
    "stability": 0.28,
    "similarity_boost": 0.82,
    "style": 0.20,
    "speed": 0.80,
    "use_speaker_boost": True,
}

SSML_MODELS = {
    "eleven_turbo_v2", "eleven_turbo_v2_5",
    "eleven_flash_v2", "eleven_flash_v2_5",
    "eleven_english_v1",
}


def _build_voice_settings(custom_settings=None):
    settings = dict(DEFAULT_VOICE_SETTINGS)
    if custom_settings:
        for key in ("stability", "similarity_boost", "style", "speed", "use_speaker_boost"):
            if key in custom_settings:
                settings[key] = custom_settings[key]
    settings["stability"] = max(0.0, min(1.0, float(settings["stability"])))
    settings["similarity_boost"] = max(0.0, min(1.0, float(settings["similarity_boost"])))
    settings["style"] = max(0.0, min(1.0, float(settings["style"])))
    settings["speed"] = max(0.7, min(1.2, float(settings["speed"])))
    return settings


def _prepare_tts_payload(script, model_id, vs):
    use_ssml = model_id in SSML_MODELS
    if use_ssml:
        ssml_text = script
        ssml_text = ssml_text.replace(' — ', ' <break time="0.6s"/> ')
        ssml_text = re.sub(r'\.\.\.', '<break time="0.35s"/>', ssml_text)
        payload = {
            "text": ssml_text,
            "model_id": model_id,
            "voice_settings": vs,
            "enable_ssml_parsing": True,
        }
    else:
        payload = {
            "text": script,
            "model_id": model_id,
            "voice_settings": vs,
        }
    return payload


def _prepare_fish_text(script):
    """Convert a humanized script to plain text suitable for Fish Audio.
    Fish Audio does not support SSML — we use punctuation for natural pacing."""
    text = script
    # em-dash breath pauses → comma (creates natural pause)
    text = text.replace(' — ', ', ')
    text = text.replace('—', ', ')
    # ellipsis hesitations → comma-space
    text = re.sub(r'\.\.\.', ', ', text)
    # clean up double commas or leading commas
    text = re.sub(r',\s*,', ',', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def _generate_audio_elevenlabs(api_key, script, voice_id, model_id, voice_settings, filepath):
    """Call ElevenLabs TTS and save MP3 to filepath. Returns (success, error_str)."""
    vs = _build_voice_settings(voice_settings)
    payload = _prepare_tts_payload(script, model_id, vs)
    try:
        resp = requests.post(
            f"{ELEVENLABS_API_BASE}/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(resp.content)
        return True, None
    except Exception as e:
        return False, str(e)


def _generate_audio_fish(script, voice_id, fish_speed=1.0, fish_emotion="neutral", filepath=None):
    """Call Fish Audio TTS and save MP3 to filepath. Returns (success, error_str)."""
    try:
        from humana_voice.fish_client import text_to_speech as fish_tts
        fish_text = _prepare_fish_text(script)
        resp = fish_tts(voice_id, fish_text, speed=fish_speed, emotion=fish_emotion)
        audio_bytes = b"".join(resp.iter_content(chunk_size=8192))
        if not audio_bytes:
            return False, "Fish Audio returned empty response"
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
        return True, None
    except Exception as e:
        return False, str(e)


def generate_audio_for_contact(contact, template, voice_id, model_id="eleven_multilingual_v2",
                                voice_settings=None, humanize=True, provider="fish_audio",
                                fish_speed=1.0, fish_emotion="neutral", api_key=None,
                                _prerendered_script=None, _cached_source=None):
    """Generate a personalized voicemail MP3 for one contact.

    provider: "fish_audio" (default, cheaper) or "elevenlabs" (legacy/premium).
    voice_settings: full VoiceStyle Engine dict (includes preset, fillers, pause_style,
                    emphasis_mode, fish_speed, fish_emotion, stability, etc.)

    Optimisation params (internal):
      _prerendered_script: skip render_template() — script already computed by the batch worker
      _cached_source: filepath to an already-generated audio file to copy instead of calling TTS
    """
    script = _prerendered_script if _prerendered_script is not None else render_template(template, contact, humanize=humanize)
    phone = contact.get("phone", "unknown")
    safe_phone = re.sub(r'[^\d]', '', phone)
    filename = f"pvm_{safe_phone}_{int(time.time())}.mp3"
    filepath = os.path.join(PVM_DIR, filename)
    os.makedirs(PVM_DIR, exist_ok=True)

    # --- VoiceStyle Engine: override fish params from voice_settings if provided ---
    if voice_settings:
        if "fish_speed" in voice_settings:
            fish_speed = float(voice_settings["fish_speed"])
        if "fish_emotion" in voice_settings:
            fish_emotion = voice_settings["fish_emotion"]

    # --- Apply voice enhancements (fillers, pauses, emphasis) ---
    enhanced_script = _apply_voice_enhancements(script, voice_settings, provider, model_id=model_id)

    # --- Deduplication: worker found a previously-generated file for identical script ---
    if _cached_source and os.path.exists(_cached_source):
        shutil.copy2(_cached_source, filepath)
        return {"phone": phone, "filename": filename, "script": script, "success": True, "from_cache": True}

    # --- Content-addressed cache lookup (includes voice_settings + model_id in key) ---
    cached_path = _cache_lookup(enhanced_script, voice_id, provider, voice_settings, model_id=model_id)
    if cached_path:
        shutil.copy2(cached_path, filepath)
        logger.debug(f"PVM cache hit for {phone} ({provider})")
        return {"phone": phone, "filename": filename, "script": script, "success": True, "from_cache": True}

    # --- Generate fresh audio ---
    if provider == "fish_audio":
        success, error = _generate_audio_fish(enhanced_script, voice_id, fish_speed=fish_speed,
                                               fish_emotion=fish_emotion, filepath=filepath)
    else:
        if not api_key:
            return {"phone": phone, "filename": None, "script": script, "success": False,
                    "error": "ElevenLabs API key not provided"}
        success, error = _generate_audio_elevenlabs(api_key, enhanced_script, voice_id, model_id,
                                                     voice_settings, filepath)

    if success:
        # Store in content-addressed cache for future reuse
        try:
            _cache_store(enhanced_script, voice_id, provider, filepath, voice_settings, model_id=model_id)
        except Exception as ce:
            logger.warning(f"PVM cache store failed: {ce}")
        return {"phone": phone, "filename": filename, "script": script, "success": True, "from_cache": False}
    else:
        logger.error(f"TTS ({provider}) failed for {phone}: {error}")
        return {"phone": phone, "filename": None, "script": script, "success": False, "error": error}


def start_generation(contacts, template, voice_id, base_url, voice_settings=None, humanize=True,
                     model_id="eleven_multilingual_v2", provider="fish_audio",
                     fish_speed=1.0, fish_emotion="neutral"):
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
        args=(contacts, template, voice_id, base_url, voice_settings, humanize, model_id,
              provider, fish_speed, fish_emotion),
        daemon=True,
    )
    t.start()
    logger.info(f"PVM generation started: {len(contacts)} contacts, provider={provider}")
    return True, "Generation started"


def _generation_worker(contacts, template, voice_id, base_url, voice_settings=None, humanize=True,
                       model_id="eleven_multilingual_v2", provider="fish_audio",
                       fish_speed=1.0, fish_emotion="neutral"):
    api_key = None
    if provider == "elevenlabs":
        try:
            api_key = _get_elevenlabs_api_key()
        except Exception as e:
            with _state_lock:
                _generation_state["status"] = "error"
                _generation_state["errors"].append(f"Auth failed: {e}")
            return

    # --- Phase 1: Pre-render all scripts and group contacts by identical script ---
    # This deduplicates TTS calls: if 50 contacts share the same script (e.g., no {first_name}
    # placeholder or duplicate names), we only call the TTS API once.
    script_groups = {}  # rendered_script -> list of contacts
    contact_scripts = {}  # phone -> rendered_script
    for contact in contacts:
        script = render_template(template, contact, humanize=humanize)
        phone = contact.get("phone", "unknown")
        contact_scripts[phone] = script
        script_groups.setdefault(script, []).append(contact)

    unique_scripts = list(script_groups.keys())
    total_contacts = len(contacts)
    unique_count = len(unique_scripts)
    dup_count = total_contacts - unique_count
    if dup_count > 0:
        logger.info(f"PVM deduplication: {total_contacts} contacts → {unique_count} unique scripts "
                    f"({dup_count} duplicates avoided)")

    audio_map = {}
    completed = 0

    # --- Phase 2: Generate one audio file per unique script ---
    # script → first generated filepath (used to copy for duplicates)
    script_to_filepath = {}

    for script, group in script_groups.items():
        primary_contact = group[0]
        phone = primary_contact.get("phone", "unknown")

        # Check if we already have a source file for this script (from a previous iteration — shouldn't happen
        # since scripts are keys, but guard anyway)
        cached_source = script_to_filepath.get(script)

        result = generate_audio_for_contact(
            primary_contact, template, voice_id,
            model_id=model_id,
            voice_settings=voice_settings,
            humanize=humanize,
            provider=provider,
            fish_speed=fish_speed,
            fish_emotion=fish_emotion,
            api_key=api_key,
            _prerendered_script=script,
            _cached_source=cached_source,
        )

        completed += 1
        with _state_lock:
            _generation_state["completed"] = completed

        if result["success"]:
            source_file = os.path.join(PVM_DIR, result["filename"])
            script_to_filepath[script] = source_file
            audio_url = f"{base_url}/audio/personalized/{result['filename']}"
            audio_map[result["phone"]] = {
                "audio_url": audio_url,
                "script": result["script"],
                "filename": result["filename"],
                "from_cache": result.get("from_cache", False),
            }

            # --- Phase 3: Copy audio for duplicate contacts in this group ---
            for dup_contact in group[1:]:
                dup_result = generate_audio_for_contact(
                    dup_contact, template, voice_id,
                    model_id=model_id,
                    voice_settings=voice_settings,
                    humanize=humanize,
                    provider=provider,
                    fish_speed=fish_speed,
                    fish_emotion=fish_emotion,
                    api_key=api_key,
                    _prerendered_script=script,
                    _cached_source=source_file,
                )
                completed += 1
                with _state_lock:
                    _generation_state["completed"] = completed
                if dup_result["success"]:
                    dup_url = f"{base_url}/audio/personalized/{dup_result['filename']}"
                    audio_map[dup_result["phone"]] = {
                        "audio_url": dup_url,
                        "script": dup_result["script"],
                        "filename": dup_result["filename"],
                        "from_cache": True,
                    }
                else:
                    with _state_lock:
                        _generation_state["errors"].append(
                            f"{dup_result['phone']}: {dup_result.get('error', 'Unknown error')}"
                        )
        else:
            with _state_lock:
                _generation_state["errors"].append(f"{phone}: {result.get('error', 'Unknown error')}")
            # Mark all duplicates in this group as failed too
            for dup_contact in group[1:]:
                completed += 1
                dp = dup_contact.get("phone", "unknown")
                with _state_lock:
                    _generation_state["completed"] = completed
                    _generation_state["errors"].append(f"{dp}: skipped (primary generation failed)")

        # Small rate-limit pause between unique scripts only
        if completed < total_contacts:
            time.sleep(0.3)

    _save_audio_map(audio_map)

    cache_hits = sum(1 for v in audio_map.values() if v.get("from_cache"))
    with _state_lock:
        _generation_state["status"] = "complete"

    logger.info(
        f"Personalized VM generation complete: {len(audio_map)}/{total_contacts} successful "
        f"({cache_hits} from cache, {unique_count} unique TTS calls)"
    )


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


def generate_preview_audio(contact, template, voice_id, voice_settings=None, humanize=True,
                           model_id="eleven_multilingual_v2", provider="fish_audio",
                           fish_speed=1.0, fish_emotion="neutral"):
    """Generate a preview audio for a single contact.

    voice_settings: full VoiceStyle Engine dict (includes fillers, pause_style, emphasis_mode,
                    fish_speed, fish_emotion, stability, etc.)
    """
    script = render_template(template, contact, humanize=humanize)
    filename = f"pvm_preview_{int(time.time())}.mp3"
    filepath = os.path.join(PVM_DIR, filename)
    os.makedirs(PVM_DIR, exist_ok=True)

    # Override fish params from voice_settings if provided
    if voice_settings:
        if "fish_speed" in voice_settings:
            fish_speed = float(voice_settings["fish_speed"])
        if "fish_emotion" in voice_settings:
            fish_emotion = voice_settings["fish_emotion"]

    # Apply VoiceStyle Engine enhancements
    enhanced_script = _apply_voice_enhancements(script, voice_settings, provider, model_id=model_id)

    if provider == "fish_audio":
        success, error = _generate_audio_fish(enhanced_script, voice_id, fish_speed=fish_speed,
                                               fish_emotion=fish_emotion, filepath=filepath)
        if success:
            return filename, script
        logger.error(f"Fish Audio preview failed: {error}")
        return None, error
    else:
        try:
            api_key = _get_elevenlabs_api_key()
        except Exception as e:
            return None, str(e)
        success, error = _generate_audio_elevenlabs(api_key, enhanced_script, voice_id, model_id,
                                                     voice_settings, filepath)
        if success:
            return filename, script
        logger.error(f"ElevenLabs preview failed: {error}")
        return None, error


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
