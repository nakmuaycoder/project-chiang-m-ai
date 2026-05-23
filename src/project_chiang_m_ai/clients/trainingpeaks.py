"""
TrainingPeaks Client

Handles direct communication with TrainingPeaks API, including
cookie-to-token exchange and workout management.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests
from dateutil import parser

from project_chiang_m_ai.config import settings
from project_chiang_m_ai.interfaces.platform import ISportPlatform
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.models.strength_workout import StrengthWorkout
from project_chiang_m_ai.models.workout import WorkoutUnion

BASE_URL = "https://tpapi.trainingpeaks.com"

# Default intensity zones boundaries (percentages)
DEFAULT_LOW_INTENSITY = 50.0
DEFAULT_HIGH_INTENSITY = 60.0

# Mapping of TrainingPeaks sport family and type IDs
# Format: {sport_type: (family_id, type_id)}
TP_SPORT_MAP = {
    "Run": (3, 3),
    "TrailRun": (3, 3),
    "Bike": (2, 2),
    "Ride": (2, 2),
    "Swim": (1, 1),
    "WeightTraining": (9, 9),
    "Strength": (9, 9),
}


@dataclass(frozen=True)
class TPMetricType:
    HRV: int = 60
    RESTING_HR: int = 5


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

        if not settings.TP_AUTH_COOKIE:
            raise ValueError(
                "TP_AUTH_COOKIE is not set. Please configure it in your .env file."
            )
        cookie = settings.TP_AUTH_COOKIE.get_secret_value()
        url = f"{BASE_URL}/users/v3/token"
        headers = {
            "Cookie": f"Production_tpAuth={cookie}",
            "Accept": "application/json",
        }

        try:
            response = requests.get(url, headers=headers, timeout=settings.API_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get("success") and "token" in data:
                self._access_token = data["token"]["access_token"]
                return self._access_token
            raise RuntimeError("Failed to extract token from TP response")
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

        response = requests.get(url, headers=headers, timeout=settings.API_TIMEOUT)
        response.raise_for_status()

        # TP returns a list of athletes associated with the account
        user_data = response.json()
        athletes = user_data.get("user", {}).get("athletes", [])
        if not athletes:
            raise ValueError(
                "No athletes found associated with this TrainingPeaks account."
            )
        self._athlete_id = athletes[0]["athleteId"]
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

            # Default to Run if type is unknown
            family_id, type_id = TP_SPORT_MAP.get(workout.type, (3, 3))

            # Construct TP payload
            payload = {
                "athleteId": athlete_id,
                "workoutDay": start_date,
                "title": workout.name,
                "description": (
                    workout.to_intervals_description()
                    if isinstance(workout, StrengthWorkout)
                    else (workout.description or "")
                ),
                "workoutTypeFamilyId": family_id,
                "workoutTypeValueId": type_id,
            }

            # Add structure if it's not a strength workout
            if not isinstance(workout, StrengthWorkout):
                tp_data = self._format_tp_structure(workout)
                payload["structure"] = json.dumps(tp_data["wire"])

                # Approximate metrics calculation for TP
                payload["totalTimePlanned"] = tp_data["metrics"]["duration_hours"]
                payload["ifPlanned"] = tp_data["metrics"]["if"]
                payload["tssPlanned"] = tp_data["metrics"]["tss"]
            else:
                # For strength workouts, add the planned duration in
                # hours (TP expects hours)
                if workout.estimated_duration:
                    payload["totalTimePlanned"] = workout.estimated_duration / 3600.0

            logger.info(f"⬆️ Uploading to TrainingPeaks: {workout.name}")
            response = requests.post(
                url, headers=headers, json=payload, timeout=settings.API_TIMEOUT
            )
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
            response = requests.delete(
                url, headers=headers, timeout=settings.API_TIMEOUT
            )
            response.raise_for_status()
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ TP Delete Error: {e}")
            return {"success": False, "error": str(e)}

    def get_wellness_data(self) -> list[dict]:
        """Fetches HRV and Pulse metrics."""
        days = settings.WELLNESS_HISTORY_DAYS
        now_utc = datetime.now(timezone.utc)
        end = now_utc.strftime("%Y-%m-%d")
        start = (now_utc - timedelta(days=days)).strftime("%Y-%m-%d")

        token = self._get_access_token()
        athlete_id = self._get_athlete_id()
        url = f"{BASE_URL}/metrics/v3/athletes/{athlete_id}/"
        url += f"consolidatedtimedmetrics/{start}/{end}"

        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(url, headers=headers, timeout=settings.API_TIMEOUT)
            response.raise_for_status()

            metrics = []
            for day in response.json():
                timestamp = day.get("timeStamp")
                if not timestamp:
                    continue
                entry = {"date": timestamp[:10]}
                for detail in day.get("details", []):
                    if detail["type"] == TPMetricType.HRV:
                        entry["hrv"] = detail["value"]
                    elif detail["type"] == TPMetricType.RESTING_HR:
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

        # Calculate total duration for the polyline
        total_duration = 0
        for block in workout.steps:
            block_duration = block.duration
            total_duration += block_duration

        polyline = []
        poly_cumulative = 0

        for block in workout.steps:
            block_duration = block.duration
            begin = cumulative_seconds
            end = cumulative_seconds + block_duration

            inner_steps = []
            for step in block.steps:
                # Extract zones
                low = (
                    step.zone.start
                    if step.zone.start is not None
                    else DEFAULT_LOW_INTENSITY
                )
                high = (
                    step.zone.end
                    if step.zone.end is not None
                    else DEFAULT_HIGH_INTENSITY
                )

                # Map intensity class
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

                # Add to polyline for each repetition
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

        # Calculate IF and TSS (NP-style simplified)
        weighted_sum = 0.0
        for block in workout.steps:
            for _ in range(block.repetitions):
                for step in block.steps:
                    low = (
                        step.zone.start
                        if step.zone.start is not None
                        else DEFAULT_LOW_INTENSITY
                    )
                    high = (
                        step.zone.end
                        if step.zone.end is not None
                        else DEFAULT_HIGH_INTENSITY
                    )
                    midpoint = (low + high) / 2.0
                    weighted_sum += step.duration * (midpoint**4)

        intensity_factor = 0.0
        tss = 0.0
        if total_duration > 0:
            intensity_factor = (weighted_sum / total_duration) ** 0.25 / 100.0
            tss = (total_duration * intensity_factor**2 * 100.0) / 3600.0

        # Choose intensity metric based on sport type
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
