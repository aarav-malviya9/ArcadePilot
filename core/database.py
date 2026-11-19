"""SQLite persistence layer — sync sqlite3, no aiosqlite."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Iterable, Optional

_SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


@contextmanager
def _connect(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    with _connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_info (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS labs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT,
                description TEXT,
                source TEXT DEFAULT 'manual',
                status TEXT DEFAULT 'not_started' CHECK(status IN ('not_started','in_progress','completed','failed')),
                progress_pct INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lab_id INTEGER NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT,
                required_op TEXT,
                prereqs TEXT DEFAULT '[]',
                suggested_cmds TEXT DEFAULT '[]',
                expected_output TEXT,
                verification_procedure TEXT,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending','running','verified','failed','manual_required','skipped')),
                completed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lab_id INTEGER REFERENCES labs(id) ON DELETE SET NULL,
                task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
                command TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                approved INTEGER NOT NULL DEFAULT 0,
                output TEXT,
                stderr TEXT,
                exit_code INTEGER,
                started_at TEXT NOT NULL,
                finished_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_lab ON tasks(lab_id)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cmd_history_lab ON command_history(lab_id)
            """
        )
        # Apply migrations if needed
        existing = {
            row["key"]: row["value"]
            for row in conn.execute("SELECT key, value FROM schema_info").fetchall()
        }
        if existing.get("version") != str(_SCHEMA_VERSION):
            _apply_migrations(conn, int(existing.get("version", 0)))
        conn.execute(
            "INSERT OR REPLACE INTO schema_info (key, value) VALUES (?, ?)",
            ("version", str(_SCHEMA_VERSION)),
        )
        conn.commit()


def _apply_migrations(conn: sqlite3.Connection, from_version: int) -> None:
    if from_version < 1:
        pass  # base schema already covers v1


# -- Lab CRUD --


def create_lab(name: str, url: str = "", description: str = "") -> int:
    now = _now_iso()
    with _connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO labs (name, url, description, status, created_at, updated_at)
            VALUES (?, ?, ?, 'not_started', ?, ?)
            """,
            (name, url or None, description or None, now, now),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_labs() -> list[dict[str, Any]]:
    with _connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT l.*, COUNT(t.id) AS task_count,
                   SUM(CASE WHEN t.status = 'verified' THEN 1 ELSE 0 END) AS done_tasks
            FROM labs l
            LEFT JOIN tasks t ON t.lab_id = l.id
            GROUP BY l.id
            ORDER BY l.updated_at DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def get_lab(lab_id: int) -> Optional[dict[str, Any]]:
    with _connect(DB_PATH) as conn:
        row = conn.execute("SELECT * FROM labs WHERE id = ?", (lab_id,)).fetchone()
        return dict(row) if row else None


def update_lab_status(lab_id: int, status: str, progress_pct: int | None = None) -> None:
    now = _now_iso()
    extra = f", progress_pct = COALESCE(?, progress_pct)" if progress_pct is not None else ""
    with _connect(DB_PATH) as conn:
        conn.execute(
            f"UPDATE labs SET status = ?, updated_at = ?{extra} WHERE id = ?",
            (status, now, progress_pct, lab_id),
        )
        conn.commit()


def delete_lab(lab_id: int) -> None:
    with _connect(DB_PATH) as conn:
        conn.execute("DELETE FROM labs WHERE id = ?", (lab_id,))
        conn.commit()


# -- Task CRUD --


def create_task(
    lab_id: int,
    title: str,
    description: str = "",
    required_op: str = "",
    prereqs: list[str] | None = None,
    suggested_cmds: list[str] | None = None,
    expected_output: str = "",
    verification_procedure: str = "",
) -> int:
    now = _now_iso()
    with _connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO tasks (lab_id, title, description, required_op,
                               prereqs, suggested_cmds, expected_output,
                               verification_procedure, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                lab_id,
                title,
                description or None,
                required_op or None,
                json.dumps(prereqs or []),
                json.dumps(suggested_cmds or []),
                expected_output or None,
                verification_procedure or None,
                now,
                now,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_tasks(lab_id: int) -> list[dict[str, Any]]:
    with _connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE lab_id = ? ORDER BY id ASC", (lab_id,)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            for key in ("prereqs", "suggested_cmds"):
                if d.get(key):
                    try:
                        d[key] = json.loads(d[key])
                    except (TypeError, ValueError):
                        pass
            out.append(d)
        return out


def get_task(task_id: int) -> Optional[dict[str, Any]]:
    with _connect(DB_PATH) as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        for key in ("prereqs", "suggested_cmds"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (TypeError, ValueError):
                    pass
        return d


def update_task_status(task_id: int, status: str) -> None:
    now = _now_iso()
    vals = {"status": status, "updated_at": now}
    if status == "verified":
        vals["completed_at"] = now
    with _connect(DB_PATH) as conn:
        set_clauses = ", ".join(f"{k} = ?" for k in vals)
        conn.execute(
            f"UPDATE tasks SET {set_clauses} WHERE id = ?",
            [*vals.values(), task_id],
        )
        conn.commit()


# -- Command history --


def append_command_history(
    lab_id: int | None,
    task_id: int | None,
    command: str,
    risk_level: str,
    approved: bool,
    output: str = "",
    stderr: str = "",
    exit_code: int | None = None,
) -> int:
    now = _now_iso()
    with _connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO command_history
              (lab_id, task_id, command, risk_level, approved, output, stderr, exit_code, started_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lab_id,
                task_id,
                command,
                risk_level,
                int(approved),
                output or None,
                stderr or None,
                exit_code,
                now,
                now,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_command_history(lab_id: int | None = None) -> list[dict[str, Any]]:
    with _connect(DB_PATH) as conn:
        if lab_id:
            rows = conn.execute(
                "SELECT * FROM command_history WHERE lab_id = ? ORDER BY id DESC LIMIT 200",
                (lab_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM command_history ORDER BY id DESC LIMIT 500"
            ).fetchall()
        return [dict(r) for r in rows]


# -- Activity log --


def log_activity(level: str, message: str) -> None:
    with _connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO activity_log (ts, level, message) VALUES (?, ?, ?)",
            (_now_iso(), level, message),
        )
        conn.commit()


def list_recent_activities(limit: int = 50) -> list[dict[str, Any]]:
    with _connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# -- Stats --


def get_stats() -> dict[str, Any]:
    with _connect(DB_PATH) as conn:
        total = conn.execute("SELECT COUNT(*) FROM labs").fetchone()[0]
        completed = conn.execute(
            "SELECT COUNT(*) FROM labs WHERE status = 'completed'"
        ).fetchone()[0]
        in_progress = conn.execute(
            "SELECT COUNT(*) FROM labs WHERE status = 'in_progress'"
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM labs WHERE status = 'failed'"
        ).fetchone()[0]
        not_started = conn.execute(
            "SELECT COUNT(*) FROM labs WHERE status = 'not_started'"
        ).fetchone()[0]
        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "failed": failed,
            "not_started": not_started,
        }


# Module-level singleton path (set by app at startup)
DB_PATH = "storage/arcadepilot.db"
