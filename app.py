"""ArcadePilot — Main entry point."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from core.config import Config
from core.database import init_db, log_activity
from core.logger import log
from ui.layout import inject_theme, render_sidebar


def main():
    # Initialize database
    db_path = os.path.join(PROJECT_ROOT, "storage", "arcadepilot.db")
    init_db(db_path)
    log_activity("info", "ArcadePilot started")

    # Apply theme
    inject_theme()

    # Render sidebar navigation
    page = render_sidebar()

    # Route to appropriate page
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


if __name__ == "__main__":
    main()
