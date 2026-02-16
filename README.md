# Voicemail Drop System

A web-based outbound voicemail drop application using Python, Flask, and the Telnyx Call Control API. Automatically dials a list of phone numbers and either transfers to a human or drops a voicemail after beep detection.

## Setup Instructions

### 1. Telnyx Account Setup

1. Create a Telnyx account at [telnyx.com](https://telnyx.com)
2. Purchase a phone number
3. Create a **Call Control Application** in the Telnyx Mission Control Portal
4. Set the webhook URL to: `https://YOUR-REPLIT-URL/webhook`
5. Note down your:
   - API Key (found under API Keys)
   - Connection ID (found in your Call Control App settings)
   - Phone number (the number you purchased)

### 2. Environment Variables

Set these in your Replit Secrets tab:

| Variable | Description |
|----------|-------------|
| `TELNYX_API_KEY` | Your Telnyx API v2 key |
| `TELNYX_CONNECTION_ID` | Your Call Control connection ID |
| `TELNYX_FROM_NUMBER` | Your Telnyx phone number (e.g. +15551234567) |
| `PUBLIC_BASE_URL` | Your Replit app's public URL (auto-set) |

### 3. Configure Telnyx Webhook URL

In Telnyx Mission Control:

1. Go to your Call Control Application
2. Under "Send a webhook to", enter: `https://YOUR-REPLIT-URL/webhook`
3. Make sure the webhook version is set to **v2**

### 4. How to Upload Audio

You have two options:

- **Upload a file**: Click "Choose File" under Voicemail Audio and select an MP3 or WAV file
- **Public URL**: Paste a direct link to an audio file hosted online

The audio file is what gets played as the voicemail message.

### 5. How to Start a Campaign

1. Enter phone numbers by either:
   - Uploading a CSV file with numbers
   - Pasting numbers directly (one per line)
2. Upload or link your voicemail audio
3. Enter the transfer number (where human-answered calls go)
4. Click **Start Campaign**
5. Watch the call log update in real-time

### 6. How It Works

For each number dialed:

- **Human answers** -> Call is immediately transferred to your transfer number
- **Machine/voicemail answers** -> System waits for the beep, then plays your voicemail audio, then hangs up
- **No answer** -> Call is hung up and marked accordingly

### 7. Troubleshooting

**Machine detection not working:**
- Make sure your Telnyx Call Control App has AMD (Answering Machine Detection) enabled
- The system uses `detect_beep` mode which waits for the voicemail beep

**Webhook not receiving events:**
- Verify your PUBLIC_BASE_URL matches your Replit URL
- Check that the webhook URL in Telnyx ends with `/webhook`
- Make sure the app is running when calls are placed

**Audio not playing:**
- If using uploaded files, ensure PUBLIC_BASE_URL is correct
- If using a URL, make sure it's publicly accessible
- Supported formats: MP3, WAV

**Calls failing:**
- Check that TELNYX_API_KEY is valid
- Verify TELNYX_CONNECTION_ID matches your Call Control App
- Ensure TELNYX_FROM_NUMBER is a valid Telnyx number in E.164 format

## Project Structure

```
/app.py              - Main Flask application
/telnyx_client.py    - Telnyx API wrapper
/call_manager.py     - Background dialer with rate limiting
/storage.py          - In-memory state management
/templates/index.html - Dashboard UI
/static/style.css    - Styling
/uploads/            - Uploaded audio files
/logs/               - Call logs
```
