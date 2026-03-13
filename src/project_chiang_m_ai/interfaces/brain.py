from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from project_chiang_m_ai.models.workout import WorkoutUnion


@dataclass
class WorkoutWithSource:
    """
    Pairs a workout with the stable, unique ID of its origin in the source system
    (e.g. a Google Calendar event ID, or a generated UUID for mock data).

    This ensures the CoachService can track and de-duplicate workouts reliably,
    even if the workout's name or date changes between syncs.
    """

    source_id: str
    workout: WorkoutUnion


class IBrain(ABC):
    """
    The Brain is responsible for determining the final workouts
    to be executed based on available context.
    """

    @abstractmethod
    def get_final_workouts(
        self, wellness_data: list[dict] | None = None
    ) -> List[WorkoutWithSource]:
        """
        Calculates and returns the final workouts to sync.

        Args:
            wellness_data: Optional wellness metrics history (e.g. HRV, RHR)
                         to adapt the workout load.

        Returns:
            List of WorkoutWithSource, each pairing a stable source_id
            with the final Workout object.
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
