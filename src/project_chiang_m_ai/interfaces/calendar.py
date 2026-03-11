"""
Abstract interface for calendar providers.
Allows swapping between Google Calendar, Outlook, etc.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional


class CalendarEvent:
    """
    Standard calendar event model (provider-agnostic).
    """

    def __init__(
        self,
        id: str,
        summary: str,
        description: Optional[str],
        start: datetime,
        end: datetime,
        raw_data: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.summary = summary
        self.description = description
        self.start = start
        self.end = end
        self.raw_data = raw_data  # Keep original data for debugging


class ICalendarProvider(ABC):
    """
    Interface that any calendar provider must implement.

    Implementations:
    - GoogleCalendarClient
    - OutlookCalendarClient
    - AppleCalendarClient
    """

    @abstractmethod
    def list_upcoming_events(
        self,
        max_results: int = 10,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
    ) -> List[CalendarEvent]:
        """
        List upcoming events from the calendar.

        Args:
            max_results: Maximum number of events to return
            calendar_id: Calendar ID (default: primary)
            time_min: Minimum start time string in ISO format.
                      If None, defaults to current time.

        Returns:
            List of CalendarEvent objects
        """
        pass

    @abstractmethod
    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        calendar_id: str = "primary",
    ) -> Optional[CalendarEvent]:
        """
        Create a new event in the calendar.

        Args:
            summary: Event title
            start_time: Start datetime
            end_time: End datetime
            description: Event description
            location: Event location
            calendar_id: Calendar ID (default: primary)

        Returns:
            Created CalendarEvent or None if failed
        """
        pass

    @abstractmethod
    def delete_event(self, event_id: str, calendar_id: str = "primary") -> bool:
        """
        Delete an event from the calendar.

        Args:
            event_id: Event ID to delete
            calendar_id: Calendar ID (default: primary)

        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    def update_event_description(
        self, event_id: str, new_description: str, calendar_id: str = "primary"
    ) -> Optional[CalendarEvent]:
        """
        Update the description of an event in the calendar.

        Args:
            event_id: Event ID to update
            new_description: New description
            calendar_id: Calendar ID (default: primary)

        Returns:
            Updated CalendarEvent or None if failed
        """
        pass
