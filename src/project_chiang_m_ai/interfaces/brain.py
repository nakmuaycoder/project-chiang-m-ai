from abc import ABC, abstractmethod
from typing import List

from project_chiang_m_ai.models.workout import WorkoutUnion


class IBrain(ABC):
    """
    The Brain is responsible for determining the final workouts
    to be executed based on available context.
    """

    @abstractmethod
    def get_final_workouts(
        self, wellness_data: list[dict] | None = None
    ) -> List[WorkoutUnion]:
        """
        Calculates and returns the final workouts to sync.

        Args:
            wellness_data: Optional wellness metrics history (e.g. HRV, RHR)
                         to adapt the workout load.

        Returns:
            List of Workout objects ready to be sent to the platform.
        """
        pass
