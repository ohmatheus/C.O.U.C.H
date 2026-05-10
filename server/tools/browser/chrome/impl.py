from playwright.sync_api import Page

from state import AppState
from tools.browser.manager import BROWSER


def goto_url(url: str, state: AppState, **_: object) -> str:
    def _do(page: Page) -> str:
        page.goto(url)
        return page.title()

    try:
        title = BROWSER.execute(_do)
    except Exception as exc:
        return f"Navigation failed: {exc}"
    state.active_app = None
    return f"Navigated to: {title}"
