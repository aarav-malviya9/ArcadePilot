"""Terminal page — command execution with safety gate."""
from __future__ import annotations

import streamlit as st
from core.config import Config
from core.logger import log
from cloud.executor import execute_command
from cloud.gcloud import detect_gcloud


def render():
    st.title("Cloud Terminal")
    config = Config.from_env()

    # gcloud status
    gc_status = detect_gcloud(config.gcloud_path)
    if gc_status.installed:
        st.success(f"gcloud installed: {gc_status.version}")
    else:
        st.warning(
            "gcloud CLI not detected. "
            "Install from https://cloud.google.com/sdk/docs/install"
        )

    st.markdown("---")
    st.subheader("Command Execution")

    command = st.text_input(
        "Enter command",
        placeholder="gcloud projects list",
        key="terminal_cmd",
    )

    risk_label, risk_color = "—", "#888"
    if command.strip():
        from core.safety import classify
        result = classify(command)
        risk_label = result.risk.value.upper()
        risk_color = {"safe": "#4caf50", "review": "#ff9800", "dangerous": "#f44336"}.get(
            result.risk.value, "#888"
        )
        st.caption(f"Risk level: <span style='color:{risk_color}'>{risk_label}</span>", unsafe_allow_html=True)

    col_exec, col_preview = st.columns([1, 3])
    with col_exec:
        approve_btn = st.button("Execute", type="primary", disabled=not command.strip())

    with col_preview:
        if command.strip():
            st.code(command, language="bash")

    if approve_btn and command.strip():
        from core.safety import classify
        safety = classify(command)
        if safety.requires_approval and not config.approve_destructive_commands:
            with st.expander(f"⚠️ Approve: {safety.risk.value.upper()} command"):
                st.write(safety.message)
                st.code(command, language="bash")
                confirm = st.checkbox("I understand and want to proceed")
                if confirm:
                    exec_result = execute_command(
                        command,
                        timeout=config.ai_timeout_sec * 2,
                        approve_destructive=False,
                    )
                    _display_execution(exec_result)
                    st.rerun()
                else:
                    st.info("Execution cancelled by user")
        else:
            exec_result = execute_command(
                command,
                timeout=config.ai_timeout_sec * 2,
                approve_destructive=config.approve_destructive_commands,
            )
            _display_execution(exec_result)
            st.rerun()

    # History
    st.markdown("---")
    st.subheader("Command History")
    history = [
        {"command": h["command"], "risk": h["risk_level"], "exit": h["exit_code"], "ts": h["started_at"]}
        for h in reversed(__import__("core.database", fromlist=["list_command_history"]).list_command_history())
    ][:20]
    for entry in history:
        with st.expander(f"{entry['ts'][:19]} | exit={entry['exit']} | [{entry['risk']}]"):
            st.code(entry["command"], language="bash")


def _display_execution(result) -> None:
    """Show execution results in UI."""
    if result.approved:
        st.success(f"Executed (exit code: {result.exit_code})")
    else:
        st.error("Command blocked by safety policy")
    if result.stdout:
        with st.expander("STDOUT"):
            st.code(result.stdout, language="text")
    if result.stderr:
        with st.expander("STDERR"):
            st.code(result.stderr, language="text")
