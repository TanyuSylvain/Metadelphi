"""
Base class for LLM providers.
"""

import platform
from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    # Override in subclasses with the public provider ID (e.g. "openai").
    provider_id: str = ""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the human-readable provider name."""
        pass

    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Return list of available models for this provider from configuration.

        Returns:
            List of dicts with 'id', 'name', 'description', 'supports_thinking',
            'thinking_locked', and 'is_image_model' keys.
        """
        from backend.config import settings

        if not self.provider_id:
            return []
        return settings.get_provider_models(self.provider_id)

    @abstractmethod
    def initialize(self, model_id: str, api_key: str, temperature: float = 0.7, thinking: bool = False, **kwargs):
        """
        Initialize and return the LLM client for a specific model.

        Args:
            model_id: Specific model ID to use
            api_key: API key for the provider
            temperature: Sampling temperature (default: 0.7)
            thinking: Enable thinking mode (default: False)
            **kwargs: Additional provider-specific configuration

        Returns:
            Initialized LLM client instance
        """
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if this provider supports streaming responses."""
        pass

    def validate_api_key(self, api_key: Optional[str]) -> str:
        """
        Validate and return API key, raising error if invalid.

        Args:
            api_key: API key to validate

        Returns:
            Validated API key

        Raises:
            ValueError: If API key is None or empty
        """
        if not api_key:
            raise ValueError(f"{self.get_provider_name()} API key not found in configuration")
        return api_key

    def validate_model_id(self, model_id: str) -> str:
        """
        Validate that the model_id is supported by this provider.

        Args:
            model_id: Model ID to validate

        Returns:
            Validated model ID

        Raises:
            ValueError: If model_id is not supported
        """
        from backend.config import settings

        if not self.provider_id:
            raise ValueError(f"Provider ID not set for {self.get_provider_name()}")

        available_model_ids = [m["id"] for m in settings.get_provider_models(self.provider_id)]
        if model_id not in available_model_ids:
            raise ValueError(
                f"Model '{model_id}' not supported by {self.get_provider_name()}. "
                f"Available models: {', '.join(available_model_ids)}"
            )
        return model_id

    def supports_thinking(self, model_id: str) -> bool:
        """Check if a model supports thinking."""
        from backend.config import settings
        model = settings.find_model(self.provider_id, model_id)
        return bool(model and model.get("supports_thinking", False))

    def is_thinking_locked(self, model_id: str) -> bool:
        """Check if thinking is locked on for a model."""
        from backend.config import settings
        model = settings.find_model(self.provider_id, model_id)
        return bool(model and model.get("thinking_locked", False))

    def is_image_model(self, model_id: str) -> bool:
        """Check if this model generates images instead of text."""
        from backend.config import settings
        model = settings.find_model(self.provider_id, model_id)
        return bool(model and model.get("is_image_model", False))

    def get_user_agent(self) -> str:
        """
        Generate a standard user-agent string for API requests.

        Returns:
            User-agent string in standard format
        """
        system = platform.system()
        release = platform.release()
        python_version = platform.python_version()
        return f"Metadelphi/1.0 ({system} {release}; Python/{python_version})"
