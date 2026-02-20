# Open Human - Intelligent Communication at Scale

## Overview
A production-ready outbound voicemail drop web application branded as "Open Human". Built with Python + Flask and Telnyx Call Control API. Users upload voicemail audio and phone number lists via a modern dashboard. The system automatically dials numbers, detects answering machines, transfers human-answered calls, and drops voicemail messages.

## Project Architecture
- **app.py** - Main Flask application with routes, webhooks, campaign control
- **telnyx_client.py** - Wrapper around Telnyx Call Control REST API
- **call_manager.py** - Queue-based dialing system with rate limiting
- **storage.py** - In-memory call state management, campaign config, and persistent call history (JSON)
- **templates/index.html** - Dashboard UI with animated splash screen and polling
- **templates/login.html** - Password-protected login page
- **static/style.css** - Dual-theme CSS with blue/cyan gradient branding
- **static/videos/bg-loop-new.mp4** - Fiber optic video background
- **personalized_vm.py** - Personalized voicemail system (CSV parsing, template rendering, human-like text processing, ElevenLabs TTS generation with full voice control)
- **gmail_client.py** - Gmail API integration via Replit connector for sending emails
- **daily_report.py** - Daily email report generator (hot leads, failed calls, voicemails)
- **uploads/** - Uploaded audio files
- **uploads/personalized/** - Generated personalized voicemail audio files
- **logs/** - Call logs
- **logs/pvm_state.json** - Personalized VM audio mapping (phone -> audio URL)

## Key Decisions
- Event-driven architecture using Telnyx webhooks
- In-memory state management (no database needed)
- Background thread for rate-limited dialing with two modes: Sequential (1 call per 2 seconds) and Simultaneous (configurable batch size, 2-50 calls at once)
- Campaign auto-pause on transfer: When a human-answered call is transferred, the campaign pauses (no new calls dialed) until the transfer target answers (call connected to human), then resumes automatically. Supports multiple concurrent transfers in simultaneous mode. Once transferred, duplicate call.answered/AMD events from Telnyx are ignored to prevent re-transfer loops.
- Transfer leg detection: Webhook events for the transfer leg (new call to transfer number) are identified by matching the destination number against the campaign's transfer number. Transfer legs are fully ignored for AMD/transfer processing to prevent re-transfer loops. Transfer leg answered -> status shows "Connected to a human, speaking now". Transfer leg hangup -> campaign resumes next number.
- Webhook handler returns 200 immediately, processes asynchronously
- AMD uses detect_words mode; voicemail audio plays immediately after machine detection
- Transfer caller ID uses Telnyx number (customer numbers require Telnyx account verification)
- Deployment target: VM (always-on) since webhooks need constant availability
- Auto-detection of webhook base URL from request headers (X-Forwarded-Host/Proto) for correct webhook delivery on both dev and published URLs
- Adaptive polling: 1s during active calls, 3s when idle
- All API fetch calls use credentials: "include" and X-Requested-With header for proper auth on published URL
- Real-time call transcription using Telnyx STT (Telnyx engine, $0.025/min), started on call.answered, stored per-call

## Voicemail Settings
- Default voicemail URL pre-loaded from Cloudinary
- Stored in logs/app_settings.json (file-based, consistent with existing architecture)
- Audio preview with built-in HTML5 player and duration display
- Campaign form audio is optional - falls back to stored voicemail URL automatically
- Test calls also use stored voicemail URL when no campaign is active
- Voicemail drop is always automatic for all machine-detected calls (no toggle)

## Branding & Design
- **Brand**: Open Human
- **Tagline**: Intelligent Communication at Scale
- **Logo**: Human silhouette (head + shoulders) with signal waves, purple-to-cyan gradient background, rounded square icon
- **Primary color**: Blue (#2563EB) - represents trust + technology
- **Secondary color**: Cyan (#06B6D4) - represents communication
- **Accent gradient**: 135deg from #2563EB to #06B6D4
- **Fonts**: Inter (UI), JetBrains Mono (monospace/data)
- **Favicon**: Brain emoji

## UI/UX
- Dual-theme system: Dark and Light modes with toggle button in header
- Theme persisted in localStorage ("vb_theme") with inline head script to prevent flash
- Blue (#2563EB) + cyan (#06B6D4) gradient accent palette
- Dark theme: deep navy backgrounds (#0B0F1A), subtle background glows
- Light theme: clean white/gray surfaces (#F8FAFC), no glows, adjusted contrast
- Smooth 0.35s transitions between themes on all elements
- Animated Open Human logo splash screen on page load with pulsing rings
- Card-based layout with real-time call status polling
- Left vertical sidebar with 8 feature buttons (Voicemail Settings, Test Dialer, Phone Numbers, Voicemail Audio, Transfer Number, Call Analytics, DNC List, Schedule) that toggle collapsible panels in the main content area
- Campaign Intelligence sidebar section (divider-separated): Call Analytics with Chart.js charts (AMD doughnut, hourly bar, daily line, hangup doughnut) and stat cards; DNC List with add/remove table UI; Campaign Scheduling with datetime picker, transfer number, phone list, and scheduled list view
- Operational Improvements section: Webhook Status Monitor (health indicator, event counts, recent events, errors); Campaign Templates (save/load campaign settings); Number Validation (validate phone numbers, detect invalid/duplicates/DNC, copy valid numbers)
- Quick Stats Banner: 4 stat cards at top (Total Calls, Hot Leads, Voicemails, Success Rate) with animated counters
- Campaign Progress Bar: shows dialed/total with animated fill during active campaigns
- Toast Notifications: slide-in toasts for campaign start/stop/complete, voicemail drops, log clearing
- Hot Lead Sound Alert: Web Audio API two-tone chime plays on human transfer detection
- Drag-and-Drop File Upload: styled drop zones for CSV phone lists and audio files with file name preview
- Campaign History Panel: sidebar panel showing daily campaign summaries (calls, leads, voicemails, success rate)
- Animated Counter Stats: smooth counting animation on stat value changes using cubic easing
- Sidebar collapses to icon-only at 900px, becomes horizontal bar at 600px
- Full-width frosted glass header with gradient logo text and glowing accent bottom line
- Realistic fiber optic video background
- Scroll-reveal animation on cards with staggered entrance
- Mouse-following glow effect on card hover
- Parallax scrolling on background video
- Clear Call Logs button (blocked during active campaigns)
- Download Report section with date presets (All Time, Today, This Week, This Month, Custom) and CSV export
- Persistent call history saved to logs/call_history.json for historical reporting across sessions
- Password protection using Flask sessions with APP_PASSWORD env var
- Responsive design with grid layout
- Detailed call status descriptions with color-coded badges (green=success, blue=in progress, yellow=warning, red=error)
- Status filter dropdown: All Calls, Successful, Failed, Warnings, In Progress
- Enhanced AMD result tracking: human, machine, fax, not_sure, timeout with distinct descriptions
- Comprehensive hangup cause mapping: busy, no answer, invalid number, rejected, network errors, etc.
- CSV export includes Status Description, AMD Result, and Hangup Cause columns
- Footer with brand info, product/company/legal links, social icons
- "Powered by Open Human" floating badge with pulse indicator
- Floating Notepad widget: chatbot-style FAB button ("N" logo) at bottom-right, expands to draggable/resizable rich text editor with toolbar (bold, italic, underline, strikethrough, font size, text color, highlight color, remove formatting, bullet/numbered lists, text alignment), content persisted in localStorage, character counter, download as text, clear all, minimize snaps back to bottom-right corner, touch drag support, Escape to close
- iPhone 17 Pro Max Live Dialer Widget: Realistic 3D iPhone in Natural Titanium/Silver color with brushed metal frame, side buttons (volume, power, silent switch), and camera module on back. 3D structure (iphone-3d-wrapper → iphone-3d-body → iphone-front + iphone-back). Shows real-time call status (number, timer, status badge, AMD result, live transcript). Minimize hides dialer and shows floating Apple logo (&#63743;) ball with physics. Click Apple ball to restore dialer. Alt+drag enables 360° rotation with momentum and snap-to-face. Drag handle for repositioning anywhere on screen. Integrated with existing pollStatus (no separate polling loop). Hot Lead Notification: When a call is transferred to a human, even if the dialer is minimized to ball form, it auto-expands with a dramatic fire/glow animation showing "HOT LEAD - Pick Up Now" with the caller's number, a countdown progress bar, then auto-minimizes back to ball after 3 seconds. Repeats on every new transfer. Tracked per call_id to avoid duplicate alerts.
- Floating Physics Balls: Notepad "N" ball (blue gradient) and iPhone Apple logo ball (silver metallic) share a physics engine with gravity, wall bouncing, drag-and-throw momentum, and ball-to-ball elastic collision. Balls bounce off each other realistically using impulse-based collision response. Both are draggable with throw physics. Collision uses proper elastic formula with restitution coefficient and random micro-perturbation for natural feel.
- Left sidebar: Icon-only strip (46px wide), no hover-expand, each icon has unique looping CSS animation (spin, ring, breathe, bounce, etc.), CSS tooltip on hover shows feature name, click opens corresponding panel with smooth scroll.

## Environment Variables
- `TELNYX_API_KEY` - Telnyx API key
- `TELNYX_CONNECTION_ID` - Telnyx Call Control connection ID
- `TELNYX_FROM_NUMBER` - Caller ID phone number
- `PUBLIC_BASE_URL` - Public URL for webhooks and audio serving (auto-detected from request if available)
- `APP_PASSWORD` - Dashboard access password
- `SESSION_SECRET` - Flask session secret key

## Running
The app runs on port 5000 with `python app.py`.
