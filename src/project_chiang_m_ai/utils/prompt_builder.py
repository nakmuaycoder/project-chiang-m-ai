import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

from project_chiang_m_ai.logger import logger


class PromptBuilder:
    """
    Utility class for loading and formatting LLM prompts.
    Centralizes prompt management to avoid hardcoding in client files.
    """

    @classmethod
    def _get_template_path(cls, template_name: str) -> str:
        """Returns the absolute path to a prompt template."""
        # Calculate path relative to this file
        # This file: src/project_chiang_m_ai/utils/prompt_builder.py
        # The project root is 4 levels up from this file's location.
        base_dir = Path(__file__).resolve().parents[3]
        return os.path.join(base_dir, "templates", template_name)

    @classmethod
    def _read_template(cls, template_name: str, fallback: str) -> str:
        """Reads a template file or returns the fallback if it fails."""
        path = cls._get_template_path(template_name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning(f"Could not find prompt template at {path}, using fallback.")
            return fallback

    @classmethod
    def build_adaptation_prompts(
        cls, daily_workouts_json: List[Dict], wellness_history: List[Dict]
    ) -> Tuple[str, str]:
        """
        Builds the system and user prompts for daily workouts adaptation.

        Args:
            daily_workouts_json: List of original workout JSONs for the day.
            wellness_history: Athlete's wellness history.

        Returns:
            Tuple[str, str]: (system_instructions, user_prompt)
        """
        # 1. System Prompt
        system_fallback = (
            "You are an expert endurance and strength coach. "
            "Output ONLY valid JSON matching the input structure. "
            "You will receive an array of workouts for the day, and you must "
            "return an array of adapted workouts in the EXACT identical order."
        )
        system_instructions = cls._read_template(
            "prompts/workout_adaptation/llm_system_prompt.txt", system_fallback
        )

        # 2. User Prompt
        user_fallback = (
            "Wellness history:\n{wellness_history}\n\n"
            "Daily Workouts:\n{workouts_json}\n\nUpdate them:"
        )
        user_template_str = cls._read_template(
            "prompts/workout_adaptation/llm_user_prompt.txt", user_fallback
        )

        # Format variables into the user prompt string
        user_prompt = user_template_str.format(
            wellness_history=json.dumps(wellness_history, indent=2),
            workouts_json=json.dumps(daily_workouts_json, indent=2),
        )

        return system_instructions, user_prompt
