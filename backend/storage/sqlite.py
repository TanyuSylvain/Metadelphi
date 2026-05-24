"""
SQLite storage implementation for conversation persistence.

This module provides persistent storage using SQLite with support for:
- Conversation metadata tracking
- Mode tracking (simple/debate)
- Debate state preservation across turns
- Message history with metadata
"""

import json
import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import aiosqlite

from .base import ConversationStorage

logger = logging.getLogger(__name__)


class SQLiteStorage(ConversationStorage):
    """SQLite-based persistent storage backend."""

    def __init__(self, database_path: str = "conversations.db"):
        """
        Initialize SQLite storage.

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = database_path
        self._initialized = False

    async def _init_db(self):
        """Initialize database schema if needed."""
        if self._initialized:
            return

        # Ensure parent directory exists
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.database_path) as db:
            # Enable foreign keys
            await db.execute("PRAGMA foreign_keys = ON")

            # Create conversations table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    mode TEXT DEFAULT 'simple',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    title TEXT,
                    metadata_json TEXT
                )
            """)

            # Create messages table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    model TEXT,
                    message_type TEXT,
                    iteration INTEGER,
                    metadata_json TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
            """)

            # Create indexes for performance
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp
                ON messages(timestamp)
            """)

            await db.commit()

        self._initialized = True
        logger.info(f"SQLite storage initialized at {self.database_path}")

    async def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation metadata."""
        await self._init_db()

        async with aiosqlite.connect(self.database_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None

                # Convert to dict
                conv = dict(row)
                # Parse metadata JSON
                if conv.get("metadata_json"):
                    try:
                        conv["metadata"] = json.loads(conv["metadata_json"])
                    except json.JSONDecodeError:
                        conv["metadata"] = {}
                else:
                    conv["metadata"] = {}
                del conv["metadata_json"]

                return conv

    async def get_messages(self, conversation_id: str) -> List[Dict]:
        """Get all messages in a conversation."""
        await self._init_db()

        async with aiosqlite.connect(self.database_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT role, content, timestamp, model, message_type,
                       iteration, metadata_json
                FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
                """,
                (conversation_id,)
            ) as cursor:
                rows = await cursor.fetchall()

                messages = []
                for row in rows:
                    msg = dict(row)
                    # Parse metadata JSON
                    if msg.get("metadata_json"):
                        try:
                            msg["metadata"] = json.loads(msg["metadata_json"])
                        except json.JSONDecodeError:
                            msg["metadata"] = {}
                    else:
                        msg["metadata"] = {}
                    del msg["metadata_json"]

                    messages.append(msg)

                return messages

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model: Optional[str] = None,
        message_type: Optional[str] = None,
        iteration: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Unique conversation identifier
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            model: Model used for this message (optional)
            message_type: Type of message (optional)
                - 'user_query', 'final_answer', 'moderator_init',
                  'moderator_synthesize', 'expert_answer', 'critic_review'
            iteration: Debate iteration number (optional)
            metadata: Additional metadata (optional)
        """
        await self._init_db()

        # Ensure conversation exists
        conv = await self.get_conversation(conversation_id)
        if not conv:
            await self.create_conversation(conversation_id, model or "unknown")

        # Serialize metadata
        metadata_json = json.dumps(metadata) if metadata else None

        async with aiosqlite.connect(self.database_path) as db:
            # Insert message
            await db.execute(
                """
                INSERT INTO messages
                (conversation_id, role, content, timestamp, model,
                 message_type, iteration, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    role,
                    content,
                    datetime.now().isoformat(),
                    model,
                    message_type,
                    iteration,
                    metadata_json
                )
            )

            # Update conversation metadata
            await db.execute(
                """
                UPDATE conversations
                SET updated_at = ?,
                    message_count = message_count + 1
                WHERE id = ?
                """,
                (datetime.now().isoformat(), conversation_id)
            )

            await db.commit()

    async def create_conversation(
        self,
        conversation_id: str,
        model: str,
        metadata: Optional[Dict] = None,
        mode: str = "simple",
        title: Optional[str] = None
    ) -> None:
        """
        Create a new conversation.

        Args:
            conversation_id: Unique conversation identifier
            model: Model ID used for this conversation
            metadata: Additional metadata (optional)
            mode: Conversation mode ('simple' or 'debate')
            title: Conversation title (optional)
        """
        await self._init_db()

        # Serialize metadata
        metadata_json = json.dumps(metadata or {})

        async with aiosqlite.connect(self.database_path) as db:
            try:
                await db.execute(
                    """
                    INSERT INTO conversations
                    (id, model, mode, created_at, updated_at,
                     message_count, title, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        conversation_id,
                        model,
                        mode,
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        0,
                        title or "New Conversation",
                        metadata_json
                    )
                )
                await db.commit()
            except sqlite3.IntegrityError:
                # Conversation already exists
                pass

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        await self._init_db()

        async with aiosqlite.connect(self.database_path) as db:
            cursor = await db.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """List all conversations."""
        await self._init_db()

        async with aiosqlite.connect(self.database_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM conversations
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            ) as cursor:
                rows = await cursor.fetchall()

                conversations = []
                for row in rows:
                    conv = dict(row)
                    # Parse metadata JSON
                    if conv.get("metadata_json"):
                        try:
                            conv["metadata"] = json.loads(conv["metadata_json"])
                        except json.JSONDecodeError:
                            conv["metadata"] = {}
                    else:
                        conv["metadata"] = {}
                    del conv["metadata_json"]

                    conversations.append(conv)

                return conversations

    async def conversation_exists(self, conversation_id: str) -> bool:
        """Check if a conversation exists."""
        await self._init_db()

        async with aiosqlite.connect(self.database_path) as db:
            async with db.execute(
                "SELECT 1 FROM conversations WHERE id = ? LIMIT 1",
                (conversation_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None

    async def update_conversation_title(
        self,
        conversation_id: str,
        title: str
    ) -> bool:
        """Update the title of a conversation."""
        await self._init_db()

        async with aiosqlite.connect(self.database_path) as db:
            cursor = await db.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, datetime.now().isoformat(), conversation_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def update_conversation_metadata(
        self,
        conversation_id: str,
        metadata: Dict
    ) -> bool:
        """
        Update conversation metadata.

        Args:
            conversation_id: Unique conversation identifier
            metadata: New metadata to merge with existing

        Returns:
            True if updated, False if conversation not found
        """
        await self._init_db()

        # Get existing conversation
        conv = await self.get_conversation(conversation_id)
        if not conv:
            return False

        # Extract mode if present in metadata
        mode = metadata.pop("mode", None)

        # Merge metadata
        existing_metadata = conv.get("metadata", {})
        merged_metadata = {**existing_metadata, **metadata}

        async with aiosqlite.connect(self.database_path) as db:
            if mode:
                # Update both mode and metadata
                cursor = await db.execute(
                    """
                    UPDATE conversations
                    SET mode = ?, metadata_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        mode,
                        json.dumps(merged_metadata),
                        datetime.now().isoformat(),
                        conversation_id
                    )
                )
            else:
                # Update only metadata
                cursor = await db.execute(
                    """
                    UPDATE conversations
                    SET metadata_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        json.dumps(merged_metadata),
                        datetime.now().isoformat(),
                        conversation_id
                    )
                )
            await db.commit()
            return cursor.rowcount > 0

    async def update_debate_state(
        self,
        conversation_id: str,
        debate_state: Dict
    ) -> bool:
        """
        Update debate state in conversation metadata.

        Args:
            conversation_id: Unique conversation identifier
            debate_state: Debate state to store

        Returns:
            True if updated, False if conversation not found
        """
        return await self.update_conversation_metadata(
            conversation_id,
            {"debate_state": debate_state}
        )

    async def get_debate_state(self, conversation_id: str) -> Optional[Dict]:
        """
        Get debate state from conversation metadata.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            Debate state dict or None
        """
        conv = await self.get_conversation(conversation_id)
        if not conv:
            return None

        return conv.get("metadata", {}).get("debate_state")

    async def delete_all_conversations(self) -> int:
        """Delete all conversations and their messages."""
        await self._init_db()

        async with aiosqlite.connect(self.database_path) as db:
            # Count conversations
            async with db.execute("SELECT COUNT(*) FROM conversations") as cursor:
                row = await cursor.fetchone()
                count = row[0] if row else 0

            # Delete all
            await db.execute("DELETE FROM conversations")
            await db.commit()

            return count
