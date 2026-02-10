"""
Coworking Agent Chat endpoints.

Provides endpoints for the coworking agent with tool calling,
file operations, and code execution within a workspace.
"""

import os
import json
import uuid
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse

from backend.api.schemas import CoworkingChatRequest
from backend.core.coworking_agent import CoworkingAgent
from backend.tools.workspace_tools import resolve_in_workspace
from backend.storage import get_storage
from backend.config import settings

router = APIRouter(prefix="/chat/coworking", tags=["coworking-chat"])

# Shared storage instance
_storage = get_storage(
    backend=settings.storage_backend,
    database_url=settings.database_url
)

# Agent pool (keyed by model_id:thinking)
_agents: dict[str, CoworkingAgent] = {}


def get_agent(model_id: str, thinking: bool = False) -> CoworkingAgent:
    """
    Get or create a coworking agent instance.

    Args:
        model_id: Model ID to use
        thinking: Enable thinking mode

    Returns:
        CoworkingAgent instance
    """
    global _agents, _storage

    agent_key = f"{model_id}:{thinking}"
    if agent_key not in _agents:
        _agents[agent_key] = CoworkingAgent(
            model_id=model_id,
            storage=_storage,
            thinking=thinking
        )
    return _agents[agent_key]


@router.post("/stream")
async def coworking_chat_stream(request: CoworkingChatRequest):
    """
    Send a message and get a streaming coworking agent response.

    Streams Server-Sent Events (SSE) with event types:
    - plan: Workflow plan steps
    - thinking_chunk: Agent reasoning token
    - tool_start: Before tool execution
    - tool_result: After tool execution
    - file_created: File written to workspace
    - response_chunk: Final response token
    - done: Workflow complete
    - error: Error occurred
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Validate workspace path
    workspace_path = os.path.abspath(request.workspace_path)
    if not os.path.isabs(request.workspace_path):
        raise HTTPException(status_code=400, detail="workspace_path must be an absolute path")

    # Resolve model
    model_id = request.model or settings.default_model
    conversation_id = request.conversation_id or str(uuid.uuid4())

    async def generate():
        """Generate SSE stream of coworking agent events."""
        try:
            agent = get_agent(
                model_id=model_id,
                thinking=request.thinking or False
            )

            async for event in agent.stream(
                question=request.message,
                conversation_id=conversation_id,
                workspace_path=workspace_path,
                max_iterations=request.max_iterations
            ):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        except Exception as e:
            error_event = json.dumps({
                "type": "error",
                "error": str(e)
            }, ensure_ascii=False)
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-ID": conversation_id,
            "X-Model-ID": model_id
        }
    )


@router.get("/files")
async def download_file(
    workspace_path: str = Query(..., description="Workspace directory path"),
    file_path: str = Query(..., description="File path relative to workspace")
):
    """
    Download a file from the workspace.

    Args:
        workspace_path: Absolute path to workspace directory
        file_path: Relative path to file within workspace
    """
    try:
        resolved = resolve_in_workspace(workspace_path, file_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not os.path.exists(resolved):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if not os.path.isfile(resolved):
        raise HTTPException(status_code=400, detail=f"Not a file: {file_path}")

    return FileResponse(
        path=resolved,
        filename=os.path.basename(resolved)
    )
