"""
Conversation Mode Manager

Handles switching between simple and debate modes for conversations,
including context transfer and metadata updates.
"""

import logging
from typing import Dict, Optional, Literal
from backend.storage.base import ConversationStorage

logger = logging.getLogger(__name__)


class ConversationModeManager:
    """Manages conversation mode switching and context transfer."""

    def __init__(self, storage: ConversationStorage):
        """
        Initialize the mode manager.

        Args:
            storage: Storage backend for conversation data
        """
        self.storage = storage

    async def switch_mode(
        self,
        conversation_id: str,
        target_mode: Literal["simple", "debate", "coworking"],
        model_config: Optional[Dict] = None
    ) -> Dict:
        """
        Switch conversation mode and prepare context.

        Args:
            conversation_id: Unique conversation identifier
            target_mode: Target mode ('simple' or 'debate')
            model_config: Model configuration for debate mode (required if target is 'debate')

        Returns:
            Dict with success status and message
        """
        # Get conversation if it exists
        conversation = await self.storage.get_conversation(conversation_id)
        if not conversation:
            # Conversation not created yet - mode will be set when first message is sent
            # Just return success, the frontend maintains the mode state
            logger.info(f"Conversation {conversation_id} not found, mode switch deferred until first message")
            return {
                "success": True,
                "conversation_id": conversation_id,
                "mode": target_mode,
                "message": f"Mode set to {target_mode} (will apply on first message)"
            }

        current_mode = conversation.get("mode", "simple")

        # Check if already in target mode
        if current_mode == target_mode:
            return {
                "success": True,
                "conversation_id": conversation_id,
                "mode": target_mode,
                "message": f"Already in {target_mode} mode"
            }

        # Prepare metadata update
        metadata = conversation.get("metadata", {})

        if target_mode == "debate":
            # Switching to debate mode
            if not model_config:
                raise ValueError("model_config is required when switching to debate mode")

            # Store model configuration
            metadata["model_config"] = model_config

            # Build conversation context for debate
            context = await self.prepare_debate_context(conversation_id)
            if context:
                metadata["debate_state"] = {
                    "conversation_context": context,
                    "previous_summary": "",
                    "last_iteration": 0
                }

            message = "Previous conversation context prepared."

        elif target_mode == "coworking":
            # Switching to coworking mode
            message = ""

        else:
            # Switching to simple mode
            # Clear debate-specific metadata
            has_debate_config = "model_config" in metadata
            metadata.pop("model_config", None)
            # Keep debate_state for history but mark as inactive
            if "debate_state" in metadata:
                metadata["debate_state"]["active"] = False

            message = "Debate configuration cleared." if has_debate_config else ""

        # Update conversation
        await self.update_conversation_mode(
            conversation_id=conversation_id,
            mode=target_mode,
            metadata=metadata
        )

        logger.info(f"Switched conversation {conversation_id} from {current_mode} to {target_mode}")

        return {
            "success": True,
            "conversation_id": conversation_id,
            "mode": target_mode,
            "message": message
        }

    async def prepare_debate_context(
        self,
        conversation_id: str,
        limit: int = 5
    ) -> str:
        """
        Build context summary for debate mode from conversation history.

        Args:
            conversation_id: Unique conversation identifier
            limit: Maximum number of message pairs to include

        Returns:
            Formatted context string
        """
        messages = await self.storage.get_messages(conversation_id)

        # Filter to user and assistant messages only
        relevant_messages = [
            msg for msg in messages
            if msg.get("role") in ("user", "assistant")
        ]

        # Take last N message pairs
        recent_messages = relevant_messages[-(limit * 2):]

        if not recent_messages:
            return ""

        # Format as conversation context
        context_lines = ["Previous conversation:"]
        for msg in recent_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Truncate very long messages
            if len(content) > 500:
                content = content[:500] + "..."

            if role == "user":
                context_lines.append(f"\nUser: {content}")
            elif role == "assistant":
                context_lines.append(f"Assistant: {content}")

        return "\n".join(context_lines)

    async def update_conversation_mode(
        self,
        conversation_id: str,
        mode: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Update conversation metadata with new mode.

        Args:
            conversation_id: Unique conversation identifier
            mode: New conversation mode
            metadata: Full metadata to update (optional)
        """
        # Get current conversation
        conversation = await self.storage.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Update mode in database
        # Note: SQLite and Memory storage need to support mode updates
        # For now, we'll update via metadata

        update_data = {"mode": mode}
        if metadata is not None:
            update_data.update(metadata)

        # Update conversation metadata
        await self.storage.update_conversation_metadata(
            conversation_id,
            update_data
        )
