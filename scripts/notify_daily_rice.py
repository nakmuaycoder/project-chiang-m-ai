"""
Script: notify_daily_rice.py

Fetches the TrainingPeaks Day Note / Workouts for a target date (default: tomorrow),
calculates/parses the cooked rice quantities (Matin, Midi, 16h, Dîner),
formats the message in the selected language (fr: Français, en: English, th: Thai),
strips/replaces emojis for Free Mobile SMS compatibility,
and sends an SMS notification via the Free Mobile SMS API.
"""

import argparse
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
        "☀️": "[Midi]",
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
            logger.info("📱 Free Mobile SMS sent successfully!")
            return True
        else:
            logger.error(f"❌ Free Mobile SMS Error HTTP {res.status_code}: {res.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Free Mobile SMS Exception: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Fetch daily rice nutrition plan and send SMS in FR, EN, or TH"
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
        help="SMS language: fr (French), en (English), th (Thai).",
    )
    args = parser.parse_args()

    if args.date:
        target_date = args.date
    else:
        tomorrow_dt = datetime.now(timezone.utc) + timedelta(days=1)
        target_date = tomorrow_dt.strftime("%Y-%m-%d")

    lang = args.lang.lower().strip()
    logger.info(f"🔍 Fetching Day Note for {target_date} ({lang.upper()})")

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

    _, sms_msg = format_rice_plan_message(plan, lang=lang, for_sms=True)

    print("========================================")
    print(f"SMS MSG (Language: {lang.upper()}):")
    print(sms_msg)
    print("========================================")

    user = os.getenv("FREE_MOBILE_USER")
    pass_key = os.getenv("FREE_MOBILE_PASS") or os.getenv("FREE_MOBILE_KEY")

    if user and pass_key:
        logger.info(
            f"🔑 Free Mobile credentials found. Sending SMS in {lang.upper()}..."
        )
        success = send_free_mobile_sms(user, pass_key, sms_msg)
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        logger.warning(
            "⚠️ FREE_MOBILE_USER or FREE_MOBILE_PASS not set in env. SMS skipped."
        )
        sys.exit(0)


if __name__ == "__main__":
    main()
