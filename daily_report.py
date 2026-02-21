"""
daily_report.py - Generates daily email reports from call history.
Reports include: Hot Leads, Failed Calls, and Voicemails Left.
"""

import csv
import io
import logging
from datetime import datetime, timedelta

from storage import get_call_history, get_report_settings, get_invalid_numbers, get_unreachable_numbers
from gmail_client import send_email

logger = logging.getLogger("voicemail_app")

HANGUP_DESCRIPTIONS = {
    "NORMAL_CLEARING": "Normal call end",
    "USER_BUSY": "Line busy",
    "NO_USER_RESPONSE": "No answer (timeout)",
    "NO_ANSWER": "No answer",
    "CALL_REJECTED": "Call rejected",
    "UNALLOCATED_NUMBER": "Invalid/unallocated number",
    "INVALID_NUMBER_FORMAT": "Invalid number format",
    "NUMBER_CHANGED": "Number changed",
    "DESTINATION_OUT_OF_ORDER": "Destination out of order",
    "NETWORK_OUT_OF_ORDER": "Network error",
    "TEMPORARY_FAILURE": "Temporary network failure",
    "RECOVERY_ON_TIMER_EXPIRE": "Call timed out",
    "ORIGINATOR_CANCEL": "Call cancelled",
    "NORMAL_TEMPORARY_FAILURE": "Temporary failure",
    "SERVICE_NOT_IMPLEMENTED": "Service unavailable",
    "EXCHANGE_ROUTING_ERROR": "Routing error",
    "MANDATORY_IE_MISSING": "Protocol error",
    "BEARERCAPABILITY_NOTAVAIL": "Bearer capability not available",
    "INCOMPATIBLE_DESTINATION": "Incompatible destination",
}


def _get_last_24h_history():
    cutoff = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
    return get_call_history(start_date=cutoff)


def _classify_calls(history):
    hot_leads = []
    failed_calls = []
    voicemails = []
    invalid_numbers = []

    unreachable_numbers = []

    for entry in history:
        if entry.get("status") == "skipped" and entry.get("hangup_cause") == "INVALID_NUMBER_FORMAT":
            invalid_numbers.append(entry)
        elif entry.get("status") == "skipped" and entry.get("hangup_cause") == "NUMBER_UNREACHABLE":
            unreachable_numbers.append(entry)
        elif entry.get("transferred"):
            hot_leads.append(entry)
        elif entry.get("voicemail_dropped"):
            voicemails.append(entry)
        else:
            status = entry.get("status", "")
            hangup = entry.get("hangup_cause", "")
            amd = entry.get("amd_result", "")
            if status in ("failed", "error", "hangup") or hangup in (
                "USER_BUSY", "NO_USER_RESPONSE", "NO_ANSWER", "CALL_REJECTED",
                "UNALLOCATED_NUMBER", "INVALID_NUMBER_FORMAT", "NUMBER_CHANGED",
                "DESTINATION_OUT_OF_ORDER", "NETWORK_OUT_OF_ORDER", "TEMPORARY_FAILURE",
                "RECOVERY_ON_TIMER_EXPIRE", "ORIGINATOR_CANCEL", "NORMAL_TEMPORARY_FAILURE",
            ) or (hangup and hangup != "NORMAL_CLEARING"):
                failed_calls.append(entry)

    return hot_leads, failed_calls, voicemails, invalid_numbers, unreachable_numbers


def _format_time(ts_str):
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%I:%M %p")
    except Exception:
        return ts_str or "N/A"


def _format_datetime(ts_str):
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%b %d, %Y %I:%M %p UTC")
    except Exception:
        return ts_str or "N/A"


def _format_phone(number):
    if not number:
        return "N/A"
    clean = number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if len(clean) == 11 and clean.startswith("1"):
        return f"+1 ({clean[1:4]}) {clean[4:7]}-{clean[7:]}"
    if len(clean) == 10:
        return f"({clean[0:3]}) {clean[3:6]}-{clean[6:]}"
    return number


