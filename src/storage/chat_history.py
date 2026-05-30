"""
会话历史持久化模块
基于 SQLite 实现跨会话的对话历史存储
"""

import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class SQLiteChatHistory:
    """基于 SQLite 的会话历史管理器"""

    def __init__(self, db_path: Optional[str] = None):
        settings = get_settings()
        if db_path is None:
            db_path = str(Path(settings.project_root) / "data" / "chat_history.db")
        self.db_path = db_path
        self._local = threading.local()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        """)
        conn.commit()

    def add_message(self, session_id: str, role: str, content: str):
        now = datetime.now().isoformat()
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )
        conn.execute(
            "INSERT OR REPLACE INTO sessions (session_id, created_at, updated_at) "
            "VALUES (?, COALESCE((SELECT created_at FROM sessions WHERE session_id = ?), ?), ?)",
            (session_id, session_id, now, now),
        )
        conn.commit()

    def get_messages(self, session_id: str) -> List[BaseMessage]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        )
        messages = []
        for role, content in cursor.fetchall():
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        return messages

    def get_session_list(self) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT session_id, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
        )
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "session_id": row[0],
                "created_at": row[1],
                "updated_at": row[2],
            })
        return sessions

    def delete_session(self, session_id: str):
        conn = self._get_conn()
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        logger.info(f"删除会话: {session_id}")

    def clear_all(self):
        conn = self._get_conn()
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM sessions")
        conn.commit()
        logger.info("清除所有会话历史")

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


_manager: Optional[SQLiteChatHistory] = None


def get_chat_history_manager() -> SQLiteChatHistory:
    global _manager
    if _manager is None:
        _manager = SQLiteChatHistory()
    return _manager
