"""Overview page — stats cards and recent activity."""
from __future__ import annotations

import streamlit as st
from core import database as db


def render():
    st.title("Overview")

    stats = db.get_stats()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Labs", stats["total"])
    c2.metric("Completed", stats["completed"])
    c3.metric("In Progress", stats["in_progress"])
    c4.metric("Failed", stats["failed"])
    c5.metric("Arcade Points", stats["total_arcadepoints"])

    st.markdown("---")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.subheader("Recent Activity")
        activities = db.list_recent_activities(limit=15)
        if not activities:
            st.info("No activity yet.")
        for act in activities:
            ts = act["ts"][11:19] if act.get("ts") else ""
            st.markdown(f"**[{ts}]** {act['message']}")

    with col_b:
        st.subheader("Quick Actions")
        if st.button("➕ Create New Lab", use_container_width=True):
            st.session_state["_show_create_lab"] = True
            st.rerun()

    if st.session_state.pop("_show_create_lab", False):
        _create_lab_form()

    # Recent labs
    st.markdown("---")
    st.subheader("Your Labs")
    labs = db.list_labs()
    if not labs:
        st.info("No labs tracked yet. Click **Create New Lab** to get started!")
        return

    for lab in labs:
        done = lab.get("done_tasks", 0) or 0
        total = lab.get("task_count", 0) or 0
        pct = int(done / total * 100) if total > 0 else 0
        status_emoji = {"not_started": "📋", "in_progress": "🔄", "completed": "✅", "failed": "❌", "paused": "⏸️"}
        emoji = status_emoji.get(lab["status"], "📋")

        with st.expander(f"{emoji} **{lab['name']}** — {lab['status'].title()}"):
            st.write(f"**ID:** #{lab['id']}")
            if lab.get("url"):
                st.markdown(f"**URL:** `{lab['url']}`")
            if lab.get("gcp_project"):
                st.caption(f"GCP Project: {lab['gcp_project']}")
            if lab.get("description"):
                st.caption(lab["description"][:120])
            st.progress(pct / 100)
            st.caption(f"{done}/{total} tasks · {pct}% complete")
            st.caption(f"Updated: {lab['updated_at'][11:19] if lab.get('updated_at') else 'N/A'}")


def _create_lab_form():
    with st.form("new_lab"):
        name = st.text_input("Lab Name *")
        url = st.text_input("Lab URL (optional)")
        desc = st.text_area("Description (optional)", height=60)
        gcp_proj = st.text_input("GCP Project ID (optional)")
        submitted = st.form_submit_button("Create Lab", type="primary")
        if submitted and name.strip():
            lab_id = db.create_lab(name.strip(), url.strip(), desc.strip())
            db.log_activity("success", f"Created lab '{name.strip()}' (ID {lab_id})")
            st.success(f"Lab created! ID: {lab_id}")
            st.rerun()
