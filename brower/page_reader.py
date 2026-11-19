"""Page content extraction helpers."""
from __future__ import annotations


def extract_visible_text(page) -> str:
    """Extract readable text from the current page body."""
    try:
        return page.inner_text("body")
    except Exception:
        return ""


def extract_headings(page) -> list[str]:
    """Return list of heading texts (h1-h3)."""
    headings = []
    for tag in ["h1", "h2", "h3"]:
        try:
            els = page.query_selector_all(tag)
            for el in els:
                t = el.text_content()
                if t:
                    headings.append(t.strip())
        except Exception:
            pass
    return headings


def extract_links(page) -> list[dict]:
    """Return list of {text, href} dicts for anchor elements."""
    links = []
    try:
        anchors = page.query_selector_all("a[href]")
        for a in anchors:
            text = a.text_content().strip()
            href = a.get_attribute("href") or ""
            if text:
                links.append({"text": text, "href": href})
    except Exception:
        pass
    return links[:100]
