import queue
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from playwright.sync_api import Page, sync_playwright

T = TypeVar("T")

_PROFILE_DIR = Path.home() / ".couch" / "browser_profile"
_DEBUG_PORT = 9222

_CHROME_SEARCH_PATHS: list[str] = [
    "/opt/google/chrome/chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/snap/bin/chromium",
]

_Cmd = tuple[Callable[[Page], Any], "queue.Queue[tuple[str, Any]]"]


def find_chrome() -> str | None:
    for p in _CHROME_SEARCH_PATHS:
        if Path(p).exists():
            return p
    return None


class BrowserManager:
    """Thread-safe Playwright manager with a dedicated browser thread.

    Lazy — the browser only opens on the first execute() call.

    Launches Chrome/Chromium via subprocess with no Playwright automation flags
    (so Google sign-in works), then connects to it via CDP.  The same Chrome
    window is reused across server restarts if it is still running.
    """

    def __init__(self) -> None:
        self._cmd_q: queue.Queue[_Cmd | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._chrome_path: str | None = None

    def configure(self, chrome_path: str | None) -> None:
        self._chrome_path = chrome_path

    def start(self) -> None:
        with self._lock:
            if self._thread is not None:
                return
            self._thread = threading.Thread(
                target=self._loop, daemon=True, name="playwright"
            )
            self._thread.start()
        self._ready.wait()

    def _open_page(self, pw: Any) -> Page:
        cdp_url = f"http://localhost:{_DEBUG_PORT}"
        executable = self._chrome_path or "chromium-browser"

        try:
            browser = pw.chromium.connect_over_cdp(cdp_url)
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            return ctx.new_page()
        except Exception:
            pass

        _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.Popen([
            executable,
            f"--remote-debugging-port={_DEBUG_PORT}",
            f"--user-data-dir={_PROFILE_DIR}",
            "--no-first-run",
            "--start-maximized",
        ])

        for _ in range(20):
            time.sleep(0.5)
            try:
                browser = pw.chromium.connect_over_cdp(cdp_url)
                ctx = browser.contexts[0] if browser.contexts else browser.new_context()
                return ctx.new_page()
            except Exception:
                continue

        raise RuntimeError(f"Could not connect to browser at {cdp_url}")

    def _loop(self) -> None:
        with sync_playwright() as pw:
            page = self._open_page(pw)
            self._ready.set()

            while True:
                item = self._cmd_q.get()
                if item is None:
                    break
                fn, resp_q = item
                try:
                    resp_q.put(("ok", fn(page)))
                except Exception as exc:
                    resp_q.put(("err", exc))

    def execute(self, fn: Callable[[Page], T]) -> T:
        if self._thread is None:
            self.start()
        resp_q: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._cmd_q.put((fn, resp_q))
        status, value = resp_q.get()
        if status == "err":
            raise value
        return value  # type: ignore[return-value]

    def stop(self) -> None:
        if self._thread is not None:
            self._cmd_q.put(None)
            self._thread.join(timeout=5)
            self._thread = None
            self._ready.clear()


BROWSER: BrowserManager = BrowserManager()
