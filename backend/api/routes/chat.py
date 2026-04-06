"""
Chat endpoints for interacting with LLM agents.
"""

import asyncio
import json
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
from backend.providers.gemini_image import GeminiImageProvider

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


@router.post("/image/stream")
async def image_chat_stream(http_request: Request, request: ChatRequest):
    """
    Send a prompt to an image generation model and get an SSE response.

    Streams Server-Sent Events with the following event types:
    - {"type": "text_chunk", "content": "..."}  — text description
    - {"type": "image", "data": "<base64>", "mime_type": "image/png", "index": N}
    - {"type": "done"}
    - {"type": "error", "message": "..."}
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    conversation_id = request.conversation_id or str(uuid.uuid4())
    model_id = request.model or "gemini-2.5-flash-image-preview"

    api_key = settings.get_api_key("gemini")
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")

    provider = GeminiImageProvider()

    run_context = await run_manager.create_run(mode="image", conversation_id=conversation_id)

    async def generate():
        task = asyncio.current_task()
        if task:
            await run_context.register_task(task)
        try:
            # Ensure conversation exists in storage
            if not await _storage.conversation_exists(conversation_id):
                await _storage.create_conversation(
                    conversation_id=conversation_id,
                    model=model_id,
                    mode="image",
                    title=request.message[:60],
                )

            # Load history for multi-turn support
            history = await _storage.get_messages(conversation_id)
            messages = GeminiImageProvider.build_messages(history, request.message)

            # Persist user message
            await _storage.add_message(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
            )

            text_acc = []
            image_acc = []

            async for event in provider.generate(messages, model_id, api_key):
                if await http_request.is_disconnected():
                    await run_context.cancel()
                    return

                event_type = event.get("type")
                if event_type == "text_chunk":
                    text_acc.append(event.get("content", ""))
                elif event_type == "image":
                    image_acc.append({"data": event.get("data", ""), "mime_type": event.get("mime_type", "image/png")})
                elif event_type == "error":
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    return

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # Persist assistant message as JSON
            assistant_content = json.dumps(
                {"text": "".join(text_acc), "images": image_acc},
                ensure_ascii=False,
            )
            await _storage.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_content,
                model=model_id,
                message_type="image_response",
            )

        except asyncio.CancelledError:
            await run_context.cancel()
            await persist_cancellation_notice(_storage, conversation_id)
        except Exception as e:
            err_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(err_event)}\n\n"
        finally:
            if task:
                await run_context.unregister_task(task)
            await run_manager.finish_run(run_context.run_id)
            run_context.mark_finished()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-ID": conversation_id,
            "X-Run-ID": run_context.run_id,
            "X-Model-ID": model_id,
        }
    )
