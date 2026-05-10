from pydantic import Field

from tools.registry import ToolEntry, ToolParams
from tools.browser.chrome.impl import chrome_back, chrome_refresh, chrome_scroll_down, chrome_scroll_up, goto_url


class GotoUrl(ToolEntry):
    name = "goto_url"
    description = "Navigate the browser to a URL. Use this to open websites, e.g. goto_url('https://www.youtube.com') to open YouTube."
    fn = staticmethod(goto_url)

    class Params(ToolParams):
        url: str = Field(description="Full URL to open, e.g. 'https://www.reddit.com'.")


class ChromeRefresh(ToolEntry):
    name = "chrome_refresh"
    description = "Reload the current browser page."
    fn = staticmethod(chrome_refresh)


class ChromeBack(ToolEntry):
    name = "chrome_back"
    description = "Navigate back in browser history."
    fn = staticmethod(chrome_back)


class ChromeScrollDown(ToolEntry):
    name = "chrome_scroll_down"
    description = "Scroll the current page down."
    fn = staticmethod(chrome_scroll_down)


class ChromeScrollUp(ToolEntry):
    name = "chrome_scroll_up"
    description = "Scroll the current page up."
    fn = staticmethod(chrome_scroll_up)


ENTRIES: list[type[ToolEntry]] = [GotoUrl, ChromeRefresh, ChromeBack, ChromeScrollDown, ChromeScrollUp]