def _build_summary(history, hot_leads, failed_calls, voicemails, invalid_numbers=None, unreachable_numbers=None):
    total = len(history)
    success = len(hot_leads) + len(voicemails)
    success_rate = round((success / total) * 100, 1) if total > 0 else 0
    return {
        "total_calls": total,
        "hot_leads": len(hot_leads),
        "failed_calls": len(failed_calls),
        "voicemails_left": len(voicemails),
        "invalid_numbers": len(invalid_numbers) if invalid_numbers else 0,
        "unreachable_numbers": len(unreachable_numbers) if unreachable_numbers else 0,
        "success_rate": success_rate,
    }


def _generate_csv_attachment(history):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date/Time", "Phone Number", "Status", "AMD Result",
        "Transferred", "Voicemail Dropped", "Hangup Cause", "Description"
    ])
    for entry in history:
        ts = _format_datetime(entry.get("timestamp", ""))
        number = entry.get("number", "")
        status = entry.get("status_description", "") or entry.get("status", "")
        amd = entry.get("amd_result", "") or ""
        transferred = "Yes" if entry.get("transferred") else "No"
        vm = "Yes" if entry.get("voicemail_dropped") else "No"
        hangup = entry.get("hangup_cause", "") or ""
        desc = HANGUP_DESCRIPTIONS.get(hangup, hangup)
        writer.writerow([ts, number, status, amd, transferred, vm, hangup, desc])
    return output.getvalue()


