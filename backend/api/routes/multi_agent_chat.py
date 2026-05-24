"""
Multi-Agent Debate Chat endpoints.

Provides endpoints for the multi-agent debate workflow with
Moderator-Expert-Critic collaboration.
"""

import asyncio
import json
import logging
import uuid
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

from backend.api.schemas import (
    MultiAgentChatRequest,
    MultiAgentChatResponse,
    MultiAgentModelConfig,
    ThinkingConfig
)
from backend.api.model_refs import resolve_model
from backend.api.run_control import CANCELLATION_MESSAGE, persist_cancellation_notice, run_manager
from backend.core.multi_agent import MultiAgentDebateWorkflow
from backend.core.run_manager import RunCancelledError
from backend.storage import get_storage
from backend.config import settings
from backend.providers import ProviderFactory, ProviderRegistry
from backend.utils.errors import sanitize_error_message

router = APIRouter(prefix="/chat/multi-agent", tags=["multi-agent-chat"])

# Shared storage instance
_storage = get_storage(
    backend=settings.storage_backend,
    database_url=settings.database_url
)

# Workflow pool (keyed by model combination)
_workflows: dict[str, MultiAgentDebateWorkflow] = {}


def get_workflow(
    moderator_model: str,
    expert_model: str,
    critic_model: str,
    max_iterations: int = 3,
    score_threshold: float = 80.0,
    thinking_moderator: bool = False,
    thinking_expert: bool = False,
    thinking_critic: bool = False
) -> MultiAgentDebateWorkflow:
    """
    Get or create a workflow instance for the specified model combination.

    Args:
        moderator_model: Model ID for moderator role
        expert_model: Model ID for expert role
        critic_model: Model ID for critic role
        max_iterations: Maximum debate iterations
        score_threshold: Score threshold for passing
        thinking_moderator: Enable thinking for moderator
        thinking_expert: Enable thinking for expert
        thinking_critic: Enable thinking for critic

    Returns:
        MultiAgentDebateWorkflow instance
    """
    global _workflows, _storage

    # Key includes all configuration including thinking parameters
    workflow_key = (
        f"{moderator_model}:{thinking_moderator}:"
        f"{expert_model}:{thinking_expert}:"
        f"{critic_model}:{thinking_critic}:"
        f"{max_iterations}:{score_threshold}"
    )

    if workflow_key not in _workflows:
        _workflows[workflow_key] = MultiAgentDebateWorkflow(
            moderator_model=moderator_model,
            expert_model=expert_model,
            critic_model=critic_model,
            storage=_storage,
            max_iterations=max_iterations,
            score_threshold=score_threshold,
            thinking_moderator=thinking_moderator,
            thinking_expert=thinking_expert,
            thinking_critic=thinking_critic
        )

    return _workflows[workflow_key]


def resolve_models(models: MultiAgentModelConfig = None) -> tuple[str, str, str]:
    """
    Resolve model configuration with defaults.

    Args:
        models: Optional per-role model configuration

    Returns:
        Tuple of (moderator_model, expert_model, critic_model)
    """
    default_model = get_debate_default_model()

    if models is None:
        return default_model, default_model, default_model

    return (
        models.moderator or default_model,
        models.expert or default_model,
        models.critic or default_model
    )


def get_debate_default_model() -> str:
    """Return a valid model ID for debate defaults."""
    configured_default = settings.default_model

    if configured_default:
        try:
            provider_name, _provider = ProviderRegistry.find_provider_for_model(configured_default)
            _, raw_model_id = ProviderRegistry.parse_model_ref(configured_default)
            return ProviderRegistry.build_model_ref(provider_name, raw_model_id)
        except ValueError:
            pass

    all_models = ProviderFactory.list_all_models()
    if not all_models:
        raise HTTPException(status_code=500, detail="No registered models are available for debate mode")

    return all_models[0]["model_ref"]


