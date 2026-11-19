"""Lab Assistant page — parse instructions and manage tasks."""
from __future__ import annotations

import streamlit as st
from core import database as db
from core.lab_parser import parse_markdown_steps, extract_gcloud_commands
from core.llm import get_conversation, analyze_lab
from core.config import Config
from core.logger import log


def render():
    st.title("Lab Assistant")

    config = Config.from_env()

    # Lab list selector
    labs = db.list_labs()
    lab_options = [(f"{l['name']} (#{l['id']})", l["id"]) for l in labs]
    selected_lab_name, selected_lab_id = None, None

    if lab_options:
        chosen = st.selectbox("Select Lab", [o[0] for o in lab_options])
        selected_lab_id = next(id for name, id in lab_options if name == chosen)
    else:
        selected_lab_id = None

    # Create new lab form
    with st.expander("Create New Lab"):
        new_name = st.text_input("Lab Name")
        new_url = st.text_input("Lab URL (optional)")
        new_desc = st.text_area("Description (optional)")
        if st.button("Create Lab"):
            if new_name:
                lab_id = db.create_lab(new_name, new_url, new_desc)
                db.log_activity("info", f"Created lab '{new_name}' with id {lab_id}")
                st.success(f"Lab created with ID {lab_id}")
                st.rerun()

    if not selected_lab_id:
        st.info("Create or select a lab to get started.")
        return

    st.session_state["lab_id"] = selected_lab_id
    lab = db.get_lab(selected_lab_id)
    st.subheader(f"Lab: {lab['name']}")

    # Parse instructions section
    st.markdown("---")
    st.subheader("Lab Instructions")

    instructions = st.text_area(
        "Paste lab instructions here (markdown or plain text)",
        height=200,
        key="lab_instructions",
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Parse Instructions"):
            if instructions.strip():
                tasks = parse_markdown_steps(instructions)
                gcloud_cmds = extract_gcloud_commands(instructions)
                for task in tasks:
                    db.create_task(
                        selected_lab_id,
                        title=task.title,
                        description=task.description,
                        required_op=task.required_op,
                        prereqs=task.prereqs,
                        suggested_cmds=task.suggested_cmds,
                        expected_output=task.expected_output,
                        verification_procedure=task.verification_procedure,
                    )
                db.update_lab_status(selected_lab_id, "in_progress")
                db.log_activity("info", f"Parsed {len(tasks)} tasks from instructions")
                st.rerun()
            else:
                st.error("Please paste instructions first")

    with col1:
        if st.button("AI Analyze"):
            if instructions.strip() and config.ai_api_key:
                try:
                    tasks = analyze_lab(instructions, config)
                    for task in tasks:
                        db.create_task(
                            selected_lab_id,
                            title=task.title,
                            description=task.description,
                            required_op=task.required_op,
                            prereqs=task.prereqs,
                            suggested_cmds=task.suggested_cmds,
                            expected_output=task.expected_output,
                            verification_procedure=task.verification_procedure,
                        )
                    db.update_lab_status(selected_lab_id, "in_progress")
                    db.log_activity("info", f"AI parsed {len(tasks)} tasks")
                    st.success(f"AI extracted {len(tasks)} tasks")
                    st.rerun()
                except Exception as exc:
                    st.error(f"AI analysis failed: {exc}")
            elif not config.ai_api_key:
                st.error("Set your AI API key in Settings first")
            else:
                st.error("Please paste instructions first")

    # Task list
    st.markdown("---")
    st.subheader("Tasks")
    tasks = db.list_tasks(selected_lab_id)

    if not tasks:
        st.info("No tasks yet. Paste instructions and click Parse or AI Analyze.")
        return

    for task in tasks:
        with st.expander(f"{'✅' if task['status'] == 'verified' else '⬜'} {task['title']}"):
            st.write(task.get("description", ""))
            if task.get("suggested_cmds"):
                st.code("\n".join(task["suggested_cmds"]), language="bash")
            if task.get("expected_output"):
                st.caption(f"Expected: {task['expected_output']}")
            if task.get("verification_procedure"):
                st.caption(f"Verify: {task['verification_procedure']}")

            col_verify, col_skip = st.columns(2)
            with col_verify:
                if st.button("Mark Verified", key=f"verify_{task['id']}"):
                    db.update_task_status(task["id"], "verified")
                    all_done = all(t["status"] == "verified" for t in db.list_tasks(selected_lab_id))
                    if all_done:
                        db.update_lab_status(selected_lab_id, "completed", 100)
                    st.rerun()
            with col_skip:
                if st.button("Skip", key=f"skip_{task['id']}"):
                    db.update_task_status(task["id"], "skipped")
                    st.rerun()

    # Completion percentage
    total = len(tasks)
    done = sum(1 for t in tasks if t["status"] == "verified")
    pct = int((done / total * 100) if total > 0 else 0)
    st.progress(pct / 100)
    st.caption(f"{done}/{total} tasks completed ({pct}%)")
