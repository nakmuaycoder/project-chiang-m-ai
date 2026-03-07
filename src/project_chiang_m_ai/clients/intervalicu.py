"""
Intervals.icu Client

Handles authentication and workout uploads to Intervals.icu using native workout format.
"""

import base64

import requests
from dateutil import parser

from project_chiang_m_ai.config import settings
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.models.strength_workout import StrengthWorkout
from project_chiang_m_ai.models.workout import WorkoutUnion

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
    def format_workout_native(cls, workout: WorkoutUnion) -> str:
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
    def upload_workout(cls, workout):
        """
        Upload a workout to Intervals.icu using native workout format.

        Args:
            workout: Workout object (RunWorkout, RideWorkout, or StrengthWorkout)

        Returns:
            dict: {"success": bool, "workout_id": int or None, "error": str or None}
        """
        auth_token = cls.encode_auth()
        headers = {
            "Authorization": f"Basic {auth_token}",
            "Content-Type": "application/json",
        }

        athlete_id = settings.INTERVALS_ATHLETE_ID
        url = f"{BASE_URL}/{athlete_id}/events"

        try:
            start_date = workout.start_date_local
            if start_date:
                dt_object = parser.isoparse(start_date)
                start_date = dt_object.strftime("%Y-%m-%dT%H:%M:%S")

            if isinstance(workout, StrengthWorkout):
                workout_description = workout.to_intervals_description()

                event_payload = {
                    "start_date_local": start_date,
                    "category": workout.category,
                    "name": workout.name,
                    "description": workout_description,
                    "type": "WeightTraining",
                }

                logger.info(f"\n📝 Uploading strength workout: {workout.name}")
                logger.info("\nWorkout structure:")
                logger.info(workout_description)
            else:
                # Format workout in native format
                workout_description = cls.format_workout_native(workout)

                # Prepare event payload
                event_payload = {
                    "start_date_local": start_date,
                    "category": "WORKOUT",
                    "name": workout.name,
                    "description": workout_description,
                    "type": workout.type,
                    "moving_time": workout.moving_time,
                }

                logger.info(f"\n📝 Uploading: {workout.name}")
                logger.info("   Format: Intervals.icu native")
                logger.info(f"   Duration: {workout.moving_time}s")
                logger.info("\nWorkout structure:")
                logger.info(workout_description)

            if workout.color:
                event_payload["color"] = workout.color

            logger.info(f"\n⬆️  Uploading to {url}")

            response = requests.post(url, headers=headers, json=event_payload)
            response.raise_for_status()

            # Extract workout ID from response
            response_data = response.json()
            workout_id = response_data.get("id")

            logger.info(f"✅ Successfully uploaded '{workout.name}'")
            if workout_id:
                logger.info(f"   Intervals.icu ID: {workout_id}")

            return {"success": True, "workout_id": workout_id, "error": None}

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error uploading workout '{workout.name}': {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.info(f"   Status: {e.response.status_code}")
                logger.info(f"   Response: {e.response.text}")
            return {"success": False, "workout_id": None, "error": str(e)}
        except Exception as e:
            logger.error(f"❌ Unexpected error for '{workout.name}': {e}")
            return {"success": False, "workout_id": None, "error": str(e)}

    @classmethod
    def delete_workout(cls, workout_id: int) -> dict:
        """
        Delete a workout from Intervals.icu by ID.

        Args:
            workout_id: Intervals.icu workout/event ID

        Returns:
            dict: {"success": bool, "error": str or None}
        """
        auth_token = cls.encode_auth()
        headers = {
            "Authorization": f"Basic {auth_token}",
        }

        athlete_id = settings.INTERVALS_ATHLETE_ID
        url = f"{BASE_URL}/{athlete_id}/events/{workout_id}"

        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()

            logger.info(f"✅ Deleted workout ID: {workout_id}")
            return {"success": True, "error": None}

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error deleting workout {workout_id}: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.info(f"   Status: {e.response.status_code}")
                logger.info(f"   Response: {e.response.text}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"❌ Unexpected error deleting {workout_id}: {e}")
            return {"success": False, "error": str(e)}
