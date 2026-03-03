# Open Humana - Your Digital Employee Agency

## Overview
Open Humana is a production-ready, multi-user outbound voicemail drop web application branded as a "Digital Employee Agency." Users hire "Alex," a Digital BDR (Business Development Representative) that handles 500 dials a day, speaks 50 languages, and never takes a break. The system automates the dialing process, detects answering machines, transfers human-answered calls, and drops pre-recorded voicemail messages. Built with Python, Flask, PostgreSQL, and the Telnyx Call Control API, it ensures data isolation per user and supports various authentication methods including email/password and Google OAuth.

## User Preferences
I prefer clear and concise communication. For explanations, prioritize a high-level understanding of the system's purpose and functionality rather than deep dives into implementation specifics unless requested. I appreciate an iterative development approach and would like to be consulted before any major architectural changes or significant feature additions. Ensure that all user-specific data is securely isolated. When making changes, prioritize maintainability and scalability. Do not introduce new external dependencies without prior discussion and approval.

## System Architecture
The application is built on a Python Flask framework with PostgreSQL for data persistence and SQLAlchemy as the ORM. It employs an event-driven architecture heavily leveraging Telnyx webhooks for real-time call control.

**Key Architectural Decisions:**
- **Invite-Only Registration**: Open signup has been removed. New users can only be created by admin via the invite system at `/admin`. Admin sends an invite email to a user's email address, which contains a unique setup link. Users click the link at `/setup-account?token=<uuid>` to create their account (set username + password). The "Get Started" button on the landing page opens the lead capture modal, which sends a confirmation email to the lead and an admin notification email.
- **Admin Panel**: Admin panel at `/admin` (protected by `@admin_required`). Admin can invite users (with optional "free access by boss" flag), view all users, revoke/restore user access. Admin is determined by `ADMIN_EMAIL` env var match OR `role == 'admin'` in the User model. The original super-admin panel at `/super-admin` is retained for detailed user activity viewing.
- **Invitation Model**: `Invitation` model stores invite tokens (UUID), email, invited_by (FK), grant_free_access flag, used/used_at. Located in `models.py`.
- **Password Reset**: Forgot password flow at `/forgot-password` (enter email) and `/reset-password?token=<uuid>` (set new password). Reset tokens stored on User model with 1-hour expiry.
- **Multi-User & Data Isolation**: User data (campaigns, call history, settings, contacts) is isolated per user ID using dedicated storage directories and database scoping. Each new user gets a `UserInstance` record on account setup (via `ensure_user_instance`). Authentication is handled via Supabase Auth (email/password) with Flask-Login for session management. Google OAuth and admin APP_PASSWORD login are also supported. Falls back to local bcrypt auth if Supabase is not configured.
- **Session Management**: Sessions persist for 7 days (`PERMANENT_SESSION_LIFETIME`).
- **User Deactivation**: Admin can revoke user access (sets `is_active_account = False`). Deactivated users see "account deactivated" message on login. Flask-Login `is_active` property returns `is_active_account`.
- **Email Templates**: `invite_email.py` contains builders for invite emails, lead confirmation emails, and password reset emails. All use Resend API via `gmail_client.py`.
- **Call Management**: A queue-based dialing system with per-user, rate-limited background threads. It supports both sequential and simultaneous dialing modes.
- **Campaign Control**: Campaigns auto-pause on human transfer and resume automatically. Transfer leg detection prevents re-transfer loops.
- **Voicemail System**: Supports both default and personalized voicemails. Personalized voicemails utilize ElevenLabs TTS with SSML for advanced speech processing.
- **Dashboard & UI/UX**: Features a clean, black-and-white SaaS interface matching the homepage mockup. Fixed left sidebar and top bar, SPA-like navigation across 8 main pages (Dashboard, Campaigns, Voicemails, Contacts, Phone Numbers, Live Calls, Reports, Settings). Light theme only — white `#ffffff` surfaces, light gray `#f5f6f8` background, `#ecedf0` borders, dark charcoal `#1a1a2e` text/accents. Uses Inter font. No blue accent — strictly grayscale/B&W. Includes adaptive polling, toast notifications, and a quick stats banner.
- **Branding**: "Open Humana" branded as a "Digital Employee Agency." The landing page positions the product as hiring "Alex," a digital super-employee, with a Human vs. Digital comparison table, Superpowers section, and simplified $99/mo salary pricing. The landing page uses its own dark theme (landing.css). The dashboard uses a clean white/light gray color palette (style.css) with subtle shadows and borders.
- **Landing Page Dashboard Mockup**: The hero section includes a fully HTML-rendered dashboard mockup inside a browser frame (replaces a static image). Shows sidebar nav, KPI stat cards, campaign status, and recent activity feed. CSS classes prefixed with `.mock-*` in `static/landing.css`. Responsive with sidebar hidden on mobile.
- **Pricing Page**: Standalone pricing page at `/pricing` with three plans: Hire One Employee ($99/mo), Hire a Team ($399/mo), and Hire an Agency (custom/contact us). CSS in `static/pricing.css`, JS in `static/pricing.js`. Nav dropdown links directly to `/pricing`.
- **Checkout Page**: Professional split-layout checkout at `/billing?plan=starter` or `/billing?plan=business`. Left panel shows Open Humana branding, plan details, feature list, and time-saved metrics. Right panel has email field, card payment via PayPal Advanced Card Fields (with card-only button fallback), name on card, and country. Guest checkout creates user accounts automatically from email on successful payment. Template in `templates/billing.html`.
- **In-Dashboard Add Credits**: Users can add credits directly from the dashboard via "Add Credits" button. Opens a modal with preset amounts ($10, $25, $50, $100) or custom amount entry (minimum $10). PayPal buttons render inside the modal. After successful payment, credits are applied immediately and the balance updates in the UI. Backend validates amount from PayPal capture response (server-side), not client input.
- **Phone Number Intelligence**: Includes format validation, carrier lookup (opt-in), and caller health intelligence (score, risk levels, CNAM check) to assess number quality and spam risk.
- **Notification System**: Features a bell icon with swing animation for new notifications, unread counts, and deduplication logic.

