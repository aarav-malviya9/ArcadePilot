"""High-level browser navigation helpers."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class NavigationResult:
    success: bool
    url: str
    title: str
    error: str = ""


def is_skills_boost_url(url: str) -> bool:
    """Check if URL points to Google Cloud Skills Boost / Arcade."""
    patterns = [
        r"\bskills\.google\b",
        r"\bgooglecloudskills\.com\b",
        r"\bgcp\.skills\.boost\b",
        r"arcade\.",
    ]
    for pat in patterns:
        if re.search(pat, url, re.IGNORECASE):
            return True
    return False


def extract_instructions_from_page(page) -> str:
    """Try to pull lab instructions from common page structures."""
    selectors = [
        "[data-testid='instruction']",
        ".instruction-content",
        ".lab-instructions",
        "main article",
        ".content",
        "body",
    ]
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el:
                text = el.text_content()
                if text and len(text) > 50:
                    return text[:8000]
        except Exception:
            continue
    # Fallback: full body text
    try:
        return page.inner_text("body")[:8000]
    except Exception:
        return ""
