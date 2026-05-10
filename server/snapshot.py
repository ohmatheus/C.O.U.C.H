import base64
import logging

from playwright.sync_api import Page

from state import AppState
from tools import get_snapshot_fns
from tools.browser.manager import BROWSER
from utils.image import resize_screenshot

log = logging.getLogger(__name__)


def take_snapshot(
    state: AppState,
    groups: list[str],
    take_screenshot: bool,
) -> str | None:
    """Snapshot browser state into `state` for applicable groups.

    Returns a base64-encoded JPEG string if take_screenshot is True, else None.
    """
    active = get_snapshot_fns(groups)
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
