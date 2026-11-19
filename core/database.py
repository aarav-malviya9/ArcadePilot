"""SQLite persistence layer — sync sqlite3."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Optional

from core.logger import log
from core.schemas import CREATE_TABLES_SQL, SCHEMA_VERSION


def _migrate(conn) -> None:
    """Add missing columns safely."""
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(labs)").fetchall()}
    if "gcp_project" not in existing_cols:
        conn.execute("ALTER TABLE labs ADD COLUMN gcp_project TEXT")
    if "arcadepoints" not in existing_cols:
        conn.execute("ALTER TABLE labs ADD COLUMN arcadepoints INTEGER DEFAULT 0")

    task_cols = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    if "gcp_service" not in task_cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN gcp_service TEXT")


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
        conn.executescript(CREATE_TABLES_SQL)

        existing = {
            row["key"]: row["value"]
            for row in conn.execute("SELECT key, value FROM schema_info").fetchall()
        }
        from_version = int(existing.get("version", 0))

        # Safe migration: add missing columns only
        _migrate(conn)

        conn.execute(
            "INSERT OR REPLACE INTO schema_info (key, value) VALUES (?, ?)",
            ("version", str(SCHEMA_VERSION)),
        )
        conn.commit()
    # Update global DB_PATH so all functions use the correct database
    globals()["DB_PATH"] = db_path
    log.info(f"Database initialized at {db_path} (v{SCHEMA_VERSION})")


# -- Lab CRUD --


def create_lab(name: str, url: str = "", description: str = "", source: str = "manual") -> int:
    now = _now_iso()
    with _connect(DB_PATH) as conn:
        cur = conn.execute(
            """INSERT INTO labs (name, url, description, source, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'not_started', ?, ?)""",
            (name, url or None, description or None, source, now, now),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_labs() -> list[dict[str, Any]]:
    with _connect(DB_PATH) as conn:
        rows = conn.execute(
            """SELECT l.*, COUNT(t.id) AS task_count,
                      SUM(CASE WHEN t.status = 'verified' THEN 1 ELSE 0 END) AS done_tasks
               FROM labs l LEFT JOIN tasks t ON t.lab_id = l.id
               GROUP BY l.id ORDER BY l.updated_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


def get_lab(lab_id: int) -> Optional[dict[str, Any]]:
    with _connect(DB_PATH) as conn:
        row = conn.execute("SELECT * FROM labs WHERE id = ?", (lab_id,)).fetchone()
        return dict(row) if row else None


def update_lab_status(lab_id: int, status: str, progress_pct: int | None = None, arcadepoints: int | None = None) -> None:
    now = _now_iso()
    set_cols = ["status = ?", "updated_at = ?"]
    params = [status, now]
    if progress_pct is not None:
        set_cols.append("progress_pct = ?")
        params.append(progress_pct)
    if arcadepoints is not None:
        set_cols.append("arcadepoints = ?")
        params.append(arcadepoints)
    params.append(lab_id)
    with _connect(DB_PATH) as conn:
        conn.execute(f"UPDATE labs SET {', '.join(set_cols)} WHERE id = ?", params)
        conn.commit()


def delete_lab(lab_id: int) -> bool:
    with _connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM labs WHERE id = ?", (lab_id,))
        conn.commit()
        return cur.rowcount > 0


# -- Task CRUD --


def create_task(
    lab_id: int,
    title: str,
    description: str = "",
    required_op: str = "",
    gcp_service: str = "",
    prereqs: list[str] | None = None,
    suggested_cmds: list[str] | None = None,
    expected_output: str = "",
    verification_procedure: str = "",
) -> int:
    now = _now_iso()
    with _connect(DB_PATH) as conn:
        cur = conn.execute(
            """INSERT INTO tasks (lab_id, title, description, required_op, gcp_service,
                                  prereqs, suggested_cmds, expected_output,
                                  verification_procedure, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (
                lab_id, title, description or None, required_op or None,
                gcp_service or None,
                json.dumps(prereqs or []),
                json.dumps(suggested_cmds or []),
                expected_output or None,
                verification_procedure or None,
                now, now,
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
        conn.execute(f"UPDATE tasks SET {set_clauses} WHERE id = ?", [*vals.values(), task_id])
        conn.commit()


# -- Command history --


def append_command_history(
    lab_id: int | None,
    task_id: int | None,
    command: str,
    risk_level: str,
    approved: bool,
    stdout: str = "",
    stderr: str = "",
    exit_code: int | None = None,
    duration_sec: float | None = None,
) -> int:
    now = _now_iso()
    with _connect(DB_PATH) as conn:
        cur = conn.execute(
            """INSERT INTO command_history
               (lab_id, task_id, command, risk_level, approved, stdout, stderr, exit_code, started_at, finished_at, duration_sec)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                lab_id, task_id, command, risk_level,
                int(approved), stdout or None, stderr or None,
                exit_code, now, now, duration_sec,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_command_history(lab_id: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
    with _connect(DB_PATH) as conn:
        if lab_id:
            rows = conn.execute(
                "SELECT * FROM command_history WHERE lab_id = ? ORDER BY id DESC LIMIT ?",
                (lab_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM command_history ORDER BY id DESC LIMIT ?", (limit,)
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
        completed = conn.execute("SELECT COUNT(*) FROM labs WHERE status = 'completed'").fetchone()[0]
        in_progress = conn.execute("SELECT COUNT(*) FROM labs WHERE status = 'in_progress'").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM labs WHERE status = 'failed'").fetchone()[0]
        paused = conn.execute("SELECT COUNT(*) FROM labs WHERE status = 'paused'").fetchone()[0]
        total_arcadepoints = conn.execute("SELECT COALESCE(SUM(arcadepoints), 0) FROM labs WHERE status = 'completed'").fetchone()[0]
        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "failed": failed,
            "paused": paused,
            "total_arcadepoints": total_arcadepoints,
        }


# Module-level singleton path (set by app at startup)
DB_PATH = "storage/arcadepilot.db"
