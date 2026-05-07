"""
FastAPI main application entry point.

This is the refactored version of the original server.py
with improved structure and organization.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.api.routes import api_router

# Initialize FastAPI app
app = FastAPI(
    title="Metadelphi API",
    description="Multi-provider LLM chat API with streaming support",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routes
app.include_router(api_router)

# Serve React frontend if dist-react exists
_DIST_REACT = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist-react")
if os.path.isdir(_DIST_REACT):
    app.mount("/", StaticFiles(directory=_DIST_REACT, html=True), name="frontend")
else:
    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/docs")


@app.get("/info")
async def info():
    """
    Get API information.
    """
    from backend.providers import ProviderRegistry

    return {
        "name": "Metadelphi API",
        "version": "2.0.0",
        "description": "Multi-provider LLM chat API",
        "providers": ProviderRegistry.list_providers(),
        "default_model": settings.default_model,
        "endpoints": {
            "GET /": "API documentation (redirect)",
            "GET /info": "API information",
            "GET /health": "Health check",
            "GET /models": "List all available models",
            "GET /models/providers": "List all providers",
            "GET /models/providers/{provider}": "Get provider info",
            "POST /chat": "Send message, get complete response",
            "POST /chat/stream": "Send message, get streaming response",
            "GET /conversations": "List all conversations",
            "GET /conversations/{id}": "Get conversation history",
            "DELETE /conversations/{id}": "Delete conversation"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    )
