from playwright.sync_api import Page

from state import AppState
from tools.browser.manager import BROWSER

_SCROLL_PX: int = 400


def configure(scroll_px: int) -> None:
    global _SCROLL_PX
    _SCROLL_PX = scroll_px


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


def chrome_refresh(state: AppState, **_: object) -> str:
    def _do(page: Page) -> str:
        page.reload()
        return page.title()

    try:
        return f"Page refreshed: {BROWSER.execute(_do)}"
    except Exception as exc:
        return f"Refresh failed: {exc}"


def chrome_back(state: AppState, **_: object) -> str:
    def _do(page: Page) -> str:
        page.go_back()
        return page.url

    try:
        return f"Went back to: {BROWSER.execute(_do)}"
    except Exception as exc:
        return f"Back navigation failed: {exc}"


def chrome_scroll_down(state: AppState, **_: object) -> str:
    BROWSER.execute(lambda page: page.mouse.wheel(0, _SCROLL_PX))
    return "Scrolled down"


def chrome_scroll_up(state: AppState, **_: object) -> str:
    BROWSER.execute(lambda page: page.mouse.wheel(0, -_SCROLL_PX))
    return "Scrolled up"
