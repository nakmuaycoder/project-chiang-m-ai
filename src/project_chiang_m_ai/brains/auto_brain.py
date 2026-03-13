from typing import List

from pydantic import ValidationError

from project_chiang_m_ai.brains.base_calendar_brain import CalendarBaseBrain
from project_chiang_m_ai.clients.google_calendar import GoogleCalendarClient
from project_chiang_m_ai.interfaces.llm import ILlmClient
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.models.workout import Workout, WorkoutUnion


class AutoAdaptiveBrain(CalendarBaseBrain):
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
        super().__init__(
            calendar_client=calendar_client, sync_mode=sync_mode, days=days
        )
        self.llm_client = llm_client

    def get_final_workouts(
        self, wellness_data: list[dict] | None = None
    ) -> List[WorkoutUnion]:
        """Reads workouts from Google Calendar and asks LLM to adapt them."""
        logger.info(
            "🧠 [AutoAdaptiveBrain] Fetching events and asking LLM to review..."
        )

        filtered_events = self._fetch_filtered_events()
        if not filtered_events:
            logger.info(
                "🧠 [AutoAdaptiveBrain] No events to evaluate. Returning empty plan."
            )
            return []

        daily_workouts_payload, valid_events = self._collect_valid_payloads(
            filtered_events
        )

        if not daily_workouts_payload:
            return []

        # Fall back to original workouts if no wellness data is available
        if not wellness_data:
            logger.warning(
                "🧠 [AutoAdaptiveBrain] No wellness data provided. "
                "Cannot adapt, falling back to original."
            )
            final_workouts = []
            for payload, event in zip(daily_workouts_payload, valid_events):
                workout = self._build_workout(payload, event)
                if workout is not None:
                    final_workouts.append(workout)
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
