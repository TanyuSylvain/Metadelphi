"""
DeepSeek provider implementation.
"""

from typing import List, Dict
from langchain_openai import ChatOpenAI
from .base import BaseLLMProvider


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek provider using OpenAI-compatible API."""

    # Models that support thinking (always on, cannot be disabled)

    def get_available_models(self) -> List[Dict[str, str]]:
        """Return available DeepSeek models."""
        return [
            {
                "id": "deepseek-chat",
                "name": "DeepSeek Chat (Latest)",
                "description": "DeepSeek's conversational model",
                "supports_thinking": False
            },
            {
                "id": "deepseek-reasoner",
                "name": "DeepSeek Reasoner (Latest)",
                "description": "Advanced reasoning model with chain-of-thought",
                "supports_thinking": True,
                "thinking_locked": True  # Cannot disable thinking
            },
        ]

    def get_provider_name(self) -> str:
        """Return the provider name."""
        return "DeepSeek"

    def supports_streaming(self) -> bool:
        """DeepSeek supports streaming."""
        return True

    def initialize(self, model_id: str, api_key: str, temperature: float = 0.7, thinking: bool = False, max_tokens: int = 32000, **kwargs):
        """
        Initialize DeepSeek LLM client.

        Args:
            model_id: DeepSeek model ID (e.g., 'deepseek-chat')
            api_key: DeepSeek API key
            temperature: Sampling temperature (default: 0.7)
            thinking: Ignored for deepseek-reasoner (always thinks)
            max_tokens: Maximum output tokens (default: 32000)
            **kwargs: Additional configuration (e.g., base_url)

        Returns:
            ChatOpenAI instance configured for DeepSeek
        """
        validated_key = self.validate_api_key(api_key)
        validated_model = self.validate_model_id(model_id)

        base_url = kwargs.get("base_url", "https://api.deepseek.com")

        # DeepSeek Reasoner doesn't support temperature parameter
        if validated_model == "deepseek-reasoner":
            return ChatOpenAI(
                model=validated_model,
                api_key=validated_key,
                base_url=base_url,
                max_tokens=max_tokens,
                streaming=True
            )
        else:
            return ChatOpenAI(
                model=validated_model,
                api_key=validated_key,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=True
            )
