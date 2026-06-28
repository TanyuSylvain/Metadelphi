"""
Provider registry for managing available LLM providers.
"""

from typing import Any, Dict, List, Optional, Type
from .base import BaseLLMProvider
from .mistral import MistralProvider
from .qwen import QwenProvider
from .glm import GLMProvider
from .minimax import MiniMaxProvider
from .deepseek import DeepSeekProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider
from .gemini_image import GeminiImageProvider
from .openai_image import OpenAIImageProvider


class ProviderRegistry:
    """Registry for all available LLM providers."""

    MODEL_REF_SEPARATOR = "::"

    # Public provider IDs -> text implementation classes.
    _providers: Dict[str, Type[BaseLLMProvider]] = {
        "mistral": MistralProvider,
        "qwen": QwenProvider,
        "glm": GLMProvider,
        "minimax": MiniMaxProvider,
        "deepseek": DeepSeekProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
    }

    # Internal image implementation classes affiliated with public providers.
    _image_providers: Dict[str, Type[BaseLLMProvider]] = {
        "openai": OpenAIImageProvider,
        "gemini": GeminiImageProvider,
    }

    @classmethod
    def get_provider(
        cls,
        provider_name: str,
        model_id: Optional[str] = None,
    ) -> BaseLLMProvider:
        """
        Get a provider instance by name.

        Args:
            provider_name: Public provider ID (e.g., 'openai', 'gemini').
            model_id: Optional model ID. If provided and the model is an image
                model, the affiliated image implementation is returned.

        Returns:
            Instance of the provider implementation.

        Raises:
            ValueError: If provider_name is not registered.
        """
        if provider_name not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Available providers: {', '.join(cls.list_providers())}"
            )

        if model_id and provider_name in cls._image_providers:
            from backend.config import settings
            model = settings.find_model(provider_name, model_id)
            if model and model.get("is_image_model"):
                return cls._image_providers[provider_name]()

        return cls._providers[provider_name]()

    @classmethod
    def list_providers(cls) -> List[str]:
        """
        List all public provider IDs.

        Returns:
            List of provider IDs.
        """
        return list(cls._providers.keys())

    @classmethod
    def build_model_ref(cls, provider_name: str, model_id: str) -> str:
        """Build a provider-qualified model reference."""
        return f"{provider_name}{cls.MODEL_REF_SEPARATOR}{model_id}"

    @classmethod
    def parse_model_ref(cls, model_ref: str) -> tuple[Optional[str], str]:
        """Parse a provider-qualified model reference into provider and raw model ID."""
        if cls.MODEL_REF_SEPARATOR in model_ref:
            provider_name, raw_model_id = model_ref.split(cls.MODEL_REF_SEPARATOR, 1)
            return provider_name, raw_model_id
        return None, model_ref

    @classmethod
    def get_all_models(cls) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all available models grouped by public provider ID.

        Returns:
            Dict mapping provider IDs to their available models from config.
        """
        from backend.config import settings

        result = {}
        for provider_name in cls.list_providers():
            result[provider_name] = settings.get_provider_models(provider_name)
        return result

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseLLMProvider]):
        """
        Register a new provider (useful for plugins/extensions).

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from BaseLLMProvider)
        """
        if not issubclass(provider_class, BaseLLMProvider):
            raise TypeError(f"{provider_class} must inherit from BaseLLMProvider")
        cls._providers[name] = provider_class

    @classmethod
    def find_provider_for_model(
        cls,
        model_id: str,
        provider_name: Optional[str] = None,
    ) -> tuple[str, BaseLLMProvider]:
        """
        Find which public provider supports a given model ID.

        Args:
            model_id: Model ID or provider-qualified model ref to search for.
            provider_name: Optional provider hint.

        Returns:
            Tuple of (provider_name, provider_instance)

        Raises:
            ValueError: If model_id is not found in any registered provider.
        """
        from backend.config import settings

        provider_hint, raw_model_id = cls.parse_model_ref(model_id)
        provider_name = provider_name or provider_hint

        if provider_name is not None:
            if provider_name not in cls._providers:
                raise ValueError(f"Unknown provider: {provider_name}")
            model = settings.find_model(provider_name, raw_model_id)
            if model:
                return provider_name, cls.get_provider(provider_name, raw_model_id)
            raise ValueError(
                f"Model '{raw_model_id}' not found for provider '{provider_name}'."
            )

        for provider_name in cls.list_providers():
            model = settings.find_model(provider_name, raw_model_id)
            if model:
                return provider_name, cls.get_provider(provider_name, raw_model_id)

        raise ValueError(
            f"Model '{raw_model_id}' not found in any registered provider."
        )
