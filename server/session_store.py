"""Persistent conversation store — SQLite.

There is ONE ongoing conversation (not one per device). Every device that
talks to Groot appends to and reads from this same history, which is what
makes "same session follows me across devices" actually true instead of
each client keeping its own separate list.
"""

import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent / "data" / "groot.sqlite3"
MAX_HISTORY_TURNS = 12  # turns kept in the "active" context sent to the LLM


def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,          -- 'user' or 'assistant'
                content TEXT NOT NULL,
                device_id TEXT,               -- which device this came from/was spoken on
                source TEXT,                  -- 'local' or 'claude:<model>' for assistant turns
                created_at REAL NOT NULL
            )
        """)


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def add_message(role: str, content: str, device_id: str = None, source: str = None):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (role, content, device_id, source, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (role, content, device_id, source, time.time()),
        )


def get_recent_history(limit_turns: int = MAX_HISTORY_TURNS) -> list[dict]:
    """Returns the last N turns as [{"role": ..., "content": ...}, ...]
    in chronological order, ready to hand to llm_client.get_response()."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
            (limit_turns * 2,),  # user+assistant pairs
        ).fetchall()
    rows.reverse()
    return [{"role": r, "content": c} for r, c in rows]


_init_db()
