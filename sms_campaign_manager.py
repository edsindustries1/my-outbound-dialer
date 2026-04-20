"""
sms_campaign_manager.py — Background worker for SMS blast campaigns.

One worker thread per running campaign. The worker walks pending recipients
from sms_campaign_recipients, calls send_compliant_sms (the single compliance
chokepoint in app.py), records the result on the recipient row, and keeps the
SmsCampaign counters in sync.

Design notes:
  * State lives in the DB. Stop/pause/resume flip campaign.status; the worker
    reads it every loop and exits cleanly so a process restart never loses work.
  * Throughput is enforced inside send_compliant_sms (claim_sms_throughput per
    sending number). The worker adds a small jitter so a single campaign can't
    monopolise the number's minute bucket.
  * Every recipient row maps 1:1 to an outbound SmsMessage row. We stamp the
    message with sms_campaign_id so the inbox/daily-report/analytics all share
    the same source of truth.
"""

import logging
import random
import threading
import time
from datetime import datetime

logger = logging.getLogger("voicemail_app.sms_campaigns")

_workers = {}            # campaign_id -> Thread
_stop_events = {}        # campaign_id -> threading.Event  (set = stop)
_pause_events = {}       # campaign_id -> threading.Event  (cleared = paused)
_lock = threading.Lock()

# Seconds between consecutive sends per worker. The global chokepoint enforces
# 75 msgs/min/number; this pacing keeps us well under that and smooths bursts.
SEND_SPACING_MIN = 0.8
SEND_SPACING_MAX = 1.3


def is_running(campaign_id: int) -> bool:
    with _lock:
        t = _workers.get(campaign_id)
        return bool(t and t.is_alive())


def _ensure_events(campaign_id: int):
    if campaign_id not in _stop_events:
        _stop_events[campaign_id] = threading.Event()
    if campaign_id not in _pause_events:
        ev = threading.Event()
        ev.set()  # default resumed
        _pause_events[campaign_id] = ev


def start(campaign_id: int) -> bool:
    """Launch (or relaunch) the worker thread for a campaign."""
    with _lock:
        existing = _workers.get(campaign_id)
        if existing and existing.is_alive():
            # Already running — make sure it's not paused.
            _ensure_events(campaign_id)
            _pause_events[campaign_id].set()
            return True
        _ensure_events(campaign_id)
        _stop_events[campaign_id].clear()
        _pause_events[campaign_id].set()
        t = threading.Thread(target=_worker, args=(campaign_id,),
                             name=f"sms-campaign-{campaign_id}", daemon=True)
        _workers[campaign_id] = t
    t.start()
    return True


def pause(campaign_id: int):
    with _lock:
        _ensure_events(campaign_id)
        _pause_events[campaign_id].clear()


def resume(campaign_id: int):
    with _lock:
        _ensure_events(campaign_id)
        _pause_events[campaign_id].set()


def cancel(campaign_id: int):
    """Signal the worker to stop. Also clears any pause so it wakes up."""
    with _lock:
        _ensure_events(campaign_id)
        _stop_events[campaign_id].set()
        _pause_events[campaign_id].set()


