"""Generate execution plans from parsed lab tasks."""
from __future__ import annotations

from core.lab_parser import Task


def generate_plan(tasks: list[Task]) -> list[dict]:
    plan = []
    for i, task in enumerate(tasks, 1):
        entry = {
            "step": i,
            "title": task.title,
            "commands": task.suggested_cmds or [f"# Review and execute manually"],
            "verification": task.verification_procedure or f"Check that {task.title.lower()} succeeds",
            "status": "pending",
        }
        plan.append(entry)
    return plan


def estimate_duration(tasks: list[Task]) -> str:
    """Return rough time estimate based on task count."""
    n = len(tasks)
    if n == 0:
        return "~0 min"
    mins = n * 5
    if mins < 60:
        return f"~{mins} min"
    hrs = mins // 60
    rem = mins % 60
    return f"~{hrs}h {rem}m" if rem else f"~{hrs}h"
