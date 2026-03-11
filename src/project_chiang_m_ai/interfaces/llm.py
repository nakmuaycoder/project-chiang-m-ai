from abc import ABC, abstractmethod
from typing import Dict, List


class ILlmClient(ABC):
    """
    Abstract interface for LLM providers (Gemini, Claude, OpenAI, etc).
    All AI coach clients must implement this interface.
    """

    @abstractmethod
    def adapt_workout(
        self, current_workout_json: Dict, wellness_history: List[Dict]
    ) -> Dict:
        """
        Send the current workout and the wellness history to the LLM to generate
        an adapted training session.

        Args:
            current_workout_json (Dict): The original workout parsed from Calendar.
            wellness_history (List[Dict]): The raw wellness data from Intervals.icu

        Returns:
            Dict: The adapted workout JSON.
        """
        pass
