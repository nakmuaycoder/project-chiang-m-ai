import html
import json
from datetime import datetime, timedelta, timezone
from typing import List

from pydantic import ValidationError

from project_chiang_m_ai.clients.google_calendar import GoogleCalendarClient
from project_chiang_m_ai.interfaces.brain import IBrain
from project_chiang_m_ai.interfaces.llm import ILlmClient
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.models.workout import Workout, WorkoutUnion


class AutoAdaptiveBrain(IBrain):
    """
    Brain that evaluates the scheduled workouts against the current wellness data
    using a Large Language Model.
    """

    def __init__(
        self,
        calendar_client: GoogleCalendarClient,
        llm_client: ILlmClient,
        sync_mode: str = "today",
        days: int = 1,
    ):
        self.calendar_client = calendar_client
        self.llm_client = llm_client
        self.sync_mode = sync_mode
        self.days = days

    def get_final_workouts(
        self, wellness_data: list[dict] | None = None
    ) -> List[WorkoutUnion]:
        """Reads workouts from Google Calendar and asks LLM to adapt them."""
        logger.info(
            "🧠 [AutoAdaptiveBrain] Fetching events and asking LLM to review..."
        )

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        future_limit = today_start + timedelta(days=self.days)

        events = self.calendar_client.list_upcoming_events(
            max_results=100, time_min=today_start.isoformat()
        )
        coach_events = [e for e in events if "coach" in e.summary.lower()]

        filtered_events = []
        if self.sync_mode == "today":
            filtered_events = [
                e
                for e in coach_events
                if e.start and today_start <= e.start < today_end
            ]
        else:
            filtered_events = [
                e
                for e in coach_events
                if e.start and today_start <= e.start < future_limit
            ]

        if not filtered_events:
            logger.info(
                "🧠 [AutoAdaptiveBrain] No events to evaluate. Returning empty plan."
            )
            return []

        # Gather workouts
        daily_workouts_payload = []
        valid_events = []

        for event in filtered_events:
            description = (event.description or "").strip()
            if not description:
                continue

            try:
                description = html.unescape(description)
                workout_json = json.loads(description)
                if "original_workout" in workout_json:
                    workout_json = workout_json["original_workout"]

                daily_workouts_payload.append(workout_json)
                valid_events.append(event)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON for event '{event.summary}': {e}")

        if not daily_workouts_payload:
            return []

        if not wellness_data:
            logger.warning(
                "🧠 [AutoAdaptiveBrain] No wellness data provided. "
                "Cannot adapt, falling back to original."
            )
            # fallback to calendar brain behaviour
            final_workouts = []
            for i, evt in enumerate(valid_events):
                payload = daily_workouts_payload[i]
                if "start_date_local" not in payload or not payload["start_date_local"]:
                    payload["start_date_local"] = evt.start.isoformat()
                try:
                    final_workouts.append(Workout(**payload))
                except ValidationError as e:
                    logger.error(
                        f"❌ [AutoAdaptiveBrain] Validation error for "
                        f"'{evt.summary}': {e}"
                    )
            return final_workouts

        # Send to LLM
        adapted_workouts_json = self.llm_client.adapt_daily_workouts(
            daily_workouts_json=daily_workouts_payload, wellness_history=wellness_data
        )

        if not adapted_workouts_json or not isinstance(adapted_workouts_json, list):
            logger.error("❌ LLM returned invalid array data. Cannot adapt.")
            return []

        final_workouts = []

        for idx, event in enumerate(valid_events):
            if idx >= len(adapted_workouts_json):
                break

            adapted_workout_json = adapted_workouts_json[idx]
            original_workout_json = daily_workouts_payload[idx]

            if not isinstance(adapted_workout_json, dict):
                continue

            adapted_workout_json["original_workout"] = original_workout_json

            # Instead of updating the calendar right now, we just parse and return it
            # The calling code (Coach) might decide to update the calendar separately
            if (
                "start_date_local" not in adapted_workout_json
                or not adapted_workout_json["start_date_local"]
            ):
                adapted_workout_json["start_date_local"] = event.start.isoformat()

            try:
                final_workouts.append(Workout(**adapted_workout_json))
            except ValidationError as e:
                logger.error(
                    f"❌ [AutoAdaptiveBrain] Validation error for "
                    f"adapted workout '{event.summary}': {e}"
                )

        logger.info(
            "🧠 [AutoAdaptiveBrain] Decided on "
            f"{len(final_workouts)} adapted final workouts."
        )
        return final_workouts
