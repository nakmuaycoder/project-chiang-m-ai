from llm_coach.models.strength_workout import StrengthWorkout
from llm_coach.models.workout import RideWorkout, RunWorkout, Workout, Zone


def test_type_inference_run():
    """
    Test that a workout without a type but with 'Trail'
    in name defaults to RunWorkout.
    """
    payload = {
        "name": "[Coach] W10 : Trail/CAP Strides [40min]",
        "description": "Trail strides",
        "steps": [],
    }

    workout = Workout(**payload)
    assert isinstance(workout, RunWorkout)
    assert workout.type == "Run"


def test_type_inference_ride():
    """
    Test that a workout without a type but with 'Vélo'
    in name defaults to RideWorkout.
    """
    payload = {
        "name": "[Coach] W10 : Vélo Endurance [Z2]",
        "description": "Easy ride",
        "steps": [],
    }

    workout = Workout(**payload)
    assert isinstance(workout, RideWorkout)
    assert workout.type == "Ride"


def test_type_inference_strength():
    """
    Test that a workout without a type but with 'Musculation'
    defaults to StrengthWorkout.
    """
    payload = {
        "name": "[Coach] W10 : Musculation Haut du corps [45min]",
        "description": "Haut du corps, gainage, mobilité",
        "blocks": [
            {
                "name": "General",
                "exercises": [
                    {"name": "Musculation Haut du corps", "sets": 1, "reps": "45m"}
                ],
            }
        ],
        "estimated_duration": 2700,
        "color": "#FF6B00",
    }

    workout = Workout(**payload)
    assert isinstance(workout, StrengthWorkout)
    assert workout.type == "WeightTraining"


def test_zone_parsing_percentage():
    """Test parsing standard percentage ranges."""
    zone = Zone(z="70-80%")
    assert zone._start == 70
    assert zone._end == 80
    assert "70% - 80%" in zone.to_value()


def test_zone_parsing_hr_lthr_override():
    """Test that HR keyword enforces unit tracking."""
    zone = Zone(z="80-90% HR")
    assert zone._start == 80
    assert zone._end == 90
    assert zone._unit == "LTHR"
    assert "LTHR" in zone.to_value()


def test_zone_parsing_raw_key():
    """Test fallback zone resolving logic."""
    zone = Zone(z="Z2")
    # By default, without checking parent, a Z2 defaults to Cycling Power Z2
    # CyclingPowerZone.get_zone("Z2") -> 56% to 75%
    assert zone._start == 56
    assert zone._end == 75


def test_duration_parsing():
    """Test human readable durations in steps."""
    from llm_coach.models.workout import Step

    step1 = Step(duration="1h 30m", zone={"z": "Z2"})
    assert step1.duration == 5400

    step2 = Step(duration="45m", zone={"z": "Z3"})
    assert step2.duration == 2700

    step3 = Step(duration="30s", zone={"z": "100%"})
    assert step3.duration == 30


def test_workout_moving_time():
    """Test that moving time counts accurately."""
    payload = {
        "name": "Test Run",
        "description": "...",
        "type": "Run",
        "steps": [
            {
                "repetitions": 2,
                "steps": [
                    {"duration": "10m", "zone": {"z": "Z2"}},
                    {"duration": "5m", "zone": {"z": "Z3"}},
                ],
            },
            {"repetitions": 1, "steps": [{"duration": "15m", "zone": {"z": "Z1"}}]},
        ],
    }

    workout = Workout(**payload)
    # Block 1 = 2 * (10m + 5m) = 30m
    # Block 2 = 1 * 15m = 15m
    # Total = 45m = 2700s
    assert workout.moving_time == 2700
