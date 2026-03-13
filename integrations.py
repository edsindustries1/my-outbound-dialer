"""
integrations.py - CRM and webhook integration module for Open Humana.

Handles:
  - Outbound webhooks (fires on call completion to any user-configured URL)
  - HubSpot CRM sync via Private App access token (paste-and-go, no OAuth)
  - GoHighLevel (GHL) CRM sync via Location API Key (paste-and-go)
  - Pipedrive CRM sync via API Token (paste-and-go)
  - Google Sheets sync via Service Account (operator sets GOOGLE_SERVICE_ACCOUNT_JSON)

All per-user configs stored in UserAppData (key-value store).
"""

import os
import json
import hmac
import hashlib
import logging
import threading
import requests
from datetime import datetime, timedelta

logger = logging.getLogger("voicemail_app")

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

KEY_WEBHOOK     = "outbound_webhook"
KEY_HUBSPOT     = "hubspot_config"
KEY_GHL         = "ghl_config"
KEY_PIPEDRIVE   = "pipedrive_config"
KEY_GSHEETS_CFG = "google_sheets_config"


# ── Config helpers ─────────────────────────────────────────────────────────────

def get_integration_config(user_id, key):
    """Read a JSON blob from UserAppData for the given user and key."""
    try:
        from app import app as _app
        from models import UserAppData
        with _app.app_context():
            row = UserAppData.query.filter_by(user_id=user_id, data_key=key).first()
            if not row:
                return {}
            return json.loads(row.data_value or "{}")
    except Exception as e:
        logger.error(f"[INTEGRATIONS] get_integration_config({key}) error: {e}")
        return {}


def set_integration_config(user_id, key, data):
    """Persist a JSON blob to UserAppData for the given user and key."""
    try:
        from app import app as _app
        from models import db, UserAppData
        with _app.app_context():
            row = UserAppData.query.filter_by(user_id=user_id, data_key=key).first()
            if row:
                row.data_value = json.dumps(data)
            else:
                row = UserAppData(user_id=user_id, data_key=key, data_value=json.dumps(data))
                db.session.add(row)
            db.session.commit()
    except Exception as e:
        logger.error(f"[INTEGRATIONS] set_integration_config({key}) error: {e}")


def integration_status(user_id):
    """Return a summary of which integrations are connected and enabled."""
    wh  = get_integration_config(user_id, KEY_WEBHOOK)
    hs  = get_integration_config(user_id, KEY_HUBSPOT)
    ghl = get_integration_config(user_id, KEY_GHL)
    pd  = get_integration_config(user_id, KEY_PIPEDRIVE)
    gs  = get_integration_config(user_id, KEY_GSHEETS_CFG)

    gs_service_account_ok = bool(GOOGLE_SERVICE_ACCOUNT_JSON)

    return {
        "webhook": {
            "connected":  bool(wh.get("url")),
            "enabled":    bool(wh.get("enabled")),
            "url":        wh.get("url", ""),
            "has_secret": bool(wh.get("secret")),
        },
        "hubspot": {
            "connected": bool(hs.get("access_token")),
            "enabled":   bool(hs.get("enabled")),
            "portal_id": hs.get("portal_id", ""),
        },
        "gohighlevel": {
            "connected":   bool(ghl.get("api_key")),
            "enabled":     bool(ghl.get("enabled")),
            "location_id": ghl.get("location_id", ""),
        },
        "pipedrive": {
            "connected":  bool(pd.get("api_token")),
            "enabled":    bool(pd.get("enabled")),
            "company":    pd.get("company_domain", ""),
        },
        "google_sheets": {
            "connected":                  bool(gs.get("sheet_id")),
            "enabled":                    bool(gs.get("enabled")),
            "sheet_id":                   gs.get("sheet_id", ""),
            "sheet_name":                 gs.get("sheet_name", "Call Log"),
            "service_account_configured": gs_service_account_ok,
            "service_account_email":      _get_sa_email(),
        },
    }


def _get_sa_email():
    """Extract the service account email from the JSON env var, if set."""
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        return ""
    try:
        sa = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        return sa.get("client_email", "")
    except Exception:
        return ""


# ── Outbound Webhook ──────────────────────────────────────────────────────────

