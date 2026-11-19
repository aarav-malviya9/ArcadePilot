"""Settings page — AI, browser, gcloud, safety configuration."""
from __future__ import annotations

import os
import streamlit as st
from core.config import Config
from core.database import log_activity as db_log
from cloud.gcloud import detect_gcloud


def render():
    st.title("Settings")

    config = Config.from_env()

    st.subheader("AI Configuration")
    api_base = st.text_input("AI API Base URL", value=config.ai_api_base, key="set_ai_base")
    api_key = st.text_input("AI API Key", value=config.ai_api_key, type="password", key="set_ai_key")
    model = st.text_input("Model", value=config.ai_model, key="set_model")
    timeout = st.number_input("Timeout (seconds)", value=config.ai_timeout_sec, min_value=5, max_value=300, key="set_timeout")

    if st.button("Test Connection"):
        test_config = Config(
            ai_api_base=api_base,
            ai_api_key=api_key,
            ai_model=model,
            ai_timeout_sec=timeout,
        )
        result = test_config.test_connection()
        if result["ok"]:
            st.success(f"Connected to {api_base}")
        else:
            st.error(f"Connection failed: {result['message']}")

    st.markdown("---")
    st.subheader("Browser Settings")
    profile_path = st.text_input(
        "Browser Profile Path",
        value=os.path.expanduser(config.browser_profile_path),
        key="set_profile",
    )
    browser_timeout = st.number_input(
        "Browser Timeout (seconds)",
        value=config.browser_timeout_sec,
        min_value=5,
        max_value=120,
        key="set_browser_timeout",
    )

    st.markdown("---")
    st.subheader("Google Cloud Settings")
    gc_path = st.text_input("gcloud Path", value=config.gcloud_path, key="set_gc_path")
    gc_project = st.text_input("Default Project", value=config.gcloud_default_project, key="set_gc_proj")
    gc_region = st.text_input("Default Region", value=config.gcloud_default_region, key="set_gc_region")
    gc_zone = st.text_input("Default Zone", value=config.gcloud_default_zone, key="set_gc_zone")

    gc_status = detect_gcloud(gc_path)
    if gc_status.installed:
        st.success(f"gcloud found: {gc_status.version}")
    else:
        st.error("gcloud not found on PATH")

    st.markdown("---")
    st.subheader("Safety Settings")
    approve_dest = st.checkbox("Auto-approve destructive commands", value=config.approve_destructive_commands, key="set_approve_dest")
    auto_safe = st.checkbox("Auto-execute safe commands", value=config.auto_execute_safe_commands, key="set_auto_safe")

    st.markdown("---")
    if st.button("Save Settings"):
        # Write .env file
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        with open(env_path, "w") as f:
            f.write(f"AI_API_BASE={api_base}\n")
            f.write(f"AI_API_KEY={api_key}\n")
            f.write(f"AI_MODEL={model}\n")
            f.write(f"AI_TIMEOUT_SEC={timeout}\n")
            f.write(f"BROWSER_PROFILE_PATH={profile_path}\n")
            f.write(f"BROWSER_TIMEOUT_SEC={browser_timeout}\n")
            f.write(f"GCLOUD_PATH={gc_path}\n")
            f.write(f"GCLOUD_DEFAULT_PROJECT={gc_project}\n")
            f.write(f"GCLOUD_DEFAULT_REGION={gc_region}\n")
            f.write(f"GCLOUD_DEFAULT_ZONE={gc_zone}\n")
            f.write(f"APPROVE_DESTRUCTIVE_COMMANDS={'true' if approve_dest else 'false'}\n")
            f.write(f"AUTO_EXECUTE_SAFE_COMMANDS={'true' if auto_safe else 'false'}\n")
        st.success("Settings saved to .env")
        db_log("info", "Settings updated")
