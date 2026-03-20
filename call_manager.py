"""
call_manager.py - Queue-based dialing system with rate limiting.
Processes phone numbers from the campaign in a background thread.
Supports sequential (one at a time) and simultaneous (batch) dialing modes.
"""

import threading
import time
import logging
from storage import (
    get_campaign,
    is_campaign_active,
    create_call_state,
    mark_campaign_complete,
    increment_dialed,
    register_call_complete_event,
    is_transfer_paused,
    wait_if_transfer_paused,
    is_campaign_paused,
    wait_if_campaign_paused,
    is_dnc,
    is_valid_phone_number,
    log_invalid_number,
    count_active_calls,
)
from telnyx_client import make_call

logger = logging.getLogger("voicemail_app")

_worker_threads = {}
_worker_threads_lock = threading.Lock()

_slot_lock = threading.Lock()
_reserved_slots = {}


def _try_reserve_slot(user_id, max_lines):
    """Atomically try to reserve a call slot for user_id. Returns True on success.
    
    Combines both actively-tracked calls AND in-flight reservations so simultaneous
    threads cannot race past the limit.
    """
    if user_id is None:
        return True
    with _slot_lock:
        key = user_id
        in_flight = _reserved_slots.get(key, 0)
        active = count_active_calls(user_id=user_id)
        total = active + in_flight
        if total >= max_lines:
            return False
        _reserved_slots[key] = in_flight + 1
        return True


def _release_slot(user_id):
    """Release a reserved slot (call after call is placed or fails)."""
    if user_id is None:
        return
    with _slot_lock:
        key = user_id
        current = _reserved_slots.get(key, 0)
        if current > 0:
            _reserved_slots[key] = current - 1


DEFAULT_MAX_LINES = 5
DAILY_DIAL_CAP = 150

PLAN_MAX_LINES = {
    "starter": 5,
    "business": 15,
}

_ALL_CAPPED = "__ALL_NUMBERS_AT_DAILY_CAP__"


def _get_user_max_lines(user_id):
    """Get the max concurrent lines for a user from UserAppData, falling back to DEFAULT_MAX_LINES."""
    try:
        from app import app as _flask_app, db
        from models import UserAppData
        import json as _json
        with _flask_app.app_context():
            rec = UserAppData.query.filter_by(user_id=user_id, data_key="max_concurrent_lines").first()
            if rec:
                val = _json.loads(rec.data_value)
                limit = int(val.get("limit", DEFAULT_MAX_LINES))
                return limit
    except Exception as e:
        logger.warning(f"Could not get max_concurrent_lines for user {user_id}, using default {DEFAULT_MAX_LINES}: {e}")
    return DEFAULT_MAX_LINES


def _get_lru_from_number(user_id, fallback=None):
    """Select the least-recently-used active number for a user that has not hit its daily dial cap.

    Returns:
        phone_number string — a number ready to use
        fallback            — if no provisioned numbers exist for the user
        _ALL_CAPPED         — if all provisioned numbers have hit the daily cap (150 dials)
    """
    try:
        from app import app as _flask_app, db
        from models import ProvisionedNumber
        from datetime import datetime
        today = datetime.utcnow().date()
        with _flask_app.app_context():
            numbers = ProvisionedNumber.query.filter_by(user_id=user_id, status="active").all()
            if not numbers:
                logger.debug(f"No active provisioned numbers for user {user_id}, using fallback")
                return fallback

            # Reset stale daily counts (new day)
            for n in numbers:
                if n.last_dial_date is None or n.last_dial_date < today:
                    n.daily_dial_count = 0
                    n.last_dial_date = today

            # Find numbers under the daily cap
            available = [n for n in numbers if n.daily_dial_count < DAILY_DIAL_CAP]

            if not available:
                db.session.commit()
                logger.warning(
                    f"All {len(numbers)} number(s) for user {user_id} have hit the daily cap "
                    f"({DAILY_DIAL_CAP} dials). Campaign will pause until tomorrow."
                )
                return _ALL_CAPPED

            # Pick least-recently-used from available numbers
            available.sort(key=lambda n: (n.last_used_at is not None, n.last_used_at or datetime.min))
            chosen = available[0]
            chosen.last_used_at = datetime.utcnow()
            chosen.daily_dial_count += 1
            chosen.last_dial_date = today
            db.session.commit()
            logger.debug(
                f"LRU caller ID for user {user_id}: {chosen.phone_number} "
                f"({chosen.daily_dial_count}/{DAILY_DIAL_CAP} dials today)"
            )
            return chosen.phone_number
    except Exception as e:
        logger.warning(f"LRU number selection failed for user {user_id}, using fallback: {e}")
        return fallback


def start_dialer(user_id=None):
    """Start the background dialer thread for a specific user."""
    key = user_id or "global"
    with _worker_threads_lock:
        thread = _worker_threads.get(key)
        if thread and thread.is_alive():
            logger.warning(f"Dialer already running for user {key}")
            return
        thread = threading.Thread(target=_dial_worker, args=(user_id,), daemon=True)
        _worker_threads[key] = thread
        thread.start()
    logger.info(f"Dialer thread started for user {key}")


