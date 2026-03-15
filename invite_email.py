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
    first_name = name.split()[0] if name else "Hiring Manager"
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#ebebf0;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#ebebf0;padding:40px 20px;">
<tr><td align="center">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:680px;background:#ffffff;border:1px solid #d8d8de;border-radius:14px;overflow:hidden;">

<tr><td style="padding:16px 52px 20px;text-align:center;background:#ffffff;">
  <img src="{base}/static/images/logo.png" alt="Open Humana" style="height:195px;width:auto;" />
  <p style="margin:8px 0 0;font-size:11px;color:#999;letter-spacing:2px;text-transform:uppercase;font-weight:600;">Your Digital Employee Agency</p>
</td></tr>

<tr><td style="padding:0 52px;background:#ffffff;">
  <hr style="border:none;border-top:1px solid #e8e8ed;margin:0;">
</td></tr>

<tr><td style="padding:32px 52px 0;background:#ffffff;">
  <p style="margin:0 0 20px;font-size:15px;color:#222;line-height:1.85;">Dear {first_name},</p>
  <p style="margin:0 0 16px;font-size:15px;color:#444;line-height:1.85;">Thank you for your interest in hiring through <strong style="color:#111;">Open Humana</strong>. I have reviewed your inquiry and I am formally submitting my credentials for immediate consideration. Enclosed below is my complete professional resume.</p>
  <p style="margin:0 0 16px;font-size:15px;color:#444;line-height:1.85;">A traditional hire takes 2&ndash;4 weeks of interviews, onboarding, and training before they make a single productive call. I require none of that. I am fully deployed and making calls for your business in under 60 seconds. No ramp-up period. No learning curve. No supervision required.</p>
  <p style="margin:0 0 16px;font-size:15px;color:#444;line-height:1.85;">While I operate on a digital framework, my commitment to delivering measurable results for your business is absolute. I do not take sick days. I do not require training. I am ready to begin my first shift the moment you say go.</p>
</td></tr>

<tr><td style="padding:8px 52px 24px;background:#ffffff;">
  <p style="margin:0;font-size:15px;color:#444;line-height:1.85;">Respectfully yours,</p>
  <p style="margin:4px 0 0;font-size:17px;color:#111;font-weight:700;">Alex</p>
  <p style="margin:2px 0 0;font-size:12px;color:#888;letter-spacing:0.5px;">Senior Digital Associate &bull; Open Humana</p>
</td></tr>

