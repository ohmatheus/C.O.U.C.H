import logging
import urllib.parse
from pathlib import Path
from typing import ClassVar

from playwright.sync_api import Page

from state import AppContext, AppState

_SNAPSHOT_JS = (Path(__file__).parent / "snapshot.js").read_text()

log = logging.getLogger(__name__)

_SNAPSHOT_LIMIT: int = 10


def configure(snapshot_limit: int) -> None:
    global _SNAPSHOT_LIMIT
    _SNAPSHOT_LIMIT = snapshot_limit


class YoutubeContext(AppContext):
    group: ClassVar[str] = "youtube"

    current_url: str | None = None
    current_video_title: str | None = None
    search_results: list[str] = []
    page_video_hrefs: list[str] = []
    dom_summary: str | None = None

    def render(self) -> str:
        parts = ["\nYouTube:"]
        if self.current_video_title:
            parts.append(f"  Now playing: {self.current_video_title}")
        if self.dom_summary:
            parts.append(f"  Info: {self.dom_summary}")
        if self.current_url:
            parts.append(f"  URL: {self.current_url}")
        label = "Up next" if self.current_video_title else "Videos"
        for i, title in enumerate(self.search_results, 1):
            parts.append(f"  [{i}] {label}: {title}")
        return "\n".join(parts) if len(parts) > 1 else ""


def _snapshot_links(page: Page, exclude_v: str = "", check_visible: bool = True) -> list[dict[str, str]]:
    """Extract watch links via eval_on_selector_all (pierces shadow DOM). Titles only —
    sidebar channel names are unreachable through any shadow DOM approach tried."""
    try:
        items: list[dict[str, str]] = page.eval_on_selector_all(
            "a[href*='/watch']",
            _SNAPSHOT_JS,
            {"limit": _SNAPSHOT_LIMIT, "excludeV": exclude_v, "checkVisible": check_visible},
        )
        log.debug("_snapshot_links: %d items", len(items))
        for i in items:
            log.debug("  link: %r", i["title"][:70])
        return items
    except Exception as exc:
        log.debug("_snapshot_links error: %s", exc)
        return []


def youtube_snapshot(page: Page, state: AppState) -> None:
    url = page.url
    log.debug("youtube_snapshot url=%s", url)
    if "youtube.com" not in url:
        state.clear_context("youtube")
        return

    existing = state.get_context("youtube")
    prior = existing if isinstance(existing, YoutubeContext) else YoutubeContext()
    prior_results = prior.search_results
    prior_hrefs = prior.page_video_hrefs
    dom_summary: str | None = None

    if "/watch" in url:
        try:
            title = page.locator("h1.ytd-watch-metadata yt-formatted-string").first.inner_text(timeout=2000)
            channel = page.locator("ytd-channel-name a").first.inner_text(timeout=2000)
            dom_summary = f"{title} — {channel}"
        except Exception:
            pass
        current_v = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("v", [""])[0]
        items = _snapshot_links(page, exclude_v=current_v, check_visible=True)
        log.debug("youtube watch sidebar snapshot: %d items", len(items))
        if items:
            prior_hrefs = [i["href"] for i in items]
            prior_results = [i["title"] for i in items]

    elif "/results" not in url:
        items = _snapshot_links(page)
        log.debug("youtube home snapshot: %d items", len(items))
        if items:
            prior_hrefs = [i["href"] for i in items]
            prior_results = [i["title"] for i in items]

    state.set_context(YoutubeContext(
        current_url=url,
        current_video_title=page.title() if "/watch" in url else None,
        search_results=prior_results,
        page_video_hrefs=prior_hrefs,
        dom_summary=dom_summary,
    ))
