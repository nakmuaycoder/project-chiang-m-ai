from project_chiang_m_ai.clients.intervalicu import IntervalicuClient
from project_chiang_m_ai.models.workout import Workout


def test_intervals_run_ride_formatter():
    """Test the translation of Run/Ride blocks into Intervals.icu native syntax."""
    payload = {
        "name": "Test Ride",
        "description": "...",
        "type": "Ride",
        "steps": [
            {
                "repetitions": 2,
                "steps": [
                    {"duration": "10m", "zone": {"z": "60-70%"}},
                    {"duration": "5m", "zone": {"z": "Z3"}, "cadence": "90"},
                ],
            }
        ],
    }

    workout = Workout(**payload)
    native_format = IntervalicuClient.format_workout_native(workout)

    # 2 blocks x 2 steps = 4 lines generated
    assert "- 10m in 60% - 70%" in native_format
    assert "- 5m in 76% - 90% (90rpm)" in native_format

    # Check that it unrolled 2 repetitions properly
    lines = native_format.split("\n")
    assert len(lines) == 4
    assert lines[0] == "- 10m in 60% - 70%"
    assert lines[1] == "- 5m in 76% - 90% (90rpm)"
    assert lines[2] == "- 10m in 60% - 70%"
    assert lines[3] == "- 5m in 76% - 90% (90rpm)"


def test_intervals_strength_formatter():
    """Test generating the plain text description for StrengthWorkouts."""
    payload = {
        "name": "[Coach] Musculation",
        "description": "...",
        "type": "WeightTraining",
        "blocks": [
            {
                "name": "Echauffement",
                "repetitions": 1,
                "exercises": [{"name": "Squat", "sets": 3, "reps": "15"}],
            }
        ],
    }

    workout = Workout(**payload)
    output = workout.to_intervals_description()

    assert "━━━ ECHAUFFEMENT ━━━" in output
    assert "• Squat" in output
    assert "3 sets × 15 reps" in output