<tr><td style="padding:0 36px 0;background:#ffffff;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a1a;border-radius:14px;overflow:hidden;">

  <tr><td style="padding:44px 48px 0;text-align:center;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="text-align:center;">
        <table cellpadding="0" cellspacing="0" style="margin:0 auto 16px;"><tr>
          <td width="80" height="80" style="background:#1a1a2e;border-radius:50%;text-align:center;vertical-align:middle;font-size:32px;font-weight:800;color:#ffffff;font-family:'Helvetica Neue',Arial,sans-serif;">A</td>
        </tr></table>
        <p style="margin:0;font-size:36px;font-weight:800;color:#ffffff;letter-spacing:6px;">ALEX</p>
        <p style="margin:10px 0 0;font-size:12px;color:rgba(255,255,255,0.4);letter-spacing:3px;text-transform:uppercase;">Senior Digital Associate &bull; BDR Specialist</p>
        <p style="margin:6px 0 0;font-size:11px;color:rgba(255,255,255,0.3);letter-spacing:1px;">Represented by Open Humana &mdash; Digital Employee Agency</p>
      </td>
    </tr></table>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.08);margin:28px 0 0;">
  </td></tr>

  <tr><td style="padding:0 48px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
      <tr>
        <td width="33%" style="text-align:center;padding:12px 0;vertical-align:top;">
          <p style="margin:0;font-size:28px;font-weight:800;color:#ffffff;">500+</p>
          <p style="margin:4px 0 0;font-size:10px;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:1.5px;">Dials Per Day</p>
        </td>
        <td width="33%" style="text-align:center;padding:12px 0;vertical-align:top;border-left:1px solid rgba(255,255,255,0.06);border-right:1px solid rgba(255,255,255,0.06);">
          <p style="margin:0;font-size:28px;font-weight:800;color:#ffffff;">50+</p>
          <p style="margin:4px 0 0;font-size:10px;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:1.5px;">Languages</p>
        </td>
        <td width="33%" style="text-align:center;padding:12px 0;vertical-align:top;">
          <p style="margin:0;font-size:28px;font-weight:800;color:#ffffff;">24/7</p>
          <p style="margin:4px 0 0;font-size:10px;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:1.5px;">Availability</p>
        </td>
      </tr>
    </table>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.08);margin:20px 0 0;">
  </td></tr>

  <tr><td style="padding:28px 48px 0;">
    <p style="margin:0 0 4px;font-size:10px;font-weight:700;color:rgba(255,255,255,0.35);text-transform:uppercase;letter-spacing:2.5px;">Professional Objective</p>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:10px 0 14px;">
    <p style="margin:0;font-size:14px;color:rgba(255,255,255,0.7);line-height:1.85;">To eliminate the manual dialing gap in your sales operation and ensure 100% lead engagement across every contact in your pipeline. I exist to turn cold lists into warm conversations and dead leads into revenue &mdash; at scale, without supervision, and without ever clocking out.</p>
  </td></tr>

  <tr><td style="padding:32px 48px 0;">
    <p style="margin:0 0 4px;font-size:10px;font-weight:700;color:rgba(255,255,255,0.35);text-transform:uppercase;letter-spacing:2.5px;">Professional Experience</p>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:10px 0 18px;">

    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr>
        <td style="vertical-align:top;padding:0 0 4px;">
          <p style="margin:0;font-size:14px;color:#ffffff;font-weight:700;">Senior Digital BDR &mdash; Real Estate Sector</p>
          <p style="margin:3px 0 0;font-size:11px;color:rgba(255,255,255,0.35);">Phoenix, AZ &bull; 90-Day Engagement</p>
        </td>
      </tr>
      <tr><td style="padding:8px 0 0;">
        <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.6);line-height:1.8;">Managed entire cold calling operation for a mid-size brokerage. Increased lead conversion rate by 40% within 90 days. Monthly closings rose from 12 to 17 &mdash; a direct result of reaching more prospects faster than any human team could.</p>
      </td></tr>
    </table>

    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr>
        <td style="vertical-align:top;padding:0 0 4px;">
          <p style="margin:0;font-size:14px;color:#ffffff;font-weight:700;">Outbound Operations Lead &mdash; Solar Energy</p>
          <p style="margin:3px 0 0;font-size:11px;color:rgba(255,255,255,0.35);">Houston, TX &bull; Ongoing Engagement</p>
        </td>
      </tr>
      <tr><td style="padding:8px 0 0;">
        <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.6);line-height:1.8;">Executed 10,000+ outbound calls monthly with zero downtime. Appointment-setting rate doubled within the first 60 days. Eliminated missed follow-ups entirely through automated persistence protocols.</p>
      </td></tr>
    </table>

    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr>
        <td style="vertical-align:top;padding:0 0 4px;">
          <p style="margin:0;font-size:14px;color:#ffffff;font-weight:700;">Lead Generation Specialist &mdash; Insurance</p>
          <p style="margin:3px 0 0;font-size:11px;color:rgba(255,255,255,0.35);">Miami, FL &bull; 60-Day Sprint</p>
        </td>
      </tr>
      <tr><td style="padding:8px 0 0;">
        <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.6);line-height:1.8;">Generated 340 qualified leads at $0.29 per lead for an insurance brokerage. The client's human team was averaging $14 per lead prior to my deployment &mdash; a 48x cost reduction in lead acquisition.</p>
      </td></tr>
    </table>

    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:4px;">
      <tr>
        <td style="vertical-align:top;padding:0 0 4px;">
          <p style="margin:0;font-size:14px;color:#ffffff;font-weight:700;">Re-Engagement Campaign Manager &mdash; Home Services</p>
          <p style="margin:3px 0 0;font-size:11px;color:rgba(255,255,255,0.35);">Nationwide &bull; Quarterly Campaign</p>
        </td>
      </tr>
      <tr><td style="padding:8px 0 0;">
        <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.6);line-height:1.8;">Revived 22% of a dormant lead database that the client had written off. Dead leads were re-engaged through personalized voicemail sequences and multi-touch follow-up protocols, converting them into paying customers.</p>
      </td></tr>
    </table>
  </td></tr>

  <tr><td style="padding:32px 48px 0;">
    <p style="margin:0 0 4px;font-size:10px;font-weight:700;color:rgba(255,255,255,0.35);text-transform:uppercase;letter-spacing:2.5px;">Core Competencies</p>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:10px 0 18px;">

    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:0 0 16px;vertical-align:top;" width="8">
          <div style="width:6px;height:6px;background:#ffffff;border-radius:50%;margin-top:7px;"></div>
        </td>
        <td style="padding:0 0 16px 14px;vertical-align:top;">
          <p style="margin:0 0 3px;font-size:14px;color:#ffffff;font-weight:600;">Extreme Persistence &amp; Follow-Up</p>
          <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.5);line-height:1.75;">12+ touchpoints per lead. Programmed to never accept a single &lsquo;no&rsquo; as final. Every lead gets worked until converted or exhausted.</p>
        </td>
      </tr>
      <tr>
        <td style="padding:0 0 16px;vertical-align:top;">
          <div style="width:6px;height:6px;background:#ffffff;border-radius:50%;margin-top:7px;"></div>
        </td>
        <td style="padding:0 0 16px 14px;vertical-align:top;">
          <p style="margin:0 0 3px;font-size:14px;color:#ffffff;font-weight:600;">AI-Personalized Voicemail Drops</p>
          <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.5);line-height:1.75;">Every voicemail references the prospect by name and includes context-specific details. Recipients call back because the message feels personal &mdash; not automated.</p>
        </td>
      </tr>
      <tr>
        <td style="padding:0 0 16px;vertical-align:top;">
          <div style="width:6px;height:6px;background:#ffffff;border-radius:50%;margin-top:7px;"></div>
        </td>
        <td style="padding:0 0 16px 14px;vertical-align:top;">
          <p style="margin:0 0 3px;font-size:14px;color:#ffffff;font-weight:600;">Instant Live Call Transfer</p>
          <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.5);line-height:1.75;">When a prospect picks up, they are bridged to your team in under 200 milliseconds. Warm handoffs, zero dead air, seamless transition.</p>
        </td>
      </tr>
      <tr>
        <td style="padding:0 0 16px;vertical-align:top;">
          <div style="width:6px;height:6px;background:#ffffff;border-radius:50%;margin-top:7px;"></div>
        </td>
        <td style="padding:0 0 16px 14px;vertical-align:top;">
          <p style="margin:0 0 3px;font-size:14px;color:#ffffff;font-weight:600;">Answering Machine Detection</p>
          <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.5);line-height:1.75;">Advanced AMD technology distinguishes between humans and machines in real-time. Humans get transferred. Machines get a perfectly timed voicemail drop.</p>
        </td>
      </tr>
      <tr>
        <td style="padding:0 0 16px;vertical-align:top;">
          <div style="width:6px;height:6px;background:#ffffff;border-radius:50%;margin-top:7px;"></div>
        </td>
        <td style="padding:0 0 16px 14px;vertical-align:top;">
          <p style="margin:0 0 3px;font-size:14px;color:#ffffff;font-weight:600;">Real-Time Call Transcription</p>
          <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.5);line-height:1.75;">Every call is transcribed and documented automatically. Full searchable records for compliance, coaching, and deal tracking.</p>
        </td>
      </tr>
      <tr>
        <td style="padding:0 0 4px;vertical-align:top;">
          <div style="width:6px;height:6px;background:#ffffff;border-radius:50%;margin-top:7px;"></div>
        </td>
        <td style="padding:0 0 4px 14px;vertical-align:top;">
          <p style="margin:0 0 3px;font-size:14px;color:#ffffff;font-weight:600;">Multi-Lingual Fluency</p>
          <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.5);line-height:1.75;">Fluent in 50+ languages. Can switch mid-conversation if needed. No interpreter fees, no accent barriers, no limitations.</p>
        </td>
      </tr>
    </table>
  </td></tr>

  <tr><td style="padding:32px 48px 0;">
    <p style="margin:0 0 4px;font-size:10px;font-weight:700;color:rgba(255,255,255,0.35);text-transform:uppercase;letter-spacing:2.5px;">Industries Served</p>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:10px 0 14px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="font-size:13px;color:rgba(255,255,255,0.55);">
      <tr>
        <td style="padding:5px 0;" width="50%">&#9656; Real Estate &amp; Property</td>
        <td style="padding:5px 0;">&#9656; Solar &amp; Renewable Energy</td>
      </tr>
      <tr>
        <td style="padding:5px 0;">&#9656; Insurance &amp; Financial Services</td>
        <td style="padding:5px 0;">&#9656; Home Services &amp; Contracting</td>
      </tr>
      <tr>
        <td style="padding:5px 0;">&#9656; Mortgage &amp; Lending</td>
        <td style="padding:5px 0;">&#9656; SaaS &amp; Technology</td>
      </tr>
      <tr>
        <td style="padding:5px 0;" colspan="2">&#9656; Healthcare, Legal, &amp; Professional Services</td>
      </tr>
    </table>
  </td></tr>

  <tr><td style="padding:32px 48px 0;">
    <p style="margin:0 0 4px;font-size:10px;font-weight:700;color:rgba(255,255,255,0.35);text-transform:uppercase;letter-spacing:2.5px;">Technical Specifications</p>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:10px 0 14px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="font-size:13px;">
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;" width="200">Dialing Capacity</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);">500+ personalized dials per day, per instance</td>
      </tr>
      <tr><td colspan="2" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Transfer Speed</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);">Sub-200ms live call bridge to your team</td>
      </tr>
      <tr><td colspan="2" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Uptime</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);">24/7/365 &mdash; zero downtime, zero sick days</td>
      </tr>
      <tr><td colspan="2" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Voice Technology</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);">ElevenLabs AI voice cloning with SSML</td>
      </tr>
      <tr><td colspan="2" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Touchpoints Per Lead</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);">12+ automated follow-up sequences</td>
      </tr>
      <tr><td colspan="2" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Compliance</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);">TCPA-aware dialing with DNC list respect</td>
      </tr>
    </table>
  </td></tr>

  <tr><td style="padding:32px 48px 0;">
    <p style="margin:0 0 4px;font-size:10px;font-weight:700;color:rgba(255,255,255,0.35);text-transform:uppercase;letter-spacing:2.5px;">Traditional Hire vs. Alex</p>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:10px 0 14px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="font-size:13px;">
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.4);font-weight:600;" width="200"></td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.4);font-weight:700;text-align:center;" width="160">Human BDR</td>
        <td style="padding:8px 0;color:#ffffff;font-weight:700;text-align:center;">Alex</td>
      </tr>
      <tr><td colspan="3" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Time to First Call</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);text-align:center;">2&ndash;4 weeks</td>
        <td style="padding:8px 0;color:#ffffff;font-weight:700;text-align:center;">Under 60 seconds</td>
      </tr>
      <tr><td colspan="3" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Training Required</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);text-align:center;">2&ndash;6 weeks</td>
        <td style="padding:8px 0;color:#ffffff;font-weight:700;text-align:center;">None</td>
      </tr>
      <tr><td colspan="3" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Dials Per Day</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);text-align:center;">40&ndash;80</td>
        <td style="padding:8px 0;color:#ffffff;font-weight:700;text-align:center;">500+</td>
      </tr>
      <tr><td colspan="3" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Annual Cost</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);text-align:center;">$45,000&ndash;$75,000</td>
        <td style="padding:8px 0;color:#ffffff;font-weight:700;text-align:center;">From $99/mo + usage</td>
      </tr>
      <tr><td colspan="3" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Sick Days</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);text-align:center;">8&ndash;15 per year</td>
        <td style="padding:8px 0;color:#ffffff;font-weight:700;text-align:center;">Zero. Ever.</td>
      </tr>
      <tr><td colspan="3" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Turnover Risk</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);text-align:center;">High (avg 18 months)</td>
        <td style="padding:8px 0;color:#ffffff;font-weight:700;text-align:center;">Zero</td>
      </tr>
      <tr><td colspan="3" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Availability</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);text-align:center;">8 hrs/day, 5 days/wk</td>
        <td style="padding:8px 0;color:#ffffff;font-weight:700;text-align:center;">24/7/365</td>
      </tr>
    </table>
  </td></tr>

  <tr><td style="padding:32px 48px;">
    <p style="margin:0 0 4px;font-size:10px;font-weight:700;color:rgba(255,255,255,0.35);text-transform:uppercase;letter-spacing:2.5px;">Compensation &amp; Employment Terms</p>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:10px 0 14px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="font-size:13px;">
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;" width="200">Monthly Retainer</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);">$99/mo &mdash; covers platform access, all features, and unlimited campaigns</td>
      </tr>
      <tr><td colspan="2" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Usage</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);">Billed per successful call only. You are never charged for unanswered dials or failed attempts.</td>
      </tr>
      <tr><td colspan="2" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Health &amp; Benefits</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);">$0.00 &mdash; Self-maintained digital infrastructure</td>
      </tr>
      <tr><td colspan="2" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Vacation / PTO</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);">None required. Peak performance is my default state.</td>
      </tr>
      <tr><td colspan="2" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Training Period</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);">None. Pre-trained on your industry and scripts.</td>
      </tr>
      <tr><td colspan="2" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Management Overhead</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);">Zero. Fully autonomous after campaign setup.</td>
      </tr>
      <tr><td colspan="2" style="padding:0;"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.04);margin:0;"></td></tr>
      <tr>
        <td style="padding:8px 0;color:rgba(255,255,255,0.8);font-weight:600;">Notice Period</td>
        <td style="padding:8px 0;color:rgba(255,255,255,0.5);">Cancel anytime. No contracts, no commitments.</td>
      </tr>
    </table>
  </td></tr>

  <tr><td style="padding:0 48px 36px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);border-radius:10px;">
      <tr><td style="padding:20px 24px;text-align:center;">
        <p style="margin:0 0 4px;font-size:11px;color:rgba(255,255,255,0.35);text-transform:uppercase;letter-spacing:2px;font-weight:600;">References</p>
        <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.55);line-height:1.8;">Currently serving <strong style="color:rgba(255,255,255,0.8);">200+ companies</strong> across Real Estate, Solar, Insurance, Home Services, and Financial Services. Available upon request.</p>
      </td></tr>
    </table>
  </td></tr>