**Technical Implementations & Features:**
- **Real-time Call Transcription**: Utilizes Telnyx STT for transcription, stored per call.
- **Telnyx Number Management**: Users can search, buy, and manage Telnyx numbers directly from the dashboard, with auto-provisioning of Call Control Applications.
- **Automated Line Provisioning**: Dashboard "Provision Line" button automates the entire flow: search local number -> purchase -> create per-user Call Control App -> assign. Shows friendly status: "Assigning Alex a local line..." -> "Alex is Ready." API endpoints: `/api/provision-line` (POST) and `/api/provision-status` (GET). Data stored in `provisioned_numbers` table.
- **Campaign Wizard**: A 5-step overlay for creating campaigns, including contact uploads and voicemail selection.
- **Reporting**: Call analytics with Chart.js charts and daily email reports for hot leads and failed calls.
- **Environment Management**: Auto-detection of webhook base URL for flexible deployment.
- **Frontend Interaction**: Features like drag-and-drop file uploads, floating Notepad widget, and an iPhone-style live dialer widget enhance user interaction.
- **Blog**: Full blog system at `/blog` with 6 articles on AI sales, compliance, and strategy. Features category filtering (server-side via query params), individual post pages at `/blog/<slug>` with Key Takeaways boxes, reading time estimates, structured H2/H3 content, and "More from the blog" related posts. Blog data in `blog_data.py`, templates in `templates/blog.html` and `templates/blog_post.html`, styles in `static/blog.css`. Uses white/light theme distinct from the dark subpage styling.
- **Sub-Pages**: About Us, Help Center (searchable FAQ accordion), TCPA Compliance (legal disclaimer), Privacy Policy, Terms of Service, and Contact Support pages. All share the landing page header/footer and use `static/pages.css` for sub-page-specific styles.
- **Alex AI Chatbot**: An interactive chat widget on the landing page powered by Pollinations AI (free, no API key required). Alex has a deep personality as a digital associate with a proven track record (real estate, solar, insurance case studies), emotional range, and lead conversion logic that provides direct links to pricing/registration. Features letter-by-letter text streaming, typing indicator, green online badge, 10-message conversation memory, and markdown link rendering. Backend in `alex_chat.py`, API at `/api/chat` and `/api/chat-alex`, widget CSS in `static/chat-widget.css`.
- **Welcome Email**: Styled as a formal job application/resume from Alex. Sent automatically when users request Alex's resume via the lead capture form. Template in `welcome_email.py`.
- **Lead Confirmation Email**: Professional thank-you email sent to leads who submit the demo request form. Template in `invite_email.py`.
- **Railway Deployment**: Configured via `railway.json` and `Procfile` for zero-touch GitHub-to-Railway deployment. Health check at `/api/health`. Global 500 error handler shows friendly "System Configuration in Progress" page.

## External Dependencies
- **Telnyx**: Primary API for Call Control, Number Lookup, and Speech-to-Text (STT).
- **PostgreSQL**: Relational database for all application data.
- **Supabase Auth**: User authentication with email/password. Configured via SUPABASE_URL, SUPABASE_ANON_KEY, and SUPABASE_SERVICE_ROLE_KEY environment variables.
- **Cloudinary**: Used for pre-loading default voicemail URLs.
- **Resend API**: Used for sending invite emails, lead confirmation emails, password reset emails, welcome emails, and daily reports. Configured via RESEND_API_KEY env var.
- **ElevenLabs TTS**: For generating personalized voicemail audio with advanced speech features.
- **Chart.js**: For rendering interactive charts in the reports section.
- **PayPal**: Payment processing for subscription plans. Configured via PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_MODE env vars.
- **Pollinations AI**: Free AI API for the Alex chatbot on the landing page.

## Key Files
- `app.py` — Main Flask application with all routes
- `models.py` — SQLAlchemy models (User, Invitation, UserAppData, UserInstance, ProvisionedNumber) + schema migration
- `gmail_client.py` — Resend API email sending
- `invite_email.py` — Email templates for invites, lead confirmations, password resets
- `welcome_email.py` — Alex resume/welcome email template
- `blog_data.py` — Blog article data
- `templates/admin.html` — Admin invite panel
- `templates/setup_account.html` — Account setup page (from invite link)
- `templates/forgot_password.html` — Forgot password form
- `templates/reset_password.html` — Reset password form
- `templates/login.html` — Login page (no signup, has forgot password link)
- `templates/billing.html` — Checkout page
- `templates/landing.html` — Landing page
