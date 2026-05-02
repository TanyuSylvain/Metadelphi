"""
API routes module.
"""

from fastapi import APIRouter
from .health import router as health_router
from .chat import router as chat_router
from .models import router as models_router
from .conversations import router as conversations_router
from .multi_agent_chat import router as multi_agent_chat_router
from .coworking_chat import router as coworking_chat_router
from .run_control import router as run_control_router
from .settings import router as settings_router

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(models_router)
api_router.include_router(conversations_router)
api_router.include_router(multi_agent_chat_router)
api_router.include_router(coworking_chat_router)
api_router.include_router(run_control_router)
api_router.include_router(settings_router)

__all__ = ["api_router"]
