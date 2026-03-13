from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from project_chiang_m_ai.models.workout import Workout
from project_chiang_m_ai.services.coach import CoachService


def test_sync_from_calendar_success():
    """Test syncing a valid workout from the brain straight to an API mock."""
    mock_brain = MagicMock()
    mock_platform = MagicMock()

    # Setup simulated brain result
    now = datetime.now(timezone.utc)
    future_date = now + timedelta(days=2)

    valid_workout_json = {
        "name": "Test Run",
        "description": "A quick test run",
        "type": "Run",
        "start_date_local": future_date.isoformat(),
        "steps": [
            {"repetitions": 1, "steps": [{"duration": "10m", "zone": {"z": "Z2"}}]}
        ],
    }

    workout = Workout(**valid_workout_json)
    mock_platform.get_wellness_data.return_value = []
    mock_brain.get_final_workouts.return_value = [workout]

    # Mock platform successful upload return
    mock_platform.push_workout.return_value = {
        "success": True,
        "workout_id": 999111,
    }

    service = CoachService(
        brain=mock_brain, platform=mock_platform, enable_tracking=False
    )

    results = service.sync_workouts(dry_run=False)

    # Validate the results matrix
    assert results["success"] is True
    assert results["processed"] == 1
    assert results["uploaded"] == 1
    assert results["failed"] == 0
    assert len(results["errors"]) == 0

    # Ensure the platform upload function was actually triggered
    mock_platform.push_workout.assert_called_once()
    args, kwargs = mock_platform.push_workout.call_args
    uploaded_workout = args[0]

    assert uploaded_workout.name == "Test Run"
    assert uploaded_workout.type == "Run"
