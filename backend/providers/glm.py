"""
Zhipu AI GLM provider implementation.
"""

from typing import List, Dict
from langchain_openai import ChatOpenAI
from .base import BaseLLMProvider


class GLMProvider(BaseLLMProvider):
    """Zhipu AI GLM provider using OpenAI-compatible API."""

    def get_available_models(self) -> List[Dict[str, str]]:
        """Return available GLM models."""
        return [
            {
                "id": "glm-5",
                "name": "GLM 5",
                "description": "Latest front-tier GLM model",
                "supports_thinking": True,
                "thinking_locked": False
            },
            {
                "id": "glm-4.7",
                "name": "GLM 4.7",
                "description": "Enhanced GLM-4 with improved capabilities",
                "supports_thinking": True,
                "thinking_locked": False
            },
            {
                "id": "glm-4.6",
                "name": "GLM 4.6",
                "description": "Balanced performance and efficiency",
                "supports_thinking": True,
                "thinking_locked": False
            },
        ]

    def get_provider_name(self) -> str:
        """Return the provider name."""
        return "Zhipu AI GLM"

    def supports_streaming(self) -> bool:
        """GLM supports streaming."""
        return True

    def initialize(self, model_id: str, api_key: str, temperature: float = 0.7, thinking: bool = False, **kwargs):
        """
        Initialize GLM LLM client.

        Args:
            model_id: GLM model ID (e.g., 'glm-4-plus')
            api_key: Zhipu AI API key
            temperature: Sampling temperature (default: 0.7)
            thinking: Enable thinking mode (default: False)
            **kwargs: Additional configuration (e.g., base_url)

        Returns:
            ChatOpenAI instance configured for GLM
        """
        validated_key = self.validate_api_key(api_key)
        validated_model = self.validate_model_id(model_id)

        base_url = kwargs.get("base_url", "https://open.bigmodel.cn/api/paas/v4")

        # Build extra_body for thinking mode
        # By default the thinking is enabled, GLM-4.6 will decide if thinking is necessary
        extra_body = {}
        if not thinking:
            extra_body["thinking"] = {'type': 'disabled'}

        return ChatOpenAI(
            model=validated_model,
            api_key=validated_key,
            base_url=base_url,
            temperature=temperature,
            streaming=True,
            extra_body=extra_body
        )
