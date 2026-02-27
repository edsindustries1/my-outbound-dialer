import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

supabase_available = bool(SUPABASE_URL and SUPABASE_ANON_KEY)

_client = None
_admin_client = None

def get_client() -> Client:
    global _client
    if _client is None and supabase_available:
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _client

def get_admin_client() -> Client:
    global _admin_client
    if _admin_client is None and SUPABASE_URL and SUPABASE_SERVICE_KEY:
        _admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _admin_client


def supabase_sign_up(email: str, password: str, name: str = None):
    client = get_client()
    if not client:
        return None, "Supabase not configured"
    try:
        options = {}
        if name:
            options["data"] = {"display_name": name}
        response = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": options if options else None,
        })
        if response.user:
            needs_confirm = response.session is None
            return {
                "user_id": response.user.id,
                "email": response.user.email,
                "needs_confirmation": needs_confirm,
            }, None
        return None, "Signup failed"
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Supabase signup error: {error_msg}")
        if "already registered" in error_msg.lower() or "already been registered" in error_msg.lower():
            return None, "An account with this email already exists"
        return None, error_msg


def supabase_send_otp(email: str):
    client = get_client()
    if not client:
        return False, "Supabase not configured"
    try:
        client.auth.sign_in_with_otp({
            "email": email,
            "options": {
                "should_create_user": True,
            }
        })
        return True, None
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Supabase OTP send error: {error_msg}")
        if "rate" in error_msg.lower() or "limit" in error_msg.lower():
            return False, "Please wait before requesting another code."
        return False, error_msg


def supabase_verify_otp(email: str, token: str):
    client = get_client()
    if not client:
        return None, "Supabase not configured"
    try:
        # Use the 6-digit email OTP flow configured in Supabase with Resend.
        # This matches: supabase.auth.verifyOtp({ email, token, type: 'signup' })
        response = client.auth.verify_otp({
            "email": email,
            "token": token,
            "type": "signup",
        })
        if response.user and response.session:
            return {
                "user_id": response.user.id,
                "email": response.user.email,
                "access_token": response.session.access_token,
            }, None
        return None, "Invalid or expired code"
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Supabase OTP verify error: {error_msg}")
        if "expired" in error_msg.lower() or "invalid" in error_msg.lower():
            return None, "Invalid or expired code. Please request a new one."
        return None, "Verification failed. Please try again."


def supabase_sign_in(email: str, password: str):
    client = get_client()
    if not client:
        return None, "Supabase not configured"
    try:
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        if response.user and response.session:
            return {
                "user_id": response.user.id,
                "email": response.user.email,
                "access_token": response.session.access_token,
            }, None
        return None, "Invalid email or password"
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Supabase login error: {error_msg}")
        if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
            return None, "Invalid email or password"
        if "not confirmed" in error_msg.lower() or "confirm" in error_msg.lower():
            return None, "Please confirm your email before logging in. Check your inbox."
        return None, "Invalid email or password"
