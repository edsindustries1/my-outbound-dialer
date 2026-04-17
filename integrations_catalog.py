"""
Public-facing catalog of every integration Open Humana ships, plus the
step-by-step setup instructions used by the /integrations marketing pages.

This is decoupled from the backend `integrations.py` module which holds the
runtime config for connectors that are wired to user accounts. The catalog
below powers the public marketing/help pages only.
"""

NATIVE = "native"
ZAPIER = "zapier"
SOON = "soon"

TIER_LABELS = {
    NATIVE: "Native integration",
    ZAPIER: "Available via Zapier & Make",
    SOON: "Coming soon",
}

INTEGRATIONS = [
    # ---------------- NATIVE (12) ----------------
    {
        "slug": "hubspot",
        "name": "HubSpot",
        "tier": NATIVE,
        "logo": "integrations/hubspot.svg",
        "tagline": "Two-way contact sync, auto-logged calls, and pipeline updates.",
        "summary": (
            "Open Humana writes every completed call to the matching HubSpot "
            "contact as an Engagement, with the full transcript, recording link, "
            "outcome, and a HubSpot timeline activity. Inbound contact list "
            "changes also pull into your campaign queue automatically."
        ),
        "what_youll_need": [
            "A HubSpot account (Starter, Professional, or Enterprise).",
            "A HubSpot Private App access token with the scopes "
            "`crm.objects.contacts.read`, `crm.objects.contacts.write`, and "
            "`timeline`.",
        ],
        "steps": [
            ("Open your HubSpot Private App settings",
             "In HubSpot, go to **Settings → Integrations → Private Apps**, then "
             "click **Create a private app**. Name it `Open Humana`."),
            ("Grant the required scopes",
             "Under the **Scopes** tab, enable `crm.objects.contacts.read`, "
             "`crm.objects.contacts.write`, and `timeline`. Save the app and "
             "copy the generated access token."),
            ("Paste the token into Open Humana",
             "Inside Open Humana, go to **Settings → Integrations → HubSpot**, "
             "paste the access token, and click **Connect**."),
            ("Run the test sync",
             "Click **Send test event**. A sample call activity will be "
             "written to a test contact in your HubSpot account so you can "
             "confirm the wire-up."),
            ("Turn on auto-logging",
             "Toggle **Log every completed call** to ON. From here on, every "
             "voicemail drop, transfer, and connected conversation is logged "
             "to the matching HubSpot contact in real time."),
        ],
    },
    {
        "slug": "salesforce",
        "name": "Salesforce",
        "tier": NATIVE,
        "logo": "integrations/salesforce.svg",
        "tagline": "Enterprise-grade Salesforce sync with custom field mapping.",
        "summary": (
            "Push every Open Humana call into Salesforce as a Task or custom "
            "Activity object, complete with disposition, duration, transcript, "
            "and recording URL. Map any Open Humana field to any Salesforce "
            "field — no Apex required."
        ),
        "what_youll_need": [
            "Salesforce Enterprise, Unlimited, or Performance edition.",
            "A Connected App with OAuth 2.0 and the `api` and `refresh_token` "
            "scopes (your Salesforce admin can create one in under 5 minutes).",
        ],
        "steps": [
            ("Create a Connected App in Salesforce",
             "In Salesforce Setup, search for **App Manager → New Connected "
             "App**. Enable OAuth Settings, set the callback URL to "
             "`https://openhumana.com/api/integrations/salesforce/callback`, "
             "and grant the `api` and `refresh_token (offline_access)` scopes."),
            ("Copy your Consumer Key and Secret",
             "Once Salesforce finishes provisioning the app (allow ~10 minutes), "
             "open it and copy the **Consumer Key** and **Consumer Secret**."),
            ("Authenticate from Open Humana",
             "In Open Humana, open **Settings → Integrations → Salesforce**, "
             "paste the Consumer Key/Secret, and click **Connect**. You'll be "
             "bounced through Salesforce's OAuth screen — approve access and "
             "you'll land back on the integrations page."),
            ("Map your fields",
             "Drag-and-drop the Open Humana call fields (outcome, transcript, "
             "recording URL, duration) onto the matching Salesforce Task or "
             "custom Activity fields."),
            ("Activate the sync",
             "Flip the **Sync completed calls** switch. Open Humana will start "
             "writing to Salesforce within 60 seconds of every call ending."),
        ],
    },
    {
        "slug": "gohighlevel",
        "name": "GoHighLevel",
        "tier": NATIVE,
        "logo": None,  # uses the inline GHL SVG mark
        "tagline": "Drop calls and contacts straight into your GHL sub-accounts.",
        "summary": (
            "Built for agencies. Connect a single GoHighLevel agency account "
            "and Open Humana will route call activity to the correct sub-"
            "account based on the campaign tag, including SMS follow-ups."
        ),
        "what_youll_need": [
            "A GoHighLevel Agency account (any plan).",
            "A GHL API key from **Settings → Business Profile → API Key**.",
        ],
        "steps": [
            ("Generate a GoHighLevel API key",
             "In GoHighLevel, go to **Agency Settings → API Key** and click "
             "**Generate**. Copy the key."),
            ("Paste it into Open Humana",
             "In Open Humana, open **Settings → Integrations → GoHighLevel**, "
             "paste the API key, and click **Connect**."),
            ("Pick the destination sub-accounts",
             "Open Humana will list every sub-account on your GHL agency. Tick "
             "the ones you want call activity to flow into."),
            ("Map campaigns to sub-accounts",
             "For each Open Humana campaign, choose which GHL sub-account it "
             "should write to. You can change this any time."),
            ("Test the wire-up",
             "Click **Send test contact**. A sample contact + activity will "
             "appear in the chosen sub-account within seconds."),
        ],
    },
    {
        "slug": "pipedrive",
        "name": "Pipedrive",
        "tier": NATIVE,
        "logo": "integrations/pipedrive.svg",
        "tagline": "Auto-create activities and notes against the matching Person.",
        "summary": (
            "Every Open Humana call lands inside the matching Pipedrive Person "
            "as a logged Call activity, with disposition, transcript, and "
            "recording link attached as a Note."
        ),
        "what_youll_need": [
            "A Pipedrive account on any plan.",
            "Your personal API token from **Personal Preferences → API**.",
        ],
        "steps": [
            ("Find your Pipedrive API token",
             "In Pipedrive, click your profile picture → **Personal "
             "Preferences → API** and copy the token."),
            ("Connect it to Open Humana",
             "In Open Humana, open **Settings → Integrations → Pipedrive**, "
             "paste the token, and click **Connect**."),
            ("Pick the activity type",
             "Choose which Pipedrive activity type Open Humana should use for "
             "logged calls — usually `Call`, but custom types are supported."),
            ("Toggle on auto-logging",
             "Flip **Log completed calls** to ON. The next call you run will "
             "appear in Pipedrive within 30 seconds."),
        ],
    },
    {
        "slug": "zoho-crm",
        "name": "Zoho CRM",
        "tier": NATIVE,
        "logo": "integrations/zoho.svg",
        "tagline": "Zoho Calls module sync with full transcript attachments.",
        "summary": (
            "Open Humana writes each call into the Zoho CRM Calls module, "
            "linked to the matching Contact or Lead, with the full transcript "
            "stored as a related Note."
        ),
        "what_youll_need": [
            "A Zoho CRM account (Standard, Professional, or above).",
            "Self-Client OAuth credentials from the "
            "[Zoho API Console](https://api-console.zoho.com).",
        ],
        "steps": [
            ("Create a Self-Client in the Zoho API Console",
             "Visit https://api-console.zoho.com, click **Add Client → "
             "Self-Client**, and copy the Client ID and Client Secret."),
            ("Generate a grant token",
             "On the same screen click **Generate Code**. Use the scope "
             "`ZohoCRM.modules.ALL` and copy the resulting token (it expires "
             "in 10 minutes — paste it quickly)."),
            ("Paste everything into Open Humana",
             "In Open Humana, open **Settings → Integrations → Zoho CRM**, "
             "paste the Client ID, Client Secret, and grant token, then click "
             "**Connect**. Open Humana will exchange the grant for a refresh "
             "token automatically."),
            ("Pick your data centre",
             "Choose `.com`, `.eu`, `.in`, or `.com.au` to match your Zoho "
             "account region."),
            ("Run the test sync",
             "Click **Send test call**. A sample call record will appear in "
             "the Zoho Calls module within seconds."),
        ],
    },
    {
        "slug": "close",
        "name": "Close",
        "tier": NATIVE,
        "logo": "integrations/close.svg",
        "tagline": "Logs every call as a Close.com Activity, instantly.",
        "summary": (
            "Open Humana writes each completed call straight into Close as a "
            "Call activity, complete with outcome, duration, transcript, and "
            "recording URL — attached to the matching Lead."
        ),
        "what_youll_need": [
            "A Close.com account on any paid plan.",
            "A Close API key from **Settings → API Keys**.",
        ],
        "steps": [
            ("Create a Close API key",
             "In Close, go to **Settings → API Keys → New API Key** and copy "
             "the generated key."),
            ("Paste it into Open Humana",
             "In Open Humana, open **Settings → Integrations → Close**, paste "
             "the key, and click **Connect**."),
            ("Pick the call outcome map",
             "Map each Open Humana outcome (`transferred`, `voicemail`, "
             "`connected`, `no-answer`) to the matching Close call result."),
            ("Activate the sync",
             "Flip **Auto-log calls** to ON. New activity will start "
             "appearing on the matching Close Lead immediately."),
        ],
    },
    {
        "slug": "google-sheets",
        "name": "Google Sheets",
        "tier": NATIVE,
        "logo": "integrations/googlesheets.svg",
        "tagline": "Live-append every call to a sheet — zero spreadsheets to maintain.",
        "summary": (
            "The simplest way to get Open Humana data anywhere. Pick a Google "
            "Sheet and Open Humana will append a row for every completed call "
            "with the contact details, outcome, duration, transcript, and "
            "recording link."
        ),
        "what_youll_need": [
            "A Google account.",
            "A Google Sheet you've shared with the Open Humana service email "
            "(shown to you on the connect screen).",
        ],
        "steps": [
            ("Create a destination Google Sheet",
             "Make a new sheet — Open Humana will auto-add the header row on "
             "first sync, so it can be totally empty."),
            ("Click Connect Google in Open Humana",
             "In Open Humana, open **Settings → Integrations → Google "
             "Sheets** and click **Connect Google**. Approve the OAuth scope "
             "for `spreadsheets`."),
            ("Pick your sheet and tab",
             "Open Humana will list every sheet on your Drive. Choose the "
             "sheet and the worksheet tab where rows should land."),
            ("(Optional) Customize columns",
             "Drag column headers to reorder or hide the fields you don't "
             "want logged."),
            ("Done — start running calls",
             "Every completed call now appends a row in real time. Open Humana "
             "writes a recording URL and a transcript link for each row."),
        ],
    },
    {
        "slug": "slack",
        "name": "Slack",
        "tier": NATIVE,
        "logo": "integrations/slack.svg",
        "tagline": "Get a Slack ping the second a prospect transfers in.",
        "summary": (
            "Pick a Slack channel and Open Humana will post a rich message for "
            "every transferred call — name, company, transfer reason, and a "
            "click-to-call link to your phone."
        ),
        "what_youll_need": [
            "A Slack workspace where you can install apps.",
            "Permission to add the Open Humana app (workspace admin or app "
            "approval).",
        ],
        "steps": [
            ("Click Add to Slack in Open Humana",
             "In Open Humana, open **Settings → Integrations → Slack** and "
             "click the **Add to Slack** button."),
            ("Approve the workspace install",
             "Slack will ask you to confirm the workspace and channel scope. "
             "Approve and you'll be sent back to Open Humana."),
            ("Pick the destination channel",
             "Choose any channel the Open Humana bot has been invited to "
             "(invite it with `/invite @OpenHumana` if you don't see it)."),
            ("Pick which events to post",
             "Decide whether you want pings for transfers only, or also for "
             "voicemail drops, no-answers, and connected calls."),
            ("Run a test post",
             "Click **Send test message**. A sample call notification will "
             "land in your chosen channel within seconds."),
        ],
    },
    {
        "slug": "salesloft",
        "name": "Salesloft",
        "tier": NATIVE,
        "logo": "integrations/salesloft.svg",
        "tagline": "Auto-log calls to the right Cadence step in Salesloft.",
        "summary": (
            "Open Humana logs every call as a Salesloft Call activity on the "
            "matching Person, advances the Cadence step automatically, and "
            "syncs disposition + recording URL."
        ),
        "what_youll_need": [
            "A Salesloft account with API access (Team plan or above).",
            "A Salesloft API key from **Settings → API & Webhooks**.",
        ],
        "steps": [
            ("Generate a Salesloft API key",
             "In Salesloft go to **Your Profile → Settings → API & Webhooks** "
             "and click **Create New Key**."),
            ("Paste it into Open Humana",
             "In Open Humana, open **Settings → Integrations → Salesloft**, "
             "paste the key, and click **Connect**."),
            ("Map outcomes to Salesloft dispositions",
             "Pair each Open Humana outcome to the matching Salesloft "
             "disposition + sentiment."),
            ("Choose Cadence behaviour",
             "Decide whether Open Humana should mark the current Cadence step "
             "complete on every successful call (recommended)."),
            ("Activate sync",
             "Flip **Auto-log to Salesloft** to ON."),
        ],
    },
    {
        "slug": "outreach",
        "name": "Outreach",
        "tier": NATIVE,
        "logo": "integrations/outreach.svg",
        "tagline": "Native Outreach Sequence task completion + call logging.",
        "summary": (
            "Open Humana writes every call into Outreach as a Call activity "
            "and (optionally) marks the matching Sequence task complete, so "
            "your reps' Outreach inbox stays in sync with reality."
        ),
        "what_youll_need": [
            "An Outreach account with API access.",
            "An OAuth Application registered in the "
            "[Outreach Developer Portal](https://app.outreach.io/oauth/applications).",
        ],
        "steps": [
            ("Register an Outreach OAuth app",
             "In the Outreach Developer Portal, click **New App**. Set the "
             "redirect URI to `https://openhumana.com/api/integrations/"
             "outreach/callback` and grant the `calls.all` and "
             "`sequenceStates.all` scopes."),
            ("Copy your Client ID and Secret",
             "Open the new app and copy the Client ID and Client Secret."),
            ("Authenticate inside Open Humana",
             "In Open Humana, open **Settings → Integrations → Outreach**, "
             "paste the credentials, and click **Connect**. You'll be sent "
             "through the Outreach OAuth flow."),
            ("Choose Sequence task behaviour",
             "Decide whether Open Humana should auto-complete the matching "
             "Sequence task when a call ends successfully."),
            ("Run the test event",
             "Click **Send test call** to confirm the wire-up. A sample call "
             "will appear on the test prospect."),
        ],
    },
    {
        "slug": "outbound-webhooks",
        "name": "Outbound Webhooks",
        "tier": NATIVE,
        "logo": None,  # uses the inline webhooks SVG mark
        "tagline": "Fire a signed POST to any URL on every call event.",
        "summary": (
            "The escape hatch. If the system you want to integrate with isn't "
            "on this page, point Open Humana at any HTTPS URL and we'll fire a "
            "signed JSON POST for every call event you choose."
        ),
        "what_youll_need": [
            "An HTTPS endpoint that can accept a JSON POST.",
            "(Optional) A shared secret you'd like Open Humana to use to "
            "sign the payloads (HMAC-SHA256 in the `X-Open-Humana-Signature` "
            "header).",
        ],
        "steps": [
            ("Add your endpoint URL",
             "In Open Humana, open **Settings → Integrations → Outbound "
             "Webhooks**, paste your HTTPS endpoint URL, and (optionally) a "
             "shared secret for signing."),
            ("Pick the events to fire",
             "Choose any combination of `call.transferred`, `call.voicemail`, "
             "`call.connected`, `call.no_answer`, `call.failed`."),
            ("Send a test payload",
             "Click **Send test webhook**. Open Humana will fire a sample "
             "payload at your endpoint and show you the response code."),
            ("Save and go live",
             "Click **Save**. Open Humana will start firing real events on the "
             "next call."),
        ],
    },
    {
        "slug": "zapier",
        "name": "Zapier",
        "tier": NATIVE,
        "logo": "integrations/zapier.svg",
        "tagline": "Open Humana ships as a native Zapier trigger app.",
        "summary": (
            "Wire Open Humana into 6,000+ Zapier apps with no code. Triggers "
            "fire on `Call Transferred`, `Voicemail Dropped`, `Call "
            "Connected`, and `Call Failed` — with the full call payload "
            "available to every downstream Zap step."
        ),
        "what_youll_need": [
            "A Zapier account (any plan, including the free tier).",
            "Your Open Humana API key from **Settings → API Access**.",
        ],
        "steps": [
            ("Find Open Humana on Zapier",
             "In Zapier, search for **Open Humana** in the app directory and "
             "click **Connect**."),
            ("Paste your Open Humana API key",
             "Grab your API key from **Settings → API Access** in Open Humana, "
             "then paste it into Zapier when prompted."),
            ("Choose a trigger",
             "Pick the call event you want to listen for — `Call "
             "Transferred`, `Voicemail Dropped`, `Call Connected`, or `Call "
             "Failed`."),
            ("Build the rest of your Zap",
             "Map any Open Humana field (transcript, recording URL, contact "
             "name, outcome, duration) into the next step of your Zap."),
            ("Turn the Zap on",
             "Hit **Publish**. Open Humana will start firing the trigger on "
             "the next matching call."),
        ],
    },

    # ---------------- ZAPIER / MAKE (5) ----------------
    {
        "slug": "make",
        "name": "Make.com",
        "tier": ZAPIER,
        "logo": "integrations/make.svg",
        "tagline": "Visual scenarios for Open Humana call events.",
        "summary": (
            "Build powerful, visual scenarios that fire on any Open Humana "
            "call event using Make.com's free HTTP / Webhook module — no "
            "intermediate connector required."
        ),
        "what_youll_need": [
            "A Make.com account (free tier works).",
            "A Make Custom Webhook URL (Make creates this for you in 30 "
            "seconds).",
        ],
        "steps": [
            ("Create a Custom Webhook in Make",
             "In Make.com, create a new scenario, add the **Webhooks → Custom "
             "Webhook** module, and click **Add** to generate a webhook URL. "
             "Copy it."),
            ("Add the webhook to Open Humana",
             "In Open Humana, open **Settings → Integrations → Outbound "
             "Webhooks**, paste the Make webhook URL as a destination, and "
             "tick the events you want."),
            ("Run a test call from Open Humana",
             "Send a test webhook from Open Humana. Make.com will catch the "
             "payload and let you build downstream modules using its fields."),
            ("Build out the scenario",
             "Add any Make module — Google Sheets, Notion, Airtable, OpenAI, "
             "Slack, etc. — and map Open Humana fields into them."),
            ("Activate the scenario",
             "Switch the Make scenario to **ON** and you're live."),
        ],
    },
    {
        "slug": "dynamics-365",
        "name": "Microsoft Dynamics 365",
        "tier": ZAPIER,
        "logo": "integrations/dynamics365.svg",
        "tagline": "Push call activities and contact updates into Dynamics CRM.",
        "summary": (
            "Open Humana hooks into Microsoft Dynamics 365 through Zapier and "
            "Make — every call event becomes a Phone Call activity on the "
            "matching Contact or Lead."
        ),
        "what_youll_need": [
            "A Microsoft Dynamics 365 account.",
            "A Zapier or Make account (their Dynamics 365 connector is "
            "free).",
        ],
        "steps": [
            ("Create a Zap with the Open Humana trigger",
             "In Zapier, pick **Open Humana → Call Transferred** (or "
             "whichever event you want) as the trigger and connect with your "
             "Open Humana API key."),
            ("Add a Dynamics 365 action step",
             "Add **Microsoft Dynamics 365 CRM → Create Phone Call** as the "
             "action. Authenticate with your Microsoft work account when "
             "prompted."),
            ("Map Open Humana fields to Dynamics fields",
             "Drop the call subject, regarding contact, duration, and "
             "description into the matching Dynamics fields."),
            ("Test and turn on",
             "Run the test, confirm the Phone Call activity appears in "
             "Dynamics, then **Publish** the Zap."),
        ],
    },
    {
        "slug": "microsoft-teams",
        "name": "Microsoft Teams",
        "tier": ZAPIER,
        "logo": "integrations/microsoftteams.svg",
        "tagline": "Real-time call notifications inside any Teams channel.",
        "summary": (
            "Get a rich card in any Microsoft Teams channel the moment Open "
            "Humana transfers a call, drops a voicemail, or finishes a "
            "conversation."
        ),
        "what_youll_need": [
            "Permissions to add an Incoming Webhook connector in your Teams "
            "channel.",
            "A Zapier or Make account.",
        ],
        "steps": [
            ("Add an Incoming Webhook to your Teams channel",
             "In Microsoft Teams, open the channel → **... → Workflows** (or "
             "**Connectors** in classic Teams) → **Incoming Webhook**. Name "
             "it `Open Humana` and copy the generated URL."),
            ("Wire it up via Zapier or Make",
             "Create a Zap (or Make scenario) with **Open Humana → Call "
             "Transferred** as the trigger and **Webhooks → POST** as the "
             "action, pointing at the Teams URL."),
            ("Format the message card",
             "Use the sample Teams Adaptive Card payload from the Open Humana "
             "docs to format a clean notification."),
            ("Turn it on",
             "Activate the Zap or Make scenario. The next transferred call "
             "will land in your Teams channel within seconds."),
        ],
    },
    {
        "slug": "activecampaign",
        "name": "ActiveCampaign",
        "tier": ZAPIER,
        "logo": "integrations/activecampaign.svg",
        "tagline": "Trigger ActiveCampaign automations on every call event.",
        "summary": (
            "Use Open Humana call events to trigger any ActiveCampaign "
            "automation — assign tags, move contacts between lists, or send a "
            "follow-up email the moment a voicemail drops."
        ),
        "what_youll_need": [
            "An ActiveCampaign account.",
            "A Zapier or Make account.",
        ],
        "steps": [
            ("Pick the Open Humana trigger",
             "In Zapier or Make, choose **Open Humana → Call Transferred** "
             "(or any other call event) as your trigger."),
            ("Add an ActiveCampaign action",
             "Add **ActiveCampaign → Add Tag to Contact** (or **Update "
             "Contact**, **Add to Automation**, etc.) as the next step."),
            ("Authenticate ActiveCampaign",
             "Paste your ActiveCampaign API URL and key (find them under "
             "**My Settings → Developer** in ActiveCampaign)."),
            ("Map Open Humana fields",
             "Map the contact email/phone returned by Open Humana to the "
             "ActiveCampaign contact lookup field."),
            ("Activate",
             "Test, then publish the Zap or Make scenario."),
        ],
    },
    {
        "slug": "mailchimp",
        "name": "Mailchimp",
        "tier": ZAPIER,
        "logo": "integrations/mailchimp.svg",
        "tagline": "Auto-add contacts to a Mailchimp audience after a call.",
        "summary": (
            "Add a contact to a Mailchimp audience (or trigger a Customer "
            "Journey) automatically when Open Humana drops a voicemail or "
            "transfers a call."
        ),
        "what_youll_need": [
            "A Mailchimp account.",
            "A Zapier or Make account.",
        ],
        "steps": [
            ("Pick the Open Humana trigger",
             "In Zapier or Make, choose **Open Humana → Voicemail Dropped** "
             "(or **Call Transferred**) as the trigger."),
            ("Add a Mailchimp action",
             "Add **Mailchimp → Add/Update Subscriber** (or **Trigger "
             "Customer Journey**) as the action step."),
            ("Authenticate Mailchimp",
             "Sign into your Mailchimp account when Zapier prompts you. "
             "Choose the audience you want to add contacts into."),
            ("Map the contact fields",
             "Map the Open Humana contact email and merge fields (name, "
             "company, phone) onto the Mailchimp subscriber."),
            ("Publish the Zap",
             "Test and turn on. New contacts will land in Mailchimp within "
             "seconds of the matching Open Humana event."),
        ],
    },

    # ---------------- COMING SOON (3) ----------------
    {
        "slug": "bullhorn",
        "name": "Bullhorn",
        "tier": SOON,
        "logo": "integrations/bullhorn.svg",
        "tagline": "Native sync for staffing & recruiting agencies.",
        "summary": (
            "We're building a native Bullhorn connector for staffing & "
            "recruiting agencies — Candidates, Jobs, Placements, and Notes "
            "all keep in sync with your Open Humana calls. In closed beta now."
        ),
        "what_youll_need": [
            "A Bullhorn account.",
            "(For the beta) Your Bullhorn cluster ID and a Bullhorn API user "
            "with the `entity` and `query` scopes.",
        ],
        "steps": [
            ("Join the Bullhorn integration beta waitlist",
             "Email **integrations@openhumana.com** with subject "
             "`Bullhorn beta` and your Bullhorn cluster ID. We'll add you to "
             "the next batch."),
            ("Receive your beta credentials",
             "Once approved, you'll get a private Open Humana build with the "
             "Bullhorn connector and a step-by-step onboarding call."),
            ("Want it sooner?",
             "Until then, Open Humana → Bullhorn works through Zapier and "
             "Make.com via Bullhorn's REST API — happy to share a starter "
             "template."),
        ],
    },
    {
        "slug": "gong",
        "name": "Gong",
        "tier": SOON,
        "logo": "integrations/gong.svg",
        "tagline": "Stream call recordings & transcripts to Gong.",
        "summary": (
            "We're building a native Gong connector that streams every Open "
            "Humana call recording + transcript into Gong's conversation "
            "intelligence layer. Targeting GA in the next quarter."
        ),
        "what_youll_need": [
            "A Gong account.",
            "(For the beta) Your Gong API access key & secret from **Company "
            "Settings → Ecosystem → API**.",
        ],
        "steps": [
            ("Join the Gong integration beta waitlist",
             "Email **integrations@openhumana.com** with subject "
             "`Gong beta`. We'll prioritize Open Humana customers already on "
             "the Business plan."),
            ("Approval & onboarding",
             "Once approved, you'll receive a private build with the Gong "
             "connector and a guided 15-minute onboarding."),
            ("Want it sooner?",
             "Use the Outbound Webhooks integration today to fire call "
             "recording URLs at any custom Gong importer."),
        ],
    },
    {
        "slug": "monday",
        "name": "monday.com",
        "tier": SOON,
        "logo": "integrations/monday.svg",
        "tagline": "Call activity as monday.com board items.",
        "summary": (
            "Native monday.com support is on the roadmap — every Open Humana "
            "call will create or update a board item with disposition, "
            "transcript, and recording link."
        ),
        "what_youll_need": [
            "A monday.com account.",
        ],
        "steps": [
            ("Join the monday.com integration beta waitlist",
             "Email **integrations@openhumana.com** with subject "
             "`monday.com beta` and the board ID you'd like calls to flow "
             "into."),
            ("Want it sooner?",
             "monday.com works today through Zapier — choose **Open Humana → "
             "Call Transferred** as the trigger and **monday.com → Create "
             "Item** as the action."),
        ],
    },
]


def by_slug(slug: str):
    for i in INTEGRATIONS:
        if i["slug"] == slug:
            return i
    return None


def by_tier():
    """Return integrations grouped into ordered tiers."""
    groups = {NATIVE: [], ZAPIER: [], SOON: []}
    for i in INTEGRATIONS:
        groups[i["tier"]].append(i)
    return groups
