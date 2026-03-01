import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from llm_coach.interfaces.calendar import CalendarEvent
from llm_coach.services.coach import CoachService


@patch("llm_coach.services.coach.IntervalicuClient")
@patch("llm_coach.services.coach.GoogleCalendarClient")
def test_sync_from_calendar_success(mock_google_cal_cls, mock_intervalicu_cls):
    """Test syncing a valid workout from the calendar straight to an API mock."""
    mock_calendar_client = mock_google_cal_cls.return_value
    mock_intervalicu_client = mock_intervalicu_cls.return_value

    # Setup simulated calendar event
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

    event = CalendarEvent(
        id="test-event-1",
        summary="[Coach] Upcoming Test Run",
        start=future_date,
        end=future_date + timedelta(hours=1),
        description=json.dumps(valid_workout_json),
    )

    mock_calendar_client.list_upcoming_events.return_value = [event]

    # Mock intervals successful upload return
    mock_intervalicu_client.upload_workout.return_value = {
        "success": True,
        "workout_id": 999111,
    }

    service = CoachService(enable_tracking=False)

    results = service.sync_from_calendar(sync_mode="all")

    # Validate the results matrix
    assert results["success"] is True
    assert results["processed"] == 1
    assert results["uploaded"] == 1
    assert results["failed"] == 0
    assert len(results["errors"]) == 0

    # Ensure the Intervalicu upload function was actually triggered
    mock_intervalicu_client.upload_workout.assert_called_once()
    args, kwargs = mock_intervalicu_client.upload_workout.call_args
    uploaded_workout = args[0]

    assert uploaded_workout.name == "Test Run"
    assert uploaded_workout.type == "Run"
