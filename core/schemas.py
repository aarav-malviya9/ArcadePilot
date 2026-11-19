"""Database schema constants and migration utilities."""
from __future__ import annotations

SCHEMA_VERSION = 2

LAB_STATUS_CHOICES = ("not_started", "in_progress", "completed", "failed", "paused")
TASK_STATUS_CHOICES = (
    "pending", "running", "verified", "failed",
    "manual_required", "skipped", "executing",
)

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS schema_info (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS labs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT,
    description TEXT,
    source TEXT DEFAULT 'manual',
    gcp_project TEXT,
    status TEXT DEFAULT 'not_started' CHECK(status IN ('not_started','in_progress','completed','failed','paused')),
    progress_pct INTEGER DEFAULT 0,
    arcadepoints INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lab_id INTEGER NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    required_op TEXT,
    gcp_service TEXT,
    prerequisites TEXT DEFAULT '[]',
    suggested_cmds TEXT DEFAULT '[]',
    expected_output TEXT,
    verification_procedure TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN (
        'pending','running','verified','failed',
        'manual_required','skipped','executing'
    )),
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS command_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lab_id INTEGER REFERENCES labs(id) ON DELETE SET NULL,
    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    command TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    approved INTEGER NOT NULL DEFAULT 0,
    stdout TEXT,
    stderr TEXT,
    exit_code INTEGER,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    duration_sec REAL
);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_lab ON tasks(lab_id);
CREATE INDEX IF NOT EXISTS idx_cmd_history_lab ON command_history(lab_id);
CREATE INDEX IF NOT EXISTS idx_activity_level ON activity_log(level);
"""

# Use INSERT OR REPLACE for schema_info and add columns only once
def _migrate(conn) -> None:
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(labs)").fetchall()}
    if "gcp_project" not in existing_cols:
        conn.execute("ALTER TABLE labs ADD COLUMN gcp_project TEXT")
    if "arcadepoints" not in existing_cols:
        conn.execute("ALTER TABLE labs ADD COLUMN arcadepoints INTEGER DEFAULT 0")

    task_cols = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    if "gcp_service" not in task_cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN gcp_service TEXT")


def get_migration_sql() -> str:
    return ""
