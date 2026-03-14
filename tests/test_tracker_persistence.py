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


def test_sync_update_flow(temp_db, mock_clients):
    """
    Test that CoachService detects a change in workout content,
    deletes the old workout on the platform, and uploads the new one.
    """
    tracker = WorkoutSyncTracker(db_path=temp_db)

    # 1. Seed the DB with an existing workout (Hash "OLD")
    source_id = "event-456"
    old_id = 111
    tracker.record_sync(
        source_id=source_id,
        source_name="My Run",
        source_date="2026-03-14",
        workout_name="My Run",
        workout_type="Run",
        workout_hash="OLD_HASH",
        sync_session_id="session_old",
        intervalicu_id=old_id,
        status="uploaded",
    )

    # 2. Setup Brain to return the SAME event but with NEW content
    new_workout_data = {
        "name": "My Run",
        "description": "Updated content!",
        "type": "Run",
        "steps": [],
    }
    new_workout = Workout(**new_workout_data)
    mock_clients["brain"].get_final_workouts.return_value = [
        WorkoutWithSource(source_id=source_id, workout=new_workout)
    ]

    # 3. Setup Mocks for delete and push
    new_id = 222
    mock_clients["platform"].get_wellness_data.return_value = []
    mock_clients["platform"].delete_workout.return_value = {"success": True}
    mock_clients["platform"].push_workout.return_value = {
        "success": True,
        "workout_id": new_id,
    }

    service = CoachService(
        brain=mock_clients["brain"],
        platform=mock_clients["platform"],
        enable_tracking=True,
    )
    service.tracker = tracker

    # 4. Run Sync
    service.sync_workouts(dry_run=False)

    # 5. VERIFY
    # - Platform delete was called for the OLD id
    mock_clients["platform"].delete_workout.assert_called_once_with(old_id)
    # - Platform push was called
    mock_clients["platform"].push_workout.assert_called_once()
    # - Tracker is updated with the NEW id and NEW hash
    mapping = tracker.history.find_by_source_id(source_id)
    assert mapping.intervalicu_id == new_id
    assert (
        mapping.status == "updated"
    )  # CoachService marks it as updated in tracker.record_sync if exists


def test_sync_skips_unchanged(temp_db, mock_clients):
    """
    Test that CoachService skips uploading a workout if the hash matches
    what's already in the tracker.
    """
    tracker = WorkoutSyncTracker(db_path=temp_db)

    # 1. Seed DB with a workout
    source_id = "event-789"
    workout_hash = "SAME_HASH"
    tracker.record_sync(
        source_id=source_id,
        source_name="Static Run",
        source_date="2026-03-14",
        workout_name="Static Run",
        workout_type="Run",
        workout_hash=workout_hash,
        sync_session_id="session_1",
        intervalicu_id=123,
        status="uploaded",
    )

    # 2. Setup Brain to return the SAME workout (which will result in SAME hash)
    workout_data = {
        "name": "Static Run",
        "description": "...",
        "type": "Run",
        "steps": [],
    }
    workout = Workout(**workout_data)
    # Ensure our mock workout will dump to the same JSON/hash
    import hashlib

    # Verify our hash calculation logic matches CoachService
    calc_hash = hashlib.sha256(workout.model_dump_json().encode("utf-8")).hexdigest()[
        :16
    ]

    # We update the seed to match the real hash of this object
    tracker.history.mappings[0].workout_hash = calc_hash
    tracker._save_history()

    mock_clients["brain"].get_final_workouts.return_value = [
        WorkoutWithSource(source_id=source_id, workout=workout)
    ]
    mock_clients["platform"].get_wellness_data.return_value = []

    service = CoachService(
        brain=mock_clients["brain"],
        platform=mock_clients["platform"],
        enable_tracking=True,
    )
    service.tracker = tracker

    # 3. Run Sync
    results = service.sync_workouts(dry_run=False)

    # 4. VERIFY
    # - Push was NEVER called
    mock_clients["platform"].push_workout.assert_not_called()
    # - Summary shows nothing uploaded
    assert results["uploaded"] == 0
    assert results["processed"] == 0  # CoachService decrements processed when skipped
