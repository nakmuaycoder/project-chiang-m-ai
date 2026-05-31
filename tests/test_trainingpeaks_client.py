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


@patch("project_chiang_m_ai.clients.trainingpeaks.requests.get")
@patch.object(TrainingPeaksClient, "_get_access_token", return_value="mock-token")
@patch.object(TrainingPeaksClient, "_get_athlete_id", return_value=12345)
def test_get_metrics(mock_get_athlete_id, mock_get_access_token, mock_get):
    """Test fetching metrics from TrainingPeaks client formats data properly."""
    # Mock Response
    mock_r = MagicMock()
    mock_r.status_code = 200
    mock_r.json.return_value = [
        {
            "timeStamp": "2026-01-01T00:00:00",
            "details": [
                {
                    "type": 60,
                    "label": "HRV",
                    "value": 45,
                    "time": "2026-01-01T00:00:00",
                },
                {
                    "type": 6,
                    "label": "Sleep Hours",
                    "value": 8.9166,
                    "time": "2026-01-01T00:00:00",
                },
                {
                    "type": 64,
                    "label": "Body Battery",
                    "value": [32, 75, 54.3],
                    "time": "2026-01-01T00:00:00",
                },
            ],
        }
    ]
    mock_get.return_value = mock_r

    client = TrainingPeaksClient()
    metrics = client.get_metrics("2026-01-01", "2026-01-03")

    assert len(metrics) == 3
    assert metrics[0] == {
        "Timestamp": "2026-01-01 00:00:00",
        "Type": "HRV",
        "Value": "45",
    }
    assert metrics[1] == {
        "Timestamp": "2026-01-01 00:00:00",
        "Type": "Sleep Hours",
        "Value": "8.92",
    }
    assert metrics[2] == {
        "Timestamp": "2026-01-01 00:00:00",
        "Type": "Body Battery",
        "Value": "Min : 32 / Max : 75 / Avg : 54",
    }


@patch("project_chiang_m_ai.clients.trainingpeaks.requests.post")
@patch("project_chiang_m_ai.clients.trainingpeaks.requests.get")
@patch.object(TrainingPeaksClient, "_get_access_token", return_value="mock-token")
@patch.object(TrainingPeaksClient, "_get_athlete_id", return_value=12345)
def test_get_workouts(mock_get_athlete_id, mock_get_access_token, mock_get, mock_post):
    """Test fetching workouts from TrainingPeaks formats fields and zones correctly."""
    # Mock get response for workout list
    mock_get_r = MagicMock()
    mock_get_r.status_code = 200
    mock_get_r.json.return_value = [
        {
            "workoutId": 3509734928,
            "title": "Hiking",
            "workoutTypeValueId": 13,
            "description": "Nice hike",
            "totalTimePlanned": 1.0,
            "distancePlanned": 5000.0,
            "workoutDay": "2026-01-04T00:00:00",
            "distance": 3289.07,
            "totalTime": 0.868,
            "elevationGain": 46.0,
            "workoutComments": [
                {
                    "dateCreated": "2026-01-04T19:00:00Z",
                    "commenterName": "Olivier Feher",
                    "comment": "Good feeling",
                    "isCoach": False,
                }
            ],
        }
    ]
    mock_get.return_value = mock_get_r

    # Mock post response for analysis
    mock_post_r = MagicMock()
    mock_post_r.status_code = 200
    mock_post_r.json.return_value = {
        "workoutId": 3509734928,
        "dataElements": [
            {
                "identifier": "HeartRate",
                "zones": [
                    {"min": 0, "max": 100},
                    {"min": 101, "max": 120},
                    {"min": 121, "max": 140},
                ],
            }
        ],
        "data": [
            {"time": 0, "HeartRate": 90},
            {"time": 60, "HeartRate": 95},
            {"time": 120, "HeartRate": 105},
        ],
    }
    mock_post.return_value = mock_post_r

    client = TrainingPeaksClient()
    workouts = client.get_workouts("2026-01-01", "2026-01-10")

    assert len(workouts) == 1
    w = workouts[0]
    assert w["Title"] == "Hiking"
    assert w["WorkoutType"] == "Walk"
    assert w["WorkoutDay"] == "2026-01-04"
    assert w["AthleteComments"] == " *01/04/2026 Olivier Feher: Good feeling*"
    assert w["HRZone1Minutes"] == 1  # 60s
    assert w["HRZone2Minutes"] == 1  # 60s
    assert w["HRZone3Minutes"] == 0
    assert w["HRZone4Minutes"] == ""
    assert w["Elevation"] == 46.0
