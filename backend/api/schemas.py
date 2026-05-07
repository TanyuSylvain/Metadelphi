"""
Pydantic schemas for API request and response models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class ChatRequest(BaseModel):
    """Request model for chat endpoints."""
    message: str = Field(..., description="User's message", min_length=1)
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for multi-turn chat")
    model: Optional[str] = Field(None, description="Model ID to use (e.g., 'mistral-large-latest')")
    thinking: Optional[bool] = Field(None, description="Enable thinking mode for models that support it")
    web_search: Optional[bool] = Field(False, description="Enable web search via DASHSCOPE MCP")
    aspect_ratio: Optional[str] = Field(None, description="Aspect ratio for image generation (e.g. 1:1, 16:9)")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What is machine learning?",
                "conversation_id": "conv-123",
                "model": "mistral-large-latest",
                "thinking": False,
                "web_search": False
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Assistant's response")
    conversation_id: str = Field(..., description="Conversation ID")
    model: str = Field(..., description="Model used for the response")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "Machine learning is...",
                "conversation_id": "conv-123",
                "model": "mistral-large-latest"
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "message": "Service is running"
            }
        }


class ModelInfo(BaseModel):
    """Information about a specific model."""
    provider: str = Field(..., description="Provider ID")
    provider_name: str = Field(..., description="Human-readable provider name")
    model_id: str = Field(..., description="Model ID")
    model_name: str = Field(..., description="Model display name")
    description: str = Field(..., description="Model description")
    supports_thinking: bool = Field(False, description="Whether thinking mode can be enabled")
    thinking_locked: bool = Field(False, description="Whether thinking mode is always on and cannot be disabled")
    is_image_model: bool = Field(False, description="Whether this model generates images instead of text")


class ModelsResponse(BaseModel):
    """Response model for listing models."""
    models: List[ModelInfo] = Field(..., description="List of available models")
    count: int = Field(..., description="Total number of models")


class ProviderInfo(BaseModel):
    """Information about a provider."""
    name: str = Field(..., description="Human-readable provider name")
    provider_id: str = Field(..., description="Provider ID")
    models: List[Dict[str, str]] = Field(..., description="Available models")
    supports_streaming: bool = Field(..., description="Whether streaming is supported")


class ConversationInfo(BaseModel):
    """Information about a conversation."""
    id: str = Field(..., description="Conversation ID")
    model: str = Field(..., description="Model used")
    mode: str = Field(default="simple", description="Conversation mode: 'simple', 'debate', or 'coworking'")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    message_count: int = Field(..., description="Number of messages")
    title: str = Field(..., description="Conversation title")
    metadata: Dict = Field(default_factory=dict, description="Conversation metadata")


class ConversationsResponse(BaseModel):
    """Response model for listing conversations."""
    conversations: List[ConversationInfo] = Field(..., description="List of conversations")
    count: int = Field(..., description="Total number of conversations")


class MessageInfo(BaseModel):
    """Information about a message."""
    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp")
    model: Optional[str] = Field(None, description="Model used (for assistant messages)")
    message_type: Optional[str] = Field(None, description="Message type (e.g. final_answer, moderator_init)")
    metadata: Optional[Dict] = Field(default=None, description="Message metadata including metrics")


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""
    conversation_id: str = Field(..., description="Conversation ID")
    messages: List[MessageInfo] = Field(..., description="List of messages")


# =============================================================================
# Metrics Schema
# =============================================================================

class StreamMetrics(BaseModel):
    """Performance metrics for an LLM response."""
    ttfb_ms: Optional[float] = Field(None, description="Time to First Byte in milliseconds")
    tps: Optional[float] = Field(None, description="Tokens Per Second")
    total_tokens: Optional[int] = Field(None, description="Total tokens (input + output)")
    input_tokens: Optional[int] = Field(None, description="Input/prompt tokens")
    output_tokens: Optional[int] = Field(None, description="Output/completion tokens")
    model_id: Optional[str] = Field(None, description="Model ID used for the response")


# =============================================================================
# Multi-Agent Debate Schemas
# =============================================================================

class MultiAgentModelConfig(BaseModel):
    """Per-role model configuration for multi-agent debate."""
    moderator: Optional[str] = Field(None, description="Model ID for moderator role")
    expert: Optional[str] = Field(None, description="Model ID for expert role")
    critic: Optional[str] = Field(None, description="Model ID for critic role")

    class Config:
        json_schema_extra = {
            "example": {
                "moderator": "glm-4-flash",
                "expert": "qwen-max",
                "critic": "mistral-large-latest"
            }
        }


class ThinkingConfig(BaseModel):
    """Thinking configuration for each role."""
    moderator: bool = Field(default=False, description="Enable thinking for moderator")
    expert: bool = Field(default=False, description="Enable thinking for expert")
    critic: bool = Field(default=False, description="Enable thinking for critic")

    class Config:
        json_schema_extra = {
            "example": {
                "moderator": False,
                "expert": True,
                "critic": False
            }
        }


class MultiAgentChatRequest(BaseModel):
    """Request model for multi-agent chat endpoints."""
    message: str = Field(..., description="User's message", min_length=1)
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID")
    models: Optional[MultiAgentModelConfig] = Field(None, description="Per-role model configuration")
    max_iterations: int = Field(default=3, ge=1, le=10, description="Maximum debate iterations")
    score_threshold: float = Field(default=80.0, ge=0, le=100, description="Score threshold for passing")
    thinking: Optional[ThinkingConfig] = Field(None, description="Thinking configuration for each role")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What are the pros and cons of microservices architecture?",
                "conversation_id": "conv-123",
                "models": {
                    "moderator": "glm-4-flash",
                    "expert": "qwen-max",
                    "critic": "mistral-large-latest"
                },
                "max_iterations": 3,
                "score_threshold": 80.0
            }
        }


class CriticIssue(BaseModel):
    """Individual issue identified by the critic."""
    category: str = Field(..., description="Issue category: logic, facts, completeness, relevance")
    severity: str = Field(..., description="Issue severity: minor, moderate, major")
    description: str = Field(..., description="Issue description")
    quote: str = Field(..., description="Original text citation")


class ExpertAnswerSchema(BaseModel):
    """Structured expert answer format."""
    version: int = Field(..., description="Answer version/iteration number")
    understanding: str = Field(..., description="Problem understanding summary")
    core_points: List[str] = Field(..., description="Core arguments/points")
    details: str = Field(..., description="Detailed explanation")
    conclusion: str = Field(..., description="Conclusion summary")
    confidence: float = Field(..., ge=0, le=1, description="Confidence level")
    limitations: List[str] = Field(default=[], description="Known limitations")
    modification_log: List[str] = Field(default=[], description="Modification history")


class CriticReviewSchema(BaseModel):
    """Structured critic review format."""
    review_version: int = Field(..., description="Review version number")
    overall_score: float = Field(..., ge=0, le=100, description="Overall score")
    passed: bool = Field(..., description="Whether answer passes threshold")
    issues: List[CriticIssue] = Field(default=[], description="List of identified issues")
    strengths: List[str] = Field(default=[], description="Positive aspects")
    suggestions: List[str] = Field(default=[], description="Improvement suggestions")
    confidence: float = Field(..., ge=0, le=1, description="Review confidence")


class IterationUpdate(BaseModel):
    """Progress update for a single iteration."""
    iteration: int = Field(..., description="Iteration number")
    phase: str = Field(..., description="Current phase: moderator_init, expert_generate, critic_review, moderator_synthesize")
    expert_answer: Optional[ExpertAnswerSchema] = Field(None, description="Expert's answer")
    critic_review: Optional[CriticReviewSchema] = Field(None, description="Critic's review")
    summary: Optional[str] = Field(None, description="Iteration summary")


class MultiAgentChatResponse(BaseModel):
    """Response model for multi-agent chat endpoint."""
    conversation_id: str = Field(..., description="Conversation ID")
    models: MultiAgentModelConfig = Field(..., description="Models used for each role")
    final_answer: str = Field(..., description="Final synthesized answer")
    was_direct_answer: bool = Field(..., description="True if moderator answered directly (simple question)")
    termination_reason: str = Field(..., description="Reason for termination")
    total_iterations: int = Field(..., description="Total iterations completed")

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv-123",
                "models": {
                    "moderator": "glm-4-flash",
                    "expert": "qwen-max",
                    "critic": "mistral-large-latest"
                },
                "final_answer": "Based on the multi-agent debate...",
                "was_direct_answer": False,
                "termination_reason": "score_threshold",
                "total_iterations": 2
            }
        }


# =============================================================================
# Coworking Agent Schemas
# =============================================================================

class OpenFileRequest(BaseModel):
    """Request model for opening a file with the native application."""
    workspace_path: str = Field(..., description="Absolute path to workspace directory")
    file_path: str = Field(..., description="File path relative to workspace")


class CoworkingChatRequest(BaseModel):
    """Request model for coworking agent chat endpoints."""
    message: str = Field(..., description="User's message", min_length=1)
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID")
    model: Optional[str] = Field(None, description="Model ID to use")
    workspace_path: str = Field(..., description="Absolute path to workspace directory")
    thinking: Optional[bool] = Field(False, description="Enable thinking mode")
    web_search: Optional[bool] = Field(False, description="Enable web search via DASHSCOPE MCP")
    max_iterations: int = Field(default=25, ge=1, le=50, description="Maximum ReAct loop iterations")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Create a hello.txt file with 'Hello World'",
                "conversation_id": "conv-123",
                "model": "qwen-max",
                "workspace_path": "/tmp/workspace",
                "thinking": False,
                "max_iterations": 25
            }
        }


# =============================================================================
# Mode Switching Schemas
# =============================================================================

class SwitchModeRequest(BaseModel):
    """Request model for switching conversation mode."""
    target_mode: str = Field(..., description="Target mode: 'simple' or 'debate'")
    debate_config: Optional[Dict] = Field(None, description="Model configuration for debate mode")

    class Config:
        json_schema_extra = {
            "example": {
                "target_mode": "debate",
                "debate_config": {
                    "moderator": "glm-4-flash",
                    "expert": "qwen-max",
                    "critic": "mistral-large-latest",
                    "max_iterations": 3,
                    "score_threshold": 80.0
                }
            }
        }


class SwitchModeResponse(BaseModel):
    """Response model for mode switching."""
    success: bool = Field(..., description="Whether the switch was successful")
    conversation_id: str = Field(..., description="Conversation ID")
    mode: str = Field(..., description="Current mode after switch")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "conversation_id": "conv-123",
                "mode": "debate",
                "message": "Switched to debate mode. Previous conversation context prepared."
            }
        }


# =============================================================================
# Provider Settings Schemas
# =============================================================================

class ProviderConfig(BaseModel):
    """Configuration for a single provider."""
    api_key_masked: Optional[str] = Field(None, description="Masked API key for display")
    api_key_set: bool = Field(False, description="Whether an API key is configured")
    base_url: Optional[str] = Field(None, description="Current base URL")
    has_base_url: bool = Field(False, description="Whether this provider supports a base URL")
    display_name: str = Field(..., description="Human-readable provider name")
    console_url: str = Field(..., description="URL to get an API key")
    default_base_url: Optional[str] = Field(None, description="Default base URL")
    test_model: Optional[str] = Field(None, description="Model ID used for connection testing")
    category: str = Field("llm", description="Provider category: 'llm' or 'tool'")


class ProviderSettingsResponse(BaseModel):
    """Response for GET /settings/providers."""
    providers: Dict[str, ProviderConfig] = Field(..., description="Provider configurations keyed by provider ID")


class ProviderUpdateRequest(BaseModel):
    """Request for PUT /settings/providers."""
    providers: Dict[str, Dict[str, Optional[str]]] = Field(
        ...,
        description="Provider updates. Each key is a provider ID, value has optional 'api_key' and 'base_url'"
    )


class SettingsUpdateResponse(BaseModel):
    """Response for PUT /settings/providers."""
    success: bool = Field(..., description="Whether the update was successful")
    message: str = Field(..., description="Status message")
    providers_updated: List[str] = Field(default_factory=list, description="List of updated provider IDs")


class ProviderTestResponse(BaseModel):
    """Response for POST /settings/providers/{id}/test."""
    success: bool = Field(..., description="Whether the test passed")
    message: str = Field(..., description="Test result message")
    latency_ms: Optional[float] = Field(None, description="Response latency in milliseconds")