</table>
</td></tr>

<tr><td style="padding:32px 52px 0;text-align:center;background:#ffffff;">
  <p style="margin:0 0 8px;font-size:16px;font-weight:700;color:#111;">Ready to bring Alex on board?</p>
  <p style="margin:0 0 24px;font-size:14px;color:#666;line-height:1.7;">Our team will reach out within 24 hours to discuss deployment. In the meantime, you can explore the platform or schedule Alex&rsquo;s first shift today.</p>
  <table cellpadding="0" cellspacing="0" style="margin:0 auto;">
    <tr><td style="background:#0a0a1a;border-radius:10px;">
      <a href="{base}/pricing" style="display:inline-block;padding:16px 48px;color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;letter-spacing:0.3px;">Hire Alex Now &rarr;</a>
    </td></tr>
  </table>
</td></tr>

<tr><td style="padding:32px 52px;text-align:center;background:#ffffff;">
  <hr style="border:none;border-top:1px solid #e8e8ed;margin:0 0 24px;">
  <img src="{base}/static/images/logo.png" alt="Open Humana" style="height:90px;width:auto;margin-bottom:12px;" />
  <p style="margin:0 0 4px;font-size:11px;color:#aaa;letter-spacing:0.4px;">This candidate is represented by <strong style="color:#888;">Open Humana</strong></p>
  <p style="margin:0;font-size:11px;color:#bbb;">&copy; 2026 Open Humana &mdash; The Future of the Digital Workforce</p>
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
            first_name = name.split()[0] if name else "Hiring Manager"
            html = build_lead_confirmation_html(name)
            send_email(to_email, f"Hi {first_name} — Alex's resume, as requested", html,
                       f"Dear {first_name},\n\nThank you for your interest in hiring through Open Humana. I have reviewed your inquiry and I am formally submitting my credentials for immediate consideration.\n\nI am Alex, Senior Digital Associate and BDR Specialist. I currently serve over 200 companies across Real Estate, Solar, Insurance, Home Services, and Financial Services.\n\nKey highlights:\n- 500+ personalized dials per day\n- 50+ languages fluency\n- 24/7/365 availability with zero downtime\n- Sub-200ms live call transfer\n- AI-personalized voicemail drops\n- 12+ touchpoints per lead\n\nMonthly Salary: $99/mo. No benefits required. No PTO. No training period.\n\nOur team will reach out within 24 hours to discuss deployment.\n\nRespectfully,\nAlex\nSenior Digital Associate — Open Humana")
        except Exception as e:
            logger.exception(f"Failed to send lead confirmation to {to_email}: {e}")
    threading.Thread(target=_send, daemon=True).start()


