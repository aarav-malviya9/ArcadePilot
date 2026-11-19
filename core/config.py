"""Application configuration loaded from .env with sensible defaults."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    ai_api_base: str = "http://127.0.0.1:31415/v1"
    ai_api_key: str = ""
    ai_model: str = "auto"
    ai_timeout_sec: int = 60
    ai_max_tokens: int = 2000
    ai_temperature: float = 0.1

    browser_profile_path: str = os.path.join(
        os.environ.get("USERPROFILE", os.path.expanduser("~")),
        ".arcadepilot-browser-profile",
    )
    browser_timeout_sec: int = 30

    gcloud_path: str = "gcloud"
    gcloud_default_project: str = ""
    gcloud_default_region: str = "us-central1"
    gcloud_default_zone: str = "us-central1-a"

    approve_destructive_commands: bool = False
    auto_execute_safe_commands: bool = True

    db_path: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "storage",
        "arcadepilot.db",
    )

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            ai_api_base=os.getenv("AI_API_BASE", cls.ai_api_base),
            ai_api_key=os.getenv("AI_API_KEY", cls.ai_api_key),
            ai_model=os.getenv("AI_MODEL", cls.ai_model),
            ai_timeout_sec=int(os.getenv("AI_TIMEOUT_SEC", cls.ai_timeout_sec)),
            ai_max_tokens=int(os.getenv("AI_MAX_TOKENS", cls.ai_max_tokens)),
            ai_temperature=float(os.getenv("AI_TEMPERATURE", cls.ai_temperature)),
            browser_profile_path=os.getenv("BROWSER_PROFILE_PATH", cls.browser_profile_path),
            browser_timeout_sec=int(os.getenv("BROWSER_TIMEOUT_SEC", cls.browser_timeout_sec)),
            gcloud_path=os.getenv("GCLOUD_PATH", cls.gcloud_path),
            gcloud_default_project=os.getenv("GCLOUD_DEFAULT_PROJECT", cls.gcloud_default_project),
            gcloud_default_region=os.getenv("GCLOUD_DEFAULT_REGION", cls.gcloud_default_region),
            gcloud_default_zone=os.getenv("GCLOUD_DEFAULT_ZONE", cls.gcloud_default_zone),
            approve_destructive_commands=os.getenv("APPROVE_DESTRUCTIVE_COMMANDS", "false").lower() in ("true", "1", "yes"),
            auto_execute_safe_commands=os.getenv("AUTO_EXECUTE_SAFE_COMMANDS", "true").lower() in ("true", "1", "yes"),
        )

    def test_connection(self) -> dict:
        """Probe the AI endpoint and list available models."""
        import requests

        result = {
            "ok": False,
            "message": "",
            "model": self.ai_model,
            "available_models": [],
        }
        try:
            headers = {}
            if self.ai_api_key:
                headers["Authorization"] = f"Bearer {self.ai_api_key}"

            resp = requests.get(
                f"{self.ai_api_base}/models",
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                result["ok"] = True
                result["message"] = f"Connected — {len(models)} models available"
                result["available_models"] = [m.get("id", "?") for m in models]
            else:
                result["message"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:
            result["message"] = str(exc)
        return result
