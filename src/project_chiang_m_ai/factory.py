"""
Factory functions for creating provider instances based on configuration.
"""

from project_chiang_m_ai.clients.google_calendar import GoogleCalendarClient
from project_chiang_m_ai.interfaces.calendar import ICalendarProvider
from project_chiang_m_ai.interfaces.workout_source import IWorkoutSource
from project_chiang_m_ai.sources.calendar_source import CalendarWorkoutSource


def get_calendar_provider() -> ICalendarProvider:
    """
    Factory to instantiate the configured calendar provider.

    Returns:
        Configured ICalendarProvider instance

    Raises:
        ValueError: If unknown provider is configured
    """
    # For now only Google Calendar is implemented
    # Future: Add CALENDAR_PROVIDER to settings to support Outlook, Apple, etc.
    return GoogleCalendarClient()


def get_workout_source() -> IWorkoutSource:
    """
    Factory to instantiate the configured workout source.

    Returns:
        Configured IWorkoutSource instance

    Raises:
        ValueError: If unknown source is configured
    """
    # For now only calendar source is implemented
    # Future: Add WORKOUT_SOURCE setting to support:
    #   - "calendar": CalendarWorkoutSource
    #   - "file": FileWorkoutSource

    calendar_provider = get_calendar_provider()
    return CalendarWorkoutSource(calendar_provider)
