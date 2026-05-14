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
        self._athlete_id = user_data["user"]["athletes"][0]["athleteId"]
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
                start_date = dt_object.strftime("%Y-%m-%d")

            # Mapping des types de sport TP
            SPORT_MAP = {
                "Run": (3, 3),
                "TrailRun": (3, 3),
                "Bike": (2, 2),
                "Ride": (2, 2),
                "Swim": (1, 1),
                "WeightTraining": (9, 9),
                "Strength": (9, 9),
            }
            family_id, type_id = SPORT_MAP.get(workout.type, (3, 3))  # Default to Run

            # Construction du payload TP
            payload = {
                "athleteId": athlete_id,
                "workoutDay": start_date,
                "title": workout.name,
                "description": workout.description or "",
                "workoutTypeFamilyId": family_id,
                "workoutTypeValueId": type_id,
            }

            # Ajout de la structure si ce n'est pas de la muscu
            if not isinstance(workout, StrengthWorkout):
                import json

                tp_data = self._format_tp_structure(workout)
                payload["structure"] = json.dumps(tp_data["wire"])

                # Calcul approximatif des métriques pour TP
                payload["totalTimePlanned"] = tp_data["metrics"]["duration_hours"]
                payload["ifPlanned"] = tp_data["metrics"]["if"]
                payload["tssPlanned"] = tp_data["metrics"]["tss"]

            logger.info(f"⬆️ Uploading to TrainingPeaks: {workout.name}")
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

            workout_id = response.json().get("workoutId")
            logger.info(f"✅ TP Upload Success! ID: {workout_id}")

            return {"success": True, "workout_id": workout_id}

        except Exception as e:
            if hasattr(e, "response") and e.response is not None:
                logger.error(
                    f"❌ TP Upload Error: {e.response.status_code} - {e.response.text}"
                )
            else:
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
                timestamp = day.get("timeStamp")
                if not timestamp:
                    continue
                entry = {"date": timestamp[:10]}
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
        """Converts app structure to TP wire format based on provided reference."""
        wire_blocks = []
        cumulative_seconds = 0

        # Calcul de la durée totale pour la polyline
        total_duration = 0
        for block in workout.steps:
            block_duration = block.duration * block.repetitions
            total_duration += block_duration

        polyline = []
        poly_cumulative = 0

        for block in workout.steps:
            block_duration = block.duration * block.repetitions
            begin = cumulative_seconds
            end = cumulative_seconds + block_duration

            inner_steps = []
            for step in block.steps:
                # Extraction des zones
                low = step.zone._start if step.zone._start is not None else 50
                high = step.zone._end if step.zone._end is not None else 60

                # Mapping de la classe d'intensité
                tp_class = "active"
                desc = (step.description or "").lower()
                if any(kw in desc for kw in ["warm", "échauff"]):
                    tp_class = "warmUp"
                elif any(kw in desc for kw in ["cool", "retour au calme"]):
                    tp_class = "coolDown"
                elif any(kw in desc for kw in ["rest", "récup", "repos"]):
                    tp_class = "rest"

                wire_step = {
                    "name": step.description or tp_class,
                    "type": "step",
                    "length": {"value": step.duration, "unit": "second"},
                    "targets": [{"minValue": float(low), "maxValue": float(high)}],
                    "intensityClass": tp_class,
                    "openDuration": False,
                }
                inner_steps.append(wire_step)

                # Ajout à la polyline pour chaque répétition
                for _rep in range(block.repetitions):
                    t_start = (
                        poly_cumulative / total_duration if total_duration > 0 else 0
                    )
                    poly_cumulative += step.duration
                    t_end = (
                        poly_cumulative / total_duration if total_duration > 0 else 0
                    )
                    intensity = float(high) / 100.0

                    # Polyline: drop to 0 → rise to intensity → hold → drop to 0
                    polyline.append([round(t_start, 4), 0])
                    polyline.append([round(t_start, 4), round(intensity, 4)])
                    polyline.append([round(t_end, 4), round(intensity, 4)])
                    polyline.append([round(t_end, 4), 0])

            # TP wrapper block
            is_rep = block.repetitions > 1
            wire_block = {
                "type": "repetition" if is_rep else "step",
                "length": {"value": block.repetitions, "unit": "repetition"},
                "steps": inner_steps,
                "begin": begin,
                "end": end,
            }
            wire_blocks.append(wire_block)
            cumulative_seconds = end

        # Calcul IF et TSS (NP-style simplified)
        weighted_sum = 0.0
        for block in workout.steps:
            for _ in range(block.repetitions):
                for step in block.steps:
                    low = step.zone._start if step.zone._start is not None else 50
                    high = step.zone._end if step.zone._end is not None else 60
                    midpoint = (low + high) / 2.0
                    weighted_sum += step.duration * (midpoint**4)

        intensity_factor = 0.0
        tss = 0.0
        if total_duration > 0:
            intensity_factor = (weighted_sum / total_duration) ** 0.25 / 100.0
            tss = (total_duration * intensity_factor**2 * 100.0) / 3600.0

        # Choix de la métrique d'intensité selon le sport
        intensity_metric = "percentOfThresholdHr"
        if workout.type in ["Bike", "Ride"]:
            intensity_metric = "percentOfFtp"

        return {
            "wire": {
                "structure": wire_blocks,
                "polyline": polyline,
                "primaryLengthMetric": "duration",
                "primaryIntensityMetric": intensity_metric,
                "primaryIntensityTargetOrRange": "range",
            },
            "metrics": {
                "duration_hours": total_duration / 3600.0,
                "if": round(intensity_factor, 3),
                "tss": round(tss, 1),
            },
        }
