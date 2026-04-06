"""
Base class for LLM providers.
"""

import platform
from abc import ABC, abstractmethod
from typing import Optional, List, Dict


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def get_available_models(self) -> List[Dict[str, str]]:
        """
        Return list of available models for this provider.

        Returns:
            List of dicts with 'id', 'name', and 'description' keys
            Example: [
                {
                    "id": "mistral-large-latest",
                    "name": "Mistral Large",
                    "description": "Most capable Mistral model"
                }
            ]
        """
        pass

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

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the human-readable provider name."""
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
            raise ValueError(f"{self.get_provider_name()} API key not found in environment variables")
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
        available_model_ids = [m["id"] for m in self.get_available_models()]
        if model_id not in available_model_ids:
            raise ValueError(
                f"Model '{model_id}' not supported by {self.get_provider_name()}. "
                f"Available models: {', '.join(available_model_ids)}"
            )
        return model_id
    
    def supports_thinking(self, model_id:str):
        """Check if supports thinking"""
        for model in self.get_available_models():
            if model.get('id') == model_id and model.get('supports_thinking', False):
                return True
        return False
    
    def is_thinking_locked(self, model_id:str):
        """Check is thinking locked"""
        for model in self.get_available_models():
            if model.get('id') == model_id and model.get('thinking_locked', False):
                return True
        return False

    def is_image_model(self, model_id: str) -> bool:
        """Check if this model generates images instead of text."""
        for model in self.get_available_models():
            if model.get('id') == model_id and model.get('is_image_model', False):
                return True
        return False

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
