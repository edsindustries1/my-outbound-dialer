"""
telnyx_client.py - Wrapper around the Telnyx Call Control REST API.
All outbound call actions go through these functions.
"""

import os
import requests
import logging

logger = logging.getLogger("voicemail_app")

TELNYX_API_BASE = "https://api.telnyx.com/v2"

_resolved_connection_id = None
_webhook_base_url = None


def set_webhook_base_url(url):
    global _webhook_base_url
    _webhook_base_url = url.rstrip("/")
    logger.info(f"Webhook base URL set to: {_webhook_base_url}")


def _get_webhook_url():
    if _webhook_base_url:
        return _webhook_base_url + "/webhook"
    return os.environ.get("PUBLIC_BASE_URL", "").rstrip("/") + "/webhook"


def _headers():
    """Build authorization headers for Telnyx API."""
    api_key = os.environ.get("TELNYX_API_KEY", "")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _get_connection_id():
    """
    Get the correct connection ID. First tries the env var,
    then auto-detects from the Telnyx account if it fails.
    """
    global _resolved_connection_id
    if _resolved_connection_id:
        return _resolved_connection_id

    env_id = os.environ.get("TELNYX_CONNECTION_ID", "")
    if env_id:
        _resolved_connection_id = env_id
        return env_id

    try:
        resp = requests.get(
            f"{TELNYX_API_BASE}/call_control_applications",
            headers=_headers(),
            timeout=15,
        )
        if resp.status_code == 200:
            apps = resp.json().get("data", [])
            if apps:
                auto_id = apps[0].get("id", "")
                logger.info(f"Auto-detected connection_id: {auto_id}")
                _resolved_connection_id = auto_id
                return auto_id
    except Exception as e:
        logger.error(f"Failed to auto-detect connection_id: {e}")

    return env_id


def validate_connection_id():
    """
    Check if the stored connection_id is valid by comparing
    with what Telnyx actually has. Auto-corrects if needed.
    """
    global _resolved_connection_id
    env_id = os.environ.get("TELNYX_CONNECTION_ID", "")

    try:
        resp = requests.get(
            f"{TELNYX_API_BASE}/call_control_applications",
            headers=_headers(),
            timeout=15,
        )
        if resp.status_code == 200:
            apps = resp.json().get("data", [])
            valid_ids = [app.get("id", "") for app in apps]

            if env_id in valid_ids:
                _resolved_connection_id = env_id
                logger.info(f"Connection ID {env_id} is valid")
                return env_id

            if valid_ids:
                correct_id = valid_ids[0]
                logger.warning(f"Connection ID {env_id} invalid, using {correct_id}")
                _resolved_connection_id = correct_id
                return correct_id
    except Exception as e:
        logger.error(f"Could not validate connection_id: {e}")

    return env_id


