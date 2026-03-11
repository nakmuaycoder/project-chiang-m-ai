"""
Factory functions for creating provider instances based on configuration.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from project_chiang_m_ai.interfaces.llm import ILlmClient

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


def get_llm_client() -> "ILlmClient":
    """
    Factory function to retrieve the appropriate LLM client based
    on the user's environment variable (LLM_PROVIDER).
    """
    from project_chiang_m_ai.config import settings

    provider = settings.LLM_PROVIDER.lower()

    if provider == "gemini":
        from project_chiang_m_ai.clients.gemini import GeminiClient

        return GeminiClient()
    # To add a different model for other users who fork this repo:
    # elif provider == "anthropic":
    #     from project_chiang_m_ai.clients.anthropic import AnthropicClient
    #     return AnthropicClient()
    # elif provider == "openai":
    #     from project_chiang_m_ai.clients.openai import OpenaiClient
    #     return OpenaiClient()
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: {provider}. Supported providers: gemini"
        )
