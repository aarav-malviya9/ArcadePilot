"""Project management helpers for Cloud integration."""
from __future__ import annotations


def format_projects(projects: list[dict]) -> str:
    """Format project list for display in UI."""
    if not projects:
        return "No projects found"
    lines = []
    for p in projects:
        pid = p.get("projectId", "?")
        name = p.get("name", "?")
        lifecycle = p.get("lifecycleState", "?")
        lines.append(f"- {pid}: {name} [{lifecycle}]")
    return "\n".join(lines)
