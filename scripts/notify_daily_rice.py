"""
Script: notify_daily_rice.py

Fetches the TrainingPeaks Day Note for a target date (default: tomorrow),
parses the cooked rice quantities (Matin, Midi, 16h, Dîner),
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
        description="Fetch daily rice nutrition plan and send SMS"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Target date in YYYY-MM-DD format (default: tomorrow)",
    )
    args = parser.parse_args()

    if args.date:
        target_date = args.date
    else:
        tomorrow_dt = datetime.now(timezone.utc) + timedelta(days=1)
        target_date = tomorrow_dt.strftime("%Y-%m-%d")

    logger.info(f"🔍 Fetching Day Note for target date: {target_date}")

    client = TrainingPeaksClient()
    notes = client.get_day_notes(target_date)

    rice_note = None
    for n in notes:
        title = n.get("title", "")
        if "Riz" in title or "Nutrition" in title:
            rice_note = n
            break

    if not rice_note and notes:
        rice_note = notes[0]

    if not rice_note:
        raw_msg = (
            f"Plan Riz ({target_date}) : "
            "Aucune note trouvee sur TrainingPeaks pour demain."
        )
    else:
        title = rice_note.get("title", "")
        desc = rice_note.get("description", "")
        raw_msg = f"[Riz {target_date}]\n{title}\n\n{desc}"

    clean_msg = sanitize_for_free_mobile_sms(raw_msg)

    print("========================================")
    print("RAW MSG:")
    print(raw_msg)
    print("----------------------------------------")
    print("CLEAN SMS MSG FOR FREE MOBILE:")
    print(clean_msg)
    print("========================================")

    user = os.getenv("FREE_MOBILE_USER")
    pass_key = os.getenv("FREE_MOBILE_PASS") or os.getenv("FREE_MOBILE_KEY")

    if user and pass_key:
        logger.info("🔑 Free Mobile credentials found. Sending SMS...")
        success = send_free_mobile_sms(user, pass_key, raw_msg)
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
