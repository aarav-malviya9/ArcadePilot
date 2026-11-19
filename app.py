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
    db_path = str(PROJECT_ROOT / "storage" / "arcadepilot.db")
    init_db(db_path)
    log_activity("info", "ArcadePilot started")

    # Theme
    inject_theme()

    # Sidebar nav
    page = render_sidebar()

    # Route to page with error handling
    try:
        if page == "Overview":
            from ui.pages.overview import render as render_overview
            render_overview()
        elif page == "Lab Assistant":
            from ui.pages.lab_assistant import render as render_lab
            render_lab()
        elif page == "Browser":
            from ui.pages.browser_panel import render as render_browser
            render_browser()
        elif page == "Terminal":
            from ui.pages.terminal import render as render_terminal
            render_terminal()
        elif page == "Progress":
            from ui.pages.progress import render as render_progress
            render_progress()
        elif page == "Settings":
            from ui.pages.settings import render as render_settings
            render_settings()
    except Exception as exc:
        st.error(f"Error loading {page}: {exc}")
        import traceback
        st.code(traceback.format_exc())
        log.error(f"Page render failed for {page}: {exc}")


if __name__ == "__main__":
    main()
