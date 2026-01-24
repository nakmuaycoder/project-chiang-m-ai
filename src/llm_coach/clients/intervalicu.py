import base64
from typing import Any, Dict

import requests

from llm_coach.config import settings
from llm_coach.models.workout import Workout

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
        formatted_steps = []
        steps_text = []

        # Loop through Top-Level Blocks (Steps objects)
        for block in workout.steps:
            # Unroll Repetitions
            for i in range(block.repetitions):
                # Is this the last rep?
                # (For Potential future logic like 'Recover on last rep')
                # is_last = (i == block.repetitions - 1)

                # Loop through Atomic Intervals (Step objects)
                for step in block.steps:
                    # Format individual step
                    step_data = {
                        "duration": f"{step.duration}s",
                        "zone": step.zone.to_value(),
                    }

                    if step.cadence:
                        step_data["cadence"] = step.cadence
                    if step.description:
                        step_data["description"] = step.description

                    formatted_steps.append(step_data)

                    # Format text line
                    line = f"- {step.duration}s {step.zone.to_value()}"
                    if step.cadence:
                        line += f" @ {step.cadence}"
                    if step.description:
                        line += f" ({step.description})"

                    # Indent slightly if part of a set > 1 rep
                    if block.repetitions > 1:
                        line = f"  {line}"

                    steps_text.append(line)

            # Add a visual separator in text if there were multiple
            # blocks(Optional but nice)
            if block.repetitions > 1 and steps_text:
                steps_text.append(f"  [x{block.repetitions}]")

        # distinct description from the workout summary vs the steps details
        full_description = workout.description
        if steps_text:
            full_description += "\n\n" + "\n".join(steps_text)

        output = {
            "start_date_local": workout.start_date_local,
            "category": "WORKOUT",
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
