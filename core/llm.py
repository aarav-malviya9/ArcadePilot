"""OpenAI-compatible LLM client with conversation history per-lab."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from openai import OpenAI

from core.config import Config
from core.gcp_services import GCService
from core.lab_parser import Task
from core.logger import log


SYSTEM_PROMPT = """You are a Google Cloud Skills Boost lab assistant named ArcadePilot.
Your job is to analyze lab instructions and extract structured, actionable tasks.
Never fabricate completions — only report what's actually required.
Never help bypass knowledge checks or quizzes.
When you see gcloud/CLI commands, include them exactly as written.
Respond ONLY in JSON."""


LAB_ANALYSIS_PROMPT = """Analyze these lab instructions and return a JSON object with 'tasks' array.

Each task must have:
- title (short imperative, max 60 chars)
- description (what needs to be done)
- required_op (one of: create, read, delete, verify, general)
- gcp_services (array of GCP services involved: e.g. ["cloud_storage", "compute_engine"])
- prerequisites (any setup steps needed first)
- suggested_cmds (gcloud/gsutil/kubectl/bq/python shell commands as array)
- expected_output (what successful execution looks like)
- verification_procedure (how to confirm completion)
- requires_manual (true if user must interact via browser/UI)

Lab instructions:
---
{text}
---"""


@dataclass
class ConversationHistory:
    lab_id: int
    messages: list[dict[str, str]] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def get_messages(self, last_n: int = 20) -> list[dict]:
        return self.messages[-last_n:]


_conversations: dict[int, ConversationHistory] = {}


def _build_client(config: Config) -> OpenAI:
    return OpenAI(
        base_url=config.ai_api_base,
        api_key=config.ai_api_key,
        timeout=config.ai_timeout_sec,
    )


def analyze_lab(text: str, config: Config) -> list[Task]:
    """Parse lab instructions into structured tasks using the LLM."""
    prompt = LAB_ANALYSIS_PROMPT.format(text=text[:8000])
    client = _build_client(config)

    try:
        resp = client.chat.completions.create(
            model=config.ai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=config.ai_temperature,
            max_tokens=config.ai_max_tokens,
        )
        content = resp.choices[0].message.content or "[]"
        tasks = _parse_llm_response(content)
        log.info(f"Parsed {len(tasks)} tasks from lab")
        return tasks
    except Exception as exc:
        log.error(f"LLM analysis failed: {exc}")
        raise


def chat_with_lab(
    lab_id: int, user_message: str, config: Config, system_context: str = ""
) -> tuple[str, bool]:
    """Chat with the AI about a specific lab. Returns (reply, has_error)."""
    conv = get_conversation(lab_id)
    conv.add("user", user_message)

    messages = [{"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{system_context}"}]
    messages.extend(conv.messages[-15:])  # keep last 15 messages

    client = _build_client(config)
    try:
        resp = client.chat.completions.create(
            model=config.ai_model,
            messages=messages,
            temperature=config.ai_temperature * 0.8,
            max_tokens=1024,
        )
        reply = resp.choices[0].message.content or ""
        conv.add("assistant", reply)
        return reply, False
    except Exception as exc:
        log.error(f"Chat error: {exc}")
        return f"Error: {exc}", True


def _parse_llm_response(content: str) -> list[Task]:
    """Extract tasks from LLM JSON response."""
    try:
        clean = content.strip()
        # Strip markdown code fences
        m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", clean)
        if m:
            clean = m.group(1)
        data = json.loads(clean)
        raw_tasks = data.get("tasks", [])
    except (json.JSONDecodeError, AttributeError, KeyError, TypeError):
        raw_tasks = []

    tasks = []
    for i, raw in enumerate(raw_tasks):
        services_raw = raw.get("gcp_services", [])
        if isinstance(services_raw, str):
            services_raw = [services_raw]
        tasks.append(Task(
            title=raw.get("title", f"Step {i+1}"),
            description=raw.get("description", ""),
            required_op=raw.get("required_op", "general"),
            gcp_services=[s for s in services_raw if isinstance(s, str)],
            prerequisites=raw.get("prerequisites", []),
            suggested_cmds=raw.get("suggested_cmds", []),
            expected_output=raw.get("expected_output", ""),
            verification_procedure=raw.get("verification_procedure", ""),
            requires_manual=bool(raw.get("requires_manual", False)),
        ))
    return tasks or [Task(title="Analyze instructions", description="No structured tasks extracted — review manually")]


def get_conversation(lab_id: int) -> ConversationHistory:
    if lab_id not in _conversations:
        _conversations[lab_id] = ConversationHistory(lab_id=lab_id)
    return _conversations[lab_id]


def clear_conversation(lab_id: int) -> None:
    _conversations.pop(lab_id, None)