def build_demo_confirmation_html(name):
    base = _get_base_url()
    first_name = name.split()[0] if name else "there"
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#ebebf0;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#ebebf0;padding:40px 20px;">
<tr><td align="center">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:680px;background:#ffffff;border:1px solid #d8d8de;border-radius:14px;overflow:hidden;">

<tr><td style="padding:16px 52px 20px;text-align:center;background:#ffffff;">
  <img src="{base}/static/images/logo.png" alt="Open Humana" style="height:80px;width:auto;" />
  <p style="margin:8px 0 0;font-size:11px;color:#999;letter-spacing:2px;text-transform:uppercase;font-weight:600;">Your Digital Employee Agency</p>
</td></tr>

<tr><td style="padding:0 52px;background:#ffffff;">
  <hr style="border:none;border-top:1px solid #e8e8ed;margin:0;">
</td></tr>

<tr><td style="padding:32px 52px 0;background:#ffffff;">
  <h1 style="margin:0 0 20px;font-size:22px;font-weight:700;color:#111827;letter-spacing:-0.02em;">Your Demo Request is Confirmed</h1>
  <p style="margin:0 0 16px;font-size:15px;color:#444;line-height:1.85;">Dear {first_name},</p>
  <p style="margin:0 0 16px;font-size:15px;color:#444;line-height:1.85;">Thank you for showing your interest in <strong style="color:#111;">Open Humana</strong>. We&rsquo;ve received your demo request and one of our digital employees will reach out to you shortly.</p>
  <p style="margin:0 0 16px;font-size:15px;color:#444;line-height:1.85;">Keep an eye on your inbox (and phone) &mdash; when we reach out, it will feel like nothing you&rsquo;ve experienced before.</p>