def _build_html_report(summary, hot_leads, failed_calls, voicemails, invalid_numbers=None, unreachable_numbers=None):
    now_str = datetime.utcnow().strftime("%B %d, %Y")
    if invalid_numbers is None:
        invalid_numbers = []
    if unreachable_numbers is None:
        unreachable_numbers = []

    hot_leads_rows = ""
    for i, lead in enumerate(hot_leads, 1):
        transcript_parts = lead.get("transcript", [])
        transcript = " ".join([t.get("text", "") for t in transcript_parts]) if transcript_parts else "N/A"
        if len(transcript) > 120:
            transcript = transcript[:120] + "..."
        hot_leads_rows += f"""
        <tr>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;">{i}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;font-weight:600;">{_format_phone(lead.get('number', ''))}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;">{_format_time(lead.get('timestamp', ''))}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;">{lead.get('ring_duration', 'N/A')}s</td>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;font-size:12px;color:#64748B;">{transcript}</td>
        </tr>"""

    failed_rows = ""
    for i, call in enumerate(failed_calls, 1):
        hangup = call.get("hangup_cause", "") or "unknown"
        desc = HANGUP_DESCRIPTIONS.get(hangup, call.get("status_description", "") or hangup)
        status_color = "#EF4444" if hangup in ("UNALLOCATED_NUMBER", "INVALID_NUMBER_FORMAT") else "#F59E0B"
        failed_rows += f"""
        <tr>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;">{i}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;font-weight:600;">{_format_phone(call.get('number', ''))}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;">{_format_time(call.get('timestamp', ''))}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;"><span style="background:{status_color};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;">{hangup}</span></td>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;">{desc}</td>
        </tr>"""

    vm_rows = ""
    for i, vm in enumerate(voicemails, 1):
        amd = vm.get("amd_result", "") or "machine"
        vm_rows += f"""
        <tr>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;">{i}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;font-weight:600;">{_format_phone(vm.get('number', ''))}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;">{_format_time(vm.get('timestamp', ''))}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;">{amd}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;">{vm.get('ring_duration', 'N/A')}s</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#F1F5F9;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F1F5F9;padding:20px 0;">
<tr><td align="center">
<table width="640" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

<!-- Header -->
<tr><td style="background:linear-gradient(135deg,#2563EB,#06B6D4);padding:32px 40px;text-align:center;">
    <h1 style="margin:0;color:#fff;font-size:26px;font-weight:700;letter-spacing:-0.5px;">Open Human</h1>
    <p style="margin:6px 0 0;color:rgba(255,255,255,0.85);font-size:13px;">Daily Campaign Report &mdash; {now_str}</p>
</td></tr>

<!-- Summary Cards -->
<tr><td style="padding:28px 32px 16px;">
    <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
        <td width="25%" style="text-align:center;padding:12px 4px;">
            <div style="background:#F8FAFC;border-radius:10px;padding:16px 8px;border:1px solid #E2E8F0;">
                <div style="font-size:28px;font-weight:700;color:#1E293B;">{summary['total_calls']}</div>
                <div style="font-size:11px;color:#64748B;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Total Calls</div>
            </div>
        </td>
        <td width="25%" style="text-align:center;padding:12px 4px;">
            <div style="background:#F0FDF4;border-radius:10px;padding:16px 8px;border:1px solid #BBF7D0;">
                <div style="font-size:28px;font-weight:700;color:#16A34A;">{summary['hot_leads']}</div>
                <div style="font-size:11px;color:#16A34A;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Hot Leads</div>
            </div>
        </td>
        <td width="25%" style="text-align:center;padding:12px 4px;">
            <div style="background:#FEF2F2;border-radius:10px;padding:16px 8px;border:1px solid #FECACA;">
                <div style="font-size:28px;font-weight:700;color:#EF4444;">{summary['failed_calls']}</div>
                <div style="font-size:11px;color:#EF4444;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Failed</div>
            </div>
        </td>
        <td width="25%" style="text-align:center;padding:12px 4px;">
            <div style="background:#EFF6FF;border-radius:10px;padding:16px 8px;border:1px solid #BFDBFE;">
                <div style="font-size:28px;font-weight:700;color:#2563EB;">{summary['voicemails_left']}</div>
                <div style="font-size:11px;color:#2563EB;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Voicemails</div>
            </div>
        </td>
    </tr>
    </table>
    {"<table width='100%' cellpadding='0' cellspacing='0' style='margin-top:8px;'><tr><td style='text-align:center;padding:4px;'><div style='background:#FFFBEB;border-radius:10px;padding:12px 8px;border:1px solid #FDE68A;'><div style='font-size:22px;font-weight:700;color:#F59E0B;'>" + str(summary['invalid_numbers']) + "</div><div style='font-size:11px;color:#F59E0B;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;'>Invalid Skipped</div></div></td></tr></table>" if summary.get('invalid_numbers', 0) > 0 else ""}
    <div style="text-align:center;margin-top:8px;">
        <span style="font-size:13px;color:#64748B;">Success Rate: <strong style="color:#1E293B;">{summary['success_rate']}%</strong></span>
    </div>
</td></tr>

<!-- Section 1: Hot Leads -->
<tr><td style="padding:16px 32px 8px;">
    <div style="display:flex;align-items:center;">
        <div style="background:#16A34A;width:4px;height:24px;border-radius:2px;display:inline-block;vertical-align:middle;"></div>
        <h2 style="margin:0 0 0 12px;font-size:18px;color:#1E293B;display:inline-block;vertical-align:middle;">&#128293; Hot Leads of the Day</h2>
    </div>
    <p style="margin:6px 0 0 16px;font-size:12px;color:#64748B;">Calls answered by a human and transferred successfully</p>
</td></tr>
<tr><td style="padding:0 32px 20px;">
    {"<table width='100%' cellpadding='0' cellspacing='0' style='border:1px solid #E2E8F0;border-radius:8px;overflow:hidden;font-size:13px;'><tr style='background:#F8FAFC;'><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>#</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Phone Number</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Time</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Ring</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Transcript</th></tr>" + hot_leads_rows + "</table>" if hot_leads else "<div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:20px;text-align:center;color:#94A3B8;font-size:13px;'>No hot leads in the last 24 hours</div>"}
</td></tr>

<!-- Section 2: Failed Calls -->
<tr><td style="padding:16px 32px 8px;">
    <div style="display:flex;align-items:center;">
        <div style="background:#EF4444;width:4px;height:24px;border-radius:2px;display:inline-block;vertical-align:middle;"></div>
        <h2 style="margin:0 0 0 12px;font-size:18px;color:#1E293B;display:inline-block;vertical-align:middle;">&#9888;&#65039; Failed Calls</h2>
    </div>
    <p style="margin:6px 0 0 16px;font-size:12px;color:#64748B;">Numbers that failed to dial with detailed failure reasons</p>
</td></tr>
<tr><td style="padding:0 32px 20px;">
    {"<table width='100%' cellpadding='0' cellspacing='0' style='border:1px solid #E2E8F0;border-radius:8px;overflow:hidden;font-size:13px;'><tr style='background:#F8FAFC;'><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>#</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Phone Number</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Time</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Cause</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Description</th></tr>" + failed_rows + "</table>" if failed_calls else "<div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:20px;text-align:center;color:#94A3B8;font-size:13px;'>No failed calls in the last 24 hours</div>"}
</td></tr>

<!-- Section 3: Voicemails Left -->
<tr><td style="padding:16px 32px 8px;">
    <div style="display:flex;align-items:center;">
        <div style="background:#2563EB;width:4px;height:24px;border-radius:2px;display:inline-block;vertical-align:middle;"></div>
        <h2 style="margin:0 0 0 12px;font-size:18px;color:#1E293B;display:inline-block;vertical-align:middle;">&#128232; Voicemails Left</h2>
    </div>
    <p style="margin:6px 0 0 16px;font-size:12px;color:#64748B;">Voicemail messages successfully dropped in the last 24 hours</p>
</td></tr>
<tr><td style="padding:0 32px 20px;">
    {"<table width='100%' cellpadding='0' cellspacing='0' style='border:1px solid #E2E8F0;border-radius:8px;overflow:hidden;font-size:13px;'><tr style='background:#F8FAFC;'><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>#</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Phone Number</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Time</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>AMD Result</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Ring</th></tr>" + vm_rows + "</table>" if voicemails else "<div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:20px;text-align:center;color:#94A3B8;font-size:13px;'>No voicemails left in the last 24 hours</div>"}
</td></tr>

<!-- Section 4: Invalid Numbers -->
<tr><td style="padding:16px 32px 8px;">
    <div style="display:flex;align-items:center;">
        <div style="background:#F59E0B;width:4px;height:24px;border-radius:2px;display:inline-block;vertical-align:middle;"></div>
        <h2 style="margin:0 0 0 12px;font-size:18px;color:#1E293B;display:inline-block;vertical-align:middle;">&#9888; Invalid Numbers ({len(invalid_numbers)})</h2>
    </div>
    <p style="margin:6px 0 0 16px;font-size:12px;color:#64748B;">Numbers that were automatically skipped due to invalid format - consider removing from your data</p>
</td></tr>
<tr><td style="padding:0 32px 20px;">
    {"<table width='100%' cellpadding='0' cellspacing='0' style='border:1px solid #E2E8F0;border-radius:8px;overflow:hidden;font-size:13px;'><tr style='background:#F8FAFC;'><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>#</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Phone Number</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Time</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Reason</th></tr>" + ''.join([f"<tr><td style='padding:10px 14px;border-bottom:1px solid #E2E8F0;'>{i}</td><td style='padding:10px 14px;border-bottom:1px solid #E2E8F0;font-weight:600;'>{_format_phone(inv.get('number', ''))}</td><td style='padding:10px 14px;border-bottom:1px solid #E2E8F0;'>{_format_time(inv.get('timestamp', ''))}</td><td style='padding:10px 14px;border-bottom:1px solid #E2E8F0;'><span style='background:#F59E0B;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;'>{inv.get('invalid_reason', inv.get('status_description', 'Invalid'))}</span></td></tr>" for i, inv in enumerate(invalid_numbers, 1)]) + "</table>" if invalid_numbers else "<div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:20px;text-align:center;color:#94A3B8;font-size:13px;'>No invalid numbers detected in the last 24 hours</div>"}
</td></tr>

<!-- Section 5: Unreachable Numbers (Carrier Check) -->
<tr><td style="padding:16px 32px 8px;">
    <div style="display:flex;align-items:center;">
        <div style="background:#EF4444;width:4px;height:24px;border-radius:2px;display:inline-block;vertical-align:middle;"></div>
        <h2 style="margin:0 0 0 12px;font-size:18px;color:#1E293B;display:inline-block;vertical-align:middle;">&#128242; Unreachable Numbers ({len(unreachable_numbers)})</h2>
    </div>
    <p style="margin:6px 0 0 16px;font-size:12px;color:#64748B;">Numbers flagged by carrier lookup as disconnected or out of service - remove from your data to protect account health</p>
</td></tr>
<tr><td style="padding:0 32px 20px;">
    {"<table width='100%' cellpadding='0' cellspacing='0' style='border:1px solid #E2E8F0;border-radius:8px;overflow:hidden;font-size:13px;'><tr style='background:#F8FAFC;'><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>#</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Phone Number</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Time</th><th style='padding:10px 14px;text-align:left;color:#64748B;font-weight:600;font-size:11px;text-transform:uppercase;'>Reason</th></tr>" + ''.join([f"<tr><td style='padding:10px 14px;border-bottom:1px solid #E2E8F0;'>{i}</td><td style='padding:10px 14px;border-bottom:1px solid #E2E8F0;font-weight:600;'>{_format_phone(unr.get('number', ''))}</td><td style='padding:10px 14px;border-bottom:1px solid #E2E8F0;'>{_format_time(unr.get('timestamp', ''))}</td><td style='padding:10px 14px;border-bottom:1px solid #E2E8F0;'><span style='background:#EF4444;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;'>{unr.get('invalid_reason', unr.get('status_description', 'Unreachable'))}</span></td></tr>" for i, unr in enumerate(unreachable_numbers, 1)]) + "</table>" if unreachable_numbers else "<div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:20px;text-align:center;color:#94A3B8;font-size:13px;'>No unreachable numbers detected in the last 24 hours</div>"}
</td></tr>

<!-- Footer -->
<tr><td style="background:#F8FAFC;padding:24px 32px;border-top:1px solid #E2E8F0;text-align:center;">
    <p style="margin:0;font-size:12px;color:#94A3B8;">This is an automated report from <strong>Open Human</strong></p>
    <p style="margin:4px 0 0;font-size:11px;color:#CBD5E1;">Generated at {datetime.utcnow().strftime('%I:%M %p UTC')} &bull; Report period: Last 24 hours</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    return html


def generate_and_send_report():
    settings = get_report_settings()
    recipient = settings.get("recipient_email", "").strip()
    if not recipient:
        logger.warning("Daily report: No recipient email configured, skipping")
        return False

    if not settings.get("enabled", False):
        logger.info("Daily report: Reporting is disabled, skipping")
        return False

    history = _get_last_24h_history()
    hot_leads, failed_calls, voicemails, invalid_numbers, unreachable_numbers = _classify_calls(history)
    summary = _build_summary(history, hot_leads, failed_calls, voicemails, invalid_numbers, unreachable_numbers)

    now_str = datetime.utcnow().strftime("%B %d, %Y")
    subject = f"Open Human Daily Report - {now_str} | {summary['hot_leads']} Hot Leads, {summary['failed_calls']} Failed, {summary['voicemails_left']} VMs"

    html_body = _build_html_report(summary, hot_leads, failed_calls, voicemails, invalid_numbers, unreachable_numbers)

    text_body = f"""Open Human Daily Report - {now_str}

