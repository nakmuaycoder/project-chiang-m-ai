import json
from typing import Dict, List

from google import genai
from google.genai import types

from project_chiang_m_ai.config import settings
from project_chiang_m_ai.interfaces.llm import ILlmClient
from project_chiang_m_ai.logger import logger
from project_chiang_m_ai.utils.prompt_builder import PromptBuilder


class GeminiClient(ILlmClient):
    """
    Client for interacting with the Gemini API to adapt workouts based on wellness data.
    """

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not set. Cannot initialize Gemini coach."
            )
        # Use the official SDK with the configured API key
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY.get_secret_value())

    def adapt_workout(
        self, current_workout_json: Dict, wellness_history: List[Dict]
    ) -> Dict:
        """
        Send the current workout and the wellness history to Gemini to generate
        an adapted training session.

        Args:
            current_workout_json (Dict): The original workout parsed from Calendar.
            wellness_history (List[Dict]): The raw wellness data from Intervals.icu

        Returns:
            Dict: The adapted workout JSON.
        """
        # Build formatted prompts using the PromptBuilder
        system_instructions, user_prompt = PromptBuilder.build_adaptation_prompts(
            current_workout_json=current_workout_json,
            wellness_history=wellness_history,
        )

        logger.info("🧠 Asking Gemini to adapt the workout...")

        try:
            # Generate the response
            # Note: We use the configured model from settings
            response = self.client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instructions,
                    temperature=0.2,  # Low temp for deterministic JSON output
                    response_mime_type="application/json",  # Forces JSON generation
                ),
            )

            response_text = response.text.strip()

            # The API should guarantee JSON response natively due to response_mime_type
            adapted_workout_json = json.loads(response_text)

            # We want to keep track of the original workout, but we do that
            # in the orchestrator so it accurately wraps the true original JSON.
            # Here we just return the adapted structure.
            logger.info("✅ Gemini successfully returned an adapted workout.")
            return adapted_workout_json

        except Exception as e:
            logger.error(f"❌ Failed to get adapted workout from Gemini: {str(e)}")
            # In case of failure, we return the original workout as a fallback
            return current_workout_json
