"""Overview page — stats cards and recent activity."""
from __future__ import annotations

import streamlit as st
from core import database as db


def render():
    st.title("Overview")

    stats = db.get_stats()
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Labs", stats["total"])
    col2.metric("Completed", stats["completed"])
    col3.metric("In Progress", stats["in_progress"])
    col4.metric("Failed", stats["failed"])
    col5.metric("Not Started", stats["not_started"])

    st.markdown("---")
    st.subheader("Recent Activity")
    activities = db.list_recent_activities(limit=20)
    if not activities:
        st.info("No activity yet. Start by creating a lab!")
        return

    for act in activities[-10:]:
        level = act["level"].upper()
        ts = act["ts"][:19]
        msg = act["message"]
        st.caption(f"[{ts}] {level}: {msg}")

    st.markdown("---")
    st.subheader("Active Labs")
    labs = db.list_labs()
    if not labs:
        st.info("No labs tracked yet.")
        return

    for lab in labs:
        with st.expander(f"{lab['name']} ({lab['status']})"):
            st.write(f"URL: {lab.get('url', 'N/A')}")
            st.write(f"Description: {lab.get('description', 'N/A')}")
            st.write(f"Tasks: {lab.get('done_tasks', 0)}/{lab.get('task_count', 0)} completed")
