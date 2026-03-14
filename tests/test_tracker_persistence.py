import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from project_chiang_m_ai.interfaces.brain import WorkoutWithSource
from project_chiang_m_ai.models.workout import Workout
from project_chiang_m_ai.services.coach import CoachService
from project_chiang_m_ai.services.workout_tracker import WorkoutSyncTracker


@pytest.fixture
def temp_db(tmp_path):
    """Provides a temporary path for the sync history database."""
    return tmp_path / "test_sync_history.json"


@pytest.fixture
def mock_clients():
    return {
        "brain": MagicMock(),
        "platform": MagicMock(),
    }


def test_tracker_records_correct_id_after_sync(temp_db, mock_clients):
    """
    Verifies that the tracker properly saves the workout ID returned by the platform.
    """
    # 1. Setup Tracker with temp DB
    tracker = WorkoutSyncTracker(db_path=temp_db)

    # 2. Setup Mock Brain returning one workout
    now = datetime.now(timezone.utc)
    workout_data = {
        "name": "Sync Test",
        "description": "Testing persistence",
        "type": "Run",
        "start_date_local": now.isoformat(),
        "steps": [],
    }
    workout = Workout(**workout_data)
    mock_clients["brain"].get_final_workouts.return_value = [
        WorkoutWithSource(source_id="source-123", workout=workout)
    ]

    # 3. Setup Mock Platform returning a specific "hardcoded" ID
    HARDCODED_PLATFORM_ID = 987654
    mock_clients["platform"].get_wellness_data.return_value = []
    mock_clients["platform"].push_workout.return_value = {
        "success": True,
        "workout_id": HARDCODED_PLATFORM_ID,
    }

    # 4. Initialize CoachService and link the tracker
    service = CoachService(
        brain=mock_clients["brain"],
        platform=mock_clients["platform"],
        enable_tracking=True,
    )
    # Inject our tracker with the temp DB path
    service.tracker = tracker

    # 5. Execute Sync
    service.sync_workouts(dry_run=False)

    # 6. VERIFICATIONS
    # Check that the file was created
    assert temp_db.exists()

    # Read the file and check the content
    with open(temp_db, "r") as f:
        data = json.load(f)

    mappings = data.get("mappings", [])
    assert len(mappings) == 1
    assert mappings[0]["source_id"] == "source-123"
    assert mappings[0]["intervalicu_id"] == HARDCODED_PLATFORM_ID
    assert mappings[0]["status"] == "uploaded"


def test_tracker_cleanup_removes_from_db(temp_db, mock_clients):
    """
    Verifies that cleanup_orphaned_workouts removes the mapping from the DB
    when the source event is gone.
    """
    tracker = WorkoutSyncTracker(db_path=temp_db)

    # Manually seed the tracker with an "orphaned" workout
    tracker.record_sync(
        source_id="dead-event",
        source_name="Gone Event",
        source_date="2026-01-01",
        workout_name="Old Workout",
        workout_type="Run",
        workout_hash="hash123",
        sync_session_id="session1",
        intervalicu_id=555,
        status="uploaded",
    )

    # Verify it exists in DB
    assert len(tracker.history.mappings) == 1

    # Setup Brain stating that only "new-event" is active
    mock_clients["brain"].get_current_source_ids.return_value = ["new-event"]
    mock_clients["platform"].delete_workout.return_value = {"success": True}

    service = CoachService(
        brain=mock_clients["brain"],
        platform=mock_clients["platform"],
        enable_tracking=True,
    )
    service.tracker = tracker

    # Run Cleanup
    service.cleanup_orphaned_workouts()

    # VERIFY: Mapping should be gone from tracker and file
    assert len(tracker.history.mappings) == 0

    with open(temp_db, "r") as f:
        data = json.load(f)
    assert len(data["mappings"]) == 0
