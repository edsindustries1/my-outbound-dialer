"""
gmail_client.py - Email integration via Resend API.
Uses RESEND_API_KEY (and optional RESEND_FROM_EMAIL) to send emails over HTTPS.
"""

import os
import logging
import base64
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger("voicemail_app")

# Resend credentials / config
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "Alex <onboarding@resend.dev>")
RESEND_API_URL = "https://api.resend.com/emails"


def send_email(to_email, subject, html_body, text_body=None, csv_attachment=None, csv_filename=None):
    try:
        if not RESEND_API_KEY:
            logger.error("Error: No API Key (RESEND_API_KEY not set)")
            print("Error: No API Key")
            return False

        # Build MIME-like structure to ensure headers are consistent
        msg = MIMEMultipart("mixed")
        msg["From"] = str(RESEND_FROM_EMAIL)
        msg["To"] = str(to_email)
        msg["Subject"] = str(subject)

        alt = MIMEMultipart("alternative")
        if text_body:
            alt.attach(MIMEText(text_body, "plain", "utf-8"))
        alt.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt)

        attachments = []
        if csv_attachment and csv_filename:
            # Resend expects base64-encoded content for attachments
            encoded = base64.b64encode(csv_attachment.encode("utf-8")).decode("ascii")
            attachments.append(
                {
                    "filename": csv_filename,
                    "content": encoded,
                }
            )

        # Prepare Resend payload
        payload = {
            "from": msg["From"],
            "to": [msg["To"]],
            "subject": msg["Subject"],
            "html": html_body,
        }
        if text_body:
            payload["text"] = text_body
        if attachments:
            payload["attachments"] = attachments

        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        }

        resp = requests.post(RESEND_API_URL, json=payload, headers=headers, timeout=5)

        if 200 <= resp.status_code < 300:
            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True

        logger.error(f"Resend API error ({resp.status_code}) sending to {to_email}: {resp.text}")
        print(f"Resend API error ({resp.status_code}) sending to {to_email}: {resp.text}")
        return False

    except Exception as e:
        # Safety net: never crash callers; just log + print
        logger.error(f"Failed to send email to {to_email}: {e}")
        logger.exception("Error while sending email via Resend")
        print(f"Failed to send email to {to_email}: {e}")
        return False


def test_connection():
    try:
        if not RESEND_API_KEY:
            return {"connected": False, "error": "RESEND_API_KEY not set"}

        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        }
        # Simple no-op call: Resend will validate the API key on any endpoint.
        resp = requests.get("https://api.resend.com/domains", headers=headers, timeout=5)

        if 200 <= resp.status_code < 300:
            return {"connected": True, "email": RESEND_FROM_EMAIL}
        return {"connected": False, "error": f"Resend status {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"connected": False, "error": str(e)}
