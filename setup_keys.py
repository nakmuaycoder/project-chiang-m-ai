"""
Script to set up API keys for the Gemini Coach application.
This script prompts the user for their Intervals.icu and Google Gemini API keys
and saves them into a local .env file.
"""

import argparse
from pathlib import Path


def main() -> None:
    """
    Parses command-line arguments and creates a .env file with the provided API keys.
    """
    # Initialize argument parser
    parser = argparse.ArgumentParser(description="Setup API keys for Gemini Coach.")

    # Define required arguments
    parser.add_argument(
        "--intervals_id",
        required=True,
        help="Your Intervals.icu Athlete ID (e.g., i12345)",
    )
    parser.add_argument(
        "--intervals_key", required=True, help="Your Intervals.icu API Key"
    )
    parser.add_argument(
        "--calendar_creds",
        required=False,
        default="credentials.json",
        help=(
            "Path to Google Calendar OAuth credentials file (default: credentials.json)"
        ),
    )
    parser.add_argument(
        "--periodization",
        required=False,
        default="3:1",
        choices=["2:1", "3:1"],
        help=(
            "Training periodization pattern: 3:1 (28 days) or 2:1 (21 days) "
            "[default: 3:1]"
        ),
    )

    args = parser.parse_args()

    env_path = Path(".env")

    # Content to be written to .env
    env_content = (
        f"INTERVALS_ATHLETE_ID={args.intervals_id}\n"
        f"INTERVALS_API_KEY={args.intervals_key}\n"
        f"GOOGLE_CALENDAR_CREDENTIALS_FILE={args.calendar_creds}\n"
        f"PERIODIZATION={args.periodization}\n"
    )

    # Write the file
    print(f"🔐 Creating {env_path.absolute()}...")
    try:
        with open(env_path, "w") as f:
            f.write(env_content)
        print("✅ Success! API keys have been saved locally.")
        print(
            "⚠️  IMPORTANT: This file contains secrets. It is ignored by Git and "
            "will NOT be uploaded to GitHub."
        )
    except Exception as e:
        print(f"❌ Error writing .env file: {e}")


if __name__ == "__main__":
    main()
