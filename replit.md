# Voice Blast - Voicemail Drop System

## Overview
A production-ready outbound voicemail drop web application branded as "Voice Blast". Built with Python + Flask and Telnyx Call Control API. Users upload voicemail audio and phone number lists via a modern dashboard. The system automatically dials numbers, detects answering machines, transfers human-answered calls, and drops voicemail messages.

## Project Architecture
- **app.py** - Main Flask application with routes, webhooks, campaign control
- **telnyx_client.py** - Wrapper around Telnyx Call Control REST API
- **call_manager.py** - Queue-based dialing system with rate limiting
- **storage.py** - In-memory call state management, campaign config, and persistent call history (JSON)
- **templates/index.html** - Dashboard UI with animated splash screen and polling
- **templates/login.html** - Password-protected login page
- **static/style.css** - Dual-theme CSS with cyan/teal gradient branding
- **static/videos/bg-loop-new.mp4** - Fiber optic video background
- **uploads/** - Uploaded audio files
- **logs/** - Call logs

## Key Decisions
- Event-driven architecture using Telnyx webhooks
- In-memory state management (no database needed)
- Background thread for rate-limited dialing with two modes: Sequential (1 call per 2 seconds) and Simultaneous (configurable batch size, 2–50 calls at once)
- Webhook handler returns 200 immediately, processes asynchronously
- AMD uses detect_words mode; voicemail audio plays immediately after machine detection
- Deployment target: VM (always-on) since webhooks need constant availability
- Auto-detection of webhook base URL from request headers (X-Forwarded-Host/Proto) for correct webhook delivery on both dev and published URLs
- Adaptive polling: 1s during active calls, 3s when idle
- All API fetch calls use credentials: "include" and X-Requested-With header for proper auth on published URL

## UI/UX
- Dual-theme system: Dark and Light modes with toggle button in header
- Theme persisted in localStorage ("vb_theme") with inline head script to prevent flash
- Cyan/teal (#06B6D4) + blue (#3B82F6) gradient accent palette
- Dark theme: deep navy backgrounds (#0B0F1A), subtle background glows
- Light theme: clean white/gray surfaces (#F8FAFC), no glows, adjusted contrast
- Smooth 0.35s transitions between themes on all elements
- Animated Voice Blast logo splash screen on page load with pulsing rings
- Card-based layout with real-time call status polling
- Full-width frosted glass header with inner content wrapper
- Realistic fiber optic video background
- Scroll-reveal animation on cards with staggered entrance
- Mouse-following glow effect on card hover
- Parallax scrolling on background video
- Clear Call Logs button (blocked during active campaigns)
- Download Report section with date presets (All Time, Today, This Week, This Month, Custom) and CSV export
- Persistent call history saved to logs/call_history.json for historical reporting across sessions
- Password protection using Flask sessions with APP_PASSWORD env var
- Responsive design with grid layout

## Environment Variables
- `TELNYX_API_KEY` - Telnyx API key
- `TELNYX_CONNECTION_ID` - Telnyx Call Control connection ID
- `TELNYX_FROM_NUMBER` - Caller ID phone number
- `PUBLIC_BASE_URL` - Public URL for webhooks and audio serving (auto-detected from request if available)
- `APP_PASSWORD` - Dashboard access password
- `SESSION_SECRET` - Flask session secret key

## Running
The app runs on port 5000 with `python app.py`.
