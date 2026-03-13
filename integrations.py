"""
integrations.py - CRM and webhook integration module for Open Humana.

Handles:
  - Outbound webhooks (fires on call completion to any user-configured URL)
  - HubSpot CRM sync (creates contacts, logs call activities via OAuth)
  - Google Sheets sync (appends rows via OAuth)

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

HUBSPOT_CLIENT_ID     = os.environ.get("HUBSPOT_CLIENT_ID", "")
HUBSPOT_CLIENT_SECRET = os.environ.get("HUBSPOT_CLIENT_SECRET", "")
HUBSPOT_SCOPES        = "crm.objects.contacts.write crm.objects.contacts.read crm.objects.engagements.write"

GOOGLE_CLIENT_ID      = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET  = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GSHEETS_SCOPE         = "https://www.googleapis.com/auth/spreadsheets"

KEY_WEBHOOK     = "outbound_webhook"
KEY_HUBSPOT     = "hubspot_tokens"
KEY_GSHEETS_TOK = "google_sheets_tokens"
KEY_GSHEETS_CFG = "google_sheets_config"


# ── Config helpers ─────────────────────────────────────────────────────────────

def get_integration_config(user_id, key):
    """Read a JSON blob from UserAppData for the given user and key."""
    try:
        from app import app as _app
        from models import db, UserAppData
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
    wh = get_integration_config(user_id, KEY_WEBHOOK)
    hs = get_integration_config(user_id, KEY_HUBSPOT)
    gs_tok = get_integration_config(user_id, KEY_GSHEETS_TOK)
    gs_cfg = get_integration_config(user_id, KEY_GSHEETS_CFG)
    return {
        "webhook": {
            "connected": bool(wh.get("url")),
            "enabled": bool(wh.get("enabled")),
            "url": wh.get("url", ""),
            "has_secret": bool(wh.get("secret")),
        },
        "hubspot": {
            "connected": bool(hs.get("access_token")),
            "enabled": bool(hs.get("enabled")),
            "portal_id": hs.get("portal_id", ""),
            "credentials_configured": bool(HUBSPOT_CLIENT_ID and HUBSPOT_CLIENT_SECRET),
        },
        "google_sheets": {
            "connected": bool(gs_tok.get("access_token")),
            "enabled": bool(gs_cfg.get("enabled")),
            "sheet_id": gs_cfg.get("sheet_id", ""),
            "sheet_name": gs_cfg.get("sheet_name", "Call Log"),
            "credentials_configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        },
    }


# ── Outbound Webhook ──────────────────────────────────────────────────────────

def fire_webhook(user_id, call_record):
    """POST call_record to user's configured webhook URL."""
    cfg = get_integration_config(user_id, KEY_WEBHOOK)
    if not cfg.get("enabled") or not cfg.get("url"):
        return
    url    = cfg["url"]
    secret = cfg.get("secret", "")
    payload = {
        "event": "call.completed",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "open_humana",
        "data": call_record,
    }
    body    = json.dumps(payload, default=str)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "OpenHumana-Webhook/1.0",
    }
    if secret:
        sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        headers["X-OpenHumana-Signature"] = f"sha256={sig}"
    try:
        resp = requests.post(url, data=body, headers=headers, timeout=8)
        logger.info(f"[WEBHOOK] user={user_id} → {url} | status={resp.status_code}")
    except Exception as e:
        logger.warning(f"[WEBHOOK] user={user_id} → {url} failed: {e}")


# ── HubSpot ───────────────────────────────────────────────────────────────────

def _hs_refresh(tokens, user_id):
    """Refresh an expired HubSpot access token using the refresh token."""
    if not HUBSPOT_CLIENT_ID or not HUBSPOT_CLIENT_SECRET:
        return tokens
    try:
        resp = requests.post("https://api.hubapi.com/oauth/v1/token", data={
            "grant_type":    "refresh_token",
            "client_id":     HUBSPOT_CLIENT_ID,
            "client_secret": HUBSPOT_CLIENT_SECRET,
            "refresh_token": tokens["refresh_token"],
        }, timeout=10)
        if resp.status_code == 200:
            new_tok = resp.json()
            tokens["access_token"] = new_tok["access_token"]
            tokens["expires_at"]   = (datetime.utcnow() + timedelta(seconds=new_tok.get("expires_in", 1800))).timestamp()
            if new_tok.get("refresh_token"):
                tokens["refresh_token"] = new_tok["refresh_token"]
            set_integration_config(user_id, KEY_HUBSPOT, tokens)
    except Exception as e:
        logger.error(f"[HUBSPOT] Token refresh error for user {user_id}: {e}")
    return tokens


