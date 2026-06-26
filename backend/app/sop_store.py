"""SQLite repository for SOP drafts (F4).

Synchronous stdlib sqlite3 — a fresh connection per call (cheap, thread-safe,
trivially testable). Append-only versions: each save is a new immutable row;
"current" = latest. Every read/write is scoped by user_id, so one anonymous
user can never touch another's SOPs. DB path comes from config.SOP_DB_PATH.
"""

import json
import sqlite3
from datetime import datetime, timezone

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sops (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    TEXT NOT NULL,
    title      TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sop_versions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sop_id        INTEGER NOT NULL REFERENCES sops(id),
    content       TEXT NOT NULL,
    analysis_json TEXT NOT NULL,
    word_count    INTEGER NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sops_user ON sops(user_id);
CREATE INDEX IF NOT EXISTS idx_versions_sop ON sop_versions(sop_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.SOP_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _owns(conn: sqlite3.Connection, user_id: str, sop_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sops WHERE id = ? AND user_id = ?", (sop_id, user_id)
    ).fetchone()
    return row is not None


def create_sop(user_id: str, title: str) -> dict:
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO sops (user_id, title, created_at) VALUES (?, ?, ?)",
            (user_id, title, _now()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM sops WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def list_sops(user_id: str) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT s.id, s.title, s.created_at,
                   v.id         AS latest_version_id,
                   v.created_at AS updated_at,
                   v.word_count AS word_count
            FROM sops s
            LEFT JOIN sop_versions v
              ON v.id = (SELECT id FROM sop_versions
                         WHERE sop_id = s.id ORDER BY id DESC LIMIT 1)
            WHERE s.user_id = ?
            ORDER BY COALESCE(v.created_at, s.created_at) DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_sop(user_id: str, sop_id: int) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM sops WHERE id = ? AND user_id = ?", (sop_id, user_id)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_version(user_id: str, sop_id: int, content: str, analysis: dict) -> dict | None:
    conn = _connect()
    try:
        if not _owns(conn, user_id, sop_id):
            return None
        cur = conn.execute(
            """INSERT INTO sop_versions (sop_id, content, analysis_json, word_count, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (sop_id, content, json.dumps(analysis), int(analysis.get("word_count", 0)), _now()),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, sop_id, created_at FROM sop_versions WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def list_versions(user_id: str, sop_id: int) -> list[dict]:
    conn = _connect()
    try:
        if not _owns(conn, user_id, sop_id):
            return []
        rows = conn.execute(
            "SELECT id, created_at, word_count FROM sop_versions WHERE sop_id = ? ORDER BY id DESC",
            (sop_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _version_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "content": row["content"],
        "analysis": json.loads(row["analysis_json"]),
        "word_count": row["word_count"],
        "created_at": row["created_at"],
    }


def get_version(user_id: str, sop_id: int, version_id: int) -> dict | None:
    conn = _connect()
    try:
        if not _owns(conn, user_id, sop_id):
            return None
        row = conn.execute(
            "SELECT * FROM sop_versions WHERE id = ? AND sop_id = ?", (version_id, sop_id)
        ).fetchone()
        return _version_row_to_dict(row) if row else None
    finally:
        conn.close()


def get_latest_version(user_id: str, sop_id: int) -> dict | None:
    conn = _connect()
    try:
        if not _owns(conn, user_id, sop_id):
            return None
        row = conn.execute(
            "SELECT * FROM sop_versions WHERE sop_id = ? ORDER BY id DESC LIMIT 1", (sop_id,)
        ).fetchone()
        return _version_row_to_dict(row) if row else None
    finally:
        conn.close()