def validate_resolved_models(
    moderator_model: str,
    expert_model: str,
    critic_model: str
) -> None:
    """Validate resolved role models before creating the workflow."""
    role_models = {
        "moderator": moderator_model,
        "expert": expert_model,
        "critic": critic_model,
    }

    for role, model_id in role_models.items():
        try:
            ProviderRegistry.find_provider_for_model(model_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid {role} model: {model_id}") from exc


def normalize_resolved_models(
    moderator_model: str,
    expert_model: str,
    critic_model: str,
) -> tuple[tuple[str, str], tuple[str, str], tuple[str, str]]:
    """Resolve provider-qualified refs to (provider, raw_model_id) tuples."""
    return (
        resolve_model(moderator_model),
        resolve_model(expert_model),
        resolve_model(critic_model),
    )


@router.post("/", response_model=MultiAgentChatResponse)
async def multi_agent_chat(request: MultiAgentChatRequest):
    """
    Send a message and get a complete multi-agent debate response.

    The workflow will:
    1. Moderator assesses question complexity
    2. For simple questions: returns direct answer
    3. For complex questions: Expert-Critic debate loop
    4. Moderator synthesizes final answer

    Args:
        request: MultiAgentChatRequest with message and optional configuration

    Returns:
        MultiAgentChatResponse with final answer and metadata
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        # Resolve models
        moderator_model, expert_model, critic_model = resolve_models(request.models)
        validate_resolved_models(moderator_model, expert_model, critic_model)
        moderator_resolved, expert_resolved, critic_resolved = normalize_resolved_models(
            moderator_model,
            expert_model,
            critic_model,
        )

        # Extract thinking configuration
        thinking = request.thinking or ThinkingConfig()

        # Get or create workflow
        workflow = get_workflow(
            moderator_model=moderator_resolved[1],
            expert_model=expert_resolved[1],
            critic_model=critic_resolved[1],
            max_iterations=request.max_iterations,
            score_threshold=request.score_threshold,
            thinking_moderator=thinking.moderator,
            thinking_expert=thinking.expert,
            thinking_critic=thinking.critic
        )

        conversation_id = request.conversation_id or str(uuid.uuid4())

        # Run the workflow
        result = await workflow.invoke(request.message, conversation_id)

        return MultiAgentChatResponse(
            conversation_id=conversation_id,
            models=MultiAgentModelConfig(
                moderator=ProviderRegistry.build_model_ref(*moderator_resolved),
                expert=ProviderRegistry.build_model_ref(*expert_resolved),
                critic=ProviderRegistry.build_model_ref(*critic_resolved),
            ),
            final_answer=result["final_answer"],
            was_direct_answer=result.get("was_direct_answer", False),
            termination_reason=result.get("termination_reason", "unknown"),
            total_iterations=result.get("total_iterations", 0)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=sanitize_error_message(e))


@router.post("/stream")
async def multi_agent_chat_stream(http_request: Request, request: MultiAgentChatRequest):
    """
    Send a message and get a streaming multi-agent debate response.

    Streams Server-Sent Events (SSE) with the following event types:
    - phase_start: New phase beginning
    - expert_answer: Expert's structured answer
    - critic_review: Critic's structured review
    - iteration_complete: Iteration finished
    - done: Final result
    - error: Error occurred

    Args:
        request: MultiAgentChatRequest with message and optional configuration

    Returns:
        StreamingResponse with SSE events
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Resolve models
    moderator_model, expert_model, critic_model = resolve_models(request.models)
    validate_resolved_models(moderator_model, expert_model, critic_model)
    moderator_resolved, expert_resolved, critic_resolved = normalize_resolved_models(
        moderator_model,
        expert_model,
        critic_model,
    )
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # Extract thinking configuration
    thinking = request.thinking or ThinkingConfig()

    run_context = await run_manager.create_run(mode="debate", conversation_id=conversation_id)

    async def generate():
        """Generate SSE stream of debate events."""
        task = asyncio.current_task()
        if task:
            await run_context.register_task(task)
        workflow = None
        try:
            workflow = get_workflow(
                moderator_model=moderator_resolved[1],
                expert_model=expert_resolved[1],
                critic_model=critic_resolved[1],
                max_iterations=request.max_iterations,
                score_threshold=request.score_threshold,
                thinking_moderator=thinking.moderator,
                thinking_expert=thinking.expert,
                thinking_critic=thinking.critic
            )

            async for event in workflow.stream(
                request.message,
                conversation_id,
                run_context=run_context,
            ):
                if await http_request.is_disconnected():
                    await run_context.cancel()
                    raise RunCancelledError("Client disconnected")
                # Format as SSE event
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        except asyncio.CancelledError:
            current_task = asyncio.current_task()
            if current_task:
                while current_task.cancelling():
                    current_task.uncancel()

            await run_context.cancel()
            await persist_cancellation_notice(_storage, conversation_id)
            if workflow and conversation_id:
                await workflow.refresh_debate_context(conversation_id)
        except RunCancelledError:
            await persist_cancellation_notice(_storage, conversation_id)
            if workflow and conversation_id:
                await workflow.refresh_debate_context(conversation_id)
            if not await http_request.is_disconnected():
                event_data = json.dumps({"type": "cancelled", "message": CANCELLATION_MESSAGE}, ensure_ascii=False)
                yield f"data: {event_data}\n\n"
        except Exception as e:
            logger.error("Multi-agent chat route error", exc_info=True)
            error_msg = sanitize_error_message(e) or "An unexpected error occurred."
            error_event = json.dumps({
                "type": "error",
                "error": error_msg
            }, ensure_ascii=False)
            yield f"data: {error_event}\n\n"
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
            "X-Moderator-Model": moderator_resolved[1],
            "X-Expert-Model": expert_resolved[1],
            "X-Critic-Model": critic_resolved[1]
        }
    )
