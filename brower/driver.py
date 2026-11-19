"""Threaded Playwright driver — daemon thread manages one Chromium persistent context."""
from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page


class _Request:
    def __init__(self, cmd, args=(), kwargs=None):
        self.cmd = cmd
        self.args = args
        self.kwargs = kwargs or {}
        self.resp_queue = queue.Queue()


class BrowserDriver(threading.Thread):
    """Daemon thread owning a single Playwright instance responding to queued commands."""

    def __init__(self, profile_path: str, timeout_sec: int = 30):
        super().__init__(daemon=True)
        self._profile_path = Path(profile_path).expanduser().resolve()
        self._timeout_sec = timeout_sec
        self._pw = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._q: queue.Queue = queue.Queue()
        self._started = threading.Event()
        self._stopped = threading.Event()

    def start_driver(self) -> dict:
        req = _Request("start")
        self._q.put(req)
        try:
            return req.resp_queue.get(timeout=self._timeout_sec + 5)
        except queue.Empty:
            return {"ok": False, "error": "timeout waiting for driver"}

    def navigate(self, url: str) -> dict:
        req = _Request("navigate", args=(url,))
        self._q.put(req)
        try:
            return req.resp_queue.get(timeout=self._timeout_sec + 5)
        except queue.Empty:
            return {"ok": False, "error": "timeout navigating"}

    def get_text(self) -> dict:
        req = _Request("get_text")
        self._q.put(req)
        try:
            return req.resp_queue.get(timeout=self._timeout_sec + 5)
        except queue.Empty:
            return {"ok": False, "error": "timeout", "text": ""}

    def screenshot(self, path: Optional[str] = None) -> dict:
        req = _Request("screenshot", args=(path,))
        self._q.put(req)
        try:
            return req.resp_queue.get(timeout=self._timeout_sec + 5)
        except queue.Empty:
            return {"ok": False, "error": "timeout taking screenshot"}

    def click(self, selector: str) -> dict:
        req = _Request("click", args=(selector,))
        self._q.put(req)
        try:
            return req.resp_queue.get(timeout=self._timeout_sec + 5)
        except queue.Empty:
            return {"ok": False, "error": "timeout clicking"}

    def stop(self) -> None:
        req = _Request("stop")
        self._q.put(req)
        self._stopped.wait(timeout=self._timeout_sec + 5)

    def run(self) -> None:
        self._started.set()
        while True:
            req = self._q.get()
            if req.cmd == "stop":
                self._cleanup()
                self._stopped.set()
                break
            elif req.cmd == "start":
                ok, err = self._do_start()
                req.resp_queue.put({"ok": ok, "error": err})
            elif req.cmd == "navigate":
                ok, err, url = self._do_navigate(req.args[0])
                req.resp_queue.put({"ok": ok, "error": err, "url": url})
            elif req.cmd == "get_text":
                ok, err, text = self._do_get_text()
                req.resp_queue.put({"ok": ok, "error": err, "text": text})
            elif req.cmd == "screenshot":
                ok, err, path = self._do_screenshot(req.args[0] if req.args else None)
                req.resp_queue.put({"ok": ok, "error": err, "path": path})
            elif req.cmd == "click":
                ok, err = self._do_click(req.args[0])
                req.resp_queue.put({"ok": ok, "error": err})

    def _do_start(self) -> tuple[bool, str]:
        try:
            self._pw = sync_playwright().start()
            self._context = self._pw.chromium.launch_persistent_context(
                str(self._profile_path),
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
            pages = self._context.pages
            self._page = pages[0] if pages else self._context.new_page()
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def _do_navigate(self, url: str) -> tuple[bool, str, str]:
        try:
            self._page.goto(url, wait_until="domcontentloaded", timeout=self._timeout_sec * 1000)
            return True, "", self._page.url
        except Exception as exc:
            return False, str(exc), self._page.url if self._page else ""

    def _do_get_text(self) -> tuple[bool, str, str]:
        try:
            return True, "", self._page.inner_text("body")
        except Exception as exc:
            return False, str(exc), ""

    def _do_screenshot(self, path: Optional[str]) -> tuple[bool, str, str]:
        try:
            if not path:
                import tempfile
                path = tempfile.mktemp(suffix=".png")
            self._page.screenshot(path=path, full_page=True)
            return True, "", path
        except Exception as exc:
            return False, str(exc), ""

    def _do_click(self, selector: str) -> tuple[bool, str]:
        try:
            self._page.click(selector, timeout=self._timeout_sec * 1000)
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def _cleanup(self) -> None:
        for attr in ("_context", "_browser", "_pw"):
            obj = getattr(self, attr)
            try:
                if obj is not None:
                    obj.close()
            except Exception:
                pass
        self._page = None
