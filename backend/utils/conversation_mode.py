"""
Helpers for recording which modes actually produced assistant output.
"""

from typing import Optional

from backend.storage.base import ConversationStorage


async def record_used_mode(
    storage: ConversationStorage,
    conversation_id: Optional[str],
    mode: str,
) -> None:
    """Append a mode to conversation metadata once assistant output is persisted."""
    if not conversation_id:
        return

    conversation = await storage.get_conversation(conversation_id)
    if not conversation:
        return

    metadata = conversation.get("metadata", {}) or {}
    history = metadata.get("mode_history")
    if isinstance(history, list):
        mode_history = [entry for entry in history if isinstance(entry, str)]
    else:
        mode_history = []

    if mode not in mode_history:
        mode_history.append(mode)
        await storage.update_conversation_metadata(
            conversation_id,
            {"mode_history": mode_history}
        )
