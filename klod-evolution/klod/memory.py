import sqlite3
from pathlib import Path


class ConversationMemory:
    def __init__(self, database: str | Path, max_messages_per_conversation: int = 100):
        self.database = Path(database).expanduser().resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.max_messages = max(10, max_messages_per_conversation)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_conversation "
                "ON messages(conversation_id, id)"
            )

    def _connect(self):
        connection = sqlite3.connect(self.database, timeout=10)
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def add(self, conversation_id: str, role: str, content: str) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("role must be user or assistant")
        if not conversation_id or len(conversation_id) > 80:
            raise ValueError("invalid conversation_id")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content must not be empty")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO messages(conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, role, content[:12000]),
            )
            connection.execute(
                """
                DELETE FROM messages
                WHERE conversation_id = ?
                  AND id NOT IN (
                    SELECT id FROM messages
                    WHERE conversation_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                  )
                """,
                (conversation_id, conversation_id, self.max_messages),
            )

    def recent(self, conversation_id: str, limit: int = 8) -> list[dict]:
        bounded_limit = max(1, min(int(limit), 40))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, bounded_limit),
            ).fetchall()
        return [
            {"role": role, "content": content, "created_at": created_at}
            for role, content, created_at in reversed(rows)
        ]

    def clear(self, conversation_id: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            return cursor.rowcount
