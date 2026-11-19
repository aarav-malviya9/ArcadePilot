"""ArcadePilot — Main entry point."""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from core.config import Config
from core.database import init_db, log_activity
from core.logger import log
from ui.layout import inject_theme, render_sidebar


def main():
    # Init DB
    init_db(PROJECT_ROOT / "storage" / "arcadepilot.db")
    log_activity("info", "ArcadePilot started")

    # Theme
    inject_theme()

    # Sidebar nav
    page = render_sidebar()

    # Route to page
    pages = {
        "Overview": None,
        "Lab Assistant": "ui/pages/lab_assistant",
        "Browser": "ui/pages/browser_panel",
        "Terminal": "ui/pages/terminal",
        "Progress": "ui/pages/progress",
        "Settings": "ui/pages/settings",
    }

    module_name = pages.get(page)
    if module_name:
        mod = __import__(module_name.replace("/", "."), fromlist=["render"])
        mod.render()
    elif page == "Overview":
        from ui.pages.overview import render as render_overview
        render_overview()


if __name__ == "__main__":
    main()
