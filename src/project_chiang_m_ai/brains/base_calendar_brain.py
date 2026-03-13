"""
Base class for Calendar-backed Brains.

Provides shared logic for fetching, filtering and parsing coach events
from Google Calendar. Subclasses implement only their adaptation strategy.
"""

import html
import json
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from pydantic import ValidationError

from project_chiang_m_ai.clients.google_calendar import GoogleCalendarClient
from project_chiang_m_ai.interfaces.brain import IBrain, WorkoutWithSource
from project_chiang_m_ai.interfaces.calendar import CalendarEvent
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.models.workout import Workout, WorkoutUnion


class CalendarBaseBrain(IBrain):
    """
    Abstract base class for Brains that source workouts from Google Calendar.

    Handles:
      - Fetching upcoming events from the calendar
      - Filtering by sync_mode ("today" or "all") and day window
      - Parsing raw JSON workout payloads from event descriptions
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

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _fetch_filtered_events(self) -> List[CalendarEvent]:
        """
        Fetches coach events from the calendar and filters them by date window.

        Returns:
            List of CalendarEvent matching the configured sync_mode and days.
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        future_limit = today_start + timedelta(days=self.days)

        events = self.calendar_client.list_upcoming_events(
            max_results=100, time_min=today_start.isoformat()
        )
        coach_events = [e for e in events if "coach" in e.summary.lower()]

        if self.sync_mode == "today":
            return [
                e
                for e in coach_events
                if e.start and today_start <= e.start < today_end
            ]
        return [
            e for e in coach_events if e.start and today_start <= e.start < future_limit
        ]

    def get_current_source_ids(self) -> list[str]:
        """
        Returns the calendar event IDs of all currently active coach events.
        Used by CoachService to detect orphaned platform workouts.
        """
        events = self._fetch_filtered_events()
        return [e.id for e in events]

    def _parse_event_payload(
        self, event: CalendarEvent, strip_adapted: bool = True
    ) -> dict | None:
        """
        Parses the JSON workout payload from a calendar event description.

        Args:
            event: The CalendarEvent to parse.
            strip_adapted: If True, unwrap "original_workout" when present
                           (i.e., skip previously adapted wrappers).

        Returns:
            Parsed workout dict, or None if parsing fails.
        """
        description = (event.description or "").strip()
        if not description:
            logger.warning(f"⚠️ Event '{event.summary}' has no description. Skipping.")
            return None

        try:
            payload = json.loads(html.unescape(description))
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON for event '{event.summary}': {e}")
            return None

        has_adapted = isinstance(payload, dict) and "original_workout" in payload
        if strip_adapted and has_adapted:
            payload = payload["original_workout"]

        if "start_date_local" not in payload or not payload["start_date_local"]:
            payload["start_date_local"] = event.start.isoformat()

        return payload

    def _build_workout(
        self, payload: dict, event: CalendarEvent
    ) -> WorkoutUnion | None:
        """
        Instantiates a Workout from a validated payload dict.

        Returns None (with logging) if validation fails.
        """
        try:
            return Workout(**payload)
        except ValidationError as e:
            logger.error(f"❌ Workout validation error for '{event.summary}': {e}")
            return None

    def _build_workout_with_source(
        self, payload: dict, event: CalendarEvent
    ) -> "WorkoutWithSource | None":
        """
        Builds a WorkoutWithSource using the calendar event ID as stable source_id.
        Returns None if validation fails.
        """
        workout = self._build_workout(payload, event)
        if workout is None:
            return None
        return WorkoutWithSource(source_id=event.id, workout=workout)

    def _collect_valid_payloads(
        self, events: List[CalendarEvent]
    ) -> Tuple[List[dict], List[CalendarEvent]]:
        """
        Parses all events and returns only those with valid payloads.

        Returns:
            Tuple of (list of raw workout dicts, list of corresponding events).
        """
        payloads, valid_events = [], []
        for event in events:
            payload = self._parse_event_payload(event)
            if payload is not None:
                payloads.append(payload)
                valid_events.append(event)
        return payloads, valid_events

    def _build_workouts_from_payloads_and_events(
        self, payloads: List[dict], events: List[CalendarEvent]
    ) -> List[WorkoutWithSource]:
        """
        Iterates over payloads and events to build a list of WorkoutWithSource
        instances. Any payloads that fail validation are ignored.
        """
        final_workouts = []
        for payload, event in zip(payloads, events):
            ws = self._build_workout_with_source(payload, event)
            if ws is not None:
                final_workouts.append(ws)
        return final_workouts
