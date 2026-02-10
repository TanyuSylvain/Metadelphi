"""
Conversation management endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.api.schemas import (
    ConversationsResponse,
    ConversationInfo,
    ConversationHistoryResponse,
    MessageInfo,
    SwitchModeRequest,
    SwitchModeResponse
)
from backend.storage import MemoryStorage
from backend.core.conversation_mode_manager import ConversationModeManager

router = APIRouter(prefix="/conversations", tags=["conversations"])

# Shared storage instance (same as used in chat routes)
# In production, this should be injected via dependency injection
from backend.api.routes.chat import _storage


@router.get("/", response_model=ConversationsResponse)
async def list_conversations(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of conversations to return"),
    offset: int = Query(0, ge=0, description="Number of conversations to skip")
):
    """
    List all conversations.

    Args:
        limit: Maximum number of conversations to return (1-100)
        offset: Number of conversations to skip

    Returns:
        List of conversations with metadata
    """
    conversations = await _storage.list_conversations(limit=limit, offset=offset)
    return ConversationsResponse(
        conversations=[ConversationInfo(**conv) for conv in conversations],
        count=len(conversations)
    )


@router.get("/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(conversation_id: str):
    """
    Get the full history of a conversation.

    Args:
        conversation_id: Conversation ID

    Returns:
        Conversation history with all messages
    """
    if not await _storage.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await _storage.get_messages(conversation_id)
    return ConversationHistoryResponse(
        conversation_id=conversation_id,
        messages=[MessageInfo(**msg) for msg in messages]
    )


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation and all its messages.

    Args:
        conversation_id: Conversation ID

    Returns:
        Success message
    """
    deleted = await _storage.delete_conversation(conversation_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"message": f"Conversation {conversation_id} deleted successfully"}


@router.delete("/")
async def delete_all_conversations():
    """
    Delete all conversations and their messages.

    Returns:
        Success message with count of deleted conversations
    """
    count = await _storage.delete_all_conversations()
    return {"message": f"Deleted {count} conversation(s)"}


@router.get("/{conversation_id}/info", response_model=ConversationInfo)
async def get_conversation_info(conversation_id: str):
    """
    Get metadata about a conversation without fetching all messages.

    Args:
        conversation_id: Conversation ID

    Returns:
        Conversation metadata
    """
    conversation = await _storage.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationInfo(**conversation)


@router.post("/{conversation_id}/switch-mode", response_model=SwitchModeResponse)
async def switch_mode(conversation_id: str, request: SwitchModeRequest):
    """
    Switch conversation mode between simple and debate.

    Args:
        conversation_id: Conversation ID
        request: Mode switch request with target mode and optional config

    Returns:
        Switch mode response with success status
    """
    # Validate target mode
    if request.target_mode not in ("simple", "debate", "coworking"):
        raise HTTPException(
            status_code=400,
            detail="target_mode must be 'simple', 'debate', or 'coworking'"
        )

    # Create mode manager
    mode_manager = ConversationModeManager(_storage)

    try:
        result = await mode_manager.switch_mode(
            conversation_id=conversation_id,
            target_mode=request.target_mode,
            model_config=request.debate_config
        )
        return SwitchModeResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