def _hs_auth_headers(user_id):
    """Return valid HubSpot auth headers, refreshing token if needed."""
    tokens = get_integration_config(user_id, KEY_HUBSPOT)
    if not tokens or not tokens.get("access_token"):
        return None
    expires_at = tokens.get("expires_at", 0)
    if datetime.utcnow().timestamp() > expires_at - 300:
        tokens = _hs_refresh(tokens, user_id)
    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "Content-Type": "application/json",
    }


def sync_to_hubspot(user_id, call_record):
    """Find or create a HubSpot contact by phone, then log the call activity."""
    cfg = get_integration_config(user_id, KEY_HUBSPOT)
    if not cfg.get("enabled") or not cfg.get("access_token"):
        return
    headers = _hs_auth_headers(user_id)
    if not headers:
        return
    phone = call_record.get("number", "").strip()
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
        logger.error(f"[HUBSPOT] Contact search error: {e}")

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
            logger.error(f"[HUBSPOT] Contact create error: {e}")

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

    connected = call_record.get("transferred") or call_record.get("voicemail_dropped")
    outcome   = "CONNECTED" if connected else "NO_ANSWER"
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
            logger.warning(f"[HUBSPOT] Engagement create failed ({eng.status_code}): {eng.text[:200]}")
    except Exception as e:
        logger.error(f"[HUBSPOT] Engagement error for user {user_id}: {e}")


# ── Google Sheets ─────────────────────────────────────────────────────────────

GSHEETS_HEADER = [
    "Timestamp", "Phone Number", "From Number", "Status",
    "Transferred", "Voicemail Dropped", "AMD Result", "Duration (s)", "Hangup Cause",
]


def _gs_refresh(tokens, user_id):
    """Refresh an expired Google access token."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return tokens
    try:
        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "grant_type":    "refresh_token",
            "client_id":     GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": tokens["refresh_token"],
        }, timeout=10)
        if resp.status_code == 200:
            new_tok = resp.json()
            tokens["access_token"] = new_tok["access_token"]
            tokens["expires_at"]   = (datetime.utcnow() + timedelta(seconds=new_tok.get("expires_in", 3600))).timestamp()
            set_integration_config(user_id, KEY_GSHEETS_TOK, tokens)
    except Exception as e:
        logger.error(f"[GSHEETS] Token refresh error for user {user_id}: {e}")
    return tokens


def sync_to_google_sheets(user_id, call_record):
    """Append a row for this call to the user's configured Google Sheet."""
    tokens  = get_integration_config(user_id, KEY_GSHEETS_TOK)
    cfg     = get_integration_config(user_id, KEY_GSHEETS_CFG)
    if not tokens or not tokens.get("access_token"):
        return
    if not cfg.get("enabled") or not cfg.get("sheet_id"):
        return

    if tokens.get("expires_at") and datetime.utcnow().timestamp() > tokens["expires_at"] - 300:
        tokens = _gs_refresh(tokens, user_id)

    access_token = tokens.get("access_token", "")
    if not access_token:
        return

    sheet_id   = cfg["sheet_id"].strip()
    sheet_name = cfg.get("sheet_name", "Call Log").strip() or "Call Log"

    ts = call_record.get("timestamp", datetime.utcnow().isoformat())
    row = [
        ts,
        call_record.get("number", ""),
        call_record.get("from_number", ""),
        call_record.get("status_description", call_record.get("status", "")),
        "Yes" if call_record.get("transferred")      else "No",
        "Yes" if call_record.get("voicemail_dropped") else "No",
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


# ── Fire all integrations ─────────────────────────────────────────────────────

def fire_all_integrations(user_id, call_record):
    """
    Asynchronously fire all enabled integrations for a completed call.
    Must be called from a daemon background thread (non-blocking).
    """
    if not user_id:
        return

    def _run():
        for name, fn in [("webhook", fire_webhook), ("hubspot", sync_to_hubspot), ("gsheets", sync_to_google_sheets)]:
            try:
                fn(user_id, call_record)
            except Exception as e:
                logger.error(f"[INTEGRATIONS] {name} error for user {user_id}: {e}")

    threading.Thread(target=_run, daemon=True).start()
