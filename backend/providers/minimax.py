"""
MiniMax provider implementation.
"""

from typing import List, Dict
from langchain_openai import ChatOpenAI
from .base import BaseLLMProvider


class MiniMaxProvider(BaseLLMProvider):
    """MiniMax provider using OpenAI-compatible API."""

    def get_available_models(self) -> List[Dict[str, str]]:
        """Return available MiniMax models."""
        return [
            {
                "id": "MiniMax-M2.7-highspeed",
                "name": "MiniMax-M2.7",
                "description": "Latest generation model with superior performance",
                "supports_thinking": True,
                "thinking_locked": True
            },
        ]

    def get_provider_name(self) -> str:
        """Return the provider name."""
        return "MiniMax"

    def supports_streaming(self) -> bool:
        """MiniMax supports streaming."""
        return True

    def initialize(self, model_id: str, api_key: str, temperature: float = 0.7, thinking: bool = False, **kwargs):
        """
        Initialize MiniMax LLM client.

        Args:
            model_id: MiniMax model ID (e.g., 'MiniMax-M2.1')
            api_key: MiniMax API key
            temperature: Sampling temperature (default: 0.7)
            thinking: Enable thinking mode (default: False)
            **kwargs: Additional configuration (e.g., base_url)

        Returns:
            ChatOpenAI instance configured for MiniMax
        """
        validated_key = self.validate_api_key(api_key)
        validated_model = self.validate_model_id(model_id)

        base_url = kwargs.get("base_url", "https://api.minimax.chat/v1")

        # Build extra_body for thinking mode
        extra_body = {}
        if thinking:
            extra_body["enable_thinking"] = True
        else:
            extra_body["enable_thinking"] = False

        return ChatOpenAI(
            model=validated_model,
            api_key=validated_key,
            base_url=base_url,
            temperature=temperature,
            streaming=True,
            extra_body=extra_body
        )
