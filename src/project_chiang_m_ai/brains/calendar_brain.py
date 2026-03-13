import html
import json
from datetime import datetime, timedelta, timezone
from typing import List

from pydantic import ValidationError

from project_chiang_m_ai.clients.google_calendar import GoogleCalendarClient
from project_chiang_m_ai.interfaces.brain import IBrain
from project_chiang_m_ai.interfaces.calendar import CalendarEvent
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.models.workout import Workout, WorkoutUnion


class GoogleCalendarBrain(IBrain):
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
        self.calendar_client = calendar_client
        self.sync_mode = sync_mode
        self.days = days

    def get_final_workouts(
        self, wellness_data: list[dict] | None = None
    ) -> List[WorkoutUnion]:
        """Reads workouts from Google Calendar and returns them as final."""
        logger.info(
            "🧠 [GoogleCalendarBrain] Fetching calendar events "
            "to decide on final workouts..."
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
                e for e in coach_events if today_start <= e.start < today_end
            ]
        else:
            filtered_events = [
                e for e in coach_events if today_start <= e.start < future_limit
            ]

        final_workouts = []

        for event in filtered_events:
            try:
                workout = self._parse_workout_from_event(event)
                final_workouts.append(workout)
            except (ValueError, json.JSONDecodeError, ValidationError) as e:
                logger.error(f"❌ Error parsing workout from '{event.summary}': {e}")

        logger.info(
            f"🧠 [GoogleCalendarBrain] Decided on {len(final_workouts)} final workouts."
        )
        return final_workouts

    def _parse_workout_from_event(self, event: CalendarEvent) -> WorkoutUnion:
        description = (event.description or "").strip()
        if not description:
            raise ValueError(f"Event '{event.summary}' has no description")

        description = html.unescape(description)
        payload = json.loads(description)

        if "original_workout" in payload:
            payload = payload["original_workout"]

        if "start_date_local" not in payload or not payload["start_date_local"]:
            payload["start_date_local"] = event.start.isoformat()

        return Workout(**payload)
