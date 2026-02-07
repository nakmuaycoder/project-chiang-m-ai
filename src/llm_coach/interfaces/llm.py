"""
Abstract interface for LLM providers.
Allows swapping between Gemini, ChatGPT, local models, etc.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ILLMProvider(ABC):
    """
    Interface that any LLM provider must implement.

    Implementations:
    - GeminiClient (Google's Gemini API)
    - OpenAIClient (ChatGPT API)
    - LocalLLMClient (Ollama, vLLM, llama.cpp)
    - ClaudeClient (Anthropic's Claude API)
    """

    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: The input prompt
            **kwargs: Provider-specific options (temperature, max_tokens, etc.)

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    def generate_structured(
        self, prompt: str, schema: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured output (JSON) matching a schema.

        Args:
            prompt: The input prompt
            schema: JSON schema for the expected output (optional)
            **kwargs: Provider-specific options

        Returns:
            Parsed JSON output as dictionary
        """
        pass
