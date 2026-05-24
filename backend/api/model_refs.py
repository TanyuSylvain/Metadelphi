"""
Helpers for provider-qualified model references used by the frontend.
"""

from backend.providers.registry import ProviderRegistry


def resolve_model(model_ref: str, provider_name: str | None = None) -> tuple[str, str]:
    """
    Resolve a model reference to (provider_name, raw_model_id).

    Supports both provider-qualified refs like ``qwen::glm-5`` and legacy
    raw model IDs like ``glm-5``.
    """
    resolved_provider, _provider = ProviderRegistry.find_provider_for_model(
        model_ref,
        provider_name=provider_name,
    )
    _, raw_model_id = ProviderRegistry.parse_model_ref(model_ref)
    return resolved_provider, raw_model_id

