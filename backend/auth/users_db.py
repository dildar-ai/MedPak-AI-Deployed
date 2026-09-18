"""
MedPak AI — User storage
SQLite-backed user accounts in backend/database/users.db.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import settings

_USERS_DB = Path(settings.USERS_DB_PATH)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    username      TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
"""


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_USERS_DB))
    conn.row_factory = sqlite3.Row
    return conn


def init_users_db() -> None:
    """Create the users table if it doesn't exist. Safe to call repeatedly."""
    with _get_conn() as conn:
        conn.execute(_SCHEMA)


# ── User CRUD ─────────────────────────────────────────────────────────────────

def create_user(email: str, username: str, password_hash: str) -> dict:
    """
    Insert a new user. Raises sqlite3.IntegrityError if the email exists.
    Returns the created user dict (without password hash).
    """
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO users (email, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (email.strip(), username.strip(), password_hash, now),
        )
        user_id = cursor.lastrowid
    return {"id": user_id, "email": email.strip(), "username": username.strip(), "created_at": now}


def get_user_by_email(email: str) -> dict | None:
    """Fetch a user by email (case-insensitive), including password hash."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE",
            (email.strip(),),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    """Fetch a user by id (no password hash exposure needed by callers)."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, email, username, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None
