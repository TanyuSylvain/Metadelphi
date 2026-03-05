"""
Google Gemini provider implementation.
"""

from typing import List, Dict
from langchain_openai import ChatOpenAI
from .base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider using OpenAI-compatible API."""

    def get_available_models(self) -> List[Dict[str, str]]:
        """Return available Gemini models."""
        return [
            {
                "id": "gemini-3.1-pro-preview",
                "name": "Gemini-3.1-pro-preview",
                "description": "Most powerful Gemini with thinking",
                "supports_thinking": True,
                "thinking_locked": False
            },
            {
                "id": "gemini-3-flash-preview",
                "name": "Gemini-3-flash-preview",
                "description": "Advanced Gemini model with thinking",
                "supports_thinking": True,
                "thinking_locked": False  # Can toggle thinking
            },
        ]

    def get_provider_name(self) -> str:
        """Return the provider name."""
        return "Google Gemini"

    def supports_streaming(self) -> bool:
        """Gemini supports streaming."""
        return True

    def initialize(self, model_id: str, api_key: str, temperature: float = 0.7, thinking: bool = False, **kwargs):
        """
        Initialize Gemini LLM client.

        Args:
            model_id: Gemini model ID (e.g., 'gemini-3-pro-preview')
            api_key: Gemini API key
            temperature: Sampling temperature (default: 0.7)
            thinking: Enable thinking mode (uses thinkingLevel parameter)
            **kwargs: Additional configuration (e.g., base_url)

        Returns:
            ChatOpenAI instance configured for Gemini
        """
        validated_key = self.validate_api_key(api_key)
        validated_model = self.validate_model_id(model_id)

        base_url = kwargs.get("base_url", "https://generativelanguage.googleapis.com/v1beta/openai")

        reason_eft = 'minimal' if 'flash' in model_id else 'low'
        if thinking:
            reason_eft = 'high'

        return ChatOpenAI(
            model=validated_model,
            api_key=validated_key,
            base_url=base_url,
            temperature=temperature,
            streaming=True,
            reasoning_effort=reason_eft,
            default_headers={"User-Agent": self.get_user_agent()}
        )
