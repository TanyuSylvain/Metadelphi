"""
Chat endpoints for interacting with LLM agents.
"""

import asyncio
import json
import uuid
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import httpx

from backend.api.schemas import ChatRequest, ChatResponse
from backend.api.model_refs import resolve_model
from backend.api.run_control import CANCELLATION_MESSAGE, persist_cancellation_notice, run_manager
from backend.core.agent import LangGraphAgent
from backend.core.run_manager import RunCancelledError
from backend.tools.web_search import get_web_search_tools
from backend.storage import get_storage
from backend.config import settings
from backend.providers.registry import ProviderRegistry
from backend.utils.errors import sanitize_error_message
from backend.utils.conversation_mode import record_used_mode

router = APIRouter(prefix="/chat", tags=["chat"])

IMAGE_INTENT_CLASSIFIER_MODEL = "gpt-5.4-mini"
IMAGE_INTENT_CLASSIFIER_CONFIDENCE_THRESHOLD = 0.75

# Shared storage instance for all agents
_storage = get_storage(
    backend=settings.storage_backend,
    database_url=settings.database_url
)

# Agent pool (keyed by model_id + thinking mode)
_agents: dict[str, LangGraphAgent] = {}


def _format_sse_event(event: dict) -> str:
    """Serialize a stream event as SSE."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _latest_image_from_history(history: list[dict]) -> dict | None:
    """Return the most recent generated image payload from stored history."""
    for msg in reversed(history):
        if msg.get("role") != "assistant":
            continue
        try:
            parsed = json.loads(msg.get("content", ""))
        except (json.JSONDecodeError, TypeError):
            continue
        images = parsed.get("images")
        if not isinstance(images, list) or not images:
            continue
        latest = images[-1]
        if isinstance(latest, dict) and latest.get("data"):
            return {
                "data": latest.get("data", ""),
                "mime_type": latest.get("mime_type", "image/png"),
                "index": latest.get("index"),
            }
    return None


def _parse_classifier_json(text: str) -> dict:
    """Parse classifier JSON, tolerating models that wrap it in prose."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


