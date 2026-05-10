from typing import ClassVar

from playwright.sync_api import Page
from pydantic import BaseModel

from state import AppContext, AppState


class ChromeTab(BaseModel):
    url: str
    title: str


class ChromeContext(AppContext):
    group: ClassVar[str] = "chrome"

    active_url: str | None = None
    active_title: str | None = None
    tabs: list[ChromeTab] = []

    def render(self) -> str:
        if not self.active_url:
            return ""
        parts = ["\nBrowser:", f"  Active: {self.active_url} — {self.active_title}"]
        if self.tabs:
            parts.append("  Tabs: " + ", ".join(t.url for t in self.tabs[:5]))
        return "\n".join(parts)


def chrome_snapshot(page: Page, state: AppState) -> None:
    tabs = [ChromeTab(url=p.url, title=p.title()) for p in page.context.pages]
    state.set_context(ChromeContext(
        active_url=page.url,
        active_title=page.title(),
        tabs=tabs,
    ))
