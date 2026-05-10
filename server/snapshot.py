import base64
import logging
from collections.abc import Callable

from playwright.sync_api import Page

from state import AppState
from tools.browser.chrome.context import chrome_snapshot
from tools.browser.manager import BROWSER
from tools.browser.youtube.context import youtube_snapshot
from utils.image import resize_screenshot

log = logging.getLogger(__name__)

_SNAPSHOT_FNS: dict[str, Callable[[Page, AppState], None]] = {
    "youtube": youtube_snapshot,
    "chrome": chrome_snapshot,
}

def take_snapshot(
    state: AppState,
    groups: list[str],
    take_screenshot: bool,
) -> str | None:
    """Snapshot browser state into `state` for applicable groups.

    Returns a base64-encoded JPEG string if take_screenshot is True, else None.
    """
    active = {g: _SNAPSHOT_FNS[g] for g in groups if g in _SNAPSHOT_FNS}
    if not active:
        return None

    def _do(page: Page) -> str | None:
        for fn in active.values():
            fn(page, state)
        if not take_screenshot:
            return None
        raw = page.screenshot(type="jpeg", quality=75)
        return base64.b64encode(resize_screenshot(raw)).decode()

    try:
        return BROWSER.execute(_do)
    except Exception as exc:
        log.warning("snapshot failed: %s", exc)
        return None
