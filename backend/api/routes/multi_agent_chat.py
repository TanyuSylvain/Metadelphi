"""
Multi-Agent Debate Chat endpoints.

Provides endpoints for the multi-agent debate workflow with
Moderator-Expert-Critic collaboration.
"""

import json
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.api.schemas import (
    MultiAgentChatRequest,
    MultiAgentChatResponse,
    MultiAgentModelConfig,
    ThinkingConfig
)
from backend.core.multi_agent import MultiAgentDebateWorkflow
from backend.storage import get_storage
from backend.config import settings
from backend.providers import ProviderFactory, ProviderRegistry

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
            ProviderRegistry.find_provider_for_model(configured_default)
            return configured_default
        except ValueError:
            pass

    all_models = ProviderFactory.list_all_models()
    if not all_models:
        raise HTTPException(status_code=500, detail="No registered models are available for debate mode")

    return all_models[0]["model_id"]


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

        # Extract thinking configuration
        thinking = request.thinking or ThinkingConfig()

        # Get or create workflow
        workflow = get_workflow(
            moderator_model=moderator_model,
            expert_model=expert_model,
            critic_model=critic_model,
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
                moderator=moderator_model,
                expert=expert_model,
                critic=critic_model
            ),
            final_answer=result["final_answer"],
            was_direct_answer=result.get("was_direct_answer", False),
            termination_reason=result.get("termination_reason", "unknown"),
            total_iterations=result.get("total_iterations", 0)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def multi_agent_chat_stream(request: MultiAgentChatRequest):
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
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # Extract thinking configuration
    thinking = request.thinking or ThinkingConfig()

    async def generate():
        """Generate SSE stream of debate events."""
        try:
            workflow = get_workflow(
                moderator_model=moderator_model,
                expert_model=expert_model,
                critic_model=critic_model,
                max_iterations=request.max_iterations,
                score_threshold=request.score_threshold,
                thinking_moderator=thinking.moderator,
                thinking_expert=thinking.expert,
                thinking_critic=thinking.critic
            )

            async for event in workflow.stream(request.message, conversation_id):
                # Format as SSE event
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
            "X-Moderator-Model": moderator_model,
            "X-Expert-Model": expert_model,
            "X-Critic-Model": critic_model
        }
    )
