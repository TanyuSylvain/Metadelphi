"""
Settings routes for provider configuration management.
"""

import asyncio

from fastapi import APIRouter, HTTPException
from backend.config import settings
from backend.api.schemas import (
    ProviderSettingsResponse,
    ProviderTestResponse,
    ProviderModelTestRequest,
    SearchEngineStatusResponse,
    SearchEngineUpdateRequest,
    SearchEngineUpdateResponse,
    ConfigResponse,
    ConfigUpdateRequest,
    ConfigUpdateResponse,
)
from backend.tools.web_search import clear_tool_cache

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/config", response_model=ConfigResponse)
async def get_full_config():
    """Get the full application configuration."""
    return ConfigResponse(config=settings.get_full_config())


@router.put("/config", response_model=ConfigUpdateResponse)
async def update_full_config(request: ConfigUpdateRequest):
    """Validate and persist the full application configuration."""
    try:
        raw_config = request.config.model_dump()
        settings.update_config(raw_config)
        clear_tool_cache()
        return ConfigUpdateResponse(
            success=True,
            message="Configuration saved",
            errors=None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "message": "Validation failed",
                "errors": str(e).split("; ") if ";" in str(e) else [str(e)],
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers", response_model=ProviderSettingsResponse)
async def get_provider_settings():
    """Get current provider configurations with masked API keys."""
    configs = settings.get_provider_configs()
    return ProviderSettingsResponse(providers=configs)


@router.post("/providers/test-model", response_model=ProviderTestResponse)
async def test_provider_model(request: ProviderModelTestRequest):
    """Test a provider/model using the supplied (possibly unsaved) credentials."""
    if request.provider_id.lower() not in settings.PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {request.provider_id}")

    result = await asyncio.to_thread(
        settings.test_model,
        request.provider_id,
        request.model_id,
        request.api_key,
        request.base_url,
        request.is_image_model,
    )
    return ProviderTestResponse(**result)


@router.post("/providers/{provider_id}/models/{model_id}/test", response_model=ProviderTestResponse)
async def test_provider_model_legacy(provider_id: str, model_id: str):
    """Test a specific saved provider/model connection using a ping-pong prompt."""
    if provider_id.lower() not in settings.PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")

    result = await asyncio.to_thread(settings.test_provider_model, provider_id, model_id)
    return ProviderTestResponse(**result)


@router.post("/providers/{provider_id}/test", response_model=ProviderTestResponse)
async def test_provider_connection(provider_id: str):
    """Test a provider connection using its first configured model (legacy endpoint)."""
    provider_id = provider_id.lower()
    if provider_id not in settings.PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")

    models = settings.get_provider_models(provider_id)
    if not models:
        raise HTTPException(status_code=400, detail=f"No models configured for provider: {provider_id}")

    result = await asyncio.to_thread(settings.test_provider_model, provider_id, models[0]["id"])
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
