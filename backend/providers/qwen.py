"""
Alibaba Qwen provider implementation.
"""

from typing import List, Dict
from langchain_openai import ChatOpenAI
from .base import BaseLLMProvider


class QwenProvider(BaseLLMProvider):
    """Alibaba Qwen provider using OpenAI-compatible API."""

    provider_id = "qwen"

    def get_provider_name(self) -> str:
        """Return the provider name."""
        return "Alibaba Qwen"

    def supports_streaming(self) -> bool:
        """Qwen supports streaming."""
        return True

    def initialize(self, model_id: str, api_key: str, temperature: float = 0.7, thinking: bool = False, max_tokens: int = 32000, **kwargs):
        """
        Initialize Qwen LLM client.

        Args:
            model_id: Qwen model ID (e.g., 'qwen-max')
            api_key: Qwen/DashScope API key
            temperature: Sampling temperature (default: 0.7)
            thinking: Not supported for Qwen models
            max_tokens: Maximum output tokens (default: 32000)
            **kwargs: Additional configuration (e.g., base_url)

        Returns:
            ChatOpenAI instance configured for Qwen
        """
        validated_key = self.validate_api_key(api_key)
        validated_model = self.validate_model_id(model_id)

        base_url = kwargs.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")

        # thinking parameter
        extra_body = {}
        if thinking:
            extra_body['enable_thinking'] = True

        return ChatOpenAI(
            model=validated_model,
            api_key=validated_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True,
            extra_body=extra_body
        )
