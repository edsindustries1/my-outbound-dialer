# Open Human - Intelligent Communication at Scale

## Overview
A production-ready outbound voicemail drop web application branded as "Open Human". Built with Python + Flask and Telnyx Call Control API. Users upload voicemail audio and phone number lists via a modern dashboard. The system automatically dials numbers, detects answering machines, transfers human-answered calls, and drops voicemail messages.

## Project Architecture
- **app.py** - Main Flask application with routes, webhooks, campaign control
- **telnyx_client.py** - Wrapper around Telnyx Call Control REST API
- **call_manager.py** - Queue-based dialing system with rate limiting
- **storage.py** - In-memory call state management, campaign config, and persistent call history (JSON)
- **templates/landing.html** - Public landing page (marketing/sales site)
- **templates/index.html** - Dashboard UI with animated splash screen and polling (auth-protected at /dashboard)
- **templates/login.html** - Password-protected login page
- **static/landing.css** - Landing page styles (hero, features, pricing, FAQ, footer, animations, visual effects)
- **static/style.css** - Dual-theme CSS with blue/cyan gradient branding (dashboard)
- **static/images/** - Landing page images (dashboard-preview, feature illustrations, hero-bg)
- **static/videos/bg-loop-new.mp4** - Fiber optic video background
- **personalized_vm.py** - Personalized voicemail system (CSV parsing, template rendering, advanced human-like speech processing with micro-hesitations/breath pauses/conversational smoothing, ElevenLabs TTS with SSML break tags for compatible models, full voice controls, multi-model support)
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
- Telnyx number management: Users can search, buy, and manage phone numbers directly from the dashboard. Auto-provisioning creates a Call Control Application with webhook URLs and assigns numbers automatically. Uses Telnyx API as source of truth (no local storage for number data). Per-campaign caller ID selection supported.

## Voicemail Settings
- Default voicemail URL pre-loaded from Cloudinary
- Stored in logs/app_settings.json (file-based, consistent with existing architecture)
- Audio preview with built-in HTML5 player and duration display
- Campaign form audio is optional - falls back to stored voicemail URL automatically
- Test calls also use stored voicemail URL when no campaign is active
- Voicemail drop is always automatic for all machine-detected calls (no toggle)

## Branding & Design
- **Brand**: Open Human
- **Tagline**: Power Sales Assistant
- **Primary color**: Google Blue (#1a73e8) - consistent across landing, login, and dashboard
- **Secondary blue**: #4285f4 (lighter accents)
- **Success**: Google Green (#0f9d58)
- **Error**: Google Red (#d93025)
- **Warning**: Google Yellow (#f9ab00)
- **Background**: Light gray (#f8f9fa)
- **Cards**: White with subtle shadows
- **Font**: Google Sans / Inter (UI), system sans-serif fallback
- **Favicon**: Brain emoji
- **Dark theme**: Google-style dark (#1f1f1f bg, #292929 surface, #8ab4f8 primary)

## Landing Page Visual Effects
- **Hero**: Dark immersive bg (#0a0a1a), 60-particle canvas with connecting lines, 3 floating gradient orbs, grid overlay, word-by-word title reveal with 3D rotation
- **Logo Trust Strip**: Infinite scroll marquee with 8 company logos, fade edges, pause-on-hover
- **Section Dividers**: Wavy SVG shapes between sections for smooth transitions
- **Animated Gradient Eyebrows**: Section labels with shifting gradient text animation
- **Featured Pricing Border**: Rotating conic gradient border using CSS @property
- **Glassmorphism Stats Bar**: Frosted glass effect with backdrop-filter
- **CTA Section Particles**: 40 floating sparkle particles on canvas, fade in/out lifecycle
- **Testimonial Auto-Play**: 5-second auto-advance carousel with pause-on-hover
- **Workflow Dash Animation**: Connecting line dash-draw triggered on scroll
- **Nav Progress Indicator**: Indigo gradient bar showing scroll progress at top of nav
- **Back-to-Top Button**: Floating indigo circle, appears after 600px scroll
- **Button Ripple Effects**: White circle expansion on hover for CTA buttons
- **Blog Card Shimmer**: Diagonal light sweep on hover
- **Bento Icon Highlight**: Icon bg changes to indigo on card hover
- **Footer Social Icons**: Twitter, LinkedIn, YouTube with hover lift effects
- **Lead Capture Modal**: Split-layout form with floating orb animation, success checkmark pop
- **Performance**: Scroll handler uses requestAnimationFrame throttling

## UI/UX - Google Ads Style SaaS Interface
- **Layout**: Fixed left sidebar (256px) + top bar (56px) + main content area
- **Navigation**: SPA-style with 8 pages: Dashboard, Campaigns, Voicemails, Contacts, Phone Numbers, Live Calls, Reports, Settings
- **Page switching**: navigateTo() function toggles page containers, updates sidebar active state and page title
- **Dual-theme system**: Light (default, Google Ads style) and Dark modes with toggle in top bar
- **Theme persisted**: localStorage ("vb_theme") with inline head script to prevent flash
- **Sidebar**: White bg, nav items with 22px SVG icons, active item has Google Blue text + light blue bg, collapsible via toggle button
- **Dashboard page**: 6 KPI metric cards (Total Calls, Connected, Voicemails, Hot Leads, Success Rate, Campaign Status) + Recent Activity table (last 20 calls auto-refreshing)
- **Campaigns page**: Active campaign status card with progress bar + Campaign History table + "+ New Campaign" button opens wizard overlay
- **Campaign Wizard**: 5-step overlay (Campaign Type, Calling Mode, Upload Contacts, Select Voicemail, Settings & Launch) with stepper navigation
- **Voicemails page**: Voicemail Settings card (saved URL, player, update) + Personalized Voicemail section with full PVM controls
- **Contacts page**: DNC List management + Number Validation tool
- **Phone Numbers page**: Search available numbers (by area code/region/type), purchase numbers with auto-provisioning (creates Call Control App, assigns webhooks), manage owned numbers (view, release), caller ID selection in campaign wizard
- **Live Calls page**: Full call logs table with status filter, search, clear logs, download report with date range picker
- **Reports page**: Call Analytics with Chart.js charts (AMD doughnut, hourly bar, daily line, hangup doughnut), stat cards, campaign history, email reports
- **Settings page**: Test Dialer, Webhook Monitor, Campaign Templates, Campaign Scheduler
- Quick Stats Banner: KPI cards with animated counters
- Campaign Progress Bar: shows dialed/total with animated fill
- Toast Notifications: slide-in toasts for campaign events
- Hot Lead Sound Alert: Web Audio API chime on human transfer
- Drag-and-Drop File Upload: styled drop zones for CSV and audio files
- Persistent call history saved to logs/call_history.json
- Password protection using Flask sessions with APP_PASSWORD env var
- Color-coded status badges (green=success, blue=in progress, amber=warning, red=error)
- Status filter dropdown: All, Successful, Failed, Warnings, In Progress
- CSV export with Status Description, AMD Result, and Hangup Cause columns
- Floating Notepad widget with rich text editor, physics ball interaction
- iPhone 17 Pro Max Live Dialer Widget with 3D rotation, live call status, Hot Lead notification
- Floating Physics Balls: Notepad + iPhone balls with gravity, collision, drag-throw physics

## Environment Variables
- `TELNYX_API_KEY` - Telnyx API key
- `TELNYX_CONNECTION_ID` - Telnyx Call Control connection ID
- `TELNYX_FROM_NUMBER` - Caller ID phone number
- `PUBLIC_BASE_URL` - Public URL for webhooks and audio serving (auto-detected from request if available)
- `APP_PASSWORD` - Dashboard access password
- `SESSION_SECRET` - Flask session secret key

## Running
The app runs on port 5000 with `python app.py`.
