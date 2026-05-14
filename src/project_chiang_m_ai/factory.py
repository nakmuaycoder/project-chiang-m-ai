"""
Factory functions for creating provider instances based on configuration.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from project_chiang_m_ai.interfaces.llm import ILlmClient

from project_chiang_m_ai.clients.google_calendar import GoogleCalendarClient
from project_chiang_m_ai.config import coach_config
from project_chiang_m_ai.interfaces.brain import IBrain
from project_chiang_m_ai.interfaces.calendar import ICalendarProvider
from project_chiang_m_ai.interfaces.platform import ISportPlatform
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


def get_platform() -> ISportPlatform:
    """Factory to instantiate the configured
    sport platform (Intervals, TrainingPeaks or Fake)."""
    dest_config = coach_config.get("coach", {}).get("destination", {})
    dest_type = dest_config.get("type", "intervals_icu")

    if dest_type == "local_storage":
        from project_chiang_m_ai.clients.local_platform import LocalArchivePlatform

        path = dest_config.get("path", "data/runs")
        return LocalArchivePlatform(output_dir=path)
    elif dest_type == "trainingpeaks":
        # Default to Intervals.icu
        from project_chiang_m_ai.clients.trainingpeaks import TrainingPeaksClient

        return TrainingPeaksClient()
    else:
        # Default to Intervals.icu
        from project_chiang_m_ai.clients.intervalicu import IntervalicuClient

        return IntervalicuClient()


def get_brain(sync_mode: str = "all", days: int = 28) -> IBrain:
    """Factory to instantiate the configured brain."""
    brain_config = coach_config.get("coach", {}).get("brain", {})
    brain_type = brain_config.get("type", "manual")

    if brain_type == "mock":
        from project_chiang_m_ai.brains.file_brain import MockFileBrain

        # Could read from config, but hardcoded for now
        return MockFileBrain()

    elif brain_type == "auto":
        from project_chiang_m_ai.brains.auto_brain import AutoAdaptiveBrain

        calendar = get_calendar_provider()
        llm = get_llm_client()
        return AutoAdaptiveBrain(
            calendar_client=calendar,
            llm_client=llm,
            sync_mode=sync_mode,
            days=days,
        )
    else:
        # manual / default
        from project_chiang_m_ai.brains.calendar_brain import GoogleCalendarBrain

        calendar = get_calendar_provider()
        return GoogleCalendarBrain(
            calendar_client=calendar,
            sync_mode=sync_mode,
            days=days,
        )
