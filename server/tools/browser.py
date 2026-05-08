import urllib.parse
from typing import Any

from playwright.sync_api import Page

from tools.browser_manager import BROWSER

_SEARCH_LIMIT: int = 10


def configure(search_limit: int) -> None:
    global _SEARCH_LIMIT
    _SEARCH_LIMIT = search_limit


def youtube_search(query: str, state: dict[str, Any], **_kwargs: object) -> str:
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)

    def _do(page: Page) -> list[str]:
        page.goto(url)
        page.wait_for_selector("ytd-video-renderer", timeout=10_000)
        els = page.locator("ytd-video-renderer #video-title").all()
        return [el.inner_text().strip() for el in els[:_SEARCH_LIMIT]]

    titles = BROWSER.execute(_do)
    state["active_app"] = "youtube"
    state["last_search"] = query
    state["browser_results"] = titles
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(titles))
    return f"YouTube results for \"{query}\":\n{numbered}"


def youtube_play_result(index: int, state: dict[str, Any], **_kwargs: object) -> str:
    def _do(page: Page) -> str:
        page.wait_for_selector(
            "ytd-video-renderer a#thumbnail, ytd-rich-item-renderer a#thumbnail",
            timeout=10_000,
        )
        thumbnails = page.locator(
            "ytd-video-renderer a#thumbnail, ytd-rich-item-renderer a#thumbnail"
        ).all()
        if not thumbnails:
            raise ValueError("No results visible on the page")
        if not 1 <= index <= len(thumbnails):
            raise ValueError(f"Index {index} out of range (1–{len(thumbnails)})")
        thumbnails[index - 1].click()
        page.wait_for_load_state("domcontentloaded")
        return page.title()

    title = BROWSER.execute(_do)
    state["is_playing"] = True
    state["browser_results"] = []
    return f"Now playing: {title}"


def youtube_toggle_pause(_state: dict[str, Any]) -> str:
    BROWSER.execute(lambda page: page.keyboard.press("k"))
    return "Toggled pause/play"


def youtube_toggle_fullscreen(_state: dict[str, Any]) -> str:
    BROWSER.execute(lambda page: page.keyboard.press("f"))
    return "Toggled fullscreen"


def youtube_toggle_mute(_state: dict[str, Any]) -> str:
    BROWSER.execute(lambda page: page.keyboard.press("m"))
    return "Toggled mute"


def goto_url(url: str, state: dict[str, Any], **_kwargs: object) -> str:
    def _do(page: Page) -> str:
        page.goto(url)
        return page.title()

    try:
        title = BROWSER.execute(_do)
    except Exception as exc:
        return f"Navigation failed: {exc}"
    state["active_app"] = None
    state["browser_results"] = []
    return f"Navigated to: {title}"