def _dial_worker(user_id=None):
    """
    Background worker that dials numbers based on campaign dial_mode.
    Sequential: one call at a time with configurable delay (1-10 minutes).
    Simultaneous: fires batch_size calls at once, waits, then next batch.
    """
    try:
        campaign = get_campaign(user_id=user_id)
        numbers = campaign.get("numbers", [])
        dial_mode = campaign.get("dial_mode", "sequential")
        batch_size = campaign.get("batch_size", 5)
        dial_delay = campaign.get("dial_delay", 2)
        from_number = campaign.get("from_number")

        if user_id is not None:
            max_lines = _get_user_max_lines(user_id)
            if batch_size > max_lines:
                logger.info(f"Capping batch_size from {batch_size} to user max_concurrent_lines={max_lines}")
                batch_size = max_lines

        logger.info(f"Dialer starting with {len(numbers)} numbers, mode={dial_mode}, batch_size={batch_size}, delay={dial_delay}min, from={from_number or 'default'}")

        if not numbers:
            logger.warning("No numbers to dial, campaign will complete")
            return

        if dial_mode == "simultaneous":
            _dial_simultaneous(numbers, batch_size, from_number, user_id=user_id)
        else:
            _dial_sequential(numbers, dial_delay, from_number, user_id=user_id)
    except Exception as e:
        logger.exception(f"Dialer worker crashed: {e}")
    finally:
        mark_campaign_complete(user_id=user_id)
        with _worker_threads_lock:
            key = user_id or "global"
            _worker_threads.pop(key, None)
        logger.info("Dialer finished processing all numbers")


def _dial_sequential(numbers, dial_delay=2, from_number=None, user_id=None):
    """Dial numbers one at a time, waiting for each call to complete then delay before the next.
    
    dial_delay: minutes to wait between calls (1-10).
    """
    delay_seconds = max(1, min(10, dial_delay)) * 60
    for i, number in enumerate(numbers):
        if not is_campaign_active(user_id=user_id):
            logger.info("Campaign stopped, dialer exiting")
            break

        if is_transfer_paused(user_id=user_id):
            logger.info("Campaign paused - live transfer in progress, waiting...")
            wait_if_transfer_paused(timeout=3600, user_id=user_id)
            logger.info("Transfer completed, campaign resuming")
            if not is_campaign_active(user_id=user_id):
                logger.info("Campaign stopped during transfer pause, exiting")
                break

        if is_campaign_paused(user_id=user_id):
            logger.info("Campaign paused by user, waiting for resume...")
            wait_if_campaign_paused(user_id=user_id)
            logger.info("Campaign resumed by user")
            if not is_campaign_active(user_id=user_id):
                logger.info("Campaign stopped while paused, exiting")
                break

        number = number.strip()
        if not number:
            continue

        if is_dnc(number, user_id=user_id):
            logger.info(f"Skipping DNC number [{i+1}/{len(numbers)}]: {number}")
            increment_dialed(user_id=user_id)
            continue

        is_valid, reason = is_valid_phone_number(number)
        if not is_valid:
            logger.info(f"Skipping invalid number [{i+1}/{len(numbers)}]: {number} ({reason})")
            log_invalid_number(number, reason, user_id=user_id)
            increment_dialed(user_id=user_id)
            continue

        if user_id is not None:
            max_lines = _get_user_max_lines(user_id)
            active = count_active_calls(user_id=user_id)
            if active >= max_lines:
                logger.warning(f"User {user_id} at max concurrent lines ({active}/{max_lines}), waiting before dialing {number}...")
                for _ in range(60):
                    time.sleep(1)
                    if not is_campaign_active(user_id=user_id):
                        break
                    if count_active_calls(user_id=user_id) < max_lines:
                        break
                if not is_campaign_active(user_id=user_id):
                    break
                active = count_active_calls(user_id=user_id)
                if active >= max_lines:
                    logger.warning(f"User {user_id} still at max lines ({active}/{max_lines}), skipping {number}")
                    increment_dialed(user_id=user_id)
                    continue

        logger.info(f"Dialing [{i+1}/{len(numbers)}]: {number}")
        try:
            effective_from = from_number
            if user_id is not None:
                effective_from = _get_lru_from_number(user_id, fallback=from_number)
                if effective_from is _ALL_CAPPED:
                    logger.warning(f"User {user_id}: all numbers at daily cap — stopping campaign for today.")
                    break
            call_control_id, call_error = make_call(number, from_number_override=effective_from)

            if call_control_id:
                complete_event = register_call_complete_event(call_control_id)
                create_call_state(call_control_id, number, user_id=user_id)
                logger.info(f"Call state created for {number}, waiting for call to complete...")
                complete_event.wait(timeout=120)
                logger.info(f"Call to {number} completed, moving to next")
            else:
                logger.error(f"Could not dial {number}: {call_error}")
                time.sleep(2)
        except Exception as e:
            logger.exception(f"Exception dialing {number}: {e}")
            time.sleep(2)

        increment_dialed(user_id=user_id)
        if i < len(numbers) - 1:
            logger.info(f"Waiting {dial_delay} minute(s) before next call...")
            for _ in range(delay_seconds):
                if not is_campaign_active(user_id=user_id):
                    break
                time.sleep(1)


