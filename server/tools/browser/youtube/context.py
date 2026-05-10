from typing import ClassVar

from playwright.sync_api import Page

from state import AppContext, AppState


class YoutubeContext(AppContext):
    group: ClassVar[str] = "youtube"

    current_url: str | None = None
    current_video_title: str | None = None
    search_results: list[str] = []
    dom_summary: str | None = None

    def render(self) -> str:
        parts = ["\nYouTube:"]
        if self.current_video_title:
            parts.append(f"  Now playing: {self.current_video_title}")
        if self.current_url:
            parts.append(f"  URL: {self.current_url}")
        for i, title in enumerate(self.search_results, 1):
            parts.append(f"  [{i}] {title}")
        if self.dom_summary:
            parts.append(f"  Info: {self.dom_summary}")
        return "\n".join(parts) if len(parts) > 1 else ""


def youtube_snapshot(page: Page, state: AppState) -> None:
    url = page.url
    if "youtube.com" not in url:
        state.clear_context("youtube")
        return

    existing = state.get_context("youtube")
    prior_results = existing.search_results if isinstance(existing, YoutubeContext) else []
    dom_summary: str | None = None

    if "/watch" in url:
        try:
            title = page.locator("h1.ytd-watch-metadata yt-formatted-string").first.inner_text(timeout=2000)
            channel = page.locator("ytd-channel-name a").first.inner_text(timeout=2000)
            dom_summary = f"{title} — {channel}"
        except Exception:
            pass

    state.set_context(YoutubeContext(
        current_url=url,
        current_video_title=page.title() if "/watch" in url else None,
        search_results=prior_results,
        dom_summary=dom_summary,
    ))
