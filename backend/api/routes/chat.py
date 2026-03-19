"""
Chat endpoints for interacting with LLM agents.
"""

import asyncio
import uuid
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.api.schemas import ChatRequest, ChatResponse
from backend.api.run_control import persist_cancellation_notice, run_manager
from backend.core.agent import LangGraphAgent
from backend.core.run_manager import RunCancelledError
from backend.tools.web_search import get_web_search_tools
from backend.storage import get_storage
from backend.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])

# Shared storage instance for all agents
_storage = get_storage(
    backend=settings.storage_backend,
    database_url=settings.database_url
)

# Agent pool (keyed by model_id + thinking mode)
_agents: dict[str, LangGraphAgent] = {}


async def get_agent(model_id: str, thinking: bool = False, web_search: bool = False) -> LangGraphAgent:
    """
    Get or create an agent instance for the specified model, thinking mode, and web search.

    Args:
        model_id: Model ID to use
        thinking: Whether thinking mode is enabled
        web_search: Whether web search is enabled

    Returns:
        LangGraphAgent instance
    """
    global _agents, _storage

    # Key includes thinking mode and web search since they affect the agent behavior
    agent_key = f"{model_id}:{thinking}:{web_search}"

    if agent_key not in _agents:
        tools = []
        if web_search:
            tools = await get_web_search_tools()

        _agents[agent_key] = LangGraphAgent(
            model_id=model_id,
            storage=_storage,
            thinking=thinking,
            tools=tools
        )

    return _agents[agent_key]


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message and get a complete response.

    Args:
        request: ChatRequest with message, optional conversation_id, and optional model

    Returns:
        ChatResponse with the agent's response
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        model_id = request.model or settings.default_model
        thinking = request.thinking if request.thinking is not None else False
        web_search = request.web_search or False
        agent = await get_agent(model_id, thinking, web_search)
        conversation_id = request.conversation_id or str(uuid.uuid4())

        response = await agent.invoke(request.message, conversation_id)

        return ChatResponse(
            response=response,
            conversation_id=conversation_id,
            model=model_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(http_request: Request, request: ChatRequest):
    """
    Send a message and get a streaming response.

    Args:
        request: ChatRequest with message, optional conversation_id, and optional model

    Returns:
        StreamingResponse with chunks of the agent's response
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    conversation_id = request.conversation_id or str(uuid.uuid4())
    model_id = request.model or settings.default_model
    thinking = request.thinking if request.thinking is not None else False
    web_search = request.web_search or False

    run_context = await run_manager.create_run(mode="simple", conversation_id=conversation_id)

    async def generate():
        """Generate streaming response chunks."""
        task = asyncio.current_task()
        if task:
            await run_context.register_task(task)
        try:
            agent = await get_agent(model_id, thinking, web_search)
            async for chunk in agent.stream(
                request.message,
                conversation_id,
                run_context=run_context,
            ):
                if await http_request.is_disconnected():
                    await run_context.cancel()
                    raise RunCancelledError("Client disconnected")
                yield chunk
        except asyncio.CancelledError:
            await run_context.cancel()
            await persist_cancellation_notice(_storage, conversation_id)
        except RunCancelledError:
            await persist_cancellation_notice(_storage, conversation_id)
        except Exception as e:
            yield f"\n[Error: {str(e)}]"
        finally:
            if task:
                await run_context.unregister_task(task)
            await run_manager.finish_run(run_context.run_id)
            run_context.mark_finished()

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-ID": conversation_id,
            "X-Run-ID": run_context.run_id,
            "X-Model-ID": model_id
        }
    )
