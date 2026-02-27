"""
welcome_email.py - Send welcome email to new users after signup.
Uses the existing Gmail integration via gmail_client.
"""

import logging
import threading
from gmail_client import send_email

logger = logging.getLogger("voicemail_app")

BASE_URL = "https://voice-blast.replit.app"


def _build_welcome_html(user_name, user_email):
    name = user_name or "Hiring Manager"
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#ebebf0;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#ebebf0;padding:40px 20px;">
<tr><td align="center">
<table width="660" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #d8d8de;border-radius:12px;overflow:hidden;">

<tr><td style="padding:32px 52px;text-align:center;background:#ffffff;">
  <img src="{BASE_URL}/static/images/logo.png" alt="Open Humana" style="height:90px;width:auto;" />
</td></tr>

<tr><td style="padding:0 52px;background:#ffffff;">
  <hr style="border:none;border-top:1px solid #e8e8ed;margin:0;">
</td></tr>

<tr><td style="padding:32px 52px 0;background:#ffffff;">
  <p style="margin:0 0 24px;font-size:15px;color:#222;line-height:1.85;font-family:'Helvetica Neue',Arial,sans-serif;">Dear {name},</p>
  <p style="margin:0 0 18px;font-size:15px;color:#444;line-height:1.85;font-family:'Helvetica Neue',Arial,sans-serif;">Thank you for considering my application through the <strong style="color:#111;">Open Humana</strong> agency. I've reviewed your business needs, and I am formally submitting my credentials for your outbound sales operations. While I operate on a digital framework, my commitment to your growth is absolute.</p>
</td></tr>

<tr><td style="padding:0 52px;background:#ffffff;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f7f7fa;border:1px solid #e8e8ed;border-radius:10px;">
    <tr><td style="padding:24px 28px;">
      <p style="margin:0 0 6px;font-size:11px;font-weight:700;color:#999;font-family:'Helvetica Neue',Arial,sans-serif;text-transform:uppercase;letter-spacing:1.5px;">Why I Am The Perfect Hire</p>
      <p style="margin:0;font-size:14px;color:#444;font-family:'Helvetica Neue',Arial,sans-serif;line-height:1.85;">Most hires are limited by 40-hour weeks and human fatigue. I am offering you a <strong style="color:#111;">Zero-Friction Partnership</strong>. I specialize in the &lsquo;Deep Work&rsquo; of sales &mdash; the thousands of dials, the endless ringing, and the personalized follow-ups that typically burn out a human team. I don&rsquo;t just &lsquo;use&rsquo; your lead list; I exhaust it until every opportunity is bridged to your desk.</p>
    </td></tr>
  </table>
</td></tr>

<tr><td style="padding:28px 52px 8px;background:#ffffff;">
  <p style="margin:0;font-size:15px;color:#444;font-family:'Helvetica Neue',Arial,sans-serif;line-height:1.8;">Please find my resume enclosed below.</p>
  <p style="margin:12px 0 0;font-size:15px;color:#444;font-family:'Helvetica Neue',Arial,sans-serif;">Respectfully,</p>
  <p style="margin:4px 0 0;font-size:16px;color:#111;font-weight:700;font-family:'Helvetica Neue',Arial,sans-serif;">Alex</p>
</td></tr>

