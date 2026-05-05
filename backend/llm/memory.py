"""
MedPak AI — Conversation Memory Manager
Manages per-session chat history in memory with SQLite persistence.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import threading
import time
from config import settings


# ── In-memory store ───────────────────────────────────────────────────────────
# session_id → list of {"role": "user"|"assistant", "content": str, "ts": float}
_sessions: dict[str, list[dict]] = {}
_session_lock = threading.Lock()


# ── SQLite history DB ─────────────────────────────────────────────────────────

def _init_history_db():
    """Create history table if it doesn't exist."""
    conn = sqlite3.connect(settings.HISTORY_DB_PATH, timeout=30)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT    NOT NULL,
            role        TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            timestamp   REAL    NOT NULL
        )
    """)
    conn.commit()
    conn.close()


_init_history_db()


# ── Memory operations ─────────────────────────────────────────────────────────

def get_history(session_id: str) -> list[dict]:
    """
    Return conversation history for a session (in-memory, role+content only).
    """
    with _session_lock:
        return [
            {"role": m["role"], "content": m["content"]}
            for m in _sessions.get(session_id, [])
        ]


def add_turn(session_id: str, user_msg: str, assistant_msg: str):
    """
    Append one user+assistant exchange to the session.
    Persists to SQLite and keeps in-memory store trimmed.
    """
    now = time.time()
    with _session_lock:
        if session_id not in _sessions:
            _sessions[session_id] = []

        _sessions[session_id].append({"role": "user", "content": user_msg, "ts": now})
        _sessions[session_id].append({"role": "assistant", "content": assistant_msg, "ts": now})

        max_msgs = settings.MAX_HISTORY_TURNS * 2
        if len(_sessions[session_id]) > max_msgs:
            _sessions[session_id] = _sessions[session_id][-max_msgs:]

    conn = sqlite3.connect(settings.HISTORY_DB_PATH, timeout=30)
    try:
        conn.execute(
            "INSERT INTO chat_history (session_id, role, content, timestamp) VALUES (?,?,?,?)",
            (session_id, "user", user_msg, now),
        )
        conn.execute(
            "INSERT INTO chat_history (session_id, role, content, timestamp) VALUES (?,?,?,?)",
            (session_id, "assistant", assistant_msg, now),
        )
        conn.commit()
    finally:
        conn.close()


def load_session_from_db(session_id: str, limit: int = 10):
    """
    Load a past session from SQLite into in-memory store.
    Call this on session resume.
    """
    conn = sqlite3.connect(settings.HISTORY_DB_PATH, timeout=30)
    try:
        rows = conn.execute(
            "SELECT role, content, timestamp FROM chat_history "
            "WHERE session_id=? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    finally:
        conn.close()

    rows = list(reversed(rows))
    loaded = [{"role": r[0], "content": r[1], "ts": r[2]} for r in rows]
    with _session_lock:
        _sessions[session_id] = loaded


def clear_session(session_id: str):
    """Clear in-memory session (does NOT delete SQLite history)."""
    with _session_lock:
        _sessions.pop(session_id, None)


def get_all_sessions() -> list[str]:
    """Return session IDs ordered by most recent activity."""
    conn = sqlite3.connect(settings.HISTORY_DB_PATH, timeout=30)
    try:
        rows = conn.execute(
            "SELECT session_id FROM chat_history "
            "GROUP BY session_id ORDER BY MAX(timestamp) DESC"
        ).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows]
