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
)
from telnyx_client import make_call

logger = logging.getLogger("voicemail_app")

_worker_threads = {}
_worker_threads_lock = threading.Lock()


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
    campaign = get_campaign(user_id=user_id)
    numbers = campaign.get("numbers", [])
    dial_mode = campaign.get("dial_mode", "sequential")
    batch_size = campaign.get("batch_size", 5)
    dial_delay = campaign.get("dial_delay", 2)
    from_number = campaign.get("from_number")

    logger.info(f"Dialer starting with {len(numbers)} numbers, mode={dial_mode}, batch_size={batch_size}, delay={dial_delay}min, from={from_number or 'default'}")

    if dial_mode == "simultaneous":
        _dial_simultaneous(numbers, batch_size, from_number, user_id=user_id)
    else:
        _dial_sequential(numbers, dial_delay, from_number, user_id=user_id)

    mark_campaign_complete(user_id=user_id)
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

        logger.info(f"Dialing [{i+1}/{len(numbers)}]: {number}")
        call_control_id, call_error = make_call(number, from_number_override=from_number)

        if call_control_id:
            complete_event = register_call_complete_event(call_control_id)
            create_call_state(call_control_id, number, user_id=user_id)
            logger.info(f"Call state created for {number}, waiting for call to complete...")
            complete_event.wait(timeout=120)
            logger.info(f"Call to {number} completed, moving to next")
        else:
            logger.error(f"Could not dial {number}: {call_error}")

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

        threads = []
        for number in batch_nums:
            t = threading.Thread(target=_place_single_call, args=(number, from_number), kwargs={"user_id": user_id}, daemon=True)
            threads.append(t)
            t.start()
            time.sleep(0.3)

        for t in threads:
            t.join(timeout=15)

        for _ in batch_nums:
            increment_dialed(user_id=user_id)

        i = batch_end
        time.sleep(2)


def _place_single_call(number, from_number=None, user_id=None):
    """Place a single call and create its state entry."""
    if is_dnc(number, user_id=user_id):
        logger.info(f"Skipping DNC number: {number}")
        return
    is_valid, reason = is_valid_phone_number(number)
    if not is_valid:
        logger.info(f"Skipping invalid number: {number} ({reason})")
        log_invalid_number(number, reason, user_id=user_id)
        return
    call_control_id, call_error = make_call(number, from_number_override=from_number)
    if call_control_id:
        create_call_state(call_control_id, number, user_id=user_id)
        logger.info(f"Call state created for {number}")
    else:
        logger.error(f"Could not dial {number}: {call_error}")
