"""
invite_email.py - Email templates for invitation system, lead confirmation, and password reset.
"""

import os
import logging
import threading
from gmail_client import send_email

logger = logging.getLogger("voicemail_app")

BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")


def _get_base_url():
    url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if not url:
        domains = os.environ.get("REPLIT_DOMAINS", "")
        if domains:
            url = "https://" + domains.split(",")[0].strip()
    return url or "https://openhumana.com"


def build_invite_html(invite_token, grant_free_access=False):
    base = _get_base_url()
    setup_url = f"{base}/setup-account?token={invite_token}"
    access_note = ""
    if grant_free_access:
        access_note = """
        <tr><td style="padding:0 52px 24px;background:#ffffff;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;">
            <tr><td style="padding:16px 20px;">
              <p style="margin:0;font-size:14px;color:#15803d;line-height:1.6;">
                <strong>Complimentary Access</strong> — Your account includes full platform access at no charge, granted by the Open Humana team.
              </p>
            </td></tr>
          </table>
        </td></tr>
        """

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f7;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f7;padding:40px 20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

<tr><td style="padding:36px 52px;text-align:center;background:#ffffff;">
  <img src="{base}/static/images/logo.png" alt="Open Humana" style="height:80px;width:auto;" />
</td></tr>

<tr><td style="padding:0 52px;background:#ffffff;">
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:0;">
</td></tr>

<tr><td style="padding:32px 52px 16px;background:#ffffff;">
  <h1 style="margin:0 0 16px;font-size:22px;font-weight:700;color:#111827;letter-spacing:-0.02em;">You've been given access to Open Humana</h1>
  <p style="margin:0 0 24px;font-size:15px;color:#4b5563;line-height:1.75;">You have been invited to access your Open Humana dashboard. Click the button below to set up your account and get started.</p>
</td></tr>

{access_note}

<tr><td style="padding:0 52px 32px;background:#ffffff;" align="center">
  <a href="{setup_url}" style="display:inline-block;padding:14px 40px;background:#111827;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;letter-spacing:-0.01em;">Set Up Your Account</a>
</td></tr>

<tr><td style="padding:0 52px 32px;background:#ffffff;">
  <p style="margin:0;font-size:13px;color:#9ca3af;line-height:1.6;">If the button doesn't work, copy and paste this link into your browser:<br>
  <a href="{setup_url}" style="color:#6366f1;word-break:break-all;">{setup_url}</a></p>
</td></tr>

<tr><td style="background:#f9fafb;padding:24px 52px;text-align:center;border-top:1px solid #e5e7eb;">
  <p style="margin:0;font-size:12px;color:#9ca3af;">&copy; 2026 Open Humana &mdash; Your Digital Employee Agency</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def build_lead_confirmation_html(name):
    base = _get_base_url()
    first_name = name.split()[0] if name else "there"
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f7;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f7;padding:40px 20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

<tr><td style="padding:36px 52px;text-align:center;background:#ffffff;">
  <img src="{base}/static/images/logo.png" alt="Open Humana" style="height:80px;width:auto;" />
</td></tr>

<tr><td style="padding:0 52px;background:#ffffff;">
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:0;">
</td></tr>

<tr><td style="padding:32px 52px 24px;background:#ffffff;">
  <h1 style="margin:0 0 16px;font-size:22px;font-weight:700;color:#111827;letter-spacing:-0.02em;">Thanks for reaching out, {first_name}!</h1>
  <p style="margin:0 0 16px;font-size:15px;color:#4b5563;line-height:1.75;">We received your request and our team will reach out to you within 24 hours to discuss how Alex can help your business scale its outbound sales.</p>
  <p style="margin:0;font-size:15px;color:#4b5563;line-height:1.75;">In the meantime, here's what Alex can do for your team:</p>
</td></tr>

