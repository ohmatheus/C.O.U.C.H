import logging
import urllib.parse
from typing import ClassVar

from playwright.sync_api import Page

from state import AppContext, AppState

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
    """Extract watch links via eval_on_selector_all (pierces shadow DOM). Titles only — channel
    names are unreachable from title anchors without traversing multiple closed shadow roots."""
    visible_js = "r.bottom > 0 && r.top < window.innerHeight &&" if check_visible else ""
    exclude_js = f"&& !href.includes('v={exclude_v}')" if exclude_v else ""
    js = f"""els => {{
        const seen = new Set();
        const out = [];
        for (const a of els) {{
            const href = a.getAttribute('href');
            const text = (a.textContent || '').replace(/\\s+/g, ' ').trim();
            const r = a.getBoundingClientRect();
            if ({visible_js} href && text.length > 10 && text.length < 200 && !seen.has(href) {exclude_js}) {{
                seen.add(href);
                out.push({{href, title: text}});
            }}
            if (out.length >= {_SNAPSHOT_LIMIT}) break;
        }}
        return out;
    }}"""
    try:
        items: list[dict[str, str]] = page.eval_on_selector_all("a[href*='/watch']", js)
        log.debug("_snapshot_links: %d items", len(items))
        for i in items:
            log.debug("  link: title=%r", i["title"][:60])
        return items
    except Exception as exc:
        log.debug("_snapshot_links error: %s", exc)
        return []


def _snapshot_cards(page: Page, card_selector: str, exclude_v: str = "") -> list[dict[str, str]]:
    """Extract title + channel per card using Playwright locators (pierces shadow DOM).
    Only use when the card locator is known to find elements quickly."""
    items: list[dict[str, str]] = []
    try:
        cards = page.locator(card_selector).all()
        log.debug("_snapshot_cards(%s): %d cards", card_selector, len(cards))
        if not cards:
            return items
        for card in cards:
            if len(items) >= _SNAPSHOT_LIMIT:
                break
            try:
                href = card.locator("a[href*='/watch']").first.get_attribute("href", timeout=300) or ""
                if not href or (exclude_v and f"v={exclude_v}" in href):
                    continue
                title = card.locator("#video-title").first.inner_text(timeout=300).strip()
                if not title:
                    continue
                channel = ""
                try:
                    channel = card.locator("ytd-channel-name a").first.inner_text(timeout=300).strip()
                except Exception:
                    pass
                label = f"{title} — {channel}" if channel else title
                log.debug("  item: title=%r channel=%r", label[:60], channel)
                items.append({"href": href, "title": label})
            except Exception as exc:
                log.debug("  card skip: %s", exc)
    except Exception as exc:
        log.debug("_snapshot_cards(%s) error: %s", card_selector, exc)
    return items


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
        # Try card-level locators first; fall back to link scan if they don't find anything
        items = _snapshot_cards(page, "ytd-compact-video-renderer", exclude_v=current_v)
        if not items:
            items = _snapshot_links(page, exclude_v=current_v, check_visible=False)
        log.debug("youtube watch sidebar snapshot: %d items", len(items))
        if items:
            prior_hrefs = [i["href"] for i in items]
            prior_results = [i["title"] for i in items]

    elif "/results" not in url:
        # Home page: skip _snapshot_cards — #video-title times out through nested shadow DOM.
        # _snapshot_links uses eval_on_selector_all which reliably pierces shadow DOM.
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
