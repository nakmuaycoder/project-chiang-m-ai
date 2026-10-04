"""
Script: notify_daily_rice.py

Fetches the TrainingPeaks Day Note / Workouts for a target date ONCE,
calculates/parses the cooked rice quantities (Matin, Midi, 16h, Dîner),
and sends multi-recipient SMS notifications in their respective requested languages
(e.g., French for user, Thai for wife) via Free Mobile SMS API.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

# Ensure src is on python path
sys.path.insert(0, "src")

from project_chiang_m_ai.clients.trainingpeaks import (  # noqa: E402
    TrainingPeaksClient,
)
from project_chiang_m_ai.logger import logger  # noqa: E402
from project_chiang_m_ai.nutrition import (  # noqa: E402
    SUPPORTED_LANGUAGES,
    calculate_rice_plan,
    format_rice_plan_message,
    parse_rice_note_text,
)

FREE_MOBILE_API_URL = "https://smsapi.free-mobile.fr/sendmsg"


def sanitize_for_free_mobile_sms(text: str) -> str:
    """Strips Emojis and converts characters for Free Mobile SMS API."""
    replacements = {
        "🍚": "[RIZ]",
        "🎯": "[PLAN]",
        "🌅": "[Matin]",
        "⚡": "[Effort]",
        "☀️": "[Midi]",
        "🍌": "[16h]",
        "🍎": "[16h]",
        "🌙": "[Soir]",
        "⚖️": "[Total]",
        "⚖": "[Total]",
        "🛋️": "[Repos]",
        "🛋": "[Repos]",
        "🏃": "[Courir]",
        "⛰️": "[Trail]",
        "⛰": "[Trail]",
        "💣": "[Volume]",
        "👑": "[Peak]",
        "📱": "",
        "🔑": "",
        "⚠️": "",
        "️": "",  # variation selector-16
    }
    for emoji, replacement in replacements.items():
        text = text.replace(emoji, replacement)

    # Remove any remaining 4-byte unicode / emoji characters
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    return text


def send_free_mobile_sms(user: str, pass_key: str, message: str) -> bool:
    """Sends SMS via Free Mobile SMS API."""
    clean_msg = sanitize_for_free_mobile_sms(message)
    try:
        params = {
            "user": user,
            "pass": pass_key,
            "msg": clean_msg,
        }
        res = requests.get(FREE_MOBILE_API_URL, params=params, timeout=15)
        if res.status_code == 200:
            logger.info(f"📱 Free Mobile SMS sent successfully to user {user}!")
            return True
        else:
            logger.error(
                f"❌ Free Mobile SMS Error HTTP {res.status_code} "
                f"for user {user}: {res.text}"
            )
            return False
    except Exception as e:
        logger.error(f"❌ Free Mobile SMS Exception for user {user}: {e}")
        return False


def parse_recipients(args) -> list[dict]:
    """
    Parses recipient list from CLI arguments or environment variables.
    Returns list of dicts: [{'user': '...', 'pass': '...', 'lang': 'fr'}, ...]
    """
    recipients = []

    # 1. Check CLI --recipient arguments (format: USER:PASS:LANG or USER:PASS)
    if args.recipient:
        for r_str in args.recipient:
            parts = r_str.split(":")
            if len(parts) >= 2:
                u = parts[0].strip()
                p = parts[1].strip()
                lang_code = parts[2].strip() if len(parts) >= 3 else "fr"
                recipients.append({"user": u, "pass": p, "lang": lang_code})

    # 2. Check FREE_MOBILE_RECIPIENTS env var (JSON or USER:PASS:LANG)
    if not recipients and os.getenv("FREE_MOBILE_RECIPIENTS"):
        raw_rec = os.getenv("FREE_MOBILE_RECIPIENTS", "").strip()
        if raw_rec.startswith("["):
            try:
                parsed = json.loads(raw_rec)
                for item in parsed:
                    if isinstance(item, dict) and item.get("user") and item.get("pass"):
                        recipients.append(
                            {
                                "user": str(item["user"]),
                                "pass": str(item["pass"]),
                                "lang": str(item.get("lang", "fr")),
                            }
                        )
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse FREE_MOBILE_RECIPIENTS JSON: {e}")
        else:
            for entry in raw_rec.split(","):
                parts = entry.strip().split(":")
                if len(parts) >= 2:
                    u = parts[0].strip()
                    p = parts[1].strip()
                    lang_code = parts[2].strip() if len(parts) >= 3 else "fr"
                    recipients.append({"user": u, "pass": p, "lang": lang_code})

    # 3. Fallback to single user CLI args or env vars (FREE_MOBILE_USER)
    if not recipients:
        u = args.user or os.getenv("FREE_MOBILE_USER")
        p = (
            args.pass_key
            or os.getenv("FREE_MOBILE_PASS")
            or os.getenv("FREE_MOBILE_KEY")
        )
        lang_code = args.lang or os.getenv("SMS_LANG", "fr")
        if u and p:
            recipients.append({"user": u, "pass": p, "lang": lang_code})

    return recipients


def main():
    parser = argparse.ArgumentParser(
        description="Fetch daily rice nutrition plan once and send multi-recipient SMS"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Target date in YYYY-MM-DD format (default: tomorrow)",
    )
    parser.add_argument(
        "--lang",
        "-l",
        type=str,
        choices=SUPPORTED_LANGUAGES,
        default=os.getenv("SMS_LANG", "fr"),
        help="Default SMS language if single recipient mode used.",
    )
    parser.add_argument(
        "--user",
        "-u",
        type=str,
        default=os.getenv("FREE_MOBILE_USER"),
        help="Free Mobile API User ID for single user mode.",
    )
    parser.add_argument(
        "--pass-key",
        "-p",
        type=str,
        default=os.getenv("FREE_MOBILE_PASS") or os.getenv("FREE_MOBILE_KEY"),
        help="Free Mobile API Pass Key for single user mode.",
    )
    parser.add_argument(
        "--recipient",
        "-r",
        action="append",
        help="Recipient specification in USER:PASS:LANG format (e.g. -r USER:KEY:fr).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print formatted SMS for all recipients without sending via API.",
    )
    args = parser.parse_args()

    if args.date:
        target_date = args.date
    else:
        tomorrow_dt = datetime.now(timezone.utc) + timedelta(days=1)
        target_date = tomorrow_dt.strftime("%Y-%m-%d")

    # --- PING TRAININGPEAKS EXACTLY ONCE ---
    logger.info(f"🔍 Fetching Day Note for target date: {target_date} (1 TP Ping)")

    client = TrainingPeaksClient()
    notes = client.get_day_notes(target_date)

    rice_note = None
    for n in notes:
        title = n.get("title", "")
        if "Riz" in title or "Rice" in title or "Nutrition" in title or "ข้าว" in title:
            rice_note = n
            break

    if not rice_note and notes:
        rice_note = notes[0]

    if rice_note and rice_note.get("description"):
        plan = parse_rice_note_text(rice_note.get("description"), target_date)
    else:
        plan = calculate_rice_plan(target_date, [])

    # --- PROCESS RECIPIENTS & SEND SMS ---
    recipients = parse_recipients(args)
    if not recipients:
        logger.warning("⚠️ No Free Mobile recipients configured. SMS skipped.")
        sys.exit(0)

    logger.info(f"📱 Processing SMS delivery for {len(recipients)} recipient(s)...")

    all_success = True
    for idx, r in enumerate(recipients, 1):
        r_user = r["user"]
        r_pass = r["pass"]
        r_lang = r["lang"].lower().strip()

        _, sms_msg = format_rice_plan_message(plan, lang=r_lang, for_sms=True)

        print("========================================")
        print(f"RECIPIENT #{idx} (User: {r_user}) - LANGUAGE: {r_lang.upper()}")
        print("----------------------------------------")
        print(sms_msg)
        print("========================================")

        if args.dry_run or os.getenv("SMS_DISABLED", "false").lower() == "true":
            logger.info(
                f"ℹ️ Dry-run mode enabled. SMS to {r_user} ({r_lang.upper()}) skipped."
            )
            continue

        logger.info(f"🔑 Sending SMS to {r_user} in {r_lang.upper()}...")
        success = send_free_mobile_sms(r_user, r_pass, sms_msg)
        if not success:
            all_success = False

    if all_success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
