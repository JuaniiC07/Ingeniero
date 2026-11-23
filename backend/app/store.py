from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app import config

DDL = """
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    car_id TEXT,
    car_name TEXT,
    track_id TEXT,
    track_name TEXT,
    setup_name TEXT,
    setup_path TEXT,
    setup_text TEXT,
    new_setup_text TEXT,
    context_json TEXT,
    feedback_json TEXT,
    diagnosis_json TEXT,
    changes_json TEXT,
    test_plan_json TEXT,
    explanation TEXT,
    warnings_json TEXT,
    status TEXT NOT NULL DEFAULT 'proposed',
    saved_path TEXT,
    result_json TEXT,
    session_id INTEGER,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at DESC);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    name TEXT,
    car_id TEXT,
    car_name TEXT,
    track_id TEXT,
    track_name TEXT,
    base_setup_path TEXT,
    current_setup_path TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    notes TEXT,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at DESC);
"""


def _connect() -> sqlite3.Connection:
    config.ensure_dirs()
    connection = sqlite3.connect(config.DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_db() -> None:
    with _connect() as connection:
        connection.executescript(DDL)
        # Migration for databases created before session_id existed.
        columns = {row[1] for row in connection.execute("PRAGMA table_info(analyses)").fetchall()}
        if "session_id" not in columns:
            connection.execute("ALTER TABLE analyses ADD COLUMN session_id INTEGER")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_analyses_session ON analyses(session_id)")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_analysis(payload: dict[str, Any]) -> int:
    ensure_db()
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO analyses (
                created_at, car_id, car_name, track_id, track_name, setup_name, setup_path,
                setup_text, new_setup_text, context_json, feedback_json, diagnosis_json,
                changes_json, test_plan_json, explanation, warnings_json, status, session_id, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now(),
                payload.get("car_id"),
                payload.get("car_name"),
                payload.get("track_id"),
                payload.get("track_name"),
                payload.get("setup_name"),
                payload.get("setup_path"),
                payload.get("setup_text"),
                payload.get("new_setup_text"),
                json.dumps(payload.get("context"), ensure_ascii=False),
                json.dumps(payload.get("feedback"), ensure_ascii=False),
                json.dumps(payload.get("diagnosis"), ensure_ascii=False),
                json.dumps(payload.get("changes"), ensure_ascii=False),
                json.dumps(payload.get("test_plan"), ensure_ascii=False),
                payload.get("explanation"),
                json.dumps(payload.get("warnings"), ensure_ascii=False),
                "proposed",
                payload.get("session_id"),
                _now(),
            ),
        )
        return int(cursor.lastrowid)


def _row_to_analysis(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    for key in (
        "context_json",
        "feedback_json",
        "diagnosis_json",
        "changes_json",
        "test_plan_json",
        "warnings_json",
        "result_json",
    ):
        if key in item and item[key]:
            try:
                item[key.replace("_json", "")] = json.loads(item[key])
            except Exception:
                item[key.replace("_json", "")] = None
        item.pop(key, None)
    return item


def get_analysis(analysis_id: int) -> dict[str, Any] | None:
    ensure_db()
    with _connect() as connection:
        row = connection.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    return _row_to_analysis(row) if row else None


def list_analyses(limit: int = 50) -> list[dict[str, Any]]:
    ensure_db()
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for row in rows:
        item = _row_to_analysis(row)
        out.append(
            {
                "id": item["id"],
                "created_at": item["created_at"],
                "car_id": item["car_id"],
                "car_name": item["car_name"],
                "track_id": item["track_id"],
                "track_name": item["track_name"],
                "setup_name": item["setup_name"],
                "status": item["status"],
                "saved_path": item["saved_path"],
                "session_id": item.get("session_id"),
                "summary": (item.get("diagnosis") or {}).get("summary"),
                "changes": [
                    change.get("summary") for change in (item.get("changes") or [])
                ],
                "result": item.get("result"),
            }
        )
    return out


def mark_saved(analysis_id: int, path: str) -> None:
    ensure_db()
    with _connect() as connection:
        connection.execute(
            "UPDATE analyses SET status = 'saved', saved_path = ?, updated_at = ? WHERE id = ?",
            (path, _now(), analysis_id),
        )


def add_result(analysis_id: int, result: dict[str, Any]) -> None:
    ensure_db()
    with _connect() as connection:
        connection.execute(
            "UPDATE analyses SET result_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(result, ensure_ascii=False), _now(), analysis_id),
        )


def set_explanation(analysis_id: int, explanation: str) -> None:
    ensure_db()
    with _connect() as connection:
        connection.execute(
            "UPDATE analyses SET explanation = ?, updated_at = ? WHERE id = ?",
            (explanation, _now(), analysis_id),
        )


def _row_to_session(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def create_session(payload: dict[str, Any]) -> int:
    ensure_db()
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO sessions (created_at, name, car_id, car_name, track_id, track_name,
                                  base_setup_path, current_setup_path, status, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now(),
                payload.get("name"),
                payload.get("car_id"),
                payload.get("car_name"),
                payload.get("track_id"),
                payload.get("track_name"),
                payload.get("base_setup_path"),
                payload.get("base_setup_path"),
                "active",
                payload.get("notes"),
                _now(),
            ),
        )
        return int(cursor.lastrowid)


def get_session(session_id: int) -> dict[str, Any] | None:
    ensure_db()
    with _connect() as connection:
        row = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return None
        session = _row_to_session(row)
        analyses = connection.execute(
            "SELECT * FROM analyses WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        session["analyses"] = [_row_to_analysis(r) for r in analyses]
        return session


def list_sessions(limit: int = 50) -> list[dict[str, Any]]:
    ensure_db()
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        out = []
        for row in rows:
            item = _row_to_session(row)
            count = connection.execute(
                "SELECT COUNT(*) FROM analyses WHERE session_id = ?", (item["id"],)
            ).fetchone()[0]
            item["analysis_count"] = count
            out.append(item)
        return out


def update_session(session_id: int, payload: dict[str, Any]) -> None:
    ensure_db()
    fields = []
    values = []
    for key in ("name", "current_setup_path", "base_setup_path", "status", "notes"):
        if key in payload and payload[key] is not None:
            fields.append(f"{key} = ?")
            values.append(payload[key])
    if not fields:
        return
    fields.append("updated_at = ?")
    values.append(_now())
    values.append(session_id)
    with _connect() as connection:
        connection.execute(
            f"UPDATE sessions SET {', '.join(fields)} WHERE id = ?", values
        )


def link_analysis_to_session(analysis_id: int, session_id: int) -> None:
    ensure_db()
    with _connect() as connection:
        connection.execute(
            "UPDATE analyses SET session_id = ?, updated_at = ? WHERE id = ?",
            (session_id, _now(), analysis_id),
        )
        row = connection.execute(
            "SELECT saved_path, new_setup_text FROM analyses WHERE id = ?", (analysis_id,)
        ).fetchone()
        if row and row["saved_path"]:
            connection.execute(
                "UPDATE sessions SET current_setup_path = ?, updated_at = ? WHERE id = ?",
                (row["saved_path"], _now(), session_id),
            )
