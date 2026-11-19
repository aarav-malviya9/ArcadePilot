"""Command safety engine — allowlist + risk classification."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

class RiskLevel(str, Enum):
    SAFE = "safe"
    REVIEW = "review"
    DANGEROUS = "dangerous"


@dataclass
class SafetyResult:
    risk: RiskLevel
    message: str
    requires_approval: bool


# Patterns for read-only gcloud commands (case-insensitive matching against the command string)
_READ_ONLY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bgcloud\b.*\b(version|auth\s+list|config\s+list|projects\s+list|compute\s+instances\s+list|compute\s+addresses\s+list|storage\s+buckets\s+list)\b"),
    re.compile(r"\bgcloud\b.*\b(beta\s+auth\s+list|config\s+get)\b"),
    re.compile(r"\b(gcloud|--version|echo|ls|dir|pwd|whoami|date)\b"),
    re.compile(r"\bpython\s+-m\s+pip\s+show\b"),
)

_CREATE_LIKE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bgcloud\b.*\b(create|start|run)\b.*\b(Instance|VM|sql|cluster|bucket|topic|subscription|firewall-rule|rule)\b"),
    re.compile(r"\b(gcloud\s+compute\s+instances\s+(create|start|stop)|gcloud\s+sql\s+instances\s+create)\b"),
    re.compile(r"\b(gcloud\s+projects\s+create)\b"),
)

_DESTROY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bgcloud\b.*\b(delete|destroy|stop|kill)\b"),
    re.compile(r"\brm\s+-rf\b"),
    re.compile(r"\b(gcloud\s+.*\bdelete\b)"),
    re.compile(r"\b(git\s+force\b|git\s+push\s+--force\b)"),
    re.compile(r"\b(chmod\s+777|chmod\s+-R\s+777)\b"),
)


def classify(command: str) -> SafetyResult:
    cmd = command.strip().lower()
    if not cmd:
        return SafetyResult(RiskLevel.SAFE, "Empty command", False)

    for pat in _DESTROY_PATTERNS:
        if pat.search(cmd):
            return SafetyResult(
                RiskLevel.DANGEROUS,
                f"Potentially destructive command detected: {pat.pattern}",
                True,
            )

    for pat in _CREATE_LIKE_PATTERNS:
        if pat.search(cmd):
            return SafetyResult(
                RiskLevel.REVIEW,
                f"Create/start operation detected: {pat.pattern}",
                True,
            )

    for pat in _READ_ONLY_PATTERNS:
        if pat.search(cmd):
            return SafetyResult(RiskLevel.SAFE, "Read-only command", False)

    # Default to review for anything we don't recognize
    return SafetyResult(
        RiskLevel.REVIEW,
        "Unrecognized command — manual review required",
        True,
    )


def is_safe_to_execute(command: str, auto_safe: bool = True) -> SafetyResult:
    result = classify(command)
    if result.risk == RiskLevel.SAFE and auto_safe:
        return SafetyResult(RiskLevel.SAFE, "Auto-executed (safe)", False)
    return result
