"""
Intervals.icu Client

Handles authentication and workout uploads to Intervals.icu using native workout format.
"""

import base64

import requests

from llm_coach.config import settings
from llm_coach.models.workout import Workout

BASE_URL = "https://intervals.icu/api/v1/athlete"


class IntervalicuClient:
    """
    Client for interacting with the Intervals.icu API.
    Uploads workouts using Intervals.icu's native workout format.
    """

    @classmethod
    def encode_auth(cls) -> str:
        """
        Encodes the API key for Basic Authentication.

        Returns:
            str: Base64 encoded "API_KEY:key" string.
        """
        api_key = settings.INTERVALS_API_KEY.get_secret_value()
        token = f"API_KEY:{api_key}".encode("utf-8")
        return base64.b64encode(token).decode("utf-8")

    @classmethod
    def format_workout_native(cls, workout: Workout) -> str:
        """
        Format workout in Intervals.icu native text format.

        Uses the format: "- 5m in 56% - 75%" (percentage ranges)
        All repetitions are unrolled into individual steps.

        Format example:
        - 10m in 60% - 70%
        - 30s in 90% - 95%
        - 30s in 60% - 70%
        ...

        Args:
            workout: The Workout object to format

        Returns:
            str: Workout description in Intervals.icu format
        """
        lines = []

        # Unroll all blocks and repetitions
        for block in workout.steps:
            for rep in range(block.repetitions):
                for step in block.steps:
                    duration_str = cls._format_duration(step.duration)
                    # Use percentage format: "56% - 75%"
                    zone_str = step.zone.to_value()

                    # Use Intervals.icu format: "- 5m in 56% - 75%"
                    description = f"- {duration_str} in {zone_str}"

                    # Add cadence if present
                    if step.cadence:
                        description += f" ({step.cadence}rpm)"

                    lines.append(description)

        return "\n".join(lines)

    @classmethod
    def _format_duration(cls, seconds: int) -> str:
        """Format duration in human-readable format."""
        if seconds >= 3600:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            if mins > 0:
                return f"{hours}h{mins}m"
            return f"{hours}h"
        elif seconds >= 60:
            mins = seconds // 60
            secs = seconds % 60
            if secs > 0:
                return f"{mins}m{secs}s"
            return f"{mins}m"
        else:
            return f"{seconds}s"

    @classmethod
    def upload_workout(cls, *workouts: Workout) -> bool:
        """
        Uploads one or more workouts to Intervals.icu.

        Uses the native Intervals.icu workout format which preserves
        step ordering correctly.

        Args:
            *workouts: Variable number of Workout objects to upload

        Returns:
            bool: True if all uploads were successful, False otherwise
        """
        auth_token = cls.encode_auth()
        headers = {
            "Authorization": f"Basic {auth_token}",
            "Content-Type": "application/json",
        }

        athlete_id = settings.INTERVALS_ATHLETE_ID
        url = f"{BASE_URL}/{athlete_id}/events"

        success = True
        for workout in workouts:
            try:
                # Format workout in native format
                workout_description = cls.format_workout_native(workout)

                # Prepare event payload
                event_payload = {
                    "start_date_local": workout.start_date_local,
                    "category": "WORKOUT",
                    "name": workout.name,
                    "description": workout_description,
                    "type": workout.type,
                    "moving_time": workout.moving_time,
                }

                if workout.color:
                    event_payload["color"] = workout.color

                print(f"\n📝 Uploading: {workout.name}")
                print("   Format: Intervals.icu native")
                print(f"   Duration: {workout.moving_time}s")
                print("\nWorkout structure:")
                print(workout_description)
                print(f"\n⬆️  Uploading to {url}")

                response = requests.post(url, headers=headers, json=event_payload)
                response.raise_for_status()

                print(f"✅ Successfully uploaded '{workout.name}'")

            except requests.exceptions.RequestException as e:
                print(f"❌ Error uploading workout '{workout.name}': {e}")
                if hasattr(e, "response") and e.response is not None:
                    print(f"   Status: {e.response.status_code}")
                    print(f"   Response: {e.response.text}")
                success = False
            except Exception as e:
                print(f"❌ Unexpected error for '{workout.name}': {e}")
                success = False

        return success
