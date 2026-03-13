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

    def get_current_source_ids(self) -> list[str] | None:
        """
        Returns the set of currently active source IDs known to this brain.

        Used by CoachService to detect and clean up orphaned workouts on the
        platform (e.g. workouts whose source calendar event has been deleted).

        Returns:
            - A list of source ID strings if the brain supports cleanup.
            - None if the brain cannot enumerate active sources (e.g. MockFileBrain).
              CoachService will skip cleanup in that case.
        """
        return None
