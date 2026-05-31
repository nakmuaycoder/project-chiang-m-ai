"""
TrainingPeaks Client

Handles direct communication with TrainingPeaks API, including
cookie-to-token exchange and workout management.
"""

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

        if (
            not settings.TP_AUTH_COOKIE
            or not settings.TP_AUTH_COOKIE.get_secret_value()
        ):
            raise ValueError(
                "TP_AUTH_COOKIE is not set or empty. "
                "Please configure it in your .env file."
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
            if not start_date:
                raise ValueError(f"Workout '{workout.name}' is missing a start date.")

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
                payload["structure"] = tp_data["wire"]

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

    def get_workouts(self, start_date: str, end_date: str) -> list[dict]:
        """
        Fetches workouts from TrainingPeaks between two dates.

        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)

        Returns:
            List of workout dictionaries formatted for CSV export
        """
        import time

        token = self._get_access_token()
        athlete_id = self._get_athlete_id()
        url = (
            f"{BASE_URL}/fitness/v6/athletes/{athlete_id}/"
            f"workouts/{start_date}/{end_date}"
        )

        headers = {"Authorization": f"Bearer {token}"}

        try:
            logger.info(
                f"📅 Fetching TrainingPeaks workouts from {start_date} to {end_date}..."
            )
            response = requests.get(url, headers=headers, timeout=settings.API_TIMEOUT)
            response.raise_for_status()
            workouts = response.json()
            if not isinstance(workouts, list):
                logger.error(
                    f"❌ Unexpected response format from TP workouts: "
                    f"expected list, got {type(workouts).__name__}"
                )
                return []

            logger.info(
                f"✅ Found {len(workouts)} workouts in range. "
                "Fetching analysis & formatting..."
            )

            TP_WORKOUT_TYPE_MAP = {
                1: "Swim",
                2: "Bike",
                3: "Run",
                9: "Strength",
                13: "Walk",
            }

            def val_or_empty(val):
                return val if val is not None else ""

            records = []
            for w in workouts:
                if not isinstance(w, dict):
                    continue
                workout_id = w.get("workoutId")
                if not workout_id:
                    continue

                # Format comments
                athlete_comments_list = []
                coach_comments_list = []
                for c in w.get("workoutComments") or []:
                    try:
                        dt_created = parser.isoparse(c["dateCreated"])
                        dt_str = dt_created.strftime("%m/%d/%Y")
                        formatted_comment = (
                            f" *{dt_str} {c['commenterName']}: {c['comment']}*"
                        )
                        if c.get("isCoach"):
                            coach_comments_list.append(formatted_comment)
                        else:
                            athlete_comments_list.append(formatted_comment)
                    except Exception:
                        pass

                athlete_comments = "\n".join(athlete_comments_list)
                coach_comments = "\n".join(coach_comments_list)

                # Initialize CSV dictionary with default empty strings
                record = {
                    "Title": val_or_empty(w.get("title")),
                    "WorkoutType": TP_WORKOUT_TYPE_MAP.get(
                        w.get("workoutTypeValueId"), val_or_empty(w.get("userTags"))
                    ),
                    "WorkoutDescription": val_or_empty(w.get("description")),
                    "PlannedDuration": val_or_empty(w.get("totalTimePlanned")),
                    "PlannedDistanceInMeters": val_or_empty(w.get("distancePlanned")),
                    "WorkoutDay": w.get("workoutDay")[:10]
                    if w.get("workoutDay")
                    else "",
                    "CoachComments": coach_comments,
                    "DistanceInMeters": val_or_empty(w.get("distance")),
                    "PowerAverage": val_or_empty(w.get("powerAverage")),
                    "PowerMax": val_or_empty(w.get("powerMaximum")),
                    "Energy": val_or_empty(w.get("energy")),
                    "AthleteComments": athlete_comments,
                    "TimeTotalInHours": val_or_empty(w.get("totalTime")),
                    "VelocityAverage": val_or_empty(w.get("velocityAverage")),
                    "VelocityMax": val_or_empty(w.get("velocityMaximum")),
                    "CadenceAverage": val_or_empty(w.get("cadenceAverage")),
                    "CadenceMax": val_or_empty(w.get("cadenceMaximum")),
                    "HeartRateAverage": val_or_empty(w.get("heartRateAverage")),
                    "HeartRateMax": val_or_empty(w.get("heartRateMaximum")),
                    "TorqueAverage": val_or_empty(w.get("torqueAverage")),
                    "TorqueMax": val_or_empty(w.get("torqueMaximum")),
                    "IF": val_or_empty(w.get("if")),
                    "TSS": val_or_empty(w.get("tssActual")),
                    # Zone columns initialized to empty
                    "HRZone1Minutes": "",
                    "HRZone2Minutes": "",
                    "HRZone3Minutes": "",
                    "HRZone4Minutes": "",
                    "HRZone5Minutes": "",
                    "HRZone6Minutes": "",
                    "HRZone7Minutes": "",
                    "HRZone8Minutes": "",
                    "HRZone9Minutes": "",
                    "HRZone10Minutes": "",
                    "PWRZone1Minutes": "",
                    "PWRZone2Minutes": "",
                    "PWRZone3Minutes": "",
                    "PWRZone4Minutes": "",
                    "PWRZone5Minutes": "",
                    "PWRZone6Minutes": "",
                    "PWRZone7Minutes": "",
                    "PWRZone8Minutes": "",
                    "PWRZone9Minutes": "",
                    "PWRZone10Minutes": "",
                    "Rpe": val_or_empty(w.get("rpe")),
                    "Feeling": val_or_empty(w.get("feeling")),
                    "Elevation": val_or_empty(w.get("elevationGain")),
                }

                # Retrieve analysis if workout is completed and has duration/details
                total_time = w.get("totalTime")
                if total_time and total_time > 0:
                    time.sleep(0.15)  # Rate limiting throttle
                    analysis_url = (
                        "https://api.peakswaresb.com/workout-analysis/v1/analyze"
                    )
                    analysis_headers = {
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    }
                    analysis_payload = {
                        "workoutId": workout_id,
                        "viewingPersonId": athlete_id,
                    }

                    try:
                        analysis_r = requests.post(
                            analysis_url,
                            headers=analysis_headers,
                            json=analysis_payload,
                            timeout=settings.API_TIMEOUT,
                        )
                        if analysis_r.status_code == 200:
                            analysis_data = analysis_r.json()
                            if not isinstance(analysis_data, dict):
                                logger.warning(
                                    f"⚠️ Unexpected analysis type for {workout_id}: "
                                    f"expected dict, got {type(analysis_data).__name__}"
                                )
                                continue

                            data_elements = analysis_data.get("dataElements")
                            if not isinstance(data_elements, list):
                                data_elements = []

                            hr_element = next(
                                (
                                    de
                                    for de in data_elements
                                    if isinstance(de, dict)
                                    and de.get("identifier") == "HeartRate"
                                ),
                                None,
                            )
                            pwr_element = next(
                                (
                                    de
                                    for de in data_elements
                                    if isinstance(de, dict)
                                    and de.get("identifier") == "Power"
                                ),
                                None,
                            )

                            hr_zones = hr_element.get("zones") if hr_element else []
                            pwr_zones = pwr_element.get("zones") if pwr_element else []
                            if not isinstance(hr_zones, list):
                                hr_zones = []
                            if not isinstance(pwr_zones, list):
                                pwr_zones = []

                            data_points = analysis_data.get("data")
                            if not isinstance(data_points, list):
                                data_points = []

                            hr_zone_seconds = [0] * 10
                            pwr_zone_seconds = [0] * 10

                            for i in range(1, len(data_points)):
                                prev_pt = data_points[i - 1]
                                curr_pt = data_points[i]
                                if not isinstance(prev_pt, dict) or not isinstance(
                                    curr_pt, dict
                                ):
                                    continue
                                t_curr = curr_pt.get("time")
                                t_prev = prev_pt.get("time")
                                if t_curr is None or t_prev is None:
                                    continue
                                dt = t_curr - t_prev
                                if dt <= 0:
                                    continue

                                hr = curr_pt.get("HeartRate")
                                if hr is not None:
                                    for idx, z in enumerate(hr_zones):
                                        z_min = z.get("min", 0)
                                        z_max = z.get("max", 999)
                                        if z_max == 0 or z_max is None:
                                            z_max = 999
                                        if z_min <= hr <= z_max:
                                            if idx < 10:
                                                hr_zone_seconds[idx] += dt
                                            break

                                pwr = curr_pt.get("Power")
                                if pwr is not None:
                                    for idx, z in enumerate(pwr_zones):
                                        z_min = z.get("min", 0)
                                        z_max = z.get("max", 999)
                                        if z_max == 0 or z_max is None:
                                            z_max = 999
                                        if z_min <= pwr <= z_max:
                                            if idx < 10:
                                                pwr_zone_seconds[idx] += dt
                                            break

                            # Map zone seconds to rounded minutes
                            for idx in range(10):
                                if idx < len(hr_zones):
                                    record[f"HRZone{idx + 1}Minutes"] = round(
                                        hr_zone_seconds[idx] / 60
                                    )
                                if idx < len(pwr_zones):
                                    record[f"PWRZone{idx + 1}Minutes"] = round(
                                        pwr_zone_seconds[idx] / 60
                                    )

                    except Exception as analysis_err:
                        logger.warning(
                            f"⚠️ No analysis for workout {workout_id}: {analysis_err}"
                        )

                records.append(record)

            return records
        except Exception as e:
            logger.error(f"❌ TP get_workouts Error: {e}")
            return []

    def get_metrics(self, start_date: str, end_date: str) -> list[dict]:
        """
        Fetches metrics/wellness data from TrainingPeaks between two dates.

        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)

        Returns:
            List of metrics dictionaries formatted for CSV export
        """
        token = self._get_access_token()
        athlete_id = self._get_athlete_id()
        url = (
            f"{BASE_URL}/metrics/v3/athletes/{athlete_id}/"
            f"consolidatedtimedmetrics/{start_date}/{end_date}"
        )

        headers = {"Authorization": f"Bearer {token}"}

        try:
            logger.info(
                f"📊 Fetching TrainingPeaks metrics from {start_date} to {end_date}..."
            )
            response = requests.get(url, headers=headers, timeout=settings.API_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                logger.error(
                    f"❌ Unexpected response format from TP metrics: "
                    f"expected list, got {type(data).__name__}"
                )
                return []

            LABEL_MAP = {
                "Time in Deep Sleep": "Time In Deep Sleep",
                "Time in Light Sleep": "Time In Light Sleep",
                "Time in REM Sleep": "Time In REM Sleep",
            }

            records = []
            for day in data:
                if not isinstance(day, dict):
                    continue
                day_ts = day.get("timeStamp")
                if not day_ts:
                    continue

                for detail in day.get("details") or []:
                    if not isinstance(detail, dict):
                        continue
                    label = detail.get("label", "")
                    label = LABEL_MAP.get(label, label)

                    val = detail.get("value")
                    val_str = ""

                    if isinstance(val, list):
                        parts = []
                        if len(val) >= 3:
                            min_val, max_val, avg_val = val[0], val[1], val[2]
                            if min_val is not None:
                                min_fmt = (
                                    int(min_val)
                                    if isinstance(min_val, (int, float))
                                    else min_val
                                )
                                parts.append(f"Min : {min_fmt}")
                            if max_val is not None:
                                max_fmt = (
                                    int(max_val)
                                    if isinstance(max_val, (int, float))
                                    else max_val
                                )
                                parts.append(f"Max : {max_fmt}")
                            if avg_val is not None:
                                avg_fmt = (
                                    int(avg_val)
                                    if isinstance(avg_val, (int, float))
                                    else avg_val
                                )
                                parts.append(f"Avg : {avg_fmt}")
                        val_str = " / ".join(parts)
                    elif isinstance(val, (int, float)):
                        if isinstance(val, float) and label == "Sleep Hours":
                            val_str = str(round(val, 2))
                        elif isinstance(val, float) and val.is_integer():
                            val_str = str(int(val))
                        else:
                            val_str = str(val)
                    elif val is not None:
                        val_str = str(val)

                    # Get timestamp for this detail or fallback to day's timestamp
                    detail_ts = detail.get("time") or day_ts
                    # Convert 'T' to space
                    formatted_ts = detail_ts.replace("T", " ")

                    records.append(
                        {"Timestamp": formatted_ts, "Type": label, "Value": val_str}
                    )

            logger.info(f"✅ Retrieved {len(records)} metric records")
            return records
        except Exception as e:
            logger.error(f"❌ TP get_metrics Error: {e}")
            return []
