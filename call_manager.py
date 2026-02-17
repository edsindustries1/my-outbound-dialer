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
)
from telnyx_client import make_call

logger = logging.getLogger("voicemail_app")

_worker_thread = None


def start_dialer():
    """Start the background dialer thread."""
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        logger.warning("Dialer already running")
        return

    _worker_thread = threading.Thread(target=_dial_worker, daemon=True)
    _worker_thread.start()
    logger.info("Dialer thread started")


def _dial_worker():
    """
    Background worker that dials numbers based on campaign dial_mode.
    Sequential: one call every 2 seconds.
    Simultaneous: fires batch_size calls at once, waits, then next batch.
    """
    campaign = get_campaign()
    numbers = campaign.get("numbers", [])
    dial_mode = campaign.get("dial_mode", "sequential")
    batch_size = campaign.get("batch_size", 5)

    logger.info(f"Dialer starting with {len(numbers)} numbers, mode={dial_mode}, batch_size={batch_size}")

    if dial_mode == "simultaneous":
        _dial_simultaneous(numbers, batch_size)
    else:
        _dial_sequential(numbers)

    mark_campaign_complete()
    logger.info("Dialer finished processing all numbers")


def _dial_sequential(numbers):
    """Dial numbers one at a time with 2 second delay between each."""
    for i, number in enumerate(numbers):
        if not is_campaign_active():
            logger.info("Campaign stopped, dialer exiting")
            break

        number = number.strip()
        if not number:
            continue

        logger.info(f"Dialing [{i+1}/{len(numbers)}]: {number}")
        _place_single_call(number)
        increment_dialed()
        time.sleep(2)


def _dial_simultaneous(numbers, batch_size):
    """Dial numbers in batches of batch_size simultaneously."""
    total = len(numbers)
    i = 0

    while i < total:
        if not is_campaign_active():
            logger.info("Campaign stopped, dialer exiting")
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
            t = threading.Thread(target=_place_single_call, args=(number,), daemon=True)
            threads.append(t)
            t.start()
            time.sleep(0.3)

        for t in threads:
            t.join(timeout=15)

        for _ in batch_nums:
            increment_dialed()

        i = batch_end
        time.sleep(2)


def _place_single_call(number):
    """Place a single call and create its state entry."""
    call_control_id = make_call(number)
    if call_control_id:
        create_call_state(call_control_id, number)
        logger.info(f"Call state created for {number}")
    else:
        logger.error(f"Could not dial {number}, skipping")
