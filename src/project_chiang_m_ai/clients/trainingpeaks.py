"""
TrainingPeaks Client

Handles direct communication with TrainingPeaks API, including
cookie-to-token exchange and workout management.
"""

from datetime import datetime, timedelta

import requests
from dateutil import parser

from project_chiang_m_ai.config import settings
from project_chiang_m_ai.interfaces.platform import ISportPlatform
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.models.strength_workout import StrengthWorkout
from project_chiang_m_ai.models.workout import WorkoutUnion

BASE_URL = "https://tpapi.trainingpeaks.com"


class TrainingPeaksClient(ISportPlatform):
    """
    Client for interacting directly with the TrainingPeaks API.
    Uses Cookie-based authentication to obtain a Bearer token.
    """

    def __init__(self):
        self._access_token = None
        self._athlete_id = None

    def _get_access_token(self) -> str:
        """
        Exchanges the Production_tpAuth cookie for a Bearer token.
        """
        if self._access_token:
            return self._access_token

        cookie = settings.TP_AUTH_COOKIE.get_secret_value()
        url = f"{BASE_URL}/users/v3/token"
        headers = {
            "Cookie": f"Production_tpAuth={cookie}",
            "Accept": "application/json",
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data.get("success") and "token" in data:
                self._access_token = data["token"]["access_token"]
                return self._access_token
            raise Exception("Failed to extract token from TP response")
        except Exception as e:
            logger.error(f"❌ TP Auth Error: {e}")
            raise

    def _get_athlete_id(self) -> int:
        """Fetches the current athlete ID."""
        if self._athlete_id:
            return self._athlete_id

        token = self._get_access_token()
        url = f"{BASE_URL}/users/v3/user"
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # TP returns a list of athletes associated with the account
        user_data = response.json()
        self._athlete_id = user_data["athletes"][0]["athleteId"]
        return self._athlete_id

    def push_workout(self, workout: WorkoutUnion) -> dict:
        """
        Uploads a workout to TrainingPeaks.
        """
        token = self._get_access_token()
        athlete_id = self._get_athlete_id()
        url = f"{BASE_URL}/fitness/v6/athletes/{athlete_id}/workouts"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            start_date = workout.start_date_local
            if start_date:
                dt_object = parser.isoparse(start_date)
                start_date = dt_object.strftime("%Y-%m-%dT00:00:00")

            # Construction du payload TP
            payload = {
                "athleteId": athlete_id,
                "workoutDay": start_date,
                "title": workout.name,
                "description": workout.description or "",
                "workoutTypeFamilyId": 3
                if not isinstance(workout, StrengthWorkout)
                else 9,
                "workoutTypeValueId": 3
                if not isinstance(workout, StrengthWorkout)
                else 9,
            }

            # Ajout de la structure si ce n'est pas de la muscu
            if not isinstance(workout, StrengthWorkout):
                import json

                structure = self._format_tp_structure(workout)
                payload["structure"] = json.dumps(structure)

            logger.info(f"⬆️ Uploading to TrainingPeaks: {workout.name}")
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

            workout_id = response.json().get("workoutId")
            logger.info(f"✅ TP Upload Success! ID: {workout_id}")

            return {"success": True, "workout_id": workout_id}

        except Exception as e:
            logger.error(f"❌ TP Upload Error: {e}")
            return {"success": False, "workout_id": None, "error": str(e)}

    def delete_workout(self, workout_id: str | int) -> dict:
        """Deletes a workout by ID."""
        token = self._get_access_token()
        athlete_id = self._get_athlete_id()
        url = f"{BASE_URL}/fitness/v6/athletes/{athlete_id}/workouts/{workout_id}"

        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ TP Delete Error: {e}")
            return {"success": False, "error": str(e)}

    def get_wellness_data(self) -> list[dict]:
        """Fetches HRV and Pulse metrics."""
        days = settings.WELLNESS_HISTORY_DAYS
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        token = self._get_access_token()
        athlete_id = self._get_athlete_id()
        url = f"{BASE_URL}/metrics/v3/athletes/{athlete_id}/"
        url += f"consolidatedtimedmetrics/{start}/{end}"

        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            metrics = []
            for day in response.json():
                entry = {"date": day.get("timeStamp")[:10]}
                for detail in day.get("details", []):
                    if detail["type"] == 60:
                        entry["hrv"] = detail["value"]
                    if detail["type"] == 5:
                        entry["resting_hr"] = detail["value"]

                if "hrv" in entry or "resting_hr" in entry:
                    metrics.append(entry)

            return metrics
        except Exception as e:
            logger.error(f"❌ TP Wellness Error: {e}")
            return []

    def _format_tp_structure(self, workout: WorkoutUnion) -> dict:
        """Converts app structure to TP wire format."""
        steps = []
        for block in workout.steps:
            for _ in range(block.repetitions):
                for step in block.steps:
                    # Extraction basique des zones
                    try:
                        z = step.zone.to_value().replace("%", "").split("-")
                        low, high = float(z[0]), float(z[1])
                    except Exception:
                        low, high = 50, 60

                    steps.append(
                        {
                            "type": "step",
                            "name": step.name or "",
                            "length": {"type": "time", "value": step.duration},
                            "intensity": {
                                "type": "percentOfThresholdHr",
                                "min": low / 100,
                                "max": high / 100,
                            },
                        }
                    )
        return {
            "structure": steps,
            "polyline": None,
            "primaryLengthMetric": "time",
            "primaryIntensityMetric": "percentOfThresholdHr",
        }
