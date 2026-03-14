from typing import List

from pydantic import ValidationError

from project_chiang_m_ai.brains.base_calendar_brain import CalendarBaseBrain
from project_chiang_m_ai.clients.google_calendar import GoogleCalendarClient
from project_chiang_m_ai.interfaces.brain import WorkoutWithSource
from project_chiang_m_ai.interfaces.llm import ILlmClient
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.models.workout import Workout


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
    ) -> List[WorkoutWithSource]:
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

        # 1. Inject source_id into payloads for LLM reconciliation
        # and create a lookup map for original data
        original_data_map = {}
        llm_payload = []

        for payload, event in zip(daily_workouts_payload, valid_events):
            payload["source_id"] = event.id
            llm_payload.append(payload)
            original_data_map[event.id] = {
                "event": event,
                "original_payload": list(daily_workouts_payload)[
                    daily_workouts_payload.index(payload)
                ].copy(),
            }

        # Fall back to original workouts if no wellness data is available
        if not wellness_data:
            logger.warning(
                "🧠 [AutoAdaptiveBrain] No wellness data provided. "
                "Cannot adapt, falling back to original."
            )
            return self._build_workouts_from_payloads_and_events(
                daily_workouts_payload, valid_events
            )

        # 2. Send to LLM
        adapted_workouts_list = self.llm_client.adapt_daily_workouts(
            daily_workouts_json=llm_payload, wellness_history=wellness_data
        )

        if not adapted_workouts_list or not isinstance(adapted_workouts_list, list):
            logger.error("❌ LLM returned invalid array data. Cannot adapt.")
            return []

        # 3. Map adapted results by source_id for quick lookup
        adapted_by_id = {}
        for item in adapted_workouts_list:
            if isinstance(item, dict) and "source_id" in item:
                adapted_by_id[item["source_id"]] = item

        # 4. Reconcile by iterating over original events to preserve order
        final_workouts = []
        for event_id, mapping in original_data_map.items():
            event = mapping["event"]
            original_workout_json = mapping["original_payload"]

            # Check if LLM returned an adapted version
            adapted_workout_json = adapted_by_id.get(event_id)

            if not adapted_workout_json:
                logger.warning(
                    f"⚠️ [AutoAdaptiveBrain] LLM missed workout '{event.summary}' "
                    f"(ID: {event_id}). Falling back to original."
                )
                # Fallback to original for this specific workout
                adapted_workout_json = original_workout_json
            else:
                # Use adapted version
                adapted_workout_json.pop("source_id", None)
                adapted_workout_json["original_workout"] = original_workout_json

            if (
                "start_date_local" not in adapted_workout_json
                or not adapted_workout_json["start_date_local"]
            ):
                adapted_workout_json["start_date_local"] = event.start.isoformat()

            try:
                final_workouts.append(
                    WorkoutWithSource(
                        source_id=event.id,
                        workout=Workout(**adapted_workout_json),
                    )
                )
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
