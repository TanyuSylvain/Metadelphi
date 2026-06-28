"""
Mistral AI provider implementation.
"""

from typing import List, Dict
from langchain_mistralai import ChatMistralAI
from .base import BaseLLMProvider


class MistralProvider(BaseLLMProvider):
    """Mistral AI provider using native ChatMistralAI."""

    provider_id = "mistral"

    def get_provider_name(self) -> str:
        """Return the provider name."""
        return "Mistral AI"

    def supports_streaming(self) -> bool:
        """Mistral supports streaming."""
        return True

    def initialize(self, model_id: str, api_key: str, temperature: float = 0.7, thinking: bool = False, max_tokens: int = 32000, **kwargs):
        """
        Initialize Mistral LLM client.

        Args:
            model_id: Mistral model ID (e.g., 'mistral-large-latest')
            api_key: Mistral API key
            temperature: Sampling temperature (default: 0.7)
            thinking: Not supported for Mistral models
            max_tokens: Maximum output tokens (default: 32000)
            **kwargs: Additional configuration (unused)

        Returns:
            ChatMistralAI instance
        """
        validated_key = self.validate_api_key(api_key)
        validated_model = self.validate_model_id(model_id)

        # thinking parameter ignored - not supported
        _ = thinking

        return ChatMistralAI(
            model=validated_model,
            api_key=validated_key,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True
        )