def _dial_simultaneous(numbers, batch_size, from_number=None, user_id=None):
    """Dial numbers in batches of batch_size simultaneously."""
    total = len(numbers)
    i = 0

    while i < total:
        if not is_campaign_active(user_id=user_id):
            logger.info("Campaign stopped, dialer exiting")
            break

        if is_transfer_paused(user_id=user_id):
            logger.info("Campaign paused - live transfer in progress, waiting...")
            wait_if_transfer_paused(timeout=3600, user_id=user_id)
            logger.info("Transfer completed, campaign resuming")
            if not is_campaign_active(user_id=user_id):
                logger.info("Campaign stopped during transfer pause, exiting")
                break

        if is_campaign_paused(user_id=user_id):
            logger.info("Campaign paused by user, waiting for resume...")
            wait_if_campaign_paused(user_id=user_id)
            logger.info("Campaign resumed by user")
            if not is_campaign_active(user_id=user_id):
                logger.info("Campaign stopped while paused, exiting")
                break

        batch_end = min(i + batch_size, total)
        batch = numbers[i:batch_end]
        batch_nums = [n.strip() for n in batch if n.strip()]

        if not batch_nums:
            i = batch_end
            continue

        logger.info(f"Dialing batch [{i+1}-{batch_end}/{total}]: {len(batch_nums)} calls simultaneously")

        results = [None] * len(batch_nums)

        def _placed_wrapper(idx, number, from_number, user_id):
            results[idx] = _place_single_call(number, from_number=from_number, user_id=user_id)

        threads = []
        for idx, number in enumerate(batch_nums):
            t = threading.Thread(target=_placed_wrapper, args=(idx, number, from_number, user_id), daemon=True)
            threads.append(t)
            t.start()
            time.sleep(0.3)

        for t in threads:
            t.join(timeout=120)

        for placed in results:
            if placed is True or placed is None:
                increment_dialed(user_id=user_id)

        i = batch_end
        time.sleep(2)


def _place_single_call(number, from_number=None, user_id=None):
    """Place a single call and create its state entry.
    
    Returns True if the call was actually placed (so caller can decide whether
    to count it as dialed), False if skipped for any reason including line cap.
    """
    reserved = False
    try:
        if is_dnc(number, user_id=user_id):
            logger.info(f"Skipping DNC number: {number}")
            return False
        is_valid, reason = is_valid_phone_number(number)
        if not is_valid:
            logger.info(f"Skipping invalid number: {number} ({reason})")
            log_invalid_number(number, reason, user_id=user_id)
            return False

        max_lines = _get_user_max_lines(user_id) if user_id is not None else DEFAULT_MAX_LINES
        if user_id is not None:
            for _wait in range(30):
                if _try_reserve_slot(user_id, max_lines):
                    reserved = True
                    break
                logger.debug(f"User {user_id} at max lines, waiting for slot ({_wait+1}/30)...")
                time.sleep(2)
            if not reserved:
                active = count_active_calls(user_id=user_id)
                logger.warning(f"User {user_id} still at max concurrent lines ({active}/{max_lines}) after wait, skipping {number}")
                return False
        else:
            reserved = True

        effective_from = from_number
        if user_id is not None:
            effective_from = _get_lru_from_number(user_id, fallback=from_number)
            if effective_from is _ALL_CAPPED:
                logger.warning(f"User {user_id}: all numbers at daily cap in simultaneous mode, skipping {number}")
                if reserved:
                    _release_slot(user_id)
                return False

        call_control_id, call_error = make_call(number, from_number_override=effective_from)
        if call_control_id:
            create_call_state(call_control_id, number, user_id=user_id)
            logger.info(f"Call state created for {number}")
            _release_slot(user_id)
            return True
        else:
            logger.error(f"Could not dial {number}: {call_error}")
            _release_slot(user_id)
            return False
    except Exception as e:
        if reserved:
            _release_slot(user_id)
        logger.exception(f"Exception in single call to {number}: {e}")
        return False


def get_active_humana_voice(user_id):
    """Return the active Humana Voice config for a user (voice_id, style_speed, style_emotion)."""
    try:
        from humana_voice.models import HumanaVoice
        voice = HumanaVoice.query.filter_by(user_id=user_id, is_active=True).first()
        if voice:
            return {
                "voice_id": voice.voice_id,
                "style_speed": voice.style_speed,
                "style_emotion": voice.style_emotion,
            }
    except Exception:
        pass
    return None
