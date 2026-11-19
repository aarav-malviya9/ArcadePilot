"""Lab Assistant page — parse instructions, manage tasks, AI chat."""
from __future__ import annotations

import os
import tempfile
import time

import streamlit as st
from core import database as db
from core.config import Config
from core.gcp_services import detect_gcp_service
from core.lab_parser import extract_all_commands, parse_markdown_steps
from core.llm import analyze_lab, chat_with_lab, clear_conversation
from core.logger import log


def render():
    st.title("Lab Assistant")
    config = Config.from_env()

    # Init session state
    if "current_lab_id" not in st.session_state:
        st.session_state["current_lab_id"] = None
    if "ai_replying" not in st.session_state:
        st.session_state["ai_replying"] = False

    # Lab selector
    labs = db.list_labs()
    lab_options = {f"{l['name']} (#{l['id']})": l["id"] for l in labs}

    if lab_options:
        chosen = st.selectbox("Select Lab", list(lab_options.keys()))
        st.session_state["current_lab_id"] = lab_options[chosen]
    else:
        st.session_state["current_lab_id"] = None

    # Create lab form
    with st.expander("➕ Create New Lab"):
        with st.form("create_lab_form"):
            name = st.text_input("Lab Name *")
            url = st.text_input("Lab URL (optional)")
            desc = st.text_area("Description (optional)", height=60)
            gcp_proj = st.text_input("GCP Project ID (optional)")
            submitted = st.form_submit_button("Create Lab", type="primary")
            if submitted and name.strip():
                lab_id = db.create_lab(name.strip(), url.strip(), desc.strip())
                if gcp_proj.strip():
                    db.update_lab_status(lab_id, "not_started", gcp_project=gcp_proj.strip())
                db.log_activity("success", f"Created lab '{name.strip()}' (ID {lab_id})")
                st.success(f"Lab created! ID: {lab_id}")
                st.rerun()

    lab_id = st.session_state["current_lab_id"]
    if not lab_id:
        st.info("Create or select a lab to get started.")
        return

    lab = db.get_lab(lab_id)
    if not lab:
        st.error("Lab not found.")
        return

    st.subheader(f"🧪 {lab['name']}")
    if lab.get("url"):
        st.caption(f"URL: `{lab['url']}`")
    if lab.get("gcp_project"):
        st.caption(f"GCP Project: **{lab['gcp_project']}**")

    # Instructions input
    st.markdown("---")
    st.subheader("📝 Lab Instructions")

    col_file, col_text = st.columns(2)
    with col_file:
        uploaded = st.file_uploader("Upload .txt/.md file", type=["txt", "md"])
    with col_text:
        instructions = st.text_area(
            "Or paste instructions here",
            height=200,
            key="lab_instructions",
            placeholder="Paste lab instructions from Google Cloud Skills Boost...",
        )

    text_content = ""
    if uploaded:
        text_content = uploaded.getvalue().decode("utf-8", errors="ignore")
    elif instructions.strip():
        text_content = instructions

    col_parse, col_ai = st.columns(2)

    with col_parse:
        if st.button("Parse Instructions", type="primary"):
            if text_content.strip():
                tasks = parse_markdown_steps(text_content)
                _add_tasks_to_lab(lab_id, tasks)
                db.update_lab_status(lab_id, "in_progress")
                st.rerun()
            else:
                st.error("Please provide instructions first.")

    with col_ai:
        if st.button("AI Analyze"):
            if text_content.strip() and config.ai_api_key:
                try:
                    with st.spinner("Analyzing with AI..."):
                        tasks = analyze_lab(text_content, config)
                    _add_tasks_to_lab(lab_id, tasks)
                    db.update_lab_status(lab_id, "in_progress")
                    db.log_activity("success", f"AI parsed {len(tasks)} tasks for '{lab['name']}'")
                    st.success(f"AI extracted {len(tasks)} tasks!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"AI analysis failed: {exc}")
            elif not config.ai_api_key:
                st.error("Set your AI API key in Settings first.")
            else:
                st.error("Please provide instructions first.")

    # Task list
    st.markdown("---")
    st.subheader("📋 Tasks")
    tasks = db.list_tasks(lab_id)

    # Summary stats
    if tasks:
        done = sum(1 for t in tasks if t["status"] == "verified")
        pending = sum(1 for t in tasks if t["status"] == "pending")
        manual = sum(1 for t in tasks if t.get("requires_manual"))
        cols_s = st.columns(4)
        cols_s[0].metric("Total", len(tasks))
        cols_s[1].metric("Done", done)
        cols_s[2].metric("Pending", pending)
        cols_s[3].metric("Needs Manual", manual)

    if not tasks:
        st.info("No tasks yet. Paste instructions above and click Parse or AI Analyze.")
        return

    # Filter tabs
    tab_all, tab_pending, tab_verified, tab_manual = st.tabs(["All", f"Pending ({pending})", f"Verified ({done})", f"Manual ({manual})"])

    with tab_all:
        _render_task_list(lab_id, tasks)
    with tab_pending:
        _render_task_list(lab_id, [t for t in tasks if t["status"] != "verified"])
    with tab_verified:
        _render_task_list(lab_id, [t for t in tasks if t["status"] == "verified"])
    with tab_manual:
        manual_tasks = [t for t in tasks if t.get("requires_manual")]
        _render_task_list(lab_id, manual_tasks if manual_tasks else tasks)

    # Completion percentage
    total = len(tasks)
    done_count = sum(1 for t in tasks if t["status"] == "verified")
    pct = int((done_count / total * 100) if total > 0 else 0)
    st.progress(pct / 100)
    st.caption(f"**{done_count}/{total} tasks completed ({pct}%)**")

    # AI Chat panel
    st.markdown("---")
    st.subheader("💬 AI Assistant")
    _render_ai_chat(lab_id, config)


def _add_tasks_to_lab(lab_id: int, tasks) -> None:
    """Save parsed tasks to database."""
    for task in tasks:
        db.create_task(
            lab_id=lab_id,
            title=task.title,
            description=task.description,
            required_op=task.required_op,
            gcp_service=", ".join(task.gcp_services) if task.gcp_services else "",
            prereqs=task.prereqs,
            suggested_cmds=task.suggested_cmds,
            expected_output=task.expected_output,
            verification_procedure=task.verification_procedure,
        )


def _render_task_list(lab_id: int, tasks: list) -> None:
    """Render a list of tasks with actions."""
    if not tasks:
        st.info("No tasks in this view.")
        return

    for task in tasks:
        checkmark = "✅" if task["status"] == "verified" else ("⏳" if task["status"] == "running" else "⬜")
        service_badge = ""
        if task.get("gcp_service"):
            services = task["gcp_service"].split(", ")
            badge = ", ".join(s[:2] for s in services)
            service_badge = f'<span style="background:#2a2a2a;padding:2px 8px;border-radius:4px;font-size:11px;">{badge}</span>'

        with st.expander(f"{checkmark} **{task['title']}** {service_badge}", expanded=False):
            if task.get("description"):
                st.markdown(task["description"][:300])
            if task.get("prerequisites"):
                st.caption(f"Prerequisites: {', '.join(task['prerequisites'])}")
            if task.get("suggested_cmds"):
                st.code("\n".join(task["suggested_cmds"]), language="bash")
            if task.get("expected_output"):
                st.caption(f"Expected: {task['expected_output']}")
            if task.get("verification_procedure"):
                st.caption(f"Verify: {task['verification_procedure']}")
            if task.get("requires_manual"):
                st.warning("⚠️ This task requires manual interaction")

            col_verify, col_run, col_skip = st.columns(3)
            with col_verify:
                if st.button("✓ Verified", key=f"verify_{task['id']}", use_container_width=True):
                    db.update_task_status(task["id"], "verified")
                    all_done = all(
                        t["status"] == "verified"
                        for t in db.list_tasks(lab_id)
                    )
                    if all_done:
                        db.update_lab_status(lab_id, "completed", progress_pct=100)
                        db.log_activity("success", f"Lab '{db.get_lab(lab_id)['name']}' marked complete!")
                    st.rerun()
            with col_run:
                if st.button("▶ Run Cmds", key=f"run_{task['id']}", use_container_width=True):
                    for cmd in task.get("suggested_cmds", [])[:3]:
                        db.append_command_history(
                            lab_id=lab_id,
                            task_id=task["id"],
                            command=cmd,
                            risk_level="review",
                            approved=False,
                        )
                    st.success("Commands added to history — go to Terminal tab to execute")
            with col_skip:
                if st.button("Skip", key=f"skip_{task['id']}", use_container_width=True):
                    db.update_task_status(task["id"], "skipped")
                    st.rerun()


def _render_ai_chat(lab_id: int, config: Config) -> None:
    """Render AI chat interface for current lab."""
    from core.llm import get_conversation

    conv = get_conversation(lab_id)

    # Display chat history
    chat_container = st.container(height=300)
    with chat_container:
        for msg in conv.messages[-10:]:
            if msg["role"] == "user":
                st.markdown(f'**You:** {msg["content"][:500]}')
            else:
                st.markdown(f'**ArcadePilot:** {msg["content"][:500]}')

    col_msg, col_clear = st.columns([5, 1])
    with col_msg:
        user_msg = st.text_input("Ask about this lab:", key="chat_input", label_visibility="collapsed")
    with col_clear:
        if st.button("Clear", type="secondary"):
            clear_conversation(lab_id)
            st.rerun()

    if user_msg.strip() and not st.session_state.get("ai_replying"):
        st.session_state["ai_replying"] = True
        with st.spinner("Thinking..."):
            reply, has_error = chat_with_lab(lab_id, user_msg, config)
        if has_error:
            st.error(reply)
        else:
            st.success(reply)
        st.session_state["ai_replying"] = False
        st.rerun()
