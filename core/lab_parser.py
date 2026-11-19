"""Lab instruction parser — deterministic first, LLM fallback."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Task:
    title: str
    description: str = ""
    required_op: str = ""
    prereqs: list[str] = field(default_factory=list)
    suggested_cmds: list[str] = field(default_factory=list)
    expected_output: str = ""
    verification_procedure: str = ""


def parse_markdown_steps(text: str) -> list[Task]:
    """Extract tasks from markdown-style numbered/bulleted steps."""
    tasks: list[Task] = []
    lines = text.splitlines()
    current_task: dict | None = None

    step_pattern = re.compile(r"^(\d+)\.\s+(.+)", re.MULTILINE)
    bullet_pattern = re.compile(r"^[-*]\s+(.+)", re.MULTILINE)

    # Try numbered steps first
    for match in step_pattern.finditer(text):
        num = int(match.group(1))
        content = match.group(2).strip()
        task = _extract_task_from_line(content, num)
        tasks.append(task)

    if tasks:
        return tasks

    # Fall back to bullets or section headers
    header_pattern = re.compile(r"^(#+)\s+(.+)", re.MULTILINE)
    for match in header_pattern.finditer(text):
        level = len(match.group(1))
        title = match.group(2).strip()
        if level <= 3 and title:
            task = Task(title=title, description=f"Complete: {title}")
            tasks.append(task)

    if not tasks:
        # Single paragraph → one task
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for i, para in enumerate(paragraphs, 1):
            if len(para) > 20:
                tasks.append(Task(title=f"Step {i}", description=para[:200]))

    return tasks or [Task(title="Complete the lab", description=text[:500])]


def _extract_task_from_line(line: str, index: int) -> Task:
    task = Task(title=line[:100], description=line)

    # Look for command patterns in the line
    cmd_patterns = [
        re.compile(r"`([^`]+)`"),
        re.compile(r"\$\s*(.+?)$"),
        re.compile(r"Run:\s*(.+)$"),
        re.compile(r"Execute:\s*(.+)$"),
        re.compile(r"Type:\s*(.+)$"),
    ]
    for pat in cmd_patterns:
        m = pat.search(line)
        if m:
            cmd = m.group(1).strip().strip("`").strip()
            if cmd and not any(c in cmd for c in ["# ", "//", "--"]):
                task.suggested_cmds.append(cmd)
                break

    # Detect op type
    lower = line.lower()
    if "create" in lower or "deploy" in lower:
        task.required_op = "create"
    elif "delete" in lower or "remove" in lower:
        task.required_op = "delete"
    elif "list" in lower or "describe" in lower or "get" in lower:
        task.required_op = "read"
    elif "verify" in lower or "check" in lower or "confirm" in lower:
        task.required_op = "verify"
    else:
        task.required_op = "general"

    return task


def extract_gcloud_commands(text: str) -> list[str]:
    """Pull out obvious gcloud/python/shell commands from instructions."""
    cmds: list[str] = []
    seen: set[str] = set()

    # Pattern 1: Lines starting with known CLI prefixes (common format)
    for match in re.finditer(
        r"(?:^|\n)\s*(gcloud|python3?|gsutil|kubectl|curl)\b[^\n]*",
        text,
        re.IGNORECASE,
    ):
        cmd = match.group(0).strip()
        if cmd not in seen:
            seen.add(cmd)
            cmds.append(cmd)

    # Pattern 2: Backtick-quoted commands containing CLI keywords
    for match in re.finditer(r"`([^`]+)`", text):
        inner = match.group(1).strip()
        if any(kw in inner.lower() for kw in ("gcloud", "python", "gsutil", "kubectl", "curl")):
            if inner not in seen:
                seen.add(inner)
                cmds.append(inner)

    return cmds[:50]


def analyze_lab_with_llm(
    text: str, config
) -> tuple[list[Task], float]:
    """LLM-based analysis — returns (tasks, confidence)."""
    from core.llm import analyze_lab
    try:
        tasks = analyze_lab(text, config)
        return tasks, 0.9
    except Exception as exc:
        return [], 0.0
