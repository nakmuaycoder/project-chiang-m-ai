import base64
from typing import Any, Dict

import requests

from gemini_coach.config import settings
from gemini_coach.models.workout import Workout

BASE_URL = "https://intervals.icu/api/v1/athlete"


class IntervalicuClient:
    """
    Client for interacting with the Intervals.icu API.
    Handles authentication and workout uploads.
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
    def format_workout(cls, workout: Workout) -> Dict[str, Any]:
        """
        Formats a Workout model into the JSON structure expected by Intervals.icu.

        Constructs the payload including metadata (date, type, etc.) and
        structured steps. It also appends a textual summary of steps to the description.

        Args:
            workout (Workout): The workout object to format.

        Returns:
            Dict[str, Any]: A dictionary representing the workout in
            Intervals.icu format.
        """
        # Generate a textual description of the steps for the description field
        steps_text = []
        formatted_steps = []

        for step in workout.steps:
            # Format step for API
            step_data = {
                "duration": step.duration,
                "zone": step.zone.to_value(),
            }

            if step.cadence:
                step_data["cadence"] = step.cadence
            if step.description:
                step_data["description"] = step.description

            formatted_steps.append(step_data)

            # Format text line for description
            line = f"- {step.duration}s {step.zone.to_value()}"
            if step.cadence:
                line += f" @ {step.cadence}"
            if step.description:
                line += f" ({step.description})"
            steps_text.append(line)

        # distinct description from the workout summary vs the steps details
        full_description = workout.description
        if steps_text:
            full_description += "\n\n" + "\n".join(steps_text)

        output = {
            "start_date_local": workout.start_date_local,
            "category": workout.category,
            "name": workout.name,
            "description": full_description,
            "type": workout.type,  # Get value from Enum
            "moving_time": workout.moving_time,
            "steps": formatted_steps,
        }

        if workout.color:
            output["color"] = workout.color

        return output

    def upload_workout(self, *workouts: Workout) -> bool:
        """
        Uploads one or more workouts to the Intervals.icu calendar.

        Uses the 'bulk' events endpoint to create workouts.

        Args:
            *workouts (Workout): Variable number of Workout objects to upload.

        Returns:
            bool: True if the upload was successful, False otherwise.
        """
        auth_token = self.encode_auth()
        headers = {
            "Authorization": f"Basic {auth_token}",
            "Content-Type": "application/json",
        }

        formatted_workouts = [self.format_workout(w) for w in workouts]

        athlete_id = settings.INTERVALS_ATHLETE_ID
        url = f"{BASE_URL}/{athlete_id}/events/bulk"

        try:
            response = requests.post(url, headers=headers, json=formatted_workouts)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error uploading workout: {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"Response: {e.response.text}")
            return False
