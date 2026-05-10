from pydantic import Field

from tools.registry import ToolEntry, ToolParams
from tools.browser.chrome.impl import goto_url


class GotoUrl(ToolEntry):
    name = "goto_url"
    description = "Navigate the browser to a URL. Use this to open websites, e.g. goto_url('https://www.youtube.com') to open YouTube."
    fn = staticmethod(goto_url)

    class Params(ToolParams):
        url: str = Field(description="Full URL to open, e.g. 'https://www.reddit.com'.")


ENTRIES: list[type[ToolEntry]] = [GotoUrl]
