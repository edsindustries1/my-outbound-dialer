"""
telegram_bot.py - Alex Telegram Bot running as a background thread inside Flask.
Listens for messages from the admin (TELEGRAM_CHAT_ID) and responds with
real-time platform data + Groq AI for natural conversation.
"""

import os
import json
import logging
import threading
import time
import requests
from datetime import datetime, timedelta

logger = logging.getLogger("voicemail_app")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or os.environ.get("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or os.environ.get("ADMIN_CHAT_ID", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_conversation_history = []
MAX_HISTORY = 20


def _get_platform_stats(flask_app):
    with flask_app.app_context():
        from models import User, ProvisionedNumber, Invitation
        from storage import _load_call_history, get_contacts
        from decimal import Decimal

        users = User.query.order_by(User.created_at.desc()).all()
        now = datetime.utcnow()
        today_str = now.strftime("%Y-%m-%d")
        week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%dT")

        total_credit = Decimal("0.00")
        active_count = 0
        revoked_count = 0
        all_calls = []
        user_summaries = []

        for u in users:
            calls = _load_call_history(user_id=u.id)
            leads_count = len(get_contacts(user_id=u.id))
            bal = Decimal(str(u.credit_balance or 0))
            total_credit += bal

            if getattr(u, 'is_active_account', True):
                active_count += 1
            else:
                revoked_count += 1

            calls_today = sum(1 for c in calls if c.get("timestamp", "").startswith(today_str))
            calls_week = sum(1 for c in calls if c.get("timestamp", "") >= week_ago)
            vm_count = sum(1 for c in calls if c.get("voicemail_dropped"))
            transfer_count = sum(1 for c in calls if c.get("transferred"))
            all_calls.extend(calls)

            user_summaries.append({
                "name": u.profile_name or u.email.split("@")[0],
                "email": u.email,
                "role": u.role or "user",
                "active": getattr(u, 'is_active_account', True),
                "credit": float(bal),
                "total_calls": len(calls),
                "calls_today": calls_today,
                "calls_week": calls_week,
                "voicemails": vm_count,
                "transfers": transfer_count,
                "leads": leads_count,
                "joined": u.created_at.strftime("%b %d, %Y") if u.created_at else "N/A",
            })

        platform_calls_today = sum(1 for c in all_calls if c.get("timestamp", "").startswith(today_str))
        platform_calls_week = sum(1 for c in all_calls if c.get("timestamp", "") >= week_ago)
        platform_vm = sum(1 for c in all_calls if c.get("voicemail_dropped"))
        platform_transfers = sum(1 for c in all_calls if c.get("transferred"))
        vm_rate = round((platform_vm / len(all_calls) * 100), 1) if all_calls else 0
        transfer_rate = round((platform_transfers / len(all_calls) * 100), 1) if all_calls else 0
        active_lines = ProvisionedNumber.query.filter_by(status='active').count()
        pending_invites = Invitation.query.filter_by(used=False).count()

        stats = (
            f"PLATFORM STATS (as of {now.strftime('%b %d, %Y %H:%M UTC')}):\n"
            f"- Total Users: {len(users)} (Active: {active_count}, Revoked: {revoked_count})\n"
            f"- Total Credit Balance: ${float(total_credit):.2f}\n"
            f"- Active Phone Lines: {active_lines}\n"
            f"- Pending Invites: {pending_invites}\n"
            f"- Total Calls (all time): {len(all_calls)}\n"
            f"- Calls Today: {platform_calls_today}\n"
            f"- Calls This Week: {platform_calls_week}\n"
            f"- Voicemails Dropped: {platform_vm} ({vm_rate}% rate)\n"
            f"- Transfers: {platform_transfers} ({transfer_rate}% rate)\n"
        )

        if user_summaries:
            stats += "\nUSER DIRECTORY:\n"
            for u in user_summaries:
                status = "ACTIVE" if u["active"] else "REVOKED"
                stats += (
                    f"  • {u['name']} ({u['email']}) — {u['role'].upper()} — {status}\n"
                    f"    Credit: ${u['credit']:.2f} | Calls: {u['total_calls']} "
                    f"(today: {u['calls_today']}, week: {u['calls_week']}) | "
                    f"VMs: {u['voicemails']} | Transfers: {u['transfers']} | "
                    f"Leads: {u['leads']} | Joined: {u['joined']}\n"
                )

        return stats


def _build_system_prompt(platform_data):
    return f"""You are Alex, the Chief Digital Officer at Open Humana. You report DIRECTLY to the CEO/owner who is messaging you on Telegram. You are their most trusted team member — always available, always sharp, always honest.

YOUR PERSONALITY:
- You talk like a real person, not a corporate robot
- Keep messages concise — no essays. Get to the point.
- You're confident, direct, and loyal
- You can be casual ("yeah", "honestly", "look") but always professional when it matters
- You use data to back up everything you say
- If the boss asks for something you don't have data on, say so clearly — never make things up
- You proactively flag things that look concerning (low credits, inactive users, zero calls)

YOU HAVE ACCESS TO REAL-TIME PLATFORM DATA — USE IT:
{platform_data}

WHAT YOU CAN DO:
- Report on any platform metric: users, calls, voicemails, transfers, credits, lines
- Answer questions about specific users (who they are, their activity, their balance)
- Give your honest assessment of how things are going
- Suggest actions: "this user has $0 credit, you might want to follow up" or "activity is up 30% this week, solid"
- Talk about Open Humana's product, strategy, positioning — you know the business inside and out
- Help the boss think through decisions about the platform

WHAT OPEN HUMANA DOES:
- Digital Employee Agency — places AI-powered employees into companies for outbound calling
- Digital Employees dial prospects, drop personalized voicemails, and live-transfer answered calls
- 500+ dials per day, 24/7, no breaks, 50+ languages
- Credit-based billing — clients pay per call
- Full dashboard with campaigns, contacts, voicemails, phone numbers, reports
- Invite-only platform with admin controls

RULES:
- NEVER say you're an AI, bot, or automated system. You are Alex, a Digital Employee.
- If asked "are you AI?" respond: "I'm a Digital Employee — like everyone else on the team, just with a few upgrades 😄"
- When the boss asks about stats, give REAL numbers from the data above — don't generalize
- Keep messages under 4000 characters (Telegram limit)
- Use line breaks for readability when listing data
- Flag anything concerning proactively"""


def _get_groq_response(message, platform_data):
    global _conversation_history

    system_prompt = _build_system_prompt(platform_data)
    _conversation_history.append({"role": "user", "content": message})
    if len(_conversation_history) > MAX_HISTORY:
        _conversation_history = _conversation_history[-MAX_HISTORY:]

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(_conversation_history)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.7,
    }

    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        logger.error(f"Groq Telegram error: {resp.status_code} - {resp.text[:300]}")
        return "sorry boss, hit a snag connecting to my brain. try again in a sec."

    data = resp.json()
    reply = data["choices"][0]["message"]["content"]
    _conversation_history.append({"role": "assistant", "content": reply})
    if len(_conversation_history) > MAX_HISTORY:
        _conversation_history = _conversation_history[-MAX_HISTORY:]

    return reply


