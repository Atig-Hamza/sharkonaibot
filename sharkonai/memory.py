"""
SharkonAI Memory System — Enhanced
Permanent SQLite-based memory with task tracking, learned facts,
conversation summaries, and semantic context retrieval.
"""

import json
import sqlite3
import asyncio
from datetime import datetime
from typing import Optional

from config import CONFIG
from logger import log


class Memory:
    """Persistent memory system using SQLite — enhanced with task tracking and knowledge."""

    def __init__(self, db_path: str = CONFIG.DATABASE_PATH):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Create a new connection (thread-safe pattern for async)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self):
        """Initialize database schema with enhanced tables."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    user_id INTEGER,
                    message_id INTEGER,
                    metadata TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    parameters TEXT DEFAULT '{}',
                    result TEXT DEFAULT '',
                    success INTEGER DEFAULT 1,
                    thought TEXT DEFAULT '',
                    response TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- NEW: Task tracking for multi-step operations
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    steps_completed INTEGER DEFAULT 0,
                    steps_total INTEGER DEFAULT 0,
                    result TEXT DEFAULT '',
                    error TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}'
                );

                -- NEW: Learned facts / knowledge base
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    source TEXT DEFAULT 'observation'
                );

                -- NEW: Conversation summaries for long-term context
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    start_message_id INTEGER,
                    end_message_id INTEGER,
                    summary TEXT NOT NULL,
                    topics TEXT DEFAULT '[]'
                );

                CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
                CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);
                CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON actions(timestamp);
                CREATE INDEX IF NOT EXISTS idx_actions_type ON actions(action_type);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category);
                CREATE INDEX IF NOT EXISTS idx_knowledge_key ON knowledge(key);
            """)
            conn.commit()
            log.info("Memory database initialized successfully (enhanced schema).")
        except Exception as e:
            log.error(f"Failed to initialize database: {e}")
            raise
        finally:
            conn.close()

    # ── Messages ────────────────────────────────────────────────────────────

    async def store_message(
        self,
        role: str,
        content: str,
        user_id: Optional[int] = None,
        message_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ):
        """Store a message (user or assistant) in memory."""
        async with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """INSERT INTO messages (timestamp, role, content, user_id, message_id, metadata)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        datetime.utcnow().isoformat(),
                        role,
                        content,
                        user_id,
                        message_id,
                        json.dumps(metadata or {}),
                    ),
                )
                conn.commit()
                log.debug(f"Stored {role} message: {content[:80]}...")
            finally:
                conn.close()

    async def get_recent_messages(self, limit: int = CONFIG.MAX_CONTEXT_MESSAGES) -> list[dict]:
        """Retrieve recent messages for AI context."""
        async with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    """SELECT role, content, timestamp FROM messages
                       ORDER BY id DESC LIMIT ?""",
                    (limit,),
                ).fetchall()
                return [dict(row) for row in reversed(rows)]
            finally:
                conn.close()

    async def get_message_count(self) -> int:
        """Return total number of stored messages."""
        async with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute("SELECT COUNT(*) as cnt FROM messages").fetchone()
                return row["cnt"]
            finally:
                conn.close()

    # ── Actions ─────────────────────────────────────────────────────────────

    async def store_action(
        self,
        action_type: str,
        parameters: dict,
        result: str,
        success: bool,
        thought: str = "",
        response: str = "",
    ):
        """Store an executed action in memory."""
        async with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """INSERT INTO actions (timestamp, action_type, parameters, result, success, thought, response)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        datetime.utcnow().isoformat(),
                        action_type,
                        json.dumps(parameters),
                        result,
                        1 if success else 0,
                        thought,
                        response,
                    ),
                )
                conn.commit()
                log.debug(f"Stored action: {action_type}")
            finally:
                conn.close()

    async def get_recent_actions(self, limit: int = 10) -> list[dict]:
        """Retrieve recent actions for context."""
        async with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    """SELECT action_type, parameters, result, success, thought, timestamp
                       FROM actions ORDER BY id DESC LIMIT ?""",
                    (limit,),
                ).fetchall()
                return [dict(row) for row in reversed(rows)]
            finally:
                conn.close()

    async def get_action_count(self) -> int:
        """Return total number of stored actions."""
        async with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute("SELECT COUNT(*) as cnt FROM actions").fetchone()
                return row["cnt"]
            finally:
                conn.close()

    # ── State ───────────────────────────────────────────────────────────────

    async def set_state(self, key: str, value: str):
        """Store or update a state key-value pair."""
        async with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """INSERT INTO state (key, value, updated_at)
                       VALUES (?, ?, ?)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                    (key, value, datetime.utcnow().isoformat()),
                )
                conn.commit()
            finally:
                conn.close()

    async def get_state(self, key: str) -> Optional[str]:
        """Retrieve a state value by key."""
        async with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT value FROM state WHERE key = ?", (key,)
                ).fetchone()
                return row["value"] if row else None
            finally:
                conn.close()

    # ── Tasks (NEW) ─────────────────────────────────────────────────────────

    async def create_task(self, description: str, steps_total: int = 0, metadata: dict = None) -> int:
        """Create a new task for tracking multi-step operations. Returns task_id."""
        async with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute(
                    """INSERT INTO tasks (timestamp, description, status, steps_total, metadata)
                       VALUES (?, ?, 'in_progress', ?, ?)""",
                    (
                        datetime.utcnow().isoformat(),
                        description,
                        steps_total,
                        json.dumps(metadata or {}),
                    ),
                )
                conn.commit()
                task_id = cursor.lastrowid
                log.info(f"Created task #{task_id}: {description}")
                return task_id
            finally:
                conn.close()

    async def update_task(self, task_id: int, status: str = None, steps_completed: int = None,
                          result: str = None, error: str = None):
        """Update a task's progress."""
        async with self._lock:
            conn = self._get_conn()
            try:
                updates = []
                params = []
                if status is not None:
                    updates.append("status = ?")
                    params.append(status)
                if steps_completed is not None:
                    updates.append("steps_completed = ?")
                    params.append(steps_completed)
                if result is not None:
                    updates.append("result = ?")
                    params.append(result)
                if error is not None:
                    updates.append("error = ?")
                    params.append(error)
                if updates:
                    params.append(task_id)
                    conn.execute(
                        f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
                        tuple(params),
                    )
                    conn.commit()
            finally:
                conn.close()

    async def get_active_tasks(self) -> list[dict]:
        """Get all currently active tasks."""
        async with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    """SELECT id, description, status, steps_completed, steps_total, timestamp
                       FROM tasks WHERE status = 'in_progress'
                       ORDER BY id DESC LIMIT 10"""
                ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    # ── Knowledge (NEW) ─────────────────────────────────────────────────────

    async def store_knowledge(self, category: str, key: str, value: str,
                               confidence: float = 1.0, source: str = "observation"):
        """Store a learned fact or piece of knowledge."""
        async with self._lock:
            conn = self._get_conn()
            try:
                # Upsert: update if same category+key exists
                existing = conn.execute(
                    "SELECT id FROM knowledge WHERE category = ? AND key = ?",
                    (category, key),
                ).fetchone()
                if existing:
                    conn.execute(
                        """UPDATE knowledge SET value = ?, confidence = ?, source = ?, timestamp = ?
                           WHERE id = ?""",
                        (value, confidence, source, datetime.utcnow().isoformat(), existing["id"]),
                    )
                else:
                    conn.execute(
                        """INSERT INTO knowledge (timestamp, category, key, value, confidence, source)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (datetime.utcnow().isoformat(), category, key, value, confidence, source),
                    )
                conn.commit()
                log.debug(f"Stored knowledge: [{category}] {key}")
            finally:
                conn.close()

    async def get_knowledge(self, category: str = None, limit: int = 20) -> list[dict]:
        """Retrieve stored knowledge, optionally filtered by category."""
        async with self._lock:
            conn = self._get_conn()
            try:
                if category:
                    rows = conn.execute(
                        """SELECT category, key, value, confidence, source, timestamp
                           FROM knowledge WHERE category = ?
                           ORDER BY confidence DESC, timestamp DESC LIMIT ?""",
                        (category, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """SELECT category, key, value, confidence, source, timestamp
                           FROM knowledge ORDER BY timestamp DESC LIMIT ?""",
                        (limit,),
                    ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    async def search_knowledge(self, query: str, limit: int = 10) -> list[dict]:
        """Search knowledge by key or value content."""
        async with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    """SELECT category, key, value, confidence FROM knowledge
                       WHERE key LIKE ? OR value LIKE ?
                       ORDER BY confidence DESC LIMIT ?""",
                    (f"%{query}%", f"%{query}%", limit),
                ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    # ── Summaries (NEW) ─────────────────────────────────────────────────────

    async def store_summary(self, summary: str, start_id: int, end_id: int, topics: list = None):
        """Store a conversation summary."""
        async with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """INSERT INTO summaries (timestamp, start_message_id, end_message_id, summary, topics)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        datetime.utcnow().isoformat(),
                        start_id,
                        end_id,
                        summary,
                        json.dumps(topics or []),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    async def get_recent_summaries(self, limit: int = 5) -> list[dict]:
        """Get recent conversation summaries for long-term context."""
        async with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    """SELECT summary, topics, timestamp FROM summaries
                       ORDER BY id DESC LIMIT ?""",
                    (limit,),
                ).fetchall()
                return [dict(row) for row in reversed(rows)]
            finally:
                conn.close()

    # ── Search ──────────────────────────────────────────────────────────────

    async def search_messages(self, query: str, limit: int = 20) -> list[dict]:
        """Search messages by content."""
        async with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    """SELECT role, content, timestamp FROM messages
                       WHERE content LIKE ? ORDER BY id DESC LIMIT ?""",
                    (f"%{query}%", limit),
                ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    # ── Maintenance ─────────────────────────────────────────────────────────

    async def clear_memory(self):
        """Clear all stored data (use with caution)."""
        async with self._lock:
            conn = self._get_conn()
            try:
                conn.executescript("""
                    DELETE FROM messages;
                    DELETE FROM actions;
                    DELETE FROM state;
                    DELETE FROM tasks;
                    DELETE FROM knowledge;
                    DELETE FROM summaries;
                """)
                conn.commit()
                log.warning("All memory cleared!")
            finally:
                conn.close()

    async def get_context_bundle(self) -> dict:
        """Build a rich context bundle for the AI brain — includes messages, actions, knowledge, tasks, summaries."""
        messages = await self.get_recent_messages(limit=CONFIG.MAX_CONTEXT_MESSAGES)
        actions = await self.get_recent_actions(limit=8)
        knowledge = await self.get_knowledge(limit=15)
        tasks = await self.get_active_tasks()
        summaries = await self.get_recent_summaries(limit=3)
        return {
            "messages": messages,
            "actions": actions,
            "knowledge": knowledge,
            "active_tasks": tasks,
            "summaries": summaries,
        }
