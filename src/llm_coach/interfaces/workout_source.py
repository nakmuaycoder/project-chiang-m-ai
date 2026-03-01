"""
Abstract interface for workout sources.
A workout source is anything that can provide a list of workouts.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from llm_coach.models.workout import Workout


class IWorkoutSource(ABC):
    """
    Abstract source of workouts.

    Implementations could be:
    - CalendarWorkoutSource: Reads from calendar events
    - DirectLLMWorkoutSource: Generates via LLM
    - FileWorkoutSource: Loads from JSON/YAML files
    - APIWorkoutSource: Fetches from external API
    """

    @abstractmethod
    def get_workouts(
        self, start_date: datetime, end_date: datetime, max_results: int = 100
    ) -> List[Workout]:
        """
        Retrieve workouts from this source within the date range.

        Args:
            start_date: Start of the date range
            end_date: End of the date range
            max_results: Maximum number of workouts to retrieve

        Returns:
            List of Workout objects
        """
        pass
