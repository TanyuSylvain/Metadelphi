"""
Shared helpers for streaming run cancellation.
"""

from typing import Optional

from backend.core.run_manager import run_manager


CANCELLATION_MESSAGE = "Current task was cancelled."


async def persist_cancellation_notice(storage, conversation_id: Optional[str]) -> None:
    """Persist a standard cancellation notice to conversation history."""
    if not conversation_id:
        return

    await storage.add_message(
        conversation_id=conversation_id,
        role="system",
        content=CANCELLATION_MESSAGE,
        metadata={"event": "run_cancelled"},
    )


__all__ = ["CANCELLATION_MESSAGE", "persist_cancellation_notice", "run_manager"]
