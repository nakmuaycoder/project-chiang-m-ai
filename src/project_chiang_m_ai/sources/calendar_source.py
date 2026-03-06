"""
Calendar-based workout source.
Reads workouts from calendar events containing JSON workout definitions.
"""

import json
from datetime import datetime
from typing import List

from project_chiang_m_ai.interfaces.calendar import ICalendarProvider
from project_chiang_m_ai.interfaces.workout_source import IWorkoutSource
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.models.workout import Workout


class CalendarWorkoutSource(IWorkoutSource):
    """
    Reads workouts from calendar events.

    Each calendar event should have a JSON workout definition in its description.
    This is the current workflow where LLM generates JSON that's manually
    added to calendar events, then synced to Intervals.icu.
    """

    def __init__(self, calendar_provider: ICalendarProvider):
        """
        Initialize the calendar workout source.

        Args:
            calendar_provider: Any ICalendarProvider implementation
                              (GoogleCalendarClient, OutlookCalendarClient, etc.)
        """
        self.calendar = calendar_provider

    def get_workouts(
        self, start_date: datetime, end_date: datetime, max_results: int = 100
    ) -> List[Workout]:
        """
        Retrieve workouts from calendar events.

        Args:
            start_date: Start of the date range (currently unused, fetches upcoming)
            end_date: End of the date range (currently unused)
            max_results: Maximum number of events to fetch

        Returns:
            List of Workout objects parsed from calendar events
        """
        # Fetch calendar events
        events = self.calendar.list_upcoming_events(max_results=max_results)

        workouts = []
        errors = []

        for event in events:
            try:
                # Parse JSON from event description
                if not event.description:
                    continue

                workout_data = json.loads(event.description)
                workout = Workout(**workout_data)
                workouts.append(workout)

            except json.JSONDecodeError as e:
                errors.append(
                    {
                        "event": event.summary,
                        "error": f"Invalid JSON: {e}",
                        "description": event.description[:100]
                        if event.description
                        else None,
                    }
                )
            except Exception as e:
                errors.append(
                    {
                        "event": event.summary,
                        "error": f"Failed to create Workout: {e}",
                        "data": workout_data if "workout_data" in locals() else None,
                    }
                )

        # Log errors (could be improved with proper logging)
        if errors:
            logger.warning(
                f"⚠️  Encountered {len(errors)} error(s) parsing calendar events:"
            )
            for err in errors:
                logger.info(f"   - {err['event']}: {err['error']}")

        return workouts
