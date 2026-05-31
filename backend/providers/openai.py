"""
OpenAI GPT provider implementation.
"""

from typing import List, Dict
from langchain_openai import ChatOpenAI
from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider using OpenAI API."""

    def get_available_models(self) -> List[Dict[str, str]]:
        """Return available OpenAI models."""
        return [
            {
                "id": "gpt-5.5",
                "name": "GPT-5.5",
                "description": "Most capable GPT-5 model",
                "supports_thinking": True,
                "thinking_locked": False
            },
            {
                "id": "gpt-5.4-mini",
                "name": "GPT-5.4 Mini",
                "description": "More efficient GPT-5 model for high-throughput workloads",
                "supports_thinking": True,
                "thinking_locked": False
            },
        ]

    def get_provider_name(self) -> str:
        """Return the provider name."""
        return "OpenAI"

    def supports_streaming(self) -> bool:
        """OpenAI supports streaming."""
        return True

    def initialize(self, model_id: str, api_key: str, temperature: float = 0.7, thinking: bool = False, max_tokens: int = 32000, **kwargs):
        """
        Initialize OpenAI LLM client.

        Args:
            model_id: OpenAI model ID (e.g., 'gpt-5.2')
            api_key: OpenAI API key
            temperature: Sampling temperature (default: 0.7)
            thinking: Not supported for this model
            max_tokens: Maximum output tokens (default: 32000)
            **kwargs: Additional configuration (e.g., base_url)

        Returns:
            ChatOpenAI instance configured for OpenAI
        """
        validated_key = self.validate_api_key(api_key)
        validated_model = self.validate_model_id(model_id)

        base_url = kwargs.get("base_url", "https://api.openai.com/v1")

        return ChatOpenAI(
            model=validated_model,
            api_key=validated_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True,
            default_headers={"User-Agent": self.get_user_agent()},
            extra_body={"reasoning": {"enabled": thinking}}
        )
