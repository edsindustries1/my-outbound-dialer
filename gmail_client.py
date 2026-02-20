"""
gmail_client.py - Gmail integration via Replit connector.
Sends emails using the connected Gmail account through the Gmail API.
"""

import os
import base64
import json
import logging
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger("voicemail_app")

_connection_settings = None


def _get_access_token():
    global _connection_settings

    if (_connection_settings
        and _connection_settings.get("settings", {}).get("expires_at")
        and _parse_expiry(_connection_settings["settings"]["expires_at"]) > _now_ms()):
        return _connection_settings["settings"]["access_token"]

    hostname = os.environ.get("REPLIT_CONNECTORS_HOSTNAME", "")
    repl_identity = os.environ.get("REPL_IDENTITY", "")
    web_repl_renewal = os.environ.get("WEB_REPL_RENEWAL", "")

    if repl_identity:
        x_replit_token = f"repl {repl_identity}"
    elif web_repl_renewal:
        x_replit_token = f"depl {web_repl_renewal}"
    else:
        raise Exception("No Replit identity token found")

    if not hostname:
        raise Exception("REPLIT_CONNECTORS_HOSTNAME not set")

    url = f"https://{hostname}/api/v2/connection?include_secrets=true&connector_names=google-mail"
    resp = requests.get(url, headers={
        "Accept": "application/json",
        "X_REPLIT_TOKEN": x_replit_token,
    })
    resp.raise_for_status()
    data = resp.json()

    items = data.get("items", [])
    if not items:
        raise Exception("Gmail not connected - no connection found")

    _connection_settings = items[0]
    settings = _connection_settings.get("settings", {})
    access_token = settings.get("access_token") or settings.get("oauth", {}).get("credentials", {}).get("access_token")

    if not access_token:
        raise Exception("Gmail not connected - no access token")

    return access_token


def _now_ms():
    import time
    return int(time.time() * 1000)


def _parse_expiry(expires_at):
    try:
        from datetime import datetime
        if isinstance(expires_at, (int, float)):
            return int(expires_at * 1000) if expires_at < 1e12 else int(expires_at)
        dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except Exception:
        return 0


def send_email(to_email, subject, html_body, text_body=None, csv_attachment=None, csv_filename=None):
    try:
        access_token = _get_access_token()

        msg = MIMEMultipart("mixed")
        msg["To"] = to_email
        msg["Subject"] = subject

        alt = MIMEMultipart("alternative")
        if text_body:
            alt.attach(MIMEText(text_body, "plain"))
        alt.attach(MIMEText(html_body, "html"))
        msg.attach(alt)

        if csv_attachment and csv_filename:
            part = MIMEBase("text", "csv")
            part.set_payload(csv_attachment.encode("utf-8"))
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={csv_filename}")
            msg.attach(part)

        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        resp = requests.post(url, headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }, json={"raw": raw_message})

        if resp.status_code == 200 or resp.status_code == 201:
            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True
        else:
            logger.error(f"Gmail API error {resp.status_code}: {resp.text}")
            return False

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def test_connection():
    try:
        token = _get_access_token()
        if not token:
            return {"connected": False, "error": "No access token available"}

        email = ""
        if _connection_settings:
            settings = _connection_settings.get("settings", {})
            oauth = settings.get("oauth", {})
            creds = oauth.get("credentials", {})
            raw = creds.get("raw", {})
            email = raw.get("email", "") or raw.get("login", "") or creds.get("email", "")

        resp = requests.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/labels",
            headers={"Authorization": f"Bearer {token}"},
            params={"maxResults": 1}
        )
        if resp.status_code == 200:
            return {"connected": True, "email": email or "Connected"}
        return {"connected": False, "error": f"API returned {resp.status_code}"}
    except Exception as e:
        return {"connected": False, "error": str(e)}
