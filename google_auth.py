"""
google_auth.py - Google OAuth Blueprint for Flask application.
Handles Google OAuth login/signup flow with user creation and welcome emails.
"""

import os
import logging
import requests
from flask import Blueprint, redirect, url_for, session, request, flash
from flask_login import login_user, logout_user
from oauthlib.oauth2 import WebApplicationClient

from models import db, User

logger = logging.getLogger("voicemail_app")

# Check if Google OAuth is configured
google_oauth_available = False
google_oauth = Blueprint("google_oauth", __name__)

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Initialize OAuth client only if credentials are available
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    google_oauth_available = True
    client = WebApplicationClient(GOOGLE_CLIENT_ID)
    logger.info("Google OAuth configured and available")
else:
    logger.info("Google OAuth not configured - GOOGLE_OAUTH_CLIENT_ID or GOOGLE_OAUTH_CLIENT_SECRET missing")
    client = None


def get_google_provider_cfg():
    """Fetch Google's provider configuration."""
    try:
        response = requests.get(GOOGLE_DISCOVERY_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch Google provider config: {e}")
        return None


@google_oauth.route("/google_login")
def google_login():
    """Redirect user to Google OAuth consent screen."""
    if not google_oauth_available:
        flash("Google OAuth is not configured", "error")
        return redirect(url_for("login"))
    
    try:
        google_provider_cfg = get_google_provider_cfg()
        if not google_provider_cfg:
            raise ValueError("Could not fetch Google provider configuration")
        
        authorization_endpoint = google_provider_cfg.get("authorization_endpoint")
        if not authorization_endpoint:
            raise ValueError("No authorization endpoint in Google config")
        
        # Build redirect URI
        redirect_uri = request.base_url.replace("http://", "https://") + "/callback"
        
        # If we're in Replit dev environment, use the dev domain
        dev_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
        if dev_domain:
            redirect_uri = f"https://{dev_domain}/google_login/callback"
        
        # Generate authorization URL
        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=redirect_uri,
            scope=["openid", "email", "profile"],
            state=os.urandom(16).hex()  # Generate a random state for CSRF protection
        )
        
        # Store state in session for verification
        session["oauth_state"] = request_uri.split("state=")[1].split("&")[0] if "state=" in request_uri else None
        
        logger.info(f"Redirecting to Google OAuth: {authorization_endpoint}")
        return redirect(request_uri)
    
    except Exception as e:
        logger.error(f"Error in google_login: {e}")
        flash("An error occurred during login. Please try again.", "error")
        return redirect(url_for("login"))


@google_oauth.route("/google_login/callback")
def google_login_callback():
    """Handle Google OAuth callback and create/login user."""
    if not google_oauth_available:
        flash("Google OAuth is not configured", "error")
        return redirect(url_for("login"))
    
    try:
        # Get authorization code
        code = request.args.get("code")
        if not code:
            raise ValueError("No authorization code received from Google")
        
        # Verify state parameter
        state = request.args.get("state")
        session_state = session.get("oauth_state")
        if not state or state != session_state:
            logger.warning("OAuth state mismatch - potential CSRF attack")
            raise ValueError("Invalid state parameter")
        
        google_provider_cfg = get_google_provider_cfg()
        if not google_provider_cfg:
            raise ValueError("Could not fetch Google provider configuration")
        
        token_endpoint = google_provider_cfg.get("token_endpoint")
        if not token_endpoint:
            raise ValueError("No token endpoint in Google config")
        
        redirect_uri = request.base_url.replace("http://", "https://")
        
        # If we're in Replit dev environment, use the dev domain
        dev_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
        if dev_domain:
            redirect_uri = f"https://{dev_domain}/google_login/callback"
        
        # Exchange authorization code for tokens
        token_request_data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        
        token_response = requests.post(token_endpoint, data=token_request_data, timeout=10)
        token_response.raise_for_status()
        tokens = token_response.json()
        
        access_token = tokens.get("access_token")
        if not access_token:
            raise ValueError("No access token in token response")
        
        # Get user info from Google
        userinfo_endpoint = google_provider_cfg.get("userinfo_endpoint")
        if not userinfo_endpoint:
            raise ValueError("No userinfo endpoint in Google config")
        
        userinfo_response = requests.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        userinfo_response.raise_for_status()
        user_info = userinfo_response.json()
        
        google_id = user_info.get("sub")
        email = user_info.get("email")
        profile_name = user_info.get("name", "")
        profile_image_url = user_info.get("picture", "")
        
        if not google_id or not email:
            raise ValueError("Missing required user info from Google")
        
        logger.info(f"OAuth callback: google_id={google_id}, email={email}")
        
        # Check if user exists by google_id or email
        user = User.query.filter(
            (User.google_id == google_id) | (User.email == email)
        ).first()
        
        if not user:
            logger.warning(f"Google OAuth login rejected — no existing account for {email}")
            flash("No account found. Access is by invitation only.", "error")
            session.pop("oauth_state", None)
            return redirect(url_for("login"))

        if not getattr(user, 'is_active_account', True):
            logger.warning(f"Google OAuth login rejected — account deactivated for {email}")
            flash("Your account has been deactivated. Please contact the administrator.", "error")
            session.pop("oauth_state", None)
            return redirect(url_for("login"))

        user.google_id = google_id
        user.profile_name = profile_name or user.profile_name
        user.profile_image_url = profile_image_url or user.profile_image_url
        db.session.commit()
        logger.info(f"User logged in via Google OAuth: {email}")

        login_user(user)
        session.permanent = True
        session.pop("oauth_state", None)

        flash(f"Welcome back, {user.profile_name or user.email}!", "success")
        return redirect(url_for("dashboard"))
    
    except Exception as e:
        logger.error(f"Error in google_login_callback: {e}")
        flash(f"An error occurred during login: {str(e)}", "error")
        return redirect(url_for("login"))


@google_oauth.route("/logout")
def logout():
    """Log out the current user."""
    try:
        logout_user()
        logger.info("User logged out")
        flash("You have been logged out successfully.", "success")
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        flash("An error occurred during logout.", "error")
    
    return redirect(url_for("landing"))