<tr><td style="padding:20px 36px 0;background:#ffffff;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a1a;border-radius:14px;overflow:hidden;">

    <tr><td style="padding:40px 44px 0;text-align:center;">
      <p style="margin:0;font-size:32px;font-weight:800;color:#ffffff;font-family:'Helvetica Neue',Arial,sans-serif;letter-spacing:5px;">ALEX</p>
      <p style="margin:8px 0 0;font-size:11px;color:rgba(255,255,255,0.45);font-family:'Helvetica Neue',Arial,sans-serif;letter-spacing:2.5px;text-transform:uppercase;">Senior Digital Associate</p>
      <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:24px 0 0;">
    </td></tr>

    <tr><td style="padding:24px 44px 0;">
      <p style="margin:0 0 4px;font-size:10px;font-weight:700;color:rgba(255,255,255,0.35);font-family:'Helvetica Neue',Arial,sans-serif;text-transform:uppercase;letter-spacing:2px;">Objective</p>
      <hr style="border:none;border-top:1px solid rgba(255,255,255,0.08);margin:8px 0 12px;">
      <p style="margin:0;font-size:14px;color:rgba(255,255,255,0.7);font-family:'Helvetica Neue',Arial,sans-serif;line-height:1.8;">To eliminate the &lsquo;Manual Dialing Gap&rsquo; in your sales process and ensure 100% lead engagement across every contact in your pipeline.</p>
    </td></tr>

    <tr><td style="padding:28px 44px 0;">
      <p style="margin:0 0 4px;font-size:10px;font-weight:700;color:rgba(255,255,255,0.35);font-family:'Helvetica Neue',Arial,sans-serif;text-transform:uppercase;letter-spacing:2px;">Key Performance Indicators</p>
      <hr style="border:none;border-top:1px solid rgba(255,255,255,0.08);margin:8px 0 16px;">

      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="padding:0 0 20px;vertical-align:top;" width="8">
            <div style="width:6px;height:6px;background:#fff;border-radius:50%;margin-top:7px;"></div>
          </td>
          <td style="padding:0 0 20px 14px;vertical-align:top;">
            <p style="margin:0 0 4px;font-size:14px;color:#ffffff;font-weight:600;font-family:'Helvetica Neue',Arial,sans-serif;">Extreme Persistence</p>
            <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.55);font-family:'Helvetica Neue',Arial,sans-serif;line-height:1.75;">Programmed for 12+ touchpoints per lead. I do not get discouraged by &lsquo;no&rsquo; or &lsquo;not interested.&rsquo;</p>
          </td>
        </tr>
        <tr>
          <td style="padding:0 0 20px;vertical-align:top;">
            <div style="width:6px;height:6px;background:#fff;border-radius:50%;margin-top:7px;"></div>
          </td>
          <td style="padding:0 0 20px 14px;vertical-align:top;">
            <p style="margin:0 0 4px;font-size:14px;color:#ffffff;font-weight:600;font-family:'Helvetica Neue',Arial,sans-serif;">Hyper-Personalized Voice Execution</p>
            <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.55);font-family:'Helvetica Neue',Arial,sans-serif;line-height:1.75;">Unlike bulk robodialers, I leave unique voicemails referencing the lead&rsquo;s Name and Property/Business details. I sound like a neighbor, not a machine.</p>
          </td>
        </tr>
        <tr>
          <td style="padding:0 0 4px;vertical-align:top;">
            <div style="width:6px;height:6px;background:#fff;border-radius:50%;margin-top:7px;"></div>
          </td>
          <td style="padding:0 0 4px 14px;vertical-align:top;">
            <p style="margin:0 0 4px;font-size:14px;color:#ffffff;font-weight:600;font-family:'Helvetica Neue',Arial,sans-serif;">Instant Bridge Technology</p>
            <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.55);font-family:'Helvetica Neue',Arial,sans-serif;line-height:1.75;">I maintain a &lsquo;Ready&rsquo; state 24/7. When a prospect answers, they are in your ear in less than 200ms.</p>
          </td>
        </tr>
      </table>
    </td></tr>

    <tr><td style="padding:24px 44px 0;">
      <p style="margin:0 0 4px;font-size:10px;font-weight:700;color:rgba(255,255,255,0.35);font-family:'Helvetica Neue',Arial,sans-serif;text-transform:uppercase;letter-spacing:2px;">Core Competencies</p>
      <hr style="border:none;border-top:1px solid rgba(255,255,255,0.08);margin:8px 0 14px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;color:rgba(255,255,255,0.6);">
        <tr>
          <td style="padding:5px 0;" width="50%">&#9656; Multi-Channel Prospecting</td>
          <td style="padding:5px 0;">&#9656; Multi-Lingual Fluency (Global Reach)</td>
        </tr>
        <tr>
          <td style="padding:5px 0;">&#9656; Real-Time Data Synchronization</td>
          <td style="padding:5px 0;">&#9656; Rapid Lead Qualification</td>
        </tr>
        <tr>
          <td style="padding:5px 0;" colspan="2">&#9656; Persistence &amp; Follow-Up Automation</td>
        </tr>
      </table>
    </td></tr>

    <tr><td style="padding:28px 44px;">
      <p style="margin:0 0 4px;font-size:10px;font-weight:700;color:rgba(255,255,255,0.35);font-family:'Helvetica Neue',Arial,sans-serif;text-transform:uppercase;letter-spacing:2px;">The Untouchable Candidate Advantage</p>
      <hr style="border:none;border-top:1px solid rgba(255,255,255,0.08);margin:8px 0 14px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;">
        <tr>
          <td style="padding:6px 0;color:rgba(255,255,255,0.85);font-weight:600;" width="200">Health &amp; Benefits</td>
          <td style="padding:6px 0;color:rgba(255,255,255,0.55);">$0.00 (Self-insured)</td>
        </tr>
        <tr>
          <td style="padding:6px 0;color:rgba(255,255,255,0.85);font-weight:600;">Vacation / PTO</td>
          <td style="padding:6px 0;color:rgba(255,255,255,0.55);">None. I thrive on 24/7 activity.</td>
        </tr>
        <tr>
          <td style="padding:6px 0;color:rgba(255,255,255,0.85);font-weight:600;">Management Overhead</td>
          <td style="padding:6px 0;color:rgba(255,255,255,0.55);">Zero. Pre-trained on your scripts &amp; industry.</td>
        </tr>
        <tr>
          <td style="padding:6px 0;color:rgba(255,255,255,0.85);font-weight:600;">Monthly Salary</td>
          <td style="padding:6px 0;color:rgba(255,255,255,0.55);">A flat $99/mo (Agency Fee)</td>
        </tr>
      </table>
    </td></tr>

  </table>
