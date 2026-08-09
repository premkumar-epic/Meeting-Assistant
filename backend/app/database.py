from __future__ import annotations

import sqlite3
import json
from pathlib import Path

# Path to local SQLite database in the backend directory
DB_PATH = Path(__file__).resolve().parents[1] / "meeting_assistant.db"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the SQLite database and create the meetings table if it doesn't exist."""
    conn = get_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                duration REAL NOT NULL,
                transcript TEXT NOT NULL,
                summary TEXT NOT NULL,
                action_items TEXT NOT NULL, -- JSON serialized list
                entities TEXT NOT NULL,     -- JSON serialized list
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()


def save_meeting(
    filename: str,
    duration: float,
    transcript: str,
    summary: str,
    action_items: list[dict[str, Any]],
    entities: list[dict[str, str]]
) -> int:
    """Save meeting metadata and results to the database. Returns the new row ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO meetings (filename, duration, transcript, summary, action_items, entities)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                duration,
                transcript,
                summary,
                json.dumps(action_items, ensure_ascii=False),
                json.dumps(entities, ensure_ascii=False)
            )
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_all_meetings() -> list[dict[str, Any]]:
    """Retrieve all saved meetings (excluding full transcript/entities to keep list light)."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT id, filename, duration, summary, created_at FROM meetings ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_meeting_by_id(meeting_id: int) -> dict[str, Any] | None:
    """Retrieve full meeting details by ID, deserializing the JSON fields."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
        if row is None:
            return None
        res = dict(row)
        res["action_items"] = json.loads(res["action_items"])
        res["entities"] = json.loads(res["entities"])
        return res
    finally:
        conn.close()


def delete_meeting(meeting_id: int) -> None:
    """Delete a meeting entry by ID."""
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
        conn.commit()
    finally:
        conn.close()
