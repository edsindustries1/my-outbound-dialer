# Voice Blast - Voicemail Drop System

## Overview
A production-ready outbound voicemail drop web application branded as "Voice Blast". Built with Python + Flask and Telnyx Call Control API. Users upload voicemail audio and phone number lists via a modern dashboard. The system automatically dials numbers, detects answering machines, transfers human-answered calls, and drops voicemail messages.

## Project Architecture
- **app.py** - Main Flask application with routes, webhooks, campaign control
- **telnyx_client.py** - Wrapper around Telnyx Call Control REST API
- **call_manager.py** - Queue-based dialing system with rate limiting
- **storage.py** - In-memory call state management and campaign config
- **templates/index.html** - Dashboard UI with animated splash screen and polling
- **static/style.css** - Dark purple gradient theme with animations
- **uploads/** - Uploaded audio files
- **logs/** - Call logs

## Key Decisions
- Event-driven architecture using Telnyx webhooks
- In-memory state management (no database needed)
- Background thread for rate-limited dialing (1 call per 2 seconds)
- Webhook handler returns 200 immediately, processes asynchronously
- AMD uses detect_words mode; voicemail audio plays immediately after machine detection
- Deployment target: VM (always-on) since webhooks need constant availability

## UI/UX
- Animated Voice Blast logo splash screen on page load with pulsing rings
- Dark purple gradient theme with card-based layout
- Real-time call status polling every 2 seconds
- Responsive design with grid layout

## Environment Variables
- `TELNYX_API_KEY` - Telnyx API key
- `TELNYX_CONNECTION_ID` - Telnyx Call Control connection ID
- `TELNYX_FROM_NUMBER` - Caller ID phone number
- `PUBLIC_BASE_URL` - Public URL for webhooks and audio serving

## Running
The app runs on port 5000 with `python app.py`.