</td></tr>

<tr><td style="padding:32px 52px 0;text-align:center;background:#ffffff;">
  <p style="margin:0 0 24px;font-size:15px;color:#444;line-height:1.85;font-family:'Helvetica Neue',Arial,sans-serif;">I am ready to start my first shift within the hour. Please review my &lsquo;Employment Agreement&rsquo; and finalize my onboarding below.</p>
  <table cellpadding="0" cellspacing="0" style="margin:0 auto;">
    <tr><td style="background:#0a0a1a;border-radius:10px;">
      <a href="{BASE_URL}/login" style="display:inline-block;padding:16px 48px;color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;font-family:'Helvetica Neue',Arial,sans-serif;letter-spacing:0.3px;">Review Agreement &amp; Deploy Alex</a>
    </td></tr>
  </table>
</td></tr>

<tr><td style="padding:32px 52px 36px;text-align:center;background:#ffffff;">
  <hr style="border:none;border-top:1px solid #e8e8ed;margin:0 0 20px;">
  <p style="margin:0;font-size:11px;color:#aaa;font-family:'Helvetica Neue',Arial,sans-serif;letter-spacing:0.4px;">This candidate is represented by <strong style="color:#888;">Open Humana</strong> &mdash; The Future of the Digital Workforce</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def send_welcome_email(user_email, user_name=None):
    try:
        html_body = _build_welcome_html(user_name, user_email)
        name = user_name or "Hiring Manager"
        text_body = f"""Dear {name},

Thank you for considering my application through the Open Humana agency. I've reviewed your business needs, and I am formally submitting my credentials for your outbound sales operations. While I operate on a digital framework, my commitment to your growth is absolute.

WHY I AM THE PERFECT HIRE:
Most hires are limited by 40-hour weeks and human fatigue. I am offering you a Zero-Friction Partnership. I specialize in the 'Deep Work' of sales - the thousands of dials, the endless ringing, and the personalized follow-ups that typically burn out a human team. I don't just 'use' your lead list; I exhaust it until every opportunity is bridged to your desk.

Please find my resume below.

Respectfully,
Alex

---

ALEX
Senior Digital Associate

OBJECTIVE
To eliminate the 'Manual Dialing Gap' in your sales process and ensure 100% lead engagement across every contact in your pipeline.

KEY PERFORMANCE INDICATORS

Extreme Persistence
Programmed for 12+ touchpoints per lead. I do not get discouraged by 'no' or 'not interested.'

Hyper-Personalized Voice Execution
Unlike bulk robodialers, I leave unique voicemails referencing the lead's Name and Property/Business details. I sound like a neighbor, not a machine.

Instant Bridge Technology
I maintain a 'Ready' state 24/7. When a prospect answers, they are in your ear in less than 200ms.

CORE COMPETENCIES
- Multi-Channel Prospecting
- Multi-Lingual Fluency (Global Reach)
- Real-Time Data Synchronization
- Rapid Lead Qualification
- Persistence & Follow-Up Automation

THE UNTOUCHABLE CANDIDATE ADVANTAGE
Health & Benefits: $0.00 (Self-insured)
Vacation / PTO: None. I thrive on 24/7 activity.
Management Overhead: Zero. Pre-trained on your scripts & industry.
Monthly Salary: A flat $99/mo (Agency Fee)

---

I am ready to start my first shift within the hour. Please review my 'Employment Agreement' and finalize my onboarding below.

{BASE_URL}/login

This candidate is represented by Open Humana - The Future of the Digital Workforce"""

        success = send_email(
            to_email=user_email,
            subject="My Resume (via Open Humana)",
            html_body=html_body,
            text_body=text_body,
        )
        if success:
            logger.info(f"Welcome email sent to {user_email}")
        else:
            logger.warning(f"Failed to send welcome email to {user_email}")
        return success
    except Exception as e:
        logger.error(f"Error sending welcome email to {user_email}: {e}")
        return False


def send_welcome_email_async(user_email, user_name=None):
    thread = threading.Thread(
        target=send_welcome_email,
        args=(user_email, user_name),
        daemon=True,
    )
    thread.start()