async def _classify_image_intent(prompt: str) -> dict:
    """
    Classify whether an image-mode follow-up should create a new image or edit
    the latest generated image. Fail closed to generation.
    """
    api_key = settings.get_api_key("openai")
    if not api_key:
        return {"action": "generate", "reason": "classifier_api_key_missing"}

    base = (settings.get_base_url("openai") or "https://api.openai.com/v1").rstrip("/")
    endpoint = f"{base}/chat/completions"
    messages = [
        {
            "role": "system",
            "content": (
                "Classify the user's next image-mode prompt. "
                "Return JSON only with: intent ('generate_new', 'edit_previous', or 'unclear'), "
                "confidence (0 to 1), and reason. "
                "Use edit_previous only when the user clearly asks to change, adjust, revise, "
                "remove, add to, restyle, or otherwise modify the latest generated image."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    body = {
        "model": IMAGE_INTENT_CLASSIFIER_MODEL,
        "messages": messages,
        "max_completion_tokens": 120,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint, json=body, headers=headers)
            if response.status_code == 400:
                fallback_body = {
                    "model": IMAGE_INTENT_CLASSIFIER_MODEL,
                    "messages": messages,
                    "max_tokens": 120,
                }
                response = await client.post(endpoint, json=fallback_body, headers=headers)
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = _parse_classifier_json(content)
        intent = str(parsed.get("intent", "unclear"))
        confidence = float(parsed.get("confidence", 0))
        if intent == "edit_previous" and confidence >= IMAGE_INTENT_CLASSIFIER_CONFIDENCE_THRESHOLD:
            return {
                "action": "edit",
                "reason": "classifier",
                "classifier_model": IMAGE_INTENT_CLASSIFIER_MODEL,
                "confidence": confidence,
            }
        return {
            "action": "generate",
            "reason": "classifier_generate_or_unclear",
            "classifier_model": IMAGE_INTENT_CLASSIFIER_MODEL,
            "confidence": confidence,
        }
    except Exception as e:
        return {
            "action": "generate",
            "reason": "classifier_failed",
            "classifier_model": IMAGE_INTENT_CLASSIFIER_MODEL,
            "error": sanitize_error_message(e, default="Intent classification failed."),
        }


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

    provider_name, raw_model_id = resolve_model(model_id)

    # Key includes thinking mode and web search since they affect the agent behavior
    agent_key = f"{provider_name}:{raw_model_id}:{thinking}:{web_search}"

    if agent_key not in _agents:
        tools = []
        if web_search:
            tools = await get_web_search_tools()

        _agents[agent_key] = LangGraphAgent(
            model_id=raw_model_id,
            provider_name=provider_name,
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
        _, raw_model_id = resolve_model(model_id)
        thinking = request.thinking if request.thinking is not None else False
        web_search = request.web_search or False
        agent = await get_agent(model_id, thinking, web_search)
        conversation_id = request.conversation_id or str(uuid.uuid4())

        response = await agent.invoke(request.message, conversation_id)

        return ChatResponse(
            response=response,
            conversation_id=conversation_id,
            model=raw_model_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=sanitize_error_message(e))


@router.post("/stream")
async def chat_stream(http_request: Request, request: ChatRequest):
    """
    Send a message and get a streaming response.

    Args:
        request: ChatRequest with message, optional conversation_id, and optional model

    Returns:
        StreamingResponse with SSE events for response chunks and terminal status
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    conversation_id = request.conversation_id or str(uuid.uuid4())
    model_id = request.model or settings.default_model
    _, raw_model_id = resolve_model(model_id)
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
                yield _format_sse_event({"type": "chunk", "content": chunk})
        except asyncio.CancelledError:
            await run_context.cancel()
            await persist_cancellation_notice(_storage, conversation_id)
        except RunCancelledError:
            await persist_cancellation_notice(_storage, conversation_id)
            if not await http_request.is_disconnected():
                yield _format_sse_event({"type": "cancelled", "message": CANCELLATION_MESSAGE})
        except Exception as e:
            yield _format_sse_event({
                "type": "error",
                "error": sanitize_error_message(e),
            })
        else:
            yield _format_sse_event({"type": "done"})
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
            "X-Model-ID": raw_model_id
        }
    )


@router.post("/image/stream")
async def image_chat_stream(http_request: Request, request: ChatRequest):
    """
    Send a prompt to an image generation model and get an SSE response.

    Streams Server-Sent Events with the following event types:
    - {"type": "image_routing", "image_action": "generate"|"edit", ...}
    - {"type": "text_chunk", "content": "..."}  — text description
    - {"type": "image", "data": "<base64>", "mime_type": "image/png", "index": N}
    - {"type": "done"}
    - {"type": "error", "message": "..."}
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    conversation_id = request.conversation_id or str(uuid.uuid4())
    model_id = request.model or "gemini-2.5-flash-image"
    provider_name, raw_model_id = resolve_model(model_id)

    try:
        provider = ProviderRegistry.get_provider(provider_name)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_id}")

    api_key = settings.get_api_key(provider_name)
    base_url = settings.get_base_url(provider_name)
    if not api_key:
        raise HTTPException(status_code=500, detail=f"API key not configured for {provider_name}")

    run_context = await run_manager.create_run(mode="image", conversation_id=conversation_id)

    async def generate():
        task = asyncio.current_task()
        if task:
            await run_context.register_task(task)
        try:
            # Ensure conversation exists in storage and is marked as image mode
            conversation = await _storage.get_conversation(conversation_id)
            if not conversation:
                await _storage.create_conversation(
                    conversation_id=conversation_id,
                    model=raw_model_id,
                    mode="image",
                    title=request.message[:60],
                )
            elif conversation.get("mode") != "image":
                await _storage.update_conversation_metadata(
                    conversation_id,
                    {"mode": "image"}
                )

            # Load history for multi-turn support and fallback edit detection
            history = await _storage.get_messages(conversation_id)
            messages = provider.build_messages(history, request.message)

            latest_history_image = _latest_image_from_history(history)
            edit_source_image = request.edit_source_image.model_dump() if request.edit_source_image else None
            routing = {
                "image_action": "generate",
                "routing_reason": "default_generate",
            }

            if request.image_action == "edit":
                edit_source_image = edit_source_image or latest_history_image
                routing = {
                    "image_action": "edit" if edit_source_image else "generate",
                    "routing_reason": "explicit_user_selection" if edit_source_image else "explicit_edit_without_source",
                }
            elif request.image_action == "generate":
                routing = {
                    "image_action": "generate",
                    "routing_reason": "explicit_generate",
                }
            elif latest_history_image and provider_name in {"openai_image", "gemini_image"}:
                classifier_result = await _classify_image_intent(request.message)
                if classifier_result.get("action") == "edit":
                    edit_source_image = latest_history_image
                    routing = {
                        "image_action": "edit",
                        "routing_reason": "classifier",
                        "classifier_model": classifier_result.get("classifier_model"),
                        "confidence": classifier_result.get("confidence"),
                    }
                else:
                    routing = {
                        "image_action": "generate",
                        "routing_reason": classifier_result.get("reason", "classifier_generate_or_unclear"),
                        "classifier_model": classifier_result.get("classifier_model"),
                        "confidence": classifier_result.get("confidence"),
                        "classifier_error": classifier_result.get("error"),
                    }

            if routing["image_action"] == "edit" and provider_name not in {"openai_image", "gemini_image"}:
                yield _format_sse_event({
                    "type": "error",
                    "message": "Image editing is currently supported only by OpenAI and Gemini image providers.",
                })
                return

            # Persist user message
            await _storage.add_message(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                metadata={"image_routing": routing},
            )
            yield _format_sse_event({"type": "image_routing", **routing})

            text_acc = []
            image_acc = []

            async for event in provider.generate(
                messages,
                raw_model_id,
                api_key,
                base_url=base_url,
                aspect_ratio=request.aspect_ratio,
                edit_source_image=edit_source_image if routing["image_action"] == "edit" else None,
            ):
                if await http_request.is_disconnected():
                    await run_context.cancel()
                    return

                event_type = event.get("type")
                if event_type == "text_chunk":
                    text_acc.append(event.get("content", ""))
                elif event_type == "image":
                    image_acc.append({
                        "data": event.get("data", ""),
                        "mime_type": event.get("mime_type", "image/png"),
                        "index": event.get("index"),
                    })
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
                model=raw_model_id,
                message_type="image_response",
                metadata={"image_routing": routing},
            )
            await record_used_mode(_storage, conversation_id, "image")

        except asyncio.CancelledError:
            await run_context.cancel()
            await persist_cancellation_notice(_storage, conversation_id)
        except Exception as e:
            err_event = {
                "type": "error",
                "message": sanitize_error_message(e, default="Image generation failed."),
            }
            yield _format_sse_event(err_event)
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
            "X-Model-ID": raw_model_id,
        }
    )
