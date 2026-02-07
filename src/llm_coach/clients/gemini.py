"""
Google Gemini LLM client.
"""

import json
from typing import Any, Dict, Optional

import google.generativeai as genai

from llm_coach.config import settings
from llm_coach.interfaces.llm import ILLMProvider


class GeminiClient(ILLMProvider):
    """
    Google Gemini implementation of the LLM provider interface.
    """

    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize the Gemini client.

        Args:
            model_name: Gemini model to use (default: gemini-2.0-flash-exp)
        """
        api_key = settings.GOOGLE_API_KEY.get_secret_value()
        genai.configure(api_key=api_key)
        self.model_name = model_name

    def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generate text from a prompt using Gemini.

        Args:
            prompt: The input prompt
            **kwargs: Additional generation parameters (temperature, max_tokens, etc.)

        Returns:
            Generated text
        """
        model = genai.GenerativeModel(self.model_name)
        response = model.generate_content(prompt, **kwargs)
        return response.text

    def generate_structured(
        self, prompt: str, schema: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output from a prompt.

        Args:
            prompt: The input prompt
            schema: JSON schema for the expected output (optional, for validation)
            **kwargs: Additional generation parameters

        Returns:
            Parsed JSON output as dictionary
        """
        # Add JSON format instruction to prompt
        json_prompt = f"{prompt}\n\nRespond with valid JSON only."

        model = genai.GenerativeModel(self.model_name)
        response = model.generate_content(json_prompt, **kwargs)

        # Parse JSON response
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from Gemini response: {e}")
