"""
DeepSeek provider implementation.
"""

from typing import List, Dict
from langchain_openai import ChatOpenAI
from .base import BaseLLMProvider


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek provider using OpenAI-compatible API."""

    def get_available_models(self) -> List[Dict[str, str]]:
        """Return available DeepSeek models."""
        return [
            {
                "id": "deepseek-v4-flash",
                "name": "DeepSeek V4 Flash",
                "description": "DeepSeek's conversational model",
                "supports_thinking": True,
                "thinking_locked": False  # Can enable/disable thinking
            },
            {
                "id": "deepseek-v4-pro",
                "name": "DeepSeek V4 Pro",
                "description": "Advanced reasoning model with chain-of-thought",
                "supports_thinking": True,
                "thinking_locked": False  # Can enable/disable thinking
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
            model_id: DeepSeek model ID (e.g., 'deepseek-v4-flash')
            api_key: DeepSeek API key
            temperature: Sampling temperature (default: 0.7)
            thinking: Whether to enable chain-of-thought reasoning
            max_tokens: Maximum output tokens (default: 32000)
            **kwargs: Additional configuration (e.g., base_url)

        Returns:
            ChatOpenAI instance configured for DeepSeek
        """
        validated_key = self.validate_api_key(api_key)
        validated_model = self.validate_model_id(model_id)

        base_url = kwargs.get("base_url", "https://api.deepseek.com")

        extra_body = {}
        if thinking:
            extra_body["reasoning_effort"] = "max"
        else:
            extra_body["thinking"] = {"type": "disabled"}

        return ChatOpenAI(
            model=validated_model,
            api_key=validated_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True,
            extra_body=extra_body
        )