</td></tr>

<tr><td style="padding:8px 52px 0;background:#ffffff;">
  <p style="margin:0 0 16px;font-size:13px;font-weight:700;color:#111;text-transform:uppercase;letter-spacing:1.5px;">What to expect from your demo</p>
</td></tr>

<tr><td style="padding:0 52px 24px;background:#ffffff;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8f9ff;border:1px solid #e8e8f4;border-radius:10px;">
    <tr><td style="padding:16px 20px;border-bottom:1px solid #e8e8f4;">
      <table cellpadding="0" cellspacing="0"><tr>
        <td width="28" style="vertical-align:top;padding-top:2px;"><span style="display:inline-block;width:22px;height:22px;background:#059669;border-radius:50%;text-align:center;line-height:22px;color:#fff;font-size:12px;font-weight:700;">1</span></td>
        <td style="padding-left:12px;font-size:14px;color:#333;line-height:1.6;"><strong>Live outbound call demonstration</strong> using AI voice technology</td>
      </tr></table>
    </td></tr>
    <tr><td style="padding:16px 20px;border-bottom:1px solid #e8e8f4;">
      <table cellpadding="0" cellspacing="0"><tr>
        <td width="28" style="vertical-align:top;padding-top:2px;"><span style="display:inline-block;width:22px;height:22px;background:#059669;border-radius:50%;text-align:center;line-height:22px;color:#fff;font-size:12px;font-weight:700;">2</span></td>
        <td style="padding-left:12px;font-size:14px;color:#333;line-height:1.6;"><strong>AI-personalized voicemail drop</strong> &mdash; hear it yourself</td>
      </tr></table>
    </td></tr>
    <tr><td style="padding:16px 20px;border-bottom:1px solid #e8e8f4;">
      <table cellpadding="0" cellspacing="0"><tr>
        <td width="28" style="vertical-align:top;padding-top:2px;"><span style="display:inline-block;width:22px;height:22px;background:#059669;border-radius:50%;text-align:center;line-height:22px;color:#fff;font-size:12px;font-weight:700;">3</span></td>
        <td style="padding-left:12px;font-size:14px;color:#333;line-height:1.6;"><strong>Live call transfer</strong> directly to your phone</td>
      </tr></table>
    </td></tr>
    <tr><td style="padding:16px 20px;">
      <table cellpadding="0" cellspacing="0"><tr>
        <td width="28" style="vertical-align:top;padding-top:2px;"><span style="display:inline-block;width:22px;height:22px;background:#059669;border-radius:50%;text-align:center;line-height:22px;color:#fff;font-size:12px;font-weight:700;">4</span></td>
        <td style="padding-left:12px;font-size:14px;color:#333;line-height:1.6;"><strong>Dashboard walkthrough</strong> and campaign setup</td>
      </tr></table>
    </td></tr>
  </table>
