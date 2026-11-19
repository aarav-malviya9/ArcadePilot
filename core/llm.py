"""OpenAI-compatible LLM client with conversation history per-lab."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from openai import OpenAI

from core.logger import log
from core.lab_parser import Task


# Structured prompt for lab analysis
LAB_ANALYSIS_PROMPT = """You are a Google Cloud learning assistant. Analyze the following lab instructions and extract structured tasks.

For each task, provide:
- title: short imperative title (max 60 chars)
- description: what needs to be done
- required_op: one of create/read/delete/verify/general
- prereqs: any prerequisites mentioned
- suggested_cmds: shell/gcloud commands needed (if any)
- expected_output: what success looks like
- verification_procedure: how to confirm completion

Return ONLY valid JSON in this exact format:
{{"tasks": [{{"title":"...","description":"...","required_op":"...","prereqs":[],"suggested_cmds":[],"expected_output":"...","verification_procedure":"..."}}]}}

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


# In-memory store keyed by lab_id
_conversations: dict[int, ConversationHistory] = {}


def set_config(api_base: str, api_key: str, model: str, timeout: int) -> OpenAI:
    return OpenAI(base_url=api_base, api_key=api_key, timeout=timeout)


def analyze_lab(text: str, config, client: OpenAI | None = None) -> list[Task]:
    """Parse lab instructions into structured tasks using the LLM."""
    prompt = LAB_ANALYSIS_PROMPT.format(text=text[:4000])
    if client is None:
        client = set_config(config.ai_api_base, config.ai_api_key, config.ai_model, config.ai_timeout_sec)

    resp = client.chat.completions.create(
        model=config.ai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2000,
    )
    content = resp.choices[0].message.content or "[]"
    tasks = _parse_llm_response(content)
    log.info(f"Parsed {len(tasks)} tasks from lab instructions")
    return tasks


def _parse_llm_response(content: str) -> list[Task]:
    """Extract tasks from LLM JSON response."""
    try:
        # Handle markdown code blocks
        clean = content.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(clean)
        raw_tasks = data.get("tasks", [])
    except (json.JSONDecodeError, AttributeError, KeyError):
        raw_tasks = []

    tasks = []
    for i, raw in enumerate(raw_tasks):
        tasks.append(Task(
            title=raw.get("title", f"Task {i+1}"),
            description=raw.get("description", ""),
            required_op=raw.get("required_op", "general"),
            prereqs=raw.get("prereqs", []),
            suggested_cmds=raw.get("suggested_cmds", []),
            expected_output=raw.get("expected_output", ""),
            verification_procedure=raw.get("verification_procedure", ""),
        ))
    return tasks or [Task(title="Analyze instructions", description="No structured tasks extracted — review manually")]


def get_conversation(lab_id: int) -> ConversationHistory:
    if lab_id not in _conversations:
        _conversations[lab_id] = ConversationHistory(lab_id=lab_id)
    return _conversations[lab_id]


def clear_conversation(lab_id: int) -> None:
    _conversations.pop(lab_id, None)
