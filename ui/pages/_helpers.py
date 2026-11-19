"""Shared helpers used across UI pages."""
from __future__ import annotations

import os
import tempfile
from typing import Optional

from core.config import Config
from core.gcp_services import GCService, detect_gcp_service
from core.lab_parser import Task
from core.logger import log


def start_browser(config: Config):
    """Start the Playwright browser driver thread."""
    from brower.driver import BrowserDriver
    driver = BrowserDriver(config.browser_profile_path, config.browser_timeout_sec)
    driver.start()
    driver._started.wait(timeout=15)
    result = driver.start_driver()
    if result["ok"]:
        return driver
    else:
        log.error(f"Browser start failed: {result['error']}")
        return None


def stop_browser(driver) -> None:
    """Gracefully stop the browser driver."""
    if driver:
        try:
            driver.stop()
        except Exception:
            pass


def save_uploaded_file(uploaded_file) -> Optional[str]:
    """Save uploaded file to temp location and return path."""
    if not uploaded_file:
        return None
    ext = os.path.splitext(uploaded_file.name)[1]
    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False, mode='w', encoding='utf-8')
    tmp.write(uploaded_file.getvalue().decode('utf-8', errors='ignore'))
    tmp.close()
    return tmp.name


def extract_instructions_from_file(file_path: str) -> str:
    """Read instructions from a saved file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""