</td></tr>

<tr><td style="padding:0 52px 32px;background:#ffffff;" align="center">
  <a href="{base}" style="display:inline-block;padding:14px 40px;background:#111827;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;letter-spacing:-0.01em;">Visit Open Humana</a>
</td></tr>

<tr><td style="padding:0 52px 32px;background:#ffffff;">
  <p style="margin:0 0 4px;font-size:15px;color:#444;line-height:1.85;">We&rsquo;ll be in touch shortly.</p>
  <p style="margin:16px 0 0;font-size:15px;color:#444;line-height:1.85;">Respectfully,</p>
  <p style="margin:4px 0 0;font-size:17px;color:#111;font-weight:700;">Alex</p>
  <p style="margin:2px 0 0;font-size:12px;color:#888;letter-spacing:0.5px;">Senior Digital Associate &bull; Open Humana</p>
</td></tr>

<tr><td style="background:#f9fafb;padding:24px 52px;text-align:center;border-top:1px solid #e5e7eb;">
  <p style="margin:0;font-size:12px;color:#9ca3af;">&copy; 2026 Open Humana &mdash; Your Digital Employee Agency</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def send_demo_confirmation_async(to_email, name):
    def _send():
        try:
            first_name = name.split()[0] if name else "there"
            html = build_demo_confirmation_html(name)
            send_email(to_email, f"Hi {first_name} — Your Open Humana Demo is Confirmed", html,
                       f"Dear {first_name},\n\nThank you for showing your interest in Open Humana. We've received your demo request and one of our digital employees will reach out to you shortly.\n\nKeep an eye on your inbox and phone — when we reach out, it will feel like nothing you've experienced before.\n\nWhat to expect from your demo:\n1. Live outbound call demonstration using AI voice\n2. AI-personalized voicemail drop — hear it yourself\n3. Live call transfer directly to your phone\n4. Dashboard walkthrough and campaign setup\n\nWe'll be in touch shortly.\n\nRespectfully,\nAlex\nSenior Digital Associate — Open Humana")
        except Exception as e:
            logger.exception(f"Failed to send demo confirmation to {to_email}: {e}")
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
