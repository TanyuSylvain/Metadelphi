"""
Settings routes for provider configuration management.
"""

import asyncio

from fastapi import APIRouter, HTTPException
from backend.config import settings
from backend.api.schemas import (
    ProviderSettingsResponse,
    ProviderUpdateRequest,
    SettingsUpdateResponse,
    ProviderTestResponse,
    SearchEngineStatusResponse,
    SearchEngineUpdateRequest,
    SearchEngineUpdateResponse,
)
from backend.tools.web_search import clear_tool_cache

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/providers", response_model=ProviderSettingsResponse)
async def get_provider_settings():
    """Get current provider configurations with masked API keys."""
    configs = settings.get_provider_configs()
    return ProviderSettingsResponse(providers=configs)


@router.put("/providers", response_model=SettingsUpdateResponse)
async def update_provider_settings(request: ProviderUpdateRequest):
    """Update provider API keys and base URLs."""
    try:
        # Validate provider IDs
        for provider_id in request.providers:
            if provider_id.upper() not in settings.PROVIDERS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown provider: {provider_id}"
                )

        updated = settings.update_providers(request.providers)
        # Search tool cache may be stale if Tavily or Bailian key changed
        clear_tool_cache()
        return SettingsUpdateResponse(
            success=True,
            message=f"Updated {len(updated)} provider(s)",
            providers_updated=updated
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/{provider_id}/test", response_model=ProviderTestResponse)
async def test_provider_connection(provider_id: str):
    """Test a provider connection using its lightest model."""
    if provider_id.upper() not in settings.PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")

    result = await asyncio.to_thread(settings.test_provider, provider_id)
    return ProviderTestResponse(**result)


@router.get("/search-engine", response_model=SearchEngineStatusResponse)
async def get_search_engine_status():
    """Get configured search engines and the current default."""
    return SearchEngineStatusResponse(**settings.get_search_engine_status())


@router.put("/search-engine", response_model=SearchEngineUpdateResponse)
async def update_search_engine(request: SearchEngineUpdateRequest):
    """Update the default search engine."""
    success = settings.update_default_search_engine(request.default)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Invalid search engine. Must be 'bailian' or 'tavily'."
        )
    clear_tool_cache()
    return SearchEngineUpdateResponse(
        success=True,
        message="Default search engine updated",
        default=settings.default_search_engine,
    )