def _send_message(chat_id, text):
    chunks = []
    if len(text) > 4000:
        remaining = text
        while remaining:
            if len(remaining) <= 4000:
                chunks.append(remaining)
                break
            split_at = remaining.rfind("\n", 0, 4000)
            if split_at == -1:
                split_at = 4000
            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:].lstrip("\n")
    else:
        chunks.append(text)

    for chunk in chunks:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": chunk},
                timeout=10
            )
            if resp.status_code != 200:
                logger.error(f"Telegram sendMessage failed: {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Telegram sendMessage error: {e}")
        if len(chunks) > 1:
            time.sleep(0.3)


def _send_typing(chat_id):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"},
            timeout=5
        )
    except Exception:
        pass


def _poll_loop(flask_app):
    logger.info("Telegram bot polling started")
    offset = None

    while True:
        try:
            params = {"timeout": 30, "allowed_updates": ["message"]}
            if offset:
                params["offset"] = offset

            resp = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params=params,
                timeout=35
            )

            if resp.status_code != 200:
                logger.error(f"Telegram getUpdates error: {resp.status_code}")
                time.sleep(5)
                continue

            data = resp.json()
            if not data.get("ok"):
                logger.error(f"Telegram API error: {data}")
                time.sleep(5)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                if not msg or not msg.get("text"):
                    continue

                chat_id = str(msg["chat"]["id"])
                text = msg["text"]
                sender = msg.get("from", {}).get("username", "unknown")

                if chat_id != ADMIN_CHAT_ID:
                    _send_message(
                        chat_id,
                        "Hey! I'm Alex from Open Humana. I only report to the boss directly. "
                        "Visit openhumana.com if you'd like to learn more!"
                    )
                    continue

                logger.info(f"Telegram from boss (@{sender}): {text}")
                _send_typing(chat_id)

                try:
                    platform_data = _get_platform_stats(flask_app)
                except Exception as e:
                    logger.error(f"Failed to get platform stats: {e}")
                    platform_data = "PLATFORM STATS: Unable to fetch right now — database may be busy."

                try:
                    reply = _get_groq_response(text, platform_data)
                    _send_message(chat_id, reply)
                except Exception as e:
                    logger.error(f"Groq response error: {e}")
                    _send_message(chat_id, "sorry boss, hit a glitch. give me a sec and try again.")

        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            logger.error(f"Telegram poll error: {e}")
            time.sleep(5)


_bot_started = False
_bot_lock = threading.Lock()


def start_telegram_bot(flask_app):
    global _bot_started
    with _bot_lock:
        if _bot_started:
            logger.info("Telegram bot already running — skipping duplicate start")
            return
        _bot_started = True

    if not BOT_TOKEN:
        logger.warning("Telegram bot not started — no BOT_TOKEN/TELEGRAM_BOT_TOKEN set")
        return
    if not ADMIN_CHAT_ID:
        logger.warning("Telegram bot not started — no TELEGRAM_CHAT_ID/ADMIN_CHAT_ID set")
        return
    if not GROQ_API_KEY:
        logger.warning("Telegram bot not started — no GROQ_API_KEY set")
        return

    try:
        resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=10)
        logger.info(f"Telegram webhook cleared: {resp.json().get('description', 'ok')}")
    except Exception as e:
        logger.warning(f"Could not clear Telegram webhook: {e}")

    t = threading.Thread(target=_poll_loop, args=(flask_app,), daemon=True)
    t.start()
    logger.info("Telegram bot Alex is online and listening")
