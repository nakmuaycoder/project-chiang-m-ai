"""
Local LLM client (Ollama, vLLM, llama.cpp, etc.)
This is a stub for future implementation.
"""

from typing import Any, Dict, Optional

from llm_coach.interfaces.llm import ILLMProvider


class LocalLLMClient(ILLMProvider):
    """
    Local LLM implementation via Ollama/vLLM/llama.cpp.

    Example use cases:
    - Fine-tuned model on personal training data
    - Privacy-first setup (no cloud API calls)
    - Cost-free inference

    TODO: Implement once you have your fine-tuned model ready
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:11434",
        model_name: str = "llama3",
    ):
        """
        Initialize local LLM client.

        Args:
            endpoint: API endpoint (Ollama default: http://localhost:11434)
            model_name: Model name (e.g., "llama3", "your-finetuned-model")
        """
        self.endpoint = endpoint
        self.model_name = model_name

    def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generate text from a prompt using local LLM.

        Args:
            prompt: The input prompt
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        # TODO: Implement Ollama API call
        # Example:
        # response = requests.post(
        #     f"{self.endpoint}/api/generate",
        #     json={
        #         "model": self.model_name,
        #         "prompt": prompt,
        #         **kwargs
        #     }
        # )
        # return response.json()["response"]

        raise NotImplementedError(
            "LocalLLMClient.generate_text() not implemented yet. "
            "Use GeminiClient or implement Ollama integration."
        )

    def generate_structured(
        self, prompt: str, schema: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output from local LLM.

        Args:
            prompt: The input prompt
            schema: JSON schema for the expected output
            **kwargs: Additional generation parameters

        Returns:
            Parsed JSON output as dictionary
        """
        # TODO: Implement with JSON mode or structured generation
        raise NotImplementedError(
            "LocalLLMClient.generate_structured() not implemented yet. "
            "Use GeminiClient or implement Ollama JSON mode."
        )
