"""Browser Panel page — Playwright integration."""
from __future__ import annotations

import os
import streamlit as st
from core.config import Config
from core.logger import log


def render():
    st.title("Browser Assistant")
    config = Config.from_env()

    st.caption(f"Profile: `{config.browser_profile_path}`")

    if "browser_driver" not in st.session_state:
        st.session_state["browser_driver"] = None
    if "browser_connected" not in st.session_state:
        st.session_state["browser_connected"] = False
    if "browser_url" not in st.session_state:
        st.session_state["browser_url"] = ""

    driver = st.session_state["browser_driver"]
    connected = st.session_state["browser_connected"]

    status_color = "#4caf50" if connected else "#f44336"
    status_text = "Connected" if connected else "Disconnected"
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">'
        f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{status_color};"></span>'
        f'<b style="color:#e8e6e3">Browser:</b> <span style="color:{status_color}">{status_text}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col_connect, col_disconnect = st.columns(2)
    with col_connect:
        if st.button("Connect", type="primary", disabled=connected):
            _start_browser(config)
    with col_disconnect:
        if st.button("Disconnect", disabled=not connected):
            driver.stop()
            st.session_state["browser_driver"] = None
            st.session_state["browser_connected"] = False
            st.info("Browser disconnected")

    if not connected:
        st.info("**Connect** to start a persistent Chromium session. Log into your Google account manually after connecting.")
        return

    driver = st.session_state["browser_driver"]

    # URL bar
    st.markdown("---")
    st.subheader("Navigation")
    current = st.session_state.get("browser_url", "")
    col_url, col_go = st.columns([5, 1])
    with col_url:
        url_val = st.text_input("URL", value=current, key="browser_url_input")
    with col_go:
        if st.button("Go", type="primary"):
            with st.spinner("Navigating..."):
                result = driver.navigate(url_val)
            if result["ok"]:
                st.session_state["browser_url"] = result["url"]
                st.success(f"Navigated to {result['url']}")
            else:
                st.error(result["error"])

    st.markdown("---")
    col_ss, col_txt, col_fill = st.columns(3)

    with col_ss:
        st.subheader("Screenshot")
        if st.button("Capture"):
            with st.spinner("Capturing..."):
                result = driver.screenshot()
            if result["ok"]:
                st.image(result["path"], use_container_width=True)
                log.info(f"Screenshot saved to {result['path']}")
            else:
                st.error(result["error"])

    with col_txt:
        st.subheader("Page Content")
        if st.button("Extract Text"):
            with st.spinner("Reading..."):
                result = driver.get_text()
            if result["ok"]:
                st.text_area("Content", value=result["text"][:10000], height=300, key="page_text")
            else:
                st.error(result["error"])

    with col_fill:
        st.subheader("Interact")
        selector = st.text_input("Selector", placeholder="#btn-submit", key="br_sel")
        if st.button("Click"):
            if selector:
                result = driver.click(selector)
                st.success("Clicked!" if result["ok"] else result["error"])
            else:
                st.warning("Enter a selector first")
        fill_s = st.text_input("Fill Selector", placeholder="input[name='email']", key="br_fs")
        fill_v = st.text_input("Fill Value", placeholder="user@example.com", key="br_fv")
        if st.button("Fill Field"):
            if fill_s and fill_v:
                result = driver.fill(fill_s, fill_v)
                st.success("Filled!" if result["ok"] else result["error"])
            else:
                st.warning("Provide both selector and value")


def _start_browser(config: Config):
    from brower.driver import BrowserDriver
    with st.spinner("Starting browser..."):
        driver = BrowserDriver(config.browser_profile_path, config.browser_timeout_sec)
        driver.start()
        driver._started.wait(timeout=15)
        result = driver.start_driver()
        if result["ok"]:
            st.session_state["browser_driver"] = driver
            st.session_state["browser_connected"] = True
            st.success("Browser connected! Please log in to your Google account.")
            log.info("Browser driver started successfully")
        else:
            st.error(f"Failed: {result['error']}")
            log.error(f"Browser start failed: {result['error']}")