Summary:
- Total Calls: {summary['total_calls']}
- Hot Leads: {summary['hot_leads']}
- Failed Calls: {summary['failed_calls']}
- Voicemails Left: {summary['voicemails_left']}
- Invalid Numbers: {summary['invalid_numbers']}
- Unreachable Numbers: {summary['unreachable_numbers']}
- Success Rate: {summary['success_rate']}%

See the HTML version for detailed tables and the attached CSV for raw data."""

    csv_data = _generate_csv_attachment(history)
    csv_filename = f"open_human_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    success = send_email(
        to_email=recipient,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        csv_attachment=csv_data,
        csv_filename=csv_filename,
    )

    if success:
        logger.info(f"Daily report sent to {recipient}: {summary['total_calls']} calls, {summary['hot_leads']} leads")
    else:
        logger.error(f"Failed to send daily report to {recipient}")

    return success


def send_test_report(recipient_email=None):
    settings = get_report_settings()
    recipient = recipient_email or settings.get("recipient_email", "").strip()
    if not recipient:
        return {"success": False, "error": "No recipient email configured"}

    history = _get_last_24h_history()
    hot_leads, failed_calls, voicemails, invalid_numbers, unreachable_numbers = _classify_calls(history)
    summary = _build_summary(history, hot_leads, failed_calls, voicemails, invalid_numbers, unreachable_numbers)

    now_str = datetime.utcnow().strftime("%B %d, %Y")
    subject = f"[TEST] Open Human Daily Report - {now_str}"

    html_body = _build_html_report(summary, hot_leads, failed_calls, voicemails, invalid_numbers, unreachable_numbers)
    csv_data = _generate_csv_attachment(history)
    csv_filename = f"open_human_test_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    success = send_email(
        to_email=recipient,
        subject=subject,
        html_body=html_body,
        csv_attachment=csv_data,
        csv_filename=csv_filename,
    )

    return {"success": success, "recipient": recipient, "summary": summary}