def fire_webhook(user_id, call_record):
    """POST call_record to user's configured webhook URL."""
    cfg = get_integration_config(user_id, KEY_WEBHOOK)
    if not cfg.get("enabled") or not cfg.get("url"):
        return
    url    = cfg["url"]
    secret = cfg.get("secret", "")
    payload = {
        "event":     "call.completed",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source":    "open_humana",
        "data":      call_record,
    }
    body    = json.dumps(payload, default=str)
    headers = {
        "Content-Type": "application/json",
        "User-Agent":   "OpenHumana-Webhook/1.0",
    }
    if secret:
        sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        headers["X-OpenHumana-Signature"] = f"sha256={sig}"
    try:
        resp = requests.post(url, data=body, headers=headers, timeout=8)
        logger.info(f"[WEBHOOK] user={user_id} → {url} | status={resp.status_code}")
    except Exception as e:
        logger.warning(f"[WEBHOOK] user={user_id} → {url} failed: {e}")


# ── HubSpot (Private App token) ───────────────────────────────────────────────

def sync_to_hubspot(user_id, call_record):
    """
    Find or create a HubSpot contact by phone, then log the call activity.
    Uses HubSpot Private App access token — no OAuth required.
    """
    cfg = get_integration_config(user_id, KEY_HUBSPOT)
    if not cfg.get("enabled") or not cfg.get("access_token"):
        return

    token   = cfg["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }
    phone = (call_record.get("number") or "").strip()
    if not phone:
        return

    contact_id = None
    try:
        search = requests.post(
            "https://api.hubapi.com/crm/v3/objects/contacts/search",
            headers=headers,
            json={
                "filterGroups": [{"filters": [{"propertyName": "phone", "operator": "EQ", "value": phone}]}],
                "limit": 1,
            },
            timeout=10,
        )
        if search.status_code == 200:
            results = search.json().get("results", [])
            if results:
                contact_id = results[0]["id"]
    except Exception as e:
        logger.error(f"[HUBSPOT] Contact search error for user {user_id}: {e}")

    if not contact_id:
        try:
            create = requests.post(
                "https://api.hubapi.com/crm/v3/objects/contacts",
                headers=headers,
                json={"properties": {"phone": phone, "hs_lead_status": "OPEN"}},
                timeout=10,
            )
            if create.status_code == 201:
                contact_id = create.json().get("id")
        except Exception as e:
            logger.error(f"[HUBSPOT] Contact create error for user {user_id}: {e}")

    if not contact_id:
        logger.warning(f"[HUBSPOT] Could not find/create contact for {phone}, user {user_id}")
        return

    notes_parts = [f"Status: {call_record.get('status_description', call_record.get('status', ''))}"]
    if call_record.get("voicemail_dropped"):
        notes_parts.append("Voicemail dropped")
    if call_record.get("transferred"):
        notes_parts.append("Transferred to human")
    if call_record.get("amd_result"):
        notes_parts.append(f"AMD: {call_record['amd_result']}")
    if call_record.get("ring_duration"):
        notes_parts.append(f"Duration: {call_record['ring_duration']}s")

    connected   = call_record.get("transferred") or call_record.get("voicemail_dropped")
    outcome     = "CONNECTED" if connected else "NO_ANSWER"
    duration_ms = int((call_record.get("ring_duration") or 0) * 1000)

    try:
        eng = requests.post(
            "https://api.hubapi.com/crm/v3/objects/calls",
            headers=headers,
            json={
                "properties": {
                    "hs_call_title":       "Outbound Call — Open Humana",
                    "hs_call_body":        " | ".join(notes_parts),
                    "hs_call_direction":   "OUTBOUND",
                    "hs_call_disposition": outcome,
                    "hs_call_duration":    str(duration_ms),
                    "hs_call_status":      outcome,
                    "hs_timestamp":        str(int(datetime.utcnow().timestamp() * 1000)),
                    "hs_call_from_number": call_record.get("from_number", ""),
                    "hs_call_to_number":   phone,
                },
            },
            timeout=10,
        )
        if eng.status_code == 201:
            call_eng_id = eng.json().get("id")
            requests.put(
                f"https://api.hubapi.com/crm/v3/objects/calls/{call_eng_id}/associations/contacts/{contact_id}/engagements_called",
                headers=headers,
                timeout=8,
            )
            logger.info(f"[HUBSPOT] Call logged for contact {contact_id}, user {user_id}")
        else:
            logger.warning(f"[HUBSPOT] Engagement failed ({eng.status_code}): {eng.text[:200]}")
    except Exception as e:
        logger.error(f"[HUBSPOT] Engagement error for user {user_id}: {e}")


def hubspot_verify_token(token):
    """
    Verify a HubSpot Private App token by calling the account info endpoint.
    Returns (True, portal_id) on success or (False, error_message) on failure.
    """
    try:
        resp = requests.get(
            "https://api.hubapi.com/account-info/v3/details",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            portal_id = str(data.get("portalId", ""))
            return True, portal_id
        return False, f"Invalid token (HTTP {resp.status_code})"
    except Exception as e:
        return False, str(e)


# ── GoHighLevel (Location API Key) ────────────────────────────────────────────

GHL_BASE = "https://rest.gohighlevel.com/v1"


def ghl_verify_token(api_key):
    """
    Verify a GHL Location API Key by fetching the location profile.
    Returns (True, location_id) or (False, error_message).
    """
    try:
        resp = requests.get(
            f"{GHL_BASE}/locations/",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            loc = data.get("location") or {}
            location_id = loc.get("id", "")
            return True, location_id
        return False, f"Invalid API key (HTTP {resp.status_code})"
    except Exception as e:
        return False, str(e)


def sync_to_ghl(user_id, call_record):
    """
    Find or create a GHL contact by phone, then log a note for the call.
    Uses GoHighLevel v1 REST API with a Location API Key.
    """
    cfg = get_integration_config(user_id, KEY_GHL)
    if not cfg.get("enabled") or not cfg.get("api_key"):
        return

    api_key = cfg["api_key"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    phone = (call_record.get("number") or "").strip()
    if not phone:
        return

    contact_id = None

    # Search for existing contact by phone
    try:
        search = requests.get(
            f"{GHL_BASE}/contacts/",
            headers=headers,
            params={"query": phone, "limit": 1},
            timeout=10,
        )
        if search.status_code == 200:
            contacts = search.json().get("contacts", [])
            if contacts:
                contact_id = contacts[0].get("id")
    except Exception as e:
        logger.error(f"[GHL] Contact search error for user {user_id}: {e}")

    # Create contact if not found
    if not contact_id:
        try:
            create = requests.post(
                f"{GHL_BASE}/contacts/",
                headers=headers,
                json={"phone": phone, "tags": ["open-humana"]},
                timeout=10,
            )
            if create.status_code in (200, 201):
                contact_id = create.json().get("contact", {}).get("id")
        except Exception as e:
            logger.error(f"[GHL] Contact create error for user {user_id}: {e}")

    if not contact_id:
        logger.warning(f"[GHL] Could not find/create contact for {phone}, user {user_id}")
        return

    # Build note body
    notes_parts = [
        f"Outbound Call — Open Humana",
        f"Status: {call_record.get('status_description', call_record.get('status', ''))}",
    ]
    if call_record.get("voicemail_dropped"):
        notes_parts.append("Voicemail dropped")
    if call_record.get("transferred"):
        notes_parts.append("Transferred to live agent")
    if call_record.get("amd_result"):
        notes_parts.append(f"AMD: {call_record['amd_result']}")
    if call_record.get("ring_duration"):
        notes_parts.append(f"Duration: {call_record['ring_duration']}s")

    try:
        note = requests.post(
            f"{GHL_BASE}/contacts/{contact_id}/notes/",
            headers=headers,
            json={"body": " | ".join(notes_parts)},
            timeout=10,
        )
        if note.status_code in (200, 201):
            logger.info(f"[GHL] Note logged for contact {contact_id}, user {user_id}")
        else:
            logger.warning(f"[GHL] Note failed ({note.status_code}): {note.text[:200]}")
    except Exception as e:
        logger.error(f"[GHL] Note error for user {user_id}: {e}")


# ── Pipedrive (API Token) ──────────────────────────────────────────────────────

PD_BASE = "https://api.pipedrive.com/v1"


def pipedrive_verify_token(api_token):
    """
    Verify a Pipedrive API token by fetching the current user profile.
    Returns (True, company_domain) or (False, error_message).
    """
    try:
        resp = requests.get(
            f"{PD_BASE}/users/me",
            params={"api_token": api_token},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            company_domain = data.get("company_domain", "")
            return True, company_domain
        return False, f"Invalid API token (HTTP {resp.status_code})"
    except Exception as e:
        return False, str(e)


def sync_to_pipedrive(user_id, call_record):
    """
    Find or create a Pipedrive person by phone, then create a call activity.
    Uses Pipedrive v1 REST API with a simple API token.
    """
    cfg = get_integration_config(user_id, KEY_PIPEDRIVE)
    if not cfg.get("enabled") or not cfg.get("api_token"):
        return

    token  = cfg["api_token"]
    params = {"api_token": token}
    phone  = (call_record.get("number") or "").strip()
    if not phone:
        return

    person_id = None

    # Search for existing person by phone
    try:
        search = requests.get(
            f"{PD_BASE}/persons/search",
            params={**params, "term": phone, "fields": "phone", "limit": 1},
            timeout=10,
        )
        if search.status_code == 200:
            items = search.json().get("data", {}).get("items", [])
            if items:
                person_id = items[0].get("item", {}).get("id")
    except Exception as e:
        logger.error(f"[PIPEDRIVE] Person search error for user {user_id}: {e}")

    # Create person if not found
    if not person_id:
        try:
            create = requests.post(
                f"{PD_BASE}/persons",
                params=params,
                json={"name": phone, "phone": [{"value": phone, "primary": True}]},
                timeout=10,
            )
            if create.status_code in (200, 201):
                person_id = create.json().get("data", {}).get("id")
        except Exception as e:
            logger.error(f"[PIPEDRIVE] Person create error for user {user_id}: {e}")

    if not person_id:
        logger.warning(f"[PIPEDRIVE] Could not find/create person for {phone}, user {user_id}")

    # Build note text
    status      = call_record.get("status_description", call_record.get("status", ""))
    flags       = []
    if call_record.get("voicemail_dropped"): flags.append("Voicemail dropped")
    if call_record.get("transferred"):       flags.append("Transferred to agent")
    if call_record.get("amd_result"):        flags.append(f"AMD: {call_record['amd_result']}")
    note_text   = f"[Open Humana] Outbound call | {status}"
    if flags: note_text += " | " + " | ".join(flags)

    # Create a note (attached to person if found)
    try:
        note_payload = {"content": note_text}
        if person_id:
            note_payload["person_id"] = person_id
        note = requests.post(
            f"{PD_BASE}/notes",
            params=params,
            json=note_payload,
            timeout=10,
        )
        if note.status_code in (200, 201):
            logger.info(f"[PIPEDRIVE] Note logged for person {person_id}, user {user_id}")
        else:
            logger.warning(f"[PIPEDRIVE] Note failed ({note.status_code}): {note.text[:200]}")
    except Exception as e:
        logger.error(f"[PIPEDRIVE] Note error for user {user_id}: {e}")

    # Log a call activity if we have a person
    if person_id:
        try:
            duration_sec = int(call_record.get("ring_duration") or 0)
            activity = requests.post(
                f"{PD_BASE}/activities",
                params=params,
                json={
                    "subject":    "Outbound Call — Open Humana",
                    "type":       "call",
                    "person_id":  person_id,
                    "done":       1,
                    "duration":   f"{duration_sec // 60:02d}:{duration_sec % 60:02d}",
                    "note":       note_text,
                },
                timeout=10,
            )
            if activity.status_code in (200, 201):
                logger.info(f"[PIPEDRIVE] Activity logged for person {person_id}, user {user_id}")
        except Exception as e:
            logger.error(f"[PIPEDRIVE] Activity error for user {user_id}: {e}")


# ── Google Sheets (Service Account) ───────────────────────────────────────────

GSHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

GSHEETS_HEADER = [
    "Timestamp", "Phone Number", "From Number", "Status",
    "Transferred", "Voicemail Dropped", "AMD Result", "Duration (s)", "Hangup Cause",
]


def _get_sa_access_token():
    """
    Obtain a short-lived Google access token using Service Account JWT.
    Returns access_token string or None on failure.
    """
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        return None
    try:
        import base64
        import time
        import json as _json

        sa = _json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        private_key_pem = sa["private_key"]
        client_email    = sa["client_email"]

        # Build JWT header + payload
        now = int(time.time())
        header  = {"alg": "RS256", "typ": "JWT"}
        payload = {
            "iss":   client_email,
            "scope": " ".join(GSHEETS_SCOPES),
            "aud":   "https://oauth2.googleapis.com/token",
            "iat":   now,
            "exp":   now + 3600,
        }

        def b64url(data):
            return base64.urlsafe_b64encode(
                _json.dumps(data, separators=(",", ":")).encode()
            ).rstrip(b"=").decode()

        signing_input = f"{b64url(header)}.{b64url(payload)}".encode()

        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
        signature   = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        sig_b64     = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

        jwt_token = f"{signing_input.decode()}.{sig_b64}"

        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion":  jwt_token,
        }, timeout=10)

        if resp.status_code == 200:
            return resp.json().get("access_token")
        logger.error(f"[GSHEETS] Token exchange failed: {resp.text[:200]}")
        return None
    except ImportError:
        logger.error("[GSHEETS] cryptography package not installed — cannot use Service Account")
        return None
    except Exception as e:
        logger.error(f"[GSHEETS] SA token error: {e}")
        return None


def sync_to_google_sheets(user_id, call_record):
    """Append a row for this call to the user's configured Google Sheet."""
    cfg = get_integration_config(user_id, KEY_GSHEETS_CFG)
    if not cfg.get("enabled") or not cfg.get("sheet_id"):
        return

    access_token = _get_sa_access_token()
    if not access_token:
        logger.warning(f"[GSHEETS] No service account token — skipping for user {user_id}")
        return

    sheet_id   = cfg["sheet_id"].strip()
    sheet_name = (cfg.get("sheet_name") or "Call Log").strip()
    ts = call_record.get("timestamp", datetime.utcnow().isoformat())

    row = [
        ts,
        call_record.get("number", ""),
        call_record.get("from_number", ""),
        call_record.get("status_description", call_record.get("status", "")),
        "Yes" if call_record.get("transferred")       else "No",
        "Yes" if call_record.get("voicemail_dropped")  else "No",
        call_record.get("amd_result", "") or "",
        str(call_record.get("ring_duration") or ""),
        call_record.get("hangup_cause", "") or "",
    ]

    try:
        resp = requests.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{sheet_name}!A1:append",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
            json={"values": [row]},
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info(f"[GSHEETS] Row appended for user {user_id}, sheet {sheet_id}")
        else:
            logger.warning(f"[GSHEETS] Append failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        logger.error(f"[GSHEETS] Append error for user {user_id}: {e}")


def google_sheets_test_connection(sheet_id, sheet_name="Call Log"):
    """
    Test write access to a Google Sheet using the service account.
    Returns (True, "") on success or (False, error_message) on failure.
    """
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        return False, "GOOGLE_SERVICE_ACCOUNT_JSON not configured"
    access_token = _get_sa_access_token()
    if not access_token:
        return False, "Could not get service account token"
    try:
        resp = requests.get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}?fields=properties.title",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            title = resp.json().get("properties", {}).get("title", "")
            return True, title
        if resp.status_code == 403:
            return False, f"Access denied — share the sheet with {_get_sa_email()}"
        return False, f"HTTP {resp.status_code}: {resp.text[:120]}"
    except Exception as e:
        return False, str(e)


# ── Fire all integrations ─────────────────────────────────────────────────────

def fire_all_integrations(user_id, call_record):
    """
    Asynchronously fire all enabled integrations for a completed call.
    Spawns a daemon background thread — non-blocking.
    """
    if not user_id:
        return

    def _run():
        for name, fn in [
            ("webhook",       fire_webhook),
            ("hubspot",       sync_to_hubspot),
            ("gohighlevel",   sync_to_ghl),
            ("pipedrive",     sync_to_pipedrive),
            ("gsheets",       sync_to_google_sheets),
        ]:
            try:
                fn(user_id, call_record)
            except Exception as e:
                logger.error(f"[INTEGRATIONS] {name} error for user {user_id}: {e}")

    threading.Thread(target=_run, daemon=True).start()
