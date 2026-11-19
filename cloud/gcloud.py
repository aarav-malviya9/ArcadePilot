"""Google Cloud CLI integration — read-only discovery and guided install."""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class GcloudStatus:
    installed: bool
    version: str = ""
    auth_active: bool = False
    active_account: str = ""
    default_project: str = ""
    region: str = ""
    zone: str = ""
    error: str = ""


def detect_gcloud(path: str = "gcloud") -> GcloudStatus:
    status = GcloudStatus(installed=False)
    if not shutil.which(path):
        # Check common Windows locations
        candidates = [
            r"C:\Program Files\Google\Cloud SDK\cloud_sdk_command_prompt.ps1",
            r"C:\Program Files (x86)\Google\Cloud SDK\cloud_sdk_command_prompt.ps1",
        ]
        for c in candidates:
            if Path(c).exists():
                return GcloudStatus(
                    installed=True,
                    error=f"gcloud binary not on PATH but SDK found at {c}. Run from Cloud SDK Command Prompt.",
                )
        return status
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            status.installed = True
            status.version = result.stdout.splitlines()[0].strip()
    except Exception as exc:
        status.error = f"gcloud --version failed: {exc}"
    return status


def get_auth_status(gcloud_path: str = "gcloud") -> dict:
    """Return list of authenticated accounts."""
    try:
        result = subprocess.run(
            [gcloud_path, "auth", "list", "--format=json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as exc:
        return {"error": str(exc)}
    return {}


def get_config(gcloud_path: str = "gcloud") -> dict:
    try:
        result = subprocess.run(
            [gcloud_path, "config", "list", "--format=json"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as exc:
        return {"error": str(exc)}
    return {}


def list_projects(gcloud_path: str = "gcloud") -> dict:
    try:
        result = subprocess.run(
            [gcloud_path, "projects", "list", "--format=json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as exc:
        return {"error": str(exc)}
    return {}


def select_project(project_id: str, gcloud_path: str = "gcloud") -> dict:
    try:
        result = subprocess.run(
            [gcloud_path, "config", "set", "project", project_id],
            capture_output=True, text=True, timeout=15,
        )
        return {"ok": result.returncode == 0, "output": result.stdout, "error": result.stderr}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
