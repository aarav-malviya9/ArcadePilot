"""Browser Panel page — Playwright integration."""
from __future__ import annotations

import os
import streamlit as st
from core.config import Config
from core.logger import log


def render():
    st.title("Browser Assistant")
    config = Config.from_env()

    profile_path = config.browser_profile_path
    st.caption(f"Profile path: {profile_path}")

    # Driver management
    if "browser_driver" not in st.session_state:
        st.session_state["browser_driver"] = None
    if "browser_connected" not in st.session_state:
        st.session_state["browser_connected"] = False

    driver = st.session_state["browser_driver"]

    col_connect, col_disconnect = st.columns(2)
    with col_connect:
        if st.button("Connect Browser") and not driver:
            from brower.driver import BrowserDriver
            driver = BrowserDriver(profile_path, timeout_sec=config.browser_timeout_sec)
            driver.start()
            driver._started.wait(timeout=10)
            result = driver.start_driver()
            if result["ok"]:
                st.session_state["browser_driver"] = driver
                st.session_state["browser_connected"] = True
                st.success("Browser connected!")
                log.info("Browser driver started")
            else:
                st.error(f"Failed to start browser: {result['error']}")
        elif driver:
            st.info("Browser already connected")

    with col_disconnect:
        if st.button("Disconnect") and driver:
            driver.stop()
            st.session_state["browser_driver"] = None
            st.session_state["browser_connected"] = False
            st.info("Browser disconnected")

    if not st.session_state["browser_connected"]:
        st.info("Connect to a browser to start navigating pages")
        return

    driver = st.session_state["browser_driver"]

    # Navigation
    st.markdown("---")
    st.subheader("Navigation")
    url = st.text_input("Navigate to URL", value="", key="browser_url_input")
    if st.button("Go"):
        if url:
            result = driver.navigate(url)
            if result["ok"]:
                st.success(f"Navigated to {result['url']}")
                st.session_state["browser_url"] = result["url"]
            else:
                st.error(result["error"])

    # Screenshot
    st.subheader("Screenshot")
    if st.button("Take Screenshot"):
        result = driver.screenshot()
        if result["ok"]:
            st.image(result["path"], use_container_width=True)
            st.success("Screenshot saved")
        else:
            st.error(result["error"])

    # Page content
    st.subheader("Page Content")
    if st.button("Extract Text"):
        result = driver.get_text()
        if result["ok"]:
            st.text_area("Page Text", value=result["text"], height=300, key="page_text")
        else:
            st.error(result["error"])

    # Click elements
    st.subheader("Click Element")
    selector = st.text_input("CSS Selector", placeholder="#submit-button")
    if st.button("Click"):
        if selector:
            result = driver.click(selector)
            if result["ok"]:
                st.success("Clicked successfully")
            else:
                st.error(result["error"])
