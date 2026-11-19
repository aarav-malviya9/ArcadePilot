"""Deterministic verification helpers — exit codes, DOM checks, output matching."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Iterable


@dataclass
class VerifyResult:
    passed: bool
    message: str
    details: str = ""


def check_exit_code(subprocess_result: subprocess.CompletedProcess, expected: int | None = None) -> VerifyResult:
    if expected is None:
        passed = subprocess_result.returncode == 0
        msg = "Exit code 0" if passed else f"Non-zero exit code: {subprocess_result.returncode}"
    else:
        passed = subprocess_result.returncode == expected
        msg = f"Exit code matches expected {expected}" if passed else f"Expected {expected}, got {subprocess_result.returncode}"
    return VerifyResult(passed, msg, subprocess_result.stdout[:500])


def contains(text: str, substr: str, case_sensitive: bool = False) -> VerifyResult:
    if not case_sensitive:
        text, substr = text.lower(), substr.lower()
    passed = substr in text
    return VerifyResult(passed, f"{'Found' if passed else 'Missing'} substring: {substr[:80]}", text[:500] if not passed else "")


def matches_regex(text: str, pattern: str) -> VerifyResult:
    import re
    try:
        found = bool(re.search(pattern, text))
        return VerifyResult(found, f"Regex {'matched' if found else 'did not match'}: {pattern}")
    except re.error as exc:
        return VerifyResult(False, f"Invalid regex '{pattern}': {exc}")


def run_and_verify(command: str, timeout: int = 30, **kwargs) -> tuple[subprocess.CompletedProcess, VerifyResult]:
    """Run a shell command and return (result, verify_result)."""
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=timeout, **kwargs
    )
    verify = VerifyResult(
        result.returncode == 0,
        f"Exit code: {result.returncode}",
        f"STDOUT:\n{result.stdout[:1000]}\nSTDERR:\n{result.stderr[:1000]}",
    )
    return result, verify
