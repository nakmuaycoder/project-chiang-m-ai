import hashlib
import json
from pathlib import Path
from typing import List

from pydantic import ValidationError

from project_chiang_m_ai.interfaces.brain import IBrain, WorkoutWithSource
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.models.workout import Workout


class MockFileBrain(IBrain):
    """
    Brain that reads pre-defined workouts from a local JSON file.
    Useful for testing the platform push logic without needing the calendar.
    """

    def __init__(self, file_path: str = "data/mock_workouts.json"):
        self.file_path = Path(file_path)

    def get_final_workouts(
        self, wellness_data: list[dict] | None = None
    ) -> List[WorkoutWithSource]:
        logger.info(f"🧠 [MockFileBrain] Reading workouts from {self.file_path}...")

        if not self.file_path.exists():
            logger.error(f"❌ [MockFileBrain] File {self.file_path} does not exist.")
            return []

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                workouts_json = json.load(f)

            if not isinstance(workouts_json, list):
                logger.error("❌ [MockFileBrain] JSON must be a list of workouts.")
                return []

            results = []
            for w in workouts_json:
                # Derive a stable source_id from the content hash so that
                # unchanged workouts are not re-uploaded on every run.
                content_hash = hashlib.sha256(
                    json.dumps(w, sort_keys=True).encode()
                ).hexdigest()
                source_id = f"mock_{content_hash[:16]}"
                results.append(
                    WorkoutWithSource(source_id=source_id, workout=Workout(**w))
                )
            return results

        except FileNotFoundError:
            logger.error(f"❌ [MockFileBrain] Workout file not found: {self.file_path}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"❌ [MockFileBrain] Invalid JSON in {self.file_path}: {e}")
            return []
        except ValidationError as e:
            logger.error(
                f"❌ [MockFileBrain] Data validation error in {self.file_path}: {e}"
            )
            return []
