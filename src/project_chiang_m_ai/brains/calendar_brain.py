from typing import List

from project_chiang_m_ai.brains.base_calendar_brain import CalendarBaseBrain
from project_chiang_m_ai.clients.google_calendar import GoogleCalendarClient
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.models.workout import WorkoutUnion


class GoogleCalendarBrain(CalendarBaseBrain):
    """
    Brain that blindly trusts Google Calendar.
    It reads coach events from the calendar and assumes they are the final workouts.
    This corresponds to the "Manual" mode where you use the mobile app.
    """

    def __init__(
        self,
        calendar_client: GoogleCalendarClient,
        sync_mode: str = "all",
        days: int = 28,
    ):
        super().__init__(
            calendar_client=calendar_client, sync_mode=sync_mode, days=days
        )

    def get_final_workouts(
        self, wellness_data: list[dict] | None = None
    ) -> List[WorkoutUnion]:
        """Reads workouts from Google Calendar and returns them as final."""
        logger.info(
            "🧠 [GoogleCalendarBrain] Fetching calendar events "
            "to decide on final workouts..."
        )

        filtered_events = self._fetch_filtered_events()
        final_workouts = []

        for event in filtered_events:
            payload = self._parse_event_payload(event)
            if payload is None:
                continue
            workout = self._build_workout(payload, event)
            if workout is not None:
                final_workouts.append(workout)

        logger.info(
            f"🧠 [GoogleCalendarBrain] Decided on {len(final_workouts)} final workouts."
        )
        return final_workouts
