import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from project_chiang_m_ai.brains.auto_brain import AutoAdaptiveBrain
from project_chiang_m_ai.interfaces.brain import WorkoutWithSource
from project_chiang_m_ai.interfaces.calendar import CalendarEvent


@pytest.fixture
def mock_clients():
    return {"calendar": MagicMock(), "llm": MagicMock()}


def test_auto_brain_nominal_flow(mock_clients):
    """
    Test that AutoAdaptiveBrain correctly aggregates events,
    calls the LLM, and returns WorkoutWithSource objects.
    """
    # 1. Setup events in Calendar
    run_json = {
        "name": "Run",
        "type": "Run",
        "description": "Original Run",
        "steps": [],
    }
    strength_json = {
        "name": "Lift",
        "type": "WeightTraining",
        "description": "Original Lift",
        "blocks": [],
    }

    from datetime import timezone

    now = datetime.now(timezone.utc)

    events = [
        CalendarEvent(
            id="ev1",
            summary="[Coach] Run",
            start=now,
            end=now,
            description=json.dumps(run_json),
        ),
        CalendarEvent(
            id="ev2",
            summary="[Coach] Lift",
            start=now,
            end=now,
            description=json.dumps(strength_json),
        ),
    ]
    mock_clients["calendar"].list_upcoming_events.return_value = events

    # 2. Setup LLM response
    adapted_run = run_json.copy()
    adapted_run["description"] = "Adapted Run"
    adapted_strength = strength_json.copy()
    adapted_strength["description"] = "Adapted Strength"

    mock_clients["llm"].adapt_daily_workouts.return_value = [
        adapted_run,
        adapted_strength,
    ]

    # 3. Initialize Brain
    brain = AutoAdaptiveBrain(
        calendar_client=mock_clients["calendar"], llm_client=mock_clients["llm"]
    )

    wellness = [{"hrv": 50}]
    results = brain.get_final_workouts(wellness_data=wellness)

    # 4. Verify
    assert len(results) == 2
    assert isinstance(results[0], WorkoutWithSource)
    assert results[0].source_id == "ev1"
    assert results[0].workout.description == "Adapted Run"
    assert results[0].workout.original_workout["name"] == "Run"

    assert results[1].source_id == "ev2"
    assert results[1].workout.description == "Adapted Strength"

    # Verify LLM was called with correct count
    mock_clients["llm"].adapt_daily_workouts.assert_called_once()
    args, kwargs = mock_clients["llm"].adapt_daily_workouts.call_args
    assert len(kwargs["daily_workouts_json"]) == 2


def test_auto_brain_no_wellness_fallback(mock_clients):
    """
    If no wellness data is provided, it should return original workouts
    without calling the LLM.
    """
    run_json = {
        "name": "Run",
        "type": "Run",
        "description": "Original Run",
        "steps": [],
    }
    from datetime import timezone

    now = datetime.now(timezone.utc)

    events = [
        CalendarEvent(
            id="ev1",
            summary="[Coach] Run",
            start=now,
            end=now,
            description=json.dumps(run_json),
        )
    ]
    mock_clients["calendar"].list_upcoming_events.return_value = events

    brain = AutoAdaptiveBrain(
        calendar_client=mock_clients["calendar"], llm_client=mock_clients["llm"]
    )

    results = brain.get_final_workouts(wellness_data=None)

    assert len(results) == 1
    assert results[0].workout.name == "Run"
    mock_clients["llm"].adapt_daily_workouts.assert_not_called()


def test_auto_brain_mismatched_llm_response(mock_clients):
    """
    If the LLM returns fewer workouts than sent, we only process
    up to what it returned.
    """
    from datetime import timezone

    now = datetime.now(timezone.utc)

    events = [
        CalendarEvent(
            id="ev1",
            summary="[Coach] Run",
            start=now,
            end=now,
            description='{"type":"Run", "description":"Original", "steps":[]}',
        ),
        CalendarEvent(
            id="ev2",
            summary="[Coach] Bike",
            start=now,
            end=now,
            description='{"type":"Ride", "description":"Original", "steps":[]}',
        ),
    ]
    mock_clients["calendar"].list_upcoming_events.return_value = events

    # LLM only returns 1 workout instead of 2
    mock_clients["llm"].adapt_daily_workouts.return_value = [
        {"name": "Adapted 1", "type": "Run", "description": "Adapted", "steps": []}
    ]

    brain = AutoAdaptiveBrain(
        calendar_client=mock_clients["calendar"], llm_client=mock_clients["llm"]
    )

    results = brain.get_final_workouts(wellness_data=[{"hrv": 50}])

    assert len(results) == 1
    assert results[0].source_id == "ev1"
