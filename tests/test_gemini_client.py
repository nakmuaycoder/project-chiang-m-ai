from unittest.mock import MagicMock, patch

import pytest
from google.api_core import exceptions as google_exceptions

from project_chiang_m_ai.clients.gemini import GeminiClient


@pytest.fixture
def mock_settings():
    with patch("project_chiang_m_ai.clients.gemini.settings") as mock:
        mock.GEMINI_API_KEY.get_secret_value.return_value = "fake_key"
        mock.LLM_MODEL = "gemini-1.5-flash"
        yield mock


def test_gemini_client_json_error_fallback(mock_settings):
    """
    Test that GeminiClient returns original workouts if the LLM
    returns invalid JSON.
    """
    with patch("google.genai.Client") as mock_genai:
        # 1. Setup mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.text = "This is not JSON"

        mock_instance = mock_genai.return_value
        mock_instance.models.generate_content.return_value = mock_response

        client = GeminiClient()

        # 2. Call adaptation
        original = [{"name": "Test"}]
        result = client.adapt_daily_workouts(original, [{"hrv": 50}])

        # 3. Verify fallback
        assert result == original


def test_gemini_client_api_error_fallback(mock_settings):
    """
    Test that GeminiClient returns original workouts if the API call fails.
    """
    with patch("google.genai.Client") as mock_genai:
        mock_instance = mock_genai.return_value
        mock_instance.models.generate_content.side_effect = (
            google_exceptions.InternalServerError("API Down")
        )

        client = GeminiClient()

        original = [{"name": "Test"}]
        result = client.adapt_daily_workouts(original, [{"hrv": 50}])

        assert result == original