def _worker(campaign_id: int):
    """Main send loop. Imports Flask app lazily to avoid circular imports."""
    try:
        from app import app as flask_app
    except Exception as e:
        logger.exception(f"[sms-campaign {campaign_id}] cannot import app: {e}")
        return

    with flask_app.app_context():
        from models import db, SmsCampaign, SmsCampaignRecipient, SmsMessage
        from app import send_compliant_sms, _is_sms_opted_out

        camp = SmsCampaign.query.get(campaign_id)
        if not camp:
            logger.warning(f"[sms-campaign {campaign_id}] not found, aborting")
            return
        if camp.status not in ("queued", "running", "paused", "interrupted"):
            logger.info(f"[sms-campaign {campaign_id}] status={camp.status}, not eligible to run")
            return

        camp.status = "running"
        if not camp.started_at:
            camp.started_at = datetime.utcnow()
        camp.updated_at = datetime.utcnow()
        db.session.commit()
        logger.info(f"[sms-campaign {campaign_id}] worker started (user={camp.user_id})")

        stop_ev = _stop_events[campaign_id]
        pause_ev = _pause_events[campaign_id]

        try:
            while not stop_ev.is_set():
                # Pause gate — wait up to 10s then recheck stop
                if not pause_ev.is_set():
                    # Reflect paused state in DB once
                    _set_status(campaign_id, "paused")
                    pause_ev.wait(timeout=10)
                    if stop_ev.is_set():
                        break
                    # On resume, flip back to running
                    _set_status(campaign_id, "running")
                    continue

                # Atomically claim the next pending recipient. A conditional
                # UPDATE ... WHERE status='pending' is safe across threads and
                # across processes (gunicorn workers): only one worker will
                # observe their UPDATE mutating a row because PG serializes
                # row-level writes. We flip it to 'sending' so no other worker
                # sees it as pending.
                from sqlalchemy import text as _text
                next_id_row = db.session.execute(
                    _text(
                        "SELECT id FROM sms_campaign_recipients "
                        "WHERE sms_campaign_id = :cid AND status = 'pending' "
                        "ORDER BY id ASC LIMIT 1 FOR UPDATE SKIP LOCKED"
                    ),
                    {"cid": campaign_id},
                ).fetchone()
                if not next_id_row:
                    db.session.commit()
                    break  # no more pending recipients
                claimed_id = next_id_row[0]
                db.session.execute(
                    _text(
                        "UPDATE sms_campaign_recipients "
                        "SET status='sending', updated_at=NOW() "
                        "WHERE id = :rid AND status = 'pending'"
                    ),
                    {"rid": claimed_id},
                )
                db.session.commit()
                recip = SmsCampaignRecipient.query.get(claimed_id)
                if not recip or recip.status != "sending":
                    continue  # lost the race, try again

                camp = SmsCampaign.query.get(campaign_id)
                if not camp:
                    break
                if stop_ev.is_set() or camp.status == "cancelled":
                    break

                # Honor per-user opt-outs just in case the list was seeded before
                # a STOP reply landed.
                if _is_sms_opted_out(camp.user_id, recip.to_number):
                    _record_result(campaign_id, recip.id, status="opted_out",
                                   error="Recipient already opted out", segments=0,
                                   sms_message_id=None)
                    continue

                contact = recip.contact_data or {}
                result = send_compliant_sms(
                    user_id=camp.user_id,
                    from_number=camp.from_number,
                    to_number=recip.to_number,
                    body=camp.body_template,
                    contact=contact,
                    call_record_id=None,
                    campaign_id=None,
                    agent_name=camp.agent_name or "",
                    custom_link=camp.custom_link or "",
                )

                # Map chokepoint result into recipient + campaign counters
                status_map = {
                    "sent": "sent",
                    "opted_out": "opted_out",
                    "skipped": "skipped",
                    "blocked": "skipped",
                    "rate_limited": "rate_limited",
                    "payment_required": "payment_required",
                    "failed": "failed",
                }
                mapped = status_map.get(result.get("status"), "failed")
                sms_msg_id = result.get("sms_message_id")
                segs = int(result.get("segments") or 0)

                # Tag the resulting SmsMessage with our campaign id so the
                # inbox, analytics, and daily report can scope by campaign.
                if sms_msg_id:
                    try:
                        m = SmsMessage.query.get(sms_msg_id)
                        if m:
                            m.sms_campaign_id = campaign_id
                            db.session.commit()
                    except Exception:
                        db.session.rollback()

                _record_result(
                    campaign_id, recip.id,
                    status=mapped,
                    error=(result.get("error") or "")[:500] if not result.get("ok") else None,
                    segments=segs,
                    sms_message_id=sms_msg_id,
                )

                # If we hit a payment wall, pause the whole campaign so the
                # operator isn't bombarded with identical failures.
                if mapped == "payment_required":
                    logger.warning(
                        f"[sms-campaign {campaign_id}] payment_required — auto-pausing"
                    )
                    _set_status(campaign_id, "paused")
                    pause(campaign_id)
                    continue

                # Light jitter between sends — chokepoint throughput limit
                # handles the hard cap, this just smooths bursts.
                time.sleep(random.uniform(SEND_SPACING_MIN, SEND_SPACING_MAX))

            # Loop exited — determine terminal status
            camp = SmsCampaign.query.get(campaign_id)
            if not camp:
                return
            remaining = (SmsCampaignRecipient.query
                         .filter_by(sms_campaign_id=campaign_id, status="pending")
                         .count())
            if stop_ev.is_set() and camp.status != "completed":
                camp.status = "cancelled"
            elif remaining == 0:
                camp.status = "completed"
                camp.completed_at = datetime.utcnow()
            camp.updated_at = datetime.utcnow()
            db.session.commit()
            logger.info(
                f"[sms-campaign {campaign_id}] worker exit status={camp.status} "
                f"sent={camp.sent_count}/{camp.total_count}"
            )
        except Exception as e:
            logger.exception(f"[sms-campaign {campaign_id}] worker crashed: {e}")
            try:
                camp = SmsCampaign.query.get(campaign_id)
                if camp and camp.status == "running":
                    camp.status = "failed"
                    camp.updated_at = datetime.utcnow()
                    db.session.commit()
            except Exception:
                db.session.rollback()
        finally:
            with _lock:
                _workers.pop(campaign_id, None)


def _set_status(campaign_id: int, status: str):
    from models import db, SmsCampaign
    try:
        camp = SmsCampaign.query.get(campaign_id)
        if camp and camp.status != status and camp.status not in ("cancelled", "completed"):
            camp.status = status
            camp.updated_at = datetime.utcnow()
            db.session.commit()
    except Exception:
        from models import db as _db
        _db.session.rollback()


def _record_result(campaign_id: int, recipient_id: int, status: str,
                   error: str = None, segments: int = 0, sms_message_id: int = None):
    """Atomically update recipient and campaign counters."""
    from models import db, SmsCampaign, SmsCampaignRecipient, SmsMessage
    try:
        recip = SmsCampaignRecipient.query.get(recipient_id)
        camp = SmsCampaign.query.get(campaign_id)
        if not recip or not camp:
            return
        recip.status = status
        recip.error = error
        recip.segments = segments
        recip.sms_message_id = sms_message_id
        recip.attempted_at = datetime.utcnow()
        if status == "sent":
            camp.sent_count = (camp.sent_count or 0) + 1
            camp.segments_sent = (camp.segments_sent or 0) + segments
            # Pull cost charged from the SmsMessage row for an accurate total
            if sms_message_id:
                m = SmsMessage.query.get(sms_message_id)
                if m and m.cost_charged:
                    from decimal import Decimal
                    camp.cost_charged = (camp.cost_charged or Decimal("0")) + m.cost_charged
        elif status == "opted_out":
            camp.opt_out_count = (camp.opt_out_count or 0) + 1
        elif status in ("skipped", "rate_limited", "payment_required"):
            camp.skipped_count = (camp.skipped_count or 0) + 1
        else:  # failed
            camp.failed_count = (camp.failed_count or 0) + 1
        camp.updated_at = datetime.utcnow()
        db.session.commit()
    except Exception as e:
        logger.exception(f"[sms-campaign {campaign_id}] record_result failed: {e}")
        from models import db as _db
        _db.session.rollback()
