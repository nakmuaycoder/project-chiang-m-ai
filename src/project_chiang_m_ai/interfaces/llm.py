from abc import ABC, abstractmethod
from typing import Dict, List


class ILlmClient(ABC):
    """
    Abstract interface for LLM providers (Gemini, Claude, OpenAI, etc).
    All AI coach clients must implement this interface.
    """

    @abstractmethod
    def adapt_daily_workouts(
        self, daily_workouts_json: List[Dict], wellness_history: List[Dict]
    ) -> List[Dict]:
        """
        Send all scheduled workouts for the day and the wellness history to the LLM
        to generate adapted training sessions.

        Args:
            daily_workouts_json (List[Dict]): Original workouts parsed from Calendar.
            wellness_history (List[Dict]): The raw wellness data from Intervals.icu

        Returns:
            List[Dict]: The adapted workouts JSONs in the same order.
        """
        pass
