"""Command execution engine with approval gate."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.logger import log
from core.safety import classify, RiskLevel


@dataclass
class ExecutionResult:
    command: str
    risk_level: str
    approved: bool
    exit_code: Optional[int]
    stdout: str
    stderr: str
    started_at: str
    finished_at: str


def execute_command(
    command: str,
    timeout: int = 120,
    approve_destructive: bool = False,
) -> ExecutionResult:
    risk = classify(command)
    should_execute = risk.risk != RiskLevel.DANGEROUS or approve_destructive

    started_at = datetime.utcnow().isoformat(timespec="seconds")
    stdout, stderr, exit_code = "", "", None

    if should_execute:
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout,
            )
            exit_code = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
        except subprocess.TimeoutExpired:
            stdout, stderr, exit_code = "", "Command timed out", -1
        except Exception as exc:
            stdout, stderr, exit_code = "", str(exc), -1
    else:
        stderr = "Command blocked by safety policy"

    finished_at = datetime.utcnow().isoformat(timespec="seconds")
    log.info(f"Executed [{risk.risk.value}] '{command[:80]}': exit={exit_code}")
    return ExecutionResult(
        command=command,
        risk_level=risk.risk.value,
        approved=should_execute,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        started_at=started_at,
        finished_at=finished_at,
    )
