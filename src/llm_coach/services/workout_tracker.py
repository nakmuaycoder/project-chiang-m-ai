"""
Workout Sync Tracker

Tracks the relationship between Google Calendar events and Intervals.icu workouts.
Enables:
- Workout update detection
- Performance-based adjustments
- Sync history
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from llm_coach.interfaces.calendar import CalendarEvent
from llm_coach.logger import logger


class WorkoutMapping(BaseModel):
    """Maps a calendar event to an Intervals.icu workout"""

    # Calendar info
    calendar_event_id: str
    calendar_event_summary: str
    calendar_event_start: str
    calendar_event_updated: Optional[str] = (
        None  # When calendar event was last modified
    )

    # Intervals.icu info
    intervalicu_id: Optional[int] = None  # Workout ID from Intervals.icu
    intervalicu_name: str
    intervalicu_type: str

    # Sync metadata
    synced_at: str
    sync_session_id: str
    workout_hash: str  # For detecting updates

    # Status
    status: str = "uploaded"  # uploaded, failed, updated, deleted


class SyncHistory(BaseModel):
    """Complete sync history"""

    version: str = "1.0"
    last_sync: Optional[str] = None
    mappings: List[WorkoutMapping] = []

    def add_mapping(self, mapping: WorkoutMapping):
        """Add a new mapping"""
        self.mappings.append(mapping)
        self.last_sync = datetime.now().isoformat()

    def find_by_calendar_id(self, calendar_id: str) -> Optional[WorkoutMapping]:
        """Find mapping by calendar event ID"""
        for mapping in self.mappings:
            if mapping.calendar_event_id == calendar_id:
                return mapping
        return None

    def find_by_intervalicu_id(self, intervalicu_id: int) -> Optional[WorkoutMapping]:
        """Find mapping by Intervals.icu workout ID"""
        for mapping in self.mappings:
            if mapping.intervalicu_id == intervalicu_id:
                return mapping
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get sync statistics"""
        return {
            "total_synced": len(self.mappings),
            "uploaded": len([m for m in self.mappings if m.status == "uploaded"]),
            "failed": len([m for m in self.mappings if m.status == "failed"]),
            "updated": len([m for m in self.mappings if m.status == "updated"]),
            "last_sync": self.last_sync,
        }


class WorkoutSyncTracker:
    """Tracks workout syncs between Calendar and Intervals.icu"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize tracker.

        Args:
            db_path: Path to JSON database file
        """
        self.db_path = db_path or Path("data/workout_sync_history.json")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.history = self._load_history()

    def _load_history(self) -> SyncHistory:
        """Load sync history from JSON file"""
        if self.db_path.exists():
            try:
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                return SyncHistory(**data)
            except Exception as e:
                logger.error(f"⚠️  Error loading sync history: {e}")
                logger.info("   Creating new history")

        return SyncHistory()

    def _save_history(self):
        """Save sync history to JSON file"""
        try:
            with open(self.db_path, "w") as f:
                json.dump(self.history.model_dump(), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"❌ Error saving sync history: {e}")

    def record_sync(
        self,
        calendar_event: CalendarEvent,
        workout_name: str,
        workout_type: str,
        workout_hash: str,
        sync_session_id: str,
        intervalicu_id: Optional[int] = None,
        status: str = "uploaded",
    ) -> WorkoutMapping:
        """
        Record a workout sync.

        Args:
            calendar_event: CalendarEvent object
            workout_name: Name of the workout
            workout_type: Type (Run, Ride, WeightTraining)
            workout_hash: Hash of workout content
            sync_session_id: Unique ID for this sync session
            intervalicu_id: Intervals.icu workout ID (if upload succeeded)
            status: Sync status (uploaded, failed, etc.)

        Returns:
            WorkoutMapping record
        """
        # Extract calendar event info from CalendarEvent object
        event_id = calendar_event.id
        event_summary = calendar_event.summary
        # event.start is already a datetime object
        start_time = calendar_event.start.isoformat()

        # Check if this event was already synced
        existing = self.history.find_by_calendar_id(event_id)

        if existing:
            # Update existing mapping
            if existing.workout_hash != workout_hash:
                # Workout content changed
                existing.status = "updated"
                existing.workout_hash = workout_hash
                existing.synced_at = datetime.now().isoformat()
                if intervalicu_id:
                    existing.intervalicu_id = intervalicu_id
                logger.info(f"   📝 Updated mapping for calendar event: {event_id}")
            else:
                logger.info(f"   ℹ️  Mapping already exists (no changes): {event_id}")

            self._save_history()
            return existing

        # Create new mapping
        mapping = WorkoutMapping(
            calendar_event_id=event_id,
            calendar_event_summary=event_summary,
            calendar_event_start=start_time,
            intervalicu_id=intervalicu_id,
            intervalicu_name=workout_name,
            intervalicu_type=workout_type,
            synced_at=datetime.now().isoformat(),
            sync_session_id=sync_session_id,
            workout_hash=workout_hash,
            status=status,
        )

        self.history.add_mapping(mapping)
        self._save_history()

        logger.info(
            f"   💾 Recorded sync: {event_summary} → Intervals.icu ID {intervalicu_id}"
        )

        return mapping

    def get_stats(self) -> Dict[str, Any]:
        """Get sync statistics"""
        return self.history.get_stats()

    def print_stats(self):
        """Print sync statistics"""
        stats = self.get_stats()

        logger.info("\n" + "=" * 70)
        logger.info("📊 SYNC HISTORY STATISTICS")
        logger.info("=" * 70)
        logger.info(f"Total workouts synced: {stats['total_synced']}")
        logger.info(f"  ✅ Uploaded: {stats['uploaded']}")
        logger.info(f"  🔄 Updated: {stats['updated']}")
        logger.error(f"  ❌ Failed: {stats['failed']}")
        logger.info(f"Last sync: {stats['last_sync']}")
        logger.info(f"Database: {self.db_path}")
        logger.info("=" * 70)

    def export_mappings(self, output_path: Optional[Path] = None) -> Path:
        """Export mappings to JSON file"""
        if output_path is None:
            output_path = Path(
                f"data/workout_mappings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(
                [m.model_dump() for m in self.history.mappings],
                f,
                indent=2,
                default=str,
            )

        logger.info(
            f"📁 Exported {len(self.history.mappings)} mappings to: {output_path}"
        )
        return output_path


# Example usage
if __name__ == "__main__":
    import hashlib

    tracker = WorkoutSyncTracker()

    # Example: Record a sync
    fake_event = {
        "id": "abc123",
        "summary": "[Coach] Morning Run",
        "start": {"dateTime": "2026-02-05T07:00:00+01:00"},
    }

    workout_content = "Easy run with strides"
    workout_hash = hashlib.md5(workout_content.encode()).hexdigest()[:8]

    mapping = tracker.record_sync(
        calendar_event=fake_event,
        workout_name="Morning Run",
        workout_type="Run",
        workout_hash=workout_hash,
        sync_session_id="test_session_1",
        intervalicu_id=12345,
        status="uploaded",
    )

    logger.info("\n✅ Recorded mapping:")
    logger.info(f"   Calendar: {mapping.calendar_event_id}")
    logger.info(f"   Intervals.icu: {mapping.intervalicu_id}")

    # Print stats
    tracker.print_stats()
