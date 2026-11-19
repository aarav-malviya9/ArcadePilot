"""Shared state keys and helpers across pages."""
from __future__ import annotations


class KEYS:
    LAB_ID = "lab_id"
    LABS = "labs"
    TASKS = "tasks"
    BROWSER_CONNECTED = "browser_connected"
    BROWSER_URL = "browser_url"
    TERMINAL_HISTORY = "terminal_history"
    APPROVE_DESTRUCTIVE = "approve_destructive"


def ensure_lab_selected():
    """If no lab selected, create a placeholder or show message."""
    if "lab_id" not in st.session_state or st.session_state["lab_id"] is None:
        st.warning("No lab selected. Please create or select a lab first.")
        return False
    return True
