from abc import ABC, abstractmethod
from typing import Any, Dict

from project_chiang_m_ai.models.workout import WorkoutUnion


class ISportPlatform(ABC):
    """
    The Sport Platform is responsible for storing and displaying
    workouts and providing wellness data about the athlete.
    """

    @abstractmethod
    def get_wellness_data(self) -> list[dict]:
        """
        Fetches the recent wellness history of the athlete.

        Returns:
            List of wellness data dictionaries, chronologically ordered
        """
        pass

    @abstractmethod
    def push_workout(self, workout: WorkoutUnion) -> Dict[str, Any]:
        """
        Pushes a single workout to the platform.

        Args:
            workout: The Workout instance to upload

        Returns:
            Dict containing at least {"success": bool, "workout_id": ...}
        """
        pass

    @abstractmethod
    def delete_workout(self, workout_id: str | int) -> Dict[str, Any]:
        """
        Deletes a workout from the platform.

        Args:
            workout_id: The platform-specific workout identifier

        Returns:
            Dict containing at least {"success": bool}
        """
        pass

    @abstractmethod
    def get_workouts(self, start_date: str, end_date: str) -> list[dict]:
        """
        Fetches workouts from the platform between two dates.

        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)

        Returns:
            List of workout dictionaries
        """
        pass

    @abstractmethod
    def get_metrics(self, start_date: str, end_date: str) -> list[dict]:
        """
        Fetches metrics/wellness data from the platform between two dates.

        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)

        Returns:
            List of metrics/wellness dictionaries
        """
        pass
