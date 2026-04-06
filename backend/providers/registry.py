"""
Provider registry for managing available LLM providers.
"""

from typing import Dict, List, Type
from .base import BaseLLMProvider
from .mistral import MistralProvider
from .qwen import QwenProvider
from .glm import GLMProvider
from .minimax import MiniMaxProvider
from .deepseek import DeepSeekProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider
from .gemini_image import GeminiImageProvider


class ProviderRegistry:
    """Registry for all available LLM providers."""

    # Registry of provider name to provider class
    _providers: Dict[str, Type[BaseLLMProvider]] = {
        "mistral": MistralProvider,
        "qwen": QwenProvider,
        "glm": GLMProvider,
        "minimax": MiniMaxProvider,
        "deepseek": DeepSeekProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "gemini_image": GeminiImageProvider,
    }

    @classmethod
    def get_provider(cls, provider_name: str) -> BaseLLMProvider:
        """
        Get a provider instance by name.

        Args:
            provider_name: Name of the provider (e.g., 'mistral', 'qwen')

        Returns:
            Instance of the provider

        Raises:
            ValueError: If provider_name is not registered
        """
        if provider_name not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Available providers: {', '.join(cls.list_providers())}"
            )
        return cls._providers[provider_name]()

    @classmethod
    def list_providers(cls) -> List[str]:
        """
        List all registered provider names.

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())

    @classmethod
    def get_all_models(cls) -> Dict[str, List[Dict[str, str]]]:
        """
        Get all available models grouped by provider.

        Returns:
            Dict mapping provider names to their available models
            Example: {
                "mistral": [
                    {"id": "mistral-large-latest", "name": "Mistral Large", ...},
                    ...
                ]
            }
        """
        result = {}
        for provider_name in cls.list_providers():
            provider = cls.get_provider(provider_name)
            result[provider_name] = provider.get_available_models()
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
    def find_provider_for_model(cls, model_id: str) -> tuple[str, BaseLLMProvider]:
        """
        Find which provider supports a given model ID.

        Args:
            model_id: Model ID to search for

        Returns:
            Tuple of (provider_name, provider_instance)

        Raises:
            ValueError: If model_id is not found in any provider
        """
        for provider_name in cls.list_providers():
            provider = cls.get_provider(provider_name)
            model_ids = [m["id"] for m in provider.get_available_models()]
            if model_id in model_ids:
                return provider_name, provider

        raise ValueError(
            f"Model '{model_id}' not found in any registered provider. "
            f"Use get_all_models() to see available models."
        )
