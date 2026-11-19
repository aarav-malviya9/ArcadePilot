"""Terminal page — real command execution with safety gate."""
from __future__ import annotations

import time
from datetime import datetime

import streamlit as st
from core import database as db
from core.config import Config
from core.safety import classify, RiskLevel
from cloud.executor import execute_command


def render():
    st.title("Cloud Terminal")
    config = Config.from_env()

    # gcloud status
    col_g, col_c = st.columns([2, 1])
    with col_g:
        st.subheader("GCP Status")
        gc_info = get_gcloud_status(config.gcloud_path)
        for k, v in gc_info.items():
            st.caption(f"{k}: {v}")
    with col_c:
        st.markdown("---")
        if st.button("Refresh Status", use_container_width=True):
            st.rerun()

    st.markdown("---")
    st.subheader("Execute Command")

    command = st.text_input(
        "Command",
        placeholder="gcloud projects list",
        key="term_cmd",
        help="Type a gcloud or shell command to execute.",
    )

    # Live risk preview
    if command.strip():
        safety = classify(command)
        color_map = {"safe": "#4caf50", "review": "#ff9800", "dangerous": "#f44336"}
        c = color_map.get(safety.risk.value, "#888")
        st.markdown(
            f"<div style='padding:8px;background:#1a1a1a;border-radius:6px;border-left:4px solid {c};'>"
            f"<b>Risk:</b> <span style='color:{c}'>{safety.risk.value.upper()}</span>"
            f"&nbsp;&nbsp;<b>Note:</b> {safety.message}"
            f"</div>",
            unsafe_allow_html=True,
        )

    exec_col, preview_col = st.columns([1, 3])
    with exec_col:
        can_exec = bool(command.strip()) and (safety.risk != RiskLevel.DANGEROUS or config.approve_destructive_commands)
        if st.button("Execute", type="primary", disabled=not can_exec):
            _execute_and_show(command, config)

    with preview_col:
        if command.strip():
            st.code(command, language="bash")

    # History
    st.markdown("---")
    st.subheader("Recent Commands")
    history = db.list_command_history(limit=30)
    if not history:
        st.info("No commands executed yet.")
        return
    for entry in reversed(history[-10:]):
        ok_icon = "✅" if entry["exit_code"] == 0 else "❌" if entry["exit_code"] is not None else "⏳"
        with st.expander(f"{ok_icon} `{entry['command'][:60]}` — exit {entry['exit_code']} [{entry['risk_level']}]"):
            st.caption(f"Time: {entry['started_at'][11:19]}")
            if entry.get("stdout"):
                st.code(entry["stdout"][:2000], language="text")
            if entry.get("stderr"):
                st.code(entry["stderr"][:2000], language="text")


def _execute_and_show(command: str, config: Config) -> None:
    safety = classify(command)

    # Require approval for non-safe commands unless auto-approved
    if safety.requires_approval and not config.auto_execute_safe_commands and safety.risk != RiskLevel.SAFE:
        with st.expander(f"⚠️ Approve: {safety.risk.value.upper()} command", expanded=True):
            st.warning(safety.message)
            st.code(command, language="bash")
            if st.checkbox("I approve this command"):
                _run_cmd(command, config)
            else:
                st.info("Execution cancelled")
    elif safety.risk == RiskLevel.DANGEROUS and not config.approve_destructive_commands:
        st.error("Destructive commands are blocked. Enable in Settings to allow.")
        return
    else:
        _run_cmd(command, config)


def _run_cmd(command: str, config: Config) -> None:
    with st.status("Executing...", expanded=True) as status:
        t0 = time.time()
        result = execute_command(
            command,
            timeout=config.ai_timeout_sec * 2,
            approve_destructive=config.approve_destructive_commands,
        )
        duration = round(time.time() - t0, 1)

        if result.approved:
            status.update(label=f"Done ({duration}s)", state="complete")
            if result.exit_code == 0:
                st.success(f"Completed in {duration}s — exit code 0")
            else:
                st.error(f"Exit code {result.exit_code} after {duration}s")
        else:
            st.error(result.stderr or "Command was blocked by safety policy")
            status.update(label="Blocked", state="error")

        if result.stdout:
            with st.expander("STDOUT"):
                st.code(result.stdout[:5000], language="text")
        if result.stderr:
            with st.expander("STDERR"):
                st.code(result.stderr[:2000], language="text")


def get_gcloud_status(path: str) -> dict:
    """Return quick gcloud status info."""
    import shutil, subprocess
    info = {}
    if shutil.which(path):
        try:
            r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
            info["Version"] = r.stdout.splitlines()[0].strip() if r.returncode == 0 else "?"
            r2 = subprocess.run([path, "auth", "list", "--format=value(account)"], capture_output=True, text=True, timeout=10)
            accounts = r2.stdout.strip().split("\n") if r2.returncode == 0 else []
            info["Accounts"] = f"{len(accounts)}"
        except Exception:
            info["Status"] = "unknown"
    else:
        info["Installed"] = "No — install from cloud.google.com/sdk"
    return info
