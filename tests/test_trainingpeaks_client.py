from unittest.mock import MagicMock, patch

from project_chiang_m_ai.clients.trainingpeaks import TrainingPeaksClient
from project_chiang_m_ai.models.workout import Workout


@patch("project_chiang_m_ai.clients.trainingpeaks.requests.post")
@patch.object(TrainingPeaksClient, "_get_access_token", return_value="mock-token")
@patch.object(TrainingPeaksClient, "_get_athlete_id", return_value=12345)
def test_trainingpeaks_strength_push(
    mock_get_athlete_id, mock_get_access_token, mock_post
):
    """
    Test pushing a strength workout to TrainingPeaks formats the description
    and duration correctly.
    """
    # Mock TP API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"workoutId": 888999}
    mock_post.return_value = mock_response

    # Create a strength workout payload matching the model
    payload = {
        "name": "[Coach] Upper Body Push",
        "description": "Chest, shoulders, triceps strength training",
        "start_date_local": "2026-02-01T16:21:29",
        "blocks": [
            {
                "name": "Warmup",
                "repetitions": 1,
                "exercises": [
                    {"name": "Arm circles", "sets": 2, "reps": "10 each direction"},
                    {"name": "Band pull-aparts", "sets": 2, "reps": "15"},
                ],
            }
        ],
        "estimated_duration": 3600,  # 1 hour
        "color": "#FF6B6B",
    }

    workout = Workout(**payload)

    client = TrainingPeaksClient()
    result = client.push_workout(workout)

    assert result["success"] is True
    assert result["workout_id"] == 888999

    # Verify requests.post was called with the correct payload
    mock_post.assert_called_once()
    called_args, called_kwargs = mock_post.call_args
    sent_payload = called_kwargs["json"]

    # Check mapping
    assert sent_payload["workoutTypeFamilyId"] == 9
    assert sent_payload["workoutTypeValueId"] == 9
    assert sent_payload["title"] == "[Coach] Upper Body Push"
    assert sent_payload["totalTimePlanned"] == 1.0  # 3600s / 3600

    # Description must be formatted using to_intervals_description
    assert "━━━ WARMUP ━━━" in sent_payload["description"]
    assert "• Arm circles" in sent_payload["description"]
    assert "2 sets × 10 each direction reps" in sent_payload["description"]
