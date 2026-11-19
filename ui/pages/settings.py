"""Settings page — AI, browser, gcloud, safety configuration."""
from __future__ import annotations

import os
import streamlit as st
from core.config import Config
from cloud.gcloud import detect_gcloud


def render():
    st.title("Settings")
    config = Config.from_env()
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".env")

    st.subheader("🤖 AI / LLM Settings")
    api_base = st.text_input("API Base URL", value=config.ai_api_base, key="set_ai_base")
    api_key = st.text_input("API Key", value=config.ai_api_key, type="password", key="set_ai_key")
    model = st.text_input("Model Name", value=config.ai_model, key="set_model")
    timeout = st.number_input("Timeout (seconds)", value=config.ai_timeout_sec, min_value=5, max_value=300, key="set_timeout")
    max_tokens = st.number_input("Max Tokens", value=config.ai_max_tokens, min_value=256, max_value=8192, key="set_max_tokens")
    temp = st.slider("Temperature", 0.0, 1.0, config.ai_temperature, 0.05, key="set_temp")

    col_test, col_info = st.columns([1, 4])
    with col_test:
        if st.button("Test Connection", type="primary"):
            test_cfg = Config(
                ai_api_base=api_base,
                ai_api_key=api_key,
                ai_model=model,
                ai_timeout_sec=timeout,
                ai_max_tokens=max_tokens,
                ai_temperature=temp,
            )
            result = test_cfg.test_connection()
            if result["ok"]:
                st.success(f"✅ {result['message']}")
                models = result.get("available_models", [])
                if models:
                    st.caption(f"Available: {', '.join(models[:10])}")
            else:
                st.error(f"❌ {result['message']}")

    st.markdown("---")
    st.subheader("🌐 Browser Settings")
    profile_path = st.text_input(
        "Profile Path",
        value=os.path.expanduser(config.browser_profile_path),
        key="set_profile",
    )
    browser_timeout = st.number_input(
        "Browser Timeout (s)",
        value=config.browser_timeout_sec,
        min_value=5,
        max_value=120,
        key="set_browser_timeout",
    )

    st.markdown("---")
    st.subheader("☁️ Google Cloud Settings")
    gc_path = st.text_input("gcloud Path", value=config.gcloud_path, key="set_gc_path")
    gc_project = st.text_input("Default Project ID", value=config.gcloud_default_project, key="set_gc_proj")
    gc_region = st.text_input("Default Region", value=config.gcloud_default_region, key="set_gc_region")
    gc_zone = st.text_input("Default Zone", value=config.gcloud_default_zone, key="set_gc_zone")

    gc_status = detect_gcloud(gc_path)
    if gc_status.installed:
        st.success(f"gcloud found: {gc_status.version}")
    else:
        st.warning("gcloud not on PATH — commands will be preview-only in the Terminal tab.")

    st.markdown("---")
    st.subheader("🔒 Safety Settings")
    approve_dest = st.checkbox(
        "Allow destructive commands (delete/update)",
        value=config.approve_destructive_commands,
        key="set_approve_dest",
    )
    auto_safe = st.checkbox(
        "Auto-execute safe (read-only) commands",
        value=config.auto_execute_safe_commands,
        key="set_auto_safe",
    )

    st.markdown("---")
    if st.button("💾 Save Settings", type="primary"):
        lines = [
            f"AI_API_BASE={api_base}",
            f"AI_API_KEY={api_key}",
            f"AI_MODEL={model}",
            f"AI_TIMEOUT_SEC={timeout}",
            f"AI_MAX_TOKENS={max_tokens}",
            f"AI_TEMPERATURE={temp}",
            f"BROWSER_PROFILE_PATH={profile_path}",
            f"BROWSER_TIMEOUT_SEC={browser_timeout}",
            f"GCLOUD_PATH={gc_path}",
            f"GCLOUD_DEFAULT_PROJECT={gc_project}",
            f"GCLOUD_DEFAULT_REGION={gc_region}",
            f"GCLOUD_DEFAULT_ZONE={gc_zone}",
            f"APPROVE_DESTRUCTIVE_COMMANDS={'true' if approve_dest else 'false'}",
            f"AUTO_EXECUTE_SAFE_COMMANDS={'true' if auto_safe else 'false'}",
        ]
        resolved_path = os.path.normpath(env_path)
        with open(resolved_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        st.success(f"Settings saved to {resolved_path}")
        st.rerun()
