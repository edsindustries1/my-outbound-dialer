# Voicemail Drop System

## Overview
A production-ready outbound voicemail drop web application using Python + Flask and Telnyx Call Control API. Users can upload voicemail audio and a list of phone numbers. The system automatically dials numbers and either transfers to a human or drops voicemail after beep detection.

## Project Architecture
- **app.py** - Main Flask application with routes, webhooks, campaign control
- **telnyx_client.py** - Wrapper around Telnyx Call Control REST API
- **call_manager.py** - Queue-based dialing system with rate limiting
- **storage.py** - In-memory call state management and campaign config
- **templates/index.html** - Dashboard UI with polling
- **static/style.css** - Dark theme styling
- **uploads/** - Uploaded audio files
- **logs/** - Call logs

## Key Decisions
- Event-driven architecture using Telnyx webhooks
- In-memory state management (no database needed)
- Background thread for rate-limited dialing (1 call per 2 seconds)
- Webhook handler returns 200 immediately, processes asynchronously

## Environment Variables
- `TELNYX_API_KEY` - Telnyx API key
- `TELNYX_CONNECTION_ID` - Telnyx Call Control connection ID
- `TELNYX_FROM_NUMBER` - Caller ID phone number
- `PUBLIC_BASE_URL` - Public URL for webhooks and audio serving

## Running
The app runs on port 5000 with `python app.py`.
