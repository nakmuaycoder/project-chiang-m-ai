from project_chiang_m_ai.utils.prompt_builder import PromptBuilder


def test_build_adaptation_prompts_structure():
    """
    Test that the PromptBuilder correctly injects wellness history
    and daily workouts into the system and user prompts.
    """
    daily_workouts = [
        {"name": "Morning Run", "type": "Run", "description": "Easy 5k"},
        {"name": "Evening Lift", "type": "WeightTraining", "description": "Legs"},
    ]
    wellness_history = [{"date": "2026-03-14", "hrv": 60, "resting_hr": 55}]

    system_prompt, user_prompt = PromptBuilder.build_adaptation_prompts(
        daily_workouts_json=daily_workouts, wellness_history=wellness_history
    )

    # Verify system instructions (from package data templates or fallback)
    assert (
        "expert endurance" in system_prompt.lower() or "coach" in system_prompt.lower()
    )
    assert "json" in system_prompt.lower()

    # Verify user prompt content
    assert "Morning Run" in user_prompt
    assert "Evening Lift" in user_prompt
    assert "2026-03-14" in user_prompt
    assert "60" in user_prompt  # HRV

    # Verify it's a valid JSON string inside the prompt if we dumped it
    assert '"hrv": 60' in user_prompt
    assert '"name": "Morning Run"' in user_prompt


def test_prompt_builder_fallback():
    """
    Test that the PromptBuilder returns reasonable prompts even if
    the template files are missing (using the fallbacks).
    """
    # We mock _read_template to simulate missing files
    from unittest.mock import patch

    with patch(
        "project_chiang_m_ai.utils.prompt_builder.PromptBuilder._read_template"
    ) as mock_read:
        # Simulate returning the fallback (second argument of _read_template)
        mock_read.side_effect = lambda name, fallback: fallback

        system, user = PromptBuilder.build_adaptation_prompts([], [])

        assert "expert endurance and strength coach" in system
        assert "Wellness history" in user
