"""SQLite store for the loan application draft (F6).

One row per user (one application). Synchronous stdlib sqlite3, fresh connection
per call. Every read/write is scoped by user_id. DB path from
config.APPLICATION_DB_PATH.
"""

import json
import sqlite3
from datetime import datetime, timezone

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    user_id        TEXT PRIMARY KEY,
    fields_json    TEXT NOT NULL,
    ai_filled_json TEXT NOT NULL,
    documents_json TEXT NOT NULL,
    status         TEXT NOT NULL,
    reference      TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.APPLICATION_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "fields": json.loads(row["fields_json"]),
        "ai_filled": json.loads(row["ai_filled_json"]),
        "documents": json.loads(row["documents_json"]),
        "status": row["status"],
        "reference": row["reference"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get(user_id: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM applications WHERE user_id = ?", (user_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def get_or_create(user_id: str, builder) -> dict:
    existing = get(user_id)
    if existing is not None:
        return existing
    draft = builder()
    now = _now()
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO applications
               (user_id, fields_json, ai_filled_json, documents_json, status,
                reference, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                json.dumps(draft["fields"]),
                json.dumps(draft["ai_filled"]),
                json.dumps(draft["documents"]),
                draft["status"],
                draft["reference"],
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get(user_id)


def save(user_id: str, fields: dict, documents: dict) -> dict | None:
    conn = _connect()
    try:
        cur = conn.execute(
            """UPDATE applications
               SET fields_json = ?, documents_json = ?, updated_at = ?
               WHERE user_id = ?""",
            (json.dumps(fields), json.dumps(documents), _now(), user_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    finally:
        conn.close()
    return get(user_id)


def delete(user_id: str) -> bool:
    """Remove this user's application row. Returns True if a row was deleted.

    Used by "start a new application": after delete, get_or_create rebuilds a
    fresh draft from the user's current memory facts.
    """
    conn = _connect()
    try:
        cur = conn.execute("DELETE FROM applications WHERE user_id = ?", (user_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def submit(user_id: str, reference: str) -> dict | None:
    conn = _connect()
    try:
        cur = conn.execute(
            "UPDATE applications SET status = 'submitted', reference = ?, updated_at = ? WHERE user_id = ?",
            (reference, _now(), user_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    finally:
        conn.close()
    return get(user_id)
