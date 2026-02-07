"""
Factory functions for creating provider instances based on configuration.
"""

from llm_coach.clients.gemini import GeminiClient
from llm_coach.clients.google_calendar import GoogleCalendarClient
from llm_coach.interfaces.calendar import ICalendarProvider
from llm_coach.interfaces.llm import ILLMProvider
from llm_coach.interfaces.workout_source import IWorkoutSource
from llm_coach.sources.calendar_source import CalendarWorkoutSource


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


def get_llm_provider() -> ILLMProvider:
    """
    Factory to instantiate the configured LLM provider.

    Returns:
        Configured ILLMProvider instance

    Raises:
        ValueError: If unknown provider is configured
    """
    # Default to Gemini for now
    # Future: Add LLM_PROVIDER setting to switch between Gemini, ChatGPT, Local
    return GeminiClient()


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
    #   - "llm": DirectLLMWorkoutSource
    #   - "file": FileWorkoutSource

    calendar_provider = get_calendar_provider()
    return CalendarWorkoutSource(calendar_provider)