def make_call(number, from_number_override=None):
    """
    Place an outbound call with answering machine detection enabled.
    Returns the call_control_id on success, or None on failure.
    """
    connection_id = _get_connection_id()
    from_number = from_number_override or os.environ.get("TELNYX_FROM_NUMBER", "")
    webhook_url = _get_webhook_url()

    number = _normalize_number(number)
    logger.info(f"Placing call to {number} with webhook_url: {webhook_url}")

    payload = {
        "connection_id": connection_id,
        "to": number,
        "from": from_number,
        "answering_machine_detection": "detect_words",
        "answering_machine_detection_config": {
            "after_greeting_silence_millis": 800,
            "between_words_silence_millis": 50,
            "greeting_duration_millis": 3500,
            "greeting_silence_duration_millis": 2000,
            "greeting_total_analysis_time_millis": 50000,
            "initial_silence_millis": 3500,
            "maximum_number_of_words": 5,
            "maximum_word_length_millis": 3500,
            "silence_threshold": 256,
            "total_analysis_time_millis": 5000,
        },
        "timeout_secs": 60,
        "time_limit_secs": 180,
        "webhook_url": webhook_url,
    }

    try:
        resp = requests.post(
            f"{TELNYX_API_BASE}/calls",
            json=payload,
            headers=_headers(),
            timeout=15,
        )
        if resp.status_code == 422 and "connection_id" in resp.text:
            logger.warning("Connection ID rejected, auto-correcting...")
            _resolved_connection_id_reset()
            correct_id = validate_connection_id()
            if correct_id and correct_id != connection_id:
                payload["connection_id"] = correct_id
                resp = requests.post(
                    f"{TELNYX_API_BASE}/calls",
                    json=payload,
                    headers=_headers(),
                    timeout=15,
                )
        if resp.status_code != 200:
            logger.error(f"Telnyx API error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        data = resp.json().get("data", {})
        call_control_id = data.get("call_control_id")
        logger.info(f"Call placed to {number}, call_control_id={call_control_id}")
        return call_control_id
    except Exception as e:
        logger.error(f"Failed to place call to {number}: {e}")
        return None


def _resolved_connection_id_reset():
    """Reset the cached connection ID so it gets re-fetched."""
    global _resolved_connection_id
    _resolved_connection_id = None


def _normalize_number(number):
    """Ensure phone number is in E.164 format with + prefix."""
    number = number.strip()
    has_plus = number.startswith("+")
    digits = "".join(c for c in number if c.isdigit())
    if has_plus:
        return "+" + digits
    return "+" + digits


def transfer_call(call_control_id, to_number, customer_number=None):
    """Transfer an active call to the specified number.
    If customer_number is provided, tries it as caller ID first.
    Falls back to the Telnyx number if Telnyx rejects the customer number."""
    telnyx_number = os.environ.get("TELNYX_FROM_NUMBER", "")
    if customer_number:
        from_display = _normalize_number(customer_number)
    else:
        from_display = telnyx_number
    webhook_url = _get_webhook_url()
    to_number = _normalize_number(to_number)
    payload = {
        "to": to_number,
        "from": from_display,
        "timeout_secs": 30,
        "webhook_url": webhook_url,
    }
    try:
        resp = requests.post(
            f"{TELNYX_API_BASE}/calls/{call_control_id}/actions/transfer",
            json=payload,
            headers=_headers(),
            timeout=15,
        )
        logger.info(f"Transfer API response {resp.status_code}: {resp.text[:500]}")
        if resp.status_code == 403 and customer_number and from_display != telnyx_number:
            logger.warning(f"Customer number {from_display} rejected by Telnyx, retrying with Telnyx number {telnyx_number}")
            payload["from"] = telnyx_number
            resp = requests.post(
                f"{TELNYX_API_BASE}/calls/{call_control_id}/actions/transfer",
                json=payload,
                headers=_headers(),
                timeout=15,
            )
            logger.info(f"Transfer retry response {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()
        logger.info(f"Call {call_control_id} transferred to {to_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to transfer call {call_control_id}: {e}")
        return False


def play_audio(call_control_id, audio_url):
    """Play an audio file on an active call."""
    payload = {"audio_url": audio_url}
    try:
        resp = requests.post(
            f"{TELNYX_API_BASE}/calls/{call_control_id}/actions/playback_start",
            json=payload,
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"Playing audio on call {call_control_id}: {audio_url}")
        return True
    except Exception as e:
        logger.error(f"Failed to play audio on call {call_control_id}: {e}")
        return False


def start_transcription(call_control_id):
    """Start real-time transcription on an active call."""
    payload = {
        "language": "en",
        "transcription_engine": "B",
        "transcription_tracks": "both",
    }
    try:
        resp = requests.post(
            f"{TELNYX_API_BASE}/calls/{call_control_id}/actions/transcription_start",
            json=payload,
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"Transcription started on call {call_control_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to start transcription on call {call_control_id}: {e}")
        return False


def start_recording(call_control_id):
    """Start recording on an active call."""
    payload = {
        "format": "mp3",
        "channels": "dual",
    }
    try:
        resp = requests.post(
            f"{TELNYX_API_BASE}/calls/{call_control_id}/actions/record_start",
            json=payload,
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"Recording started on call {call_control_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to start recording on call {call_control_id}: {e}")
        return False


def hangup_call(call_control_id):
    """Hang up an active call."""
    try:
        resp = requests.post(
            f"{TELNYX_API_BASE}/calls/{call_control_id}/actions/hangup",
            json={},
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"Hangup call {call_control_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to hangup call {call_control_id}: {e}")
        return False


def search_available_numbers(country_code="US", area_code=None, state=None, city=None, number_type="local", limit=20):
    params = {
        "filter[country_code]": country_code,
        "filter[features][]": "voice",
        "filter[limit]": min(limit, 40),
    }
    if area_code:
        params["filter[national_destination_code]"] = area_code
    if state:
        params["filter[administrative_area]"] = state
    if city:
        params["filter[locality]"] = city
    if number_type:
        params["filter[number_type]"] = number_type

    try:
        resp = requests.get(
            f"{TELNYX_API_BASE}/available_phone_numbers",
            params=params,
            headers=_headers(),
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        results = []
        for n in data:
            cost = n.get("cost_information", {})
            results.append({
                "phone_number": n.get("phone_number", ""),
                "region": n.get("region_information", [{}])[0].get("region_name", "") if n.get("region_information") else "",
                "rate_center": n.get("region_information", [{}])[0].get("rate_center", "") if n.get("region_information") else "",
                "monthly_cost": cost.get("monthly_cost", "1.00"),
                "upfront_cost": cost.get("upfront_cost", "1.00"),
                "currency": cost.get("currency", "USD"),
                "number_type": n.get("phone_number_type", "local"),
                "features": n.get("features", []),
            })
        logger.info(f"Found {len(results)} available numbers")
        return {"success": True, "numbers": results}
    except Exception as e:
        logger.error(f"Number search failed: {e}")
        return {"success": False, "error": str(e)}


def purchase_number(phone_number, connection_id=None):
    payload = {
        "phone_numbers": [{"phone_number": phone_number}],
    }
    if connection_id:
        payload["connection_id"] = connection_id

    try:
        resp = requests.post(
            f"{TELNYX_API_BASE}/number_orders",
            json=payload,
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        order = resp.json().get("data", {})
        logger.info(f"Number order created: {order.get('id')} for {phone_number}")
        return {
            "success": True,
            "order_id": order.get("id"),
            "status": order.get("status", "pending"),
            "phone_numbers": [pn.get("phone_number", "") for pn in order.get("phone_numbers", [])],
        }
    except requests.exceptions.HTTPError as e:
        error_body = ""
        try:
            error_body = e.response.json().get("errors", [{}])[0].get("detail", str(e))
        except Exception:
            error_body = str(e)
        logger.error(f"Number purchase failed: {error_body}")
        return {"success": False, "error": error_body}
    except Exception as e:
        logger.error(f"Number purchase failed: {e}")
        return {"success": False, "error": str(e)}


def create_call_control_app(app_name, webhook_url):
    payload = {
        "application_name": app_name,
        "webhook_event_url": webhook_url,
        "webhook_api_version": "2",
        "first_command_timeout": True,
        "first_command_timeout_secs": 30,
        "dtmf_type": "RFC 2833",
        "outbound": {
            "channel_limit": 50,
        },
    }
    try:
        resp = requests.post(
            f"{TELNYX_API_BASE}/call_control_applications",
            json=payload,
            headers=_headers(),
            timeout=20,
        )
        resp.raise_for_status()
        app_data = resp.json().get("data", {})
        logger.info(f"Call Control App created: {app_data.get('id')} - {app_name}")
        return {
            "success": True,
            "app_id": app_data.get("id"),
            "app_name": app_data.get("application_name"),
        }
    except requests.exceptions.HTTPError as e:
        error_body = ""
        try:
            error_body = e.response.json().get("errors", [{}])[0].get("detail", str(e))
        except Exception:
            error_body = str(e)
        logger.error(f"App creation failed: {error_body}")
        return {"success": False, "error": error_body}
    except Exception as e:
        logger.error(f"App creation failed: {e}")
        return {"success": False, "error": str(e)}


def assign_number_to_app(phone_number_id, connection_id):
    payload = {"connection_id": connection_id}
    try:
        resp = requests.patch(
            f"{TELNYX_API_BASE}/phone_numbers/{phone_number_id}",
            json=payload,
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        logger.info(f"Number {phone_number_id} assigned to app {connection_id}")
        return {"success": True, "phone_number": data.get("phone_number"), "connection_id": data.get("connection_id")}
    except Exception as e:
        logger.error(f"Failed to assign number: {e}")
        return {"success": False, "error": str(e)}


def list_owned_numbers():
    try:
        all_numbers = []
        page = 1
        while True:
            resp = requests.get(
                f"{TELNYX_API_BASE}/phone_numbers",
                params={"page[number]": page, "page[size]": 50},
                headers=_headers(),
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            numbers = data.get("data", [])
            if not numbers:
                break
            for n in numbers:
                all_numbers.append({
                    "id": n.get("id", ""),
                    "phone_number": n.get("phone_number", ""),
                    "status": n.get("status", ""),
                    "connection_id": n.get("connection_id", ""),
                    "connection_name": n.get("connection_name", ""),
                    "number_type": n.get("phone_number_type", ""),
                    "created_at": n.get("created_at", ""),
                })
            meta = data.get("meta", {})
            total_pages = meta.get("total_pages", 1)
            if page >= total_pages:
                break
            page += 1
        logger.info(f"Found {len(all_numbers)} owned numbers")
        return {"success": True, "numbers": all_numbers}
    except Exception as e:
        logger.error(f"Failed to list owned numbers: {e}")
        return {"success": False, "error": str(e)}


def release_number(phone_number_id):
    try:
        resp = requests.delete(
            f"{TELNYX_API_BASE}/phone_numbers/{phone_number_id}",
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"Number {phone_number_id} released")
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to release number: {e}")
        return {"success": False, "error": str(e)}


def list_call_control_apps():
    try:
        resp = requests.get(
            f"{TELNYX_API_BASE}/call_control_applications",
            params={"page[size]": 50},
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        apps = resp.json().get("data", [])
        results = []
        for a in apps:
            results.append({
                "id": a.get("id", ""),
                "name": a.get("application_name", ""),
                "webhook_url": a.get("webhook_event_url", ""),
                "created_at": a.get("created_at", ""),
            })
        return {"success": True, "apps": results}
    except Exception as e:
        logger.error(f"Failed to list apps: {e}")
        return {"success": False, "error": str(e)}


def lookup_number(phone_number):
    """
    Perform a Telnyx Number Lookup to check carrier info and line status.
    Returns carrier name, line type, and whether the number is reachable.
    Cost: $0.0015 per lookup.
    """
    normalized = _normalize_number(phone_number)
    try:
        resp = requests.get(
            f"{TELNYX_API_BASE}/number_lookup/{normalized}",
            params={"type": "carrier"},
            headers=_headers(),
            timeout=15,
        )
        if resp.status_code == 404:
            return {
                "valid": False,
                "phone_number": normalized,
                "carrier": None,
                "line_type": None,
                "reason": "Number not found - likely disconnected or invalid",
            }
        if resp.status_code == 422:
            return {
                "valid": False,
                "phone_number": normalized,
                "carrier": None,
                "line_type": None,
                "reason": "Invalid phone number format",
            }
        resp.raise_for_status()
        data = resp.json().get("data", {})
        carrier = data.get("carrier", {})
        carrier_name = carrier.get("name", "")
        line_type = carrier.get("type", "")
        mobile_country_code = carrier.get("mobile_country_code", "")
        mobile_network_code = carrier.get("mobile_network_code", "")

        is_valid = True
        reason = "Reachable"

        if not carrier_name and not line_type:
            is_valid = False
            reason = "No carrier data - number may be disconnected"

        return {
            "valid": is_valid,
            "phone_number": data.get("phone_number", normalized),
            "carrier": carrier_name,
            "line_type": line_type,
            "mobile_country_code": mobile_country_code,
            "mobile_network_code": mobile_network_code,
            "reason": reason,
        }
    except requests.exceptions.HTTPError as e:
        error_msg = str(e)
        try:
            error_msg = e.response.json().get("errors", [{}])[0].get("detail", str(e))
        except Exception:
            pass
        logger.error(f"Number lookup failed for {normalized}: {error_msg}")
        return {
            "valid": None,
            "phone_number": normalized,
            "carrier": None,
            "line_type": None,
            "reason": f"Lookup failed: {error_msg}",
        }
    except Exception as e:
        logger.error(f"Number lookup failed for {normalized}: {e}")
        return {
            "valid": None,
            "phone_number": normalized,
            "carrier": None,
            "line_type": None,
            "reason": f"Lookup error: {str(e)}",
        }


def lookup_numbers_batch(phone_numbers, max_concurrent=5):
    """
    Validate a batch of phone numbers using Telnyx Number Lookup.
    Returns dict with 'reachable', 'unreachable', and 'unknown' lists.
    Rate-limits to max_concurrent lookups at a time.
    """
    import concurrent.futures
    import time as _time

    results = {"reachable": [], "unreachable": [], "unknown": [], "total": len(phone_numbers)}

    def _lookup_single(number):
        result = lookup_number(number)
        _time.sleep(0.1)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {executor.submit(_lookup_single, num): num for num in phone_numbers}
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result["valid"] is True:
                    results["reachable"].append(result)
                elif result["valid"] is False:
                    results["unreachable"].append(result)
                else:
                    results["unknown"].append(result)
            except Exception as e:
                num = futures[future]
                logger.error(f"Lookup thread error for {num}: {e}")
                results["unknown"].append({
                    "valid": None,
                    "phone_number": num,
                    "carrier": None,
                    "line_type": None,
                    "reason": f"Thread error: {str(e)}",
                })

    logger.info(f"Batch lookup complete: {len(results['reachable'])} reachable, {len(results['unreachable'])} unreachable, {len(results['unknown'])} unknown out of {results['total']}")
    return results


def get_number_order_status(order_id):
    try:
        resp = requests.get(
            f"{TELNYX_API_BASE}/number_orders/{order_id}",
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        order = resp.json().get("data", {})
        return {
            "success": True,
            "status": order.get("status", ""),
            "phone_numbers": [
                {
                    "phone_number": pn.get("phone_number", ""),
                    "status": pn.get("status", ""),
                }
                for pn in order.get("phone_numbers", [])
            ],
        }
    except Exception as e:
        logger.error(f"Failed to check order status: {e}")
        return {"success": False, "error": str(e)}
