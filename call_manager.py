"""
call_manager.py - Queue-based dialing system with rate limiting.
Processes phone numbers from the campaign in a background thread.
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

# Background worker thread reference
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
    Background worker that dials numbers one at a time.
    Rate limited to 1 call every 2 seconds.
    Stops when campaign is no longer active.
    """
    campaign = get_campaign()
    numbers = campaign.get("numbers", [])

    logger.info(f"Dialer starting with {len(numbers)} numbers")

    for i, number in enumerate(numbers):
        if not is_campaign_active():
            logger.info("Campaign stopped, dialer exiting")
            break

        number = number.strip()
        if not number:
            continue

        logger.info(f"Dialing [{i+1}/{len(numbers)}]: {number}")

        call_control_id = make_call(number)

        if call_control_id:
            create_call_state(call_control_id, number)
            logger.info(f"Call state created for {number}")
        else:
            logger.error(f"Could not dial {number}, skipping")

        increment_dialed()
        time.sleep(2)

    mark_campaign_complete()
    logger.info("Dialer finished processing all numbers")
