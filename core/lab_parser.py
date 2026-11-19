"""Universal lab instruction parser with GCP service detection."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from core.gcp_services import detect_gcp_service, GCService


@dataclass
class Task:
    title: str
    description: str = ""
    required_op: str = ""
    gcp_services: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    suggested_cmds: list[str] = field(default_factory=list)
    expected_output: str = ""
    verification_procedure: str = ""
    requires_manual: bool = False


def parse_markdown_steps(text: str) -> list[Task]:
    """Extract tasks from markdown-style numbered/bulleted steps."""
    tasks: list[Task] = []
    step_pattern = re.compile(r"^(\d+)\.\s+(.+)", re.MULTILINE)
    header_pattern = re.compile(r"^(#{1,3})\s+(.+)", re.MULTILINE)

    for match in step_pattern.finditer(text):
        content = match.group(2).strip()
        task = _extract_task(content)
        tasks.append(task)

    if not tasks:
        for match in header_pattern.finditer(text):
            level = len(match.group(1))
            title = match.group(2).strip()
            if level <= 3 and title:
                tasks.append(_extract_task(title))

    if not tasks:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for i, para in enumerate(paragraphs, 1):
            if len(para) > 20:
                tasks.append(Task(title=f"Step {i}", description=para[:200]))

    return tasks or [Task(title="Complete the lab", description=text[:500])]


def _extract_task(line: str) -> Task:
    task = Task(title=line[:100], description=line)

    # Detect commands
    cmd_patterns = [
        re.compile(r"`([^`]+)`"),
        re.compile(r"\$\s*(.+?)$"),
        re.compile(r"(?:^|\n)\s*(gcloud|python3?|gsutil|kubectl|curl|bq)\b[^\n]*"),
    ]
    for pat in cmd_patterns:
        for m in pat.finditer(line):
            cmd = m.group(1).strip().strip("`").strip()
            if cmd and not cmd.startswith("#") and cmd not in task.suggested_cmds:
                task.suggested_cmds.append(cmd)

    # Detect operations
    lower = line.lower()
    if "create" in lower or "deploy" in lower or "build" in lower:
        task.required_op = "create"
    elif "delete" in lower or "remove" in lower or "destroy" in lower:
        task.required_op = "delete"
    elif "list" in lower or "describe" in lower or "get" in lower or "show" in lower:
        task.required_op = "read"
    elif "verify" in lower or "check" in lower or "confirm" in lower:
        task.required_op = "verify"
    else:
        task.required_op = "general"

    # Detect manual-required signals
    manual_signals = ["click", "open browser", "login", "enter your", "select from dropdown"]
    if any(sig in lower for sig in manual_signals):
        task.requires_manual = True

    # Detect GCP services
    services = detect_gcp_service(line)
    task.gcp_services = [s.value for s in services]

    return task


def extract_all_commands(text: str) -> list[str]:
    """Pull all visible CLI commands from instructions."""
    cmds: list[str] = []
    seen: set[str] = set()

    # Match lines that start with a CLI prefix (possibly after whitespace)
    for match in re.finditer(
        r"(?:^|\n)\s*(gcloud|python3?|gsutil|kubectl|curl|bq)\b[^\n]*",
        text,
        re.IGNORECASE | re.MULTILINE,
    ):
        cmd = match.group(0).strip()
        if cmd not in seen:
            seen.add(cmd)
            cmds.append(cmd)

    # Also catch inline commands: ... gcloud something ...
    for match in re.finditer(
        r"\b(gcloud|python3?|gsutil|kubectl|curl|bq)\b[ \S]*",
        text,
        re.IGNORECASE,
    ):
        cmd = match.group(0).strip()
        if len(cmd) > 5 and cmd not in seen:
            seen.add(cmd)
            cmds.append(cmd)

    # Backtick-quoted commands containing CLI keywords
    for match in re.finditer(r"`([^`]+)`", text):
        inner = match.group(1).strip()
        if any(kw in inner.lower() for kw in ("gcloud", "python", "gsutil", "kubectl", "curl", "bq")):
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
