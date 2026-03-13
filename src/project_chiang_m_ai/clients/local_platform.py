import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from project_chiang_m_ai.interfaces.platform import ISportPlatform
from project_chiang_m_ai.models.workout import WorkoutUnion

logger = logging.getLogger(__name__)


class LocalArchivePlatform(ISportPlatform):
    """
    Fake platform that writes workouts to the local filesystem
    instead of sending them to a real API like Intervals.icu.
    Used for testing and "dry runs".
    """

    def __init__(self, output_dir: str = "data/runs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_wellness_data(self) -> list[dict]:
        """
        Returns dummy wellness data or loads from a mock file if needed.
        """
        logger.info("📊 [LocalArchivePlatform] Fetching mock wellness history...")
        # A simple dummy history for adaptation testing
        now = datetime.now(timezone.utc)
        history = [
            {
                "date": (
                    now.replace(hour=0, minute=0, second=0) - datetime.timedelta(days=i)
                ).strftime("%Y-%m-%d"),
                "hrv": 60 + i,
                "resting_hr": 50 - i,
            }
            for i in range(10)
        ]
        return history

    def push_workout(self, workout: WorkoutUnion) -> Dict[str, Any]:
        """
        Serializes the workout and saves it as a JSON file in the output directory.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() else "_" for c in workout.name)
        filename = f"{timestamp}_{safe_name}.json"
        filepath = self.output_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(workout.model_dump(), f, indent=2, default=str)

            logger.info(f"✅ [LocalArchivePlatform] Saved workout to {filepath}")
            return {"success": True, "workout_id": filename, "error": None}

        except Exception as e:
            logger.error(f"❌ [LocalArchivePlatform] Error saving workout: {e}")
            return {"success": False, "workout_id": None, "error": str(e)}

    def delete_workout(self, workout_id: str | int) -> Dict[str, Any]:
        """
        Simulates deleting a workout by removing the file.
        """
        filepath = self.output_dir / str(workout_id)

        if filepath.exists():
            filepath.unlink()
            logger.info(f"✅ [LocalArchivePlatform] Mock deleted file {filepath}")
            return {"success": True, "error": None}
        else:
            logger.warning(
                f"⚠️ [LocalArchivePlatform] File not found for deletion: {filepath}"
            )
            return {"success": False, "error": "File not found"}