<tr><td style="padding:0 52px 24px;background:#ffffff;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;">
    <tr><td style="padding:20px 24px;">
      <p style="margin:0 0 10px;font-size:14px;color:#111827;line-height:1.7;"><strong>500+ automated dials per day</strong> — while your team focuses on closing</p>
      <p style="margin:0 0 10px;font-size:14px;color:#111827;line-height:1.7;"><strong>AI-personalized voicemails</strong> — every message tailored to the prospect</p>
      <p style="margin:0 0 10px;font-size:14px;color:#111827;line-height:1.7;"><strong>Live call transfers</strong> — warm handoffs when a real prospect picks up</p>
      <p style="margin:0;font-size:14px;color:#111827;line-height:1.7;"><strong>Real-time transcription</strong> — every call documented automatically</p>
    </td></tr>
  </table>
</td></tr>

<tr><td style="padding:0 52px 32px;background:#ffffff;" align="center">
  <a href="{base}" style="display:inline-block;padding:14px 36px;background:#111827;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:700;font-size:14px;">Learn More About Alex</a>
</td></tr>

<tr><td style="background:#f9fafb;padding:24px 52px;text-align:center;border-top:1px solid #e5e7eb;">
  <p style="margin:0;font-size:12px;color:#9ca3af;">&copy; 2026 Open Humana &mdash; Your Digital Employee Agency</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def build_password_reset_html(reset_token):
    base = _get_base_url()
    reset_url = f"{base}/reset-password?token={reset_token}"
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f7;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f7;padding:40px 20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

<tr><td style="padding:36px 52px;text-align:center;background:#ffffff;">
  <img src="{base}/static/images/logo.png" alt="Open Humana" style="height:80px;width:auto;" />
</td></tr>

<tr><td style="padding:0 52px;background:#ffffff;">
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:0;">
</td></tr>

<tr><td style="padding:32px 52px 24px;background:#ffffff;">
  <h1 style="margin:0 0 16px;font-size:22px;font-weight:700;color:#111827;">Reset Your Password</h1>
  <p style="margin:0 0 24px;font-size:15px;color:#4b5563;line-height:1.75;">We received a request to reset your password. Click the button below to create a new password. This link expires in 1 hour.</p>
</td></tr>

<tr><td style="padding:0 52px 32px;background:#ffffff;" align="center">
  <a href="{reset_url}" style="display:inline-block;padding:14px 40px;background:#111827;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;">Reset Password</a>
</td></tr>

<tr><td style="padding:0 52px 32px;background:#ffffff;">
  <p style="margin:0;font-size:13px;color:#9ca3af;line-height:1.6;">If you didn't request this, you can safely ignore this email. Your password will not change.</p>
</td></tr>

<tr><td style="background:#f9fafb;padding:24px 52px;text-align:center;border-top:1px solid #e5e7eb;">
  <p style="margin:0;font-size:12px;color:#9ca3af;">&copy; 2026 Open Humana &mdash; Your Digital Employee Agency</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def send_invite_email(to_email, invite_token, grant_free_access=False):
    html = build_invite_html(invite_token, grant_free_access)
    subject = "You've been given access to OpenHumana"
    text = "You have been invited to access your OpenHumana dashboard. Visit your setup link to create your account."
    return send_email(to_email, subject, html, text)


def send_invite_email_async(to_email, invite_token, grant_free_access=False):
    def _send():
        try:
            send_invite_email(to_email, invite_token, grant_free_access)
        except Exception as e:
            logger.exception(f"Failed to send invite email to {to_email}: {e}")
    threading.Thread(target=_send, daemon=True).start()


def send_lead_confirmation_async(to_email, name):
    def _send():
        try:
            html = build_lead_confirmation_html(name)
            send_email(to_email, "Welcome to OpenHumana — We'll be in touch shortly!", html,
                       f"Hi {name},\n\nThanks for your interest in OpenHumana. Our team will reach out within 24 hours.\n\nBest,\nThe OpenHumana Team")
        except Exception as e:
            logger.exception(f"Failed to send lead confirmation to {to_email}: {e}")
    threading.Thread(target=_send, daemon=True).start()


def send_password_reset_async(to_email, reset_token):
    def _send():
        try:
            html = build_password_reset_html(reset_token)
            send_email(to_email, "Reset Your OpenHumana Password", html,
                       "You requested a password reset. Visit the link in the HTML version of this email to reset your password.")
        except Exception as e:
            logger.exception(f"Failed to send password reset to {to_email}: {e}")
    threading.Thread(target=_send, daemon=True).start()
