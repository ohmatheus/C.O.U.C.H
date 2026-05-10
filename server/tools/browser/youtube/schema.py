from pydantic import Field

from tools.registry import ToolEntry, ToolParams
from tools.browser.youtube.impl import (
    youtube_play_result,
    youtube_search,
    youtube_toggle_fullscreen,
    youtube_toggle_mute,
    youtube_toggle_pause,
)


class YoutubeSearch(ToolEntry):
    name = "youtube_search"
    description = "Search YouTube for specific content and return the top results as a numbered list of titles. Do NOT use this to open YouTube — use goto_url for that."
    requires_vision = True
    fn = staticmethod(youtube_search)

    class Params(ToolParams):
        query: str = Field(description="YouTube search query.")


class YoutubePlayResult(ToolEntry):
    name = "youtube_play_result"
    description = "Play the YouTube video at the given position in the current page (search results or homepage). Use browser_results from state to match a title to an index."
    requires_vision = True
    fn = staticmethod(youtube_play_result)

    class Params(ToolParams):
        index: int = Field(description="1-based position of the video to play.")


class YoutubeTogglePause(ToolEntry):
    name = "youtube_toggle_pause"
    description = "Pause or resume the currently playing YouTube video."
    fn = staticmethod(youtube_toggle_pause)


class YoutubeToggleFullscreen(ToolEntry):
    name = "youtube_toggle_fullscreen"
    description = "Toggle fullscreen for the currently playing YouTube video."
    fn = staticmethod(youtube_toggle_fullscreen)


class YoutubeToggleMute(ToolEntry):
    name = "youtube_toggle_mute"
    description = "Mute or unmute the currently playing YouTube video."
    fn = staticmethod(youtube_toggle_mute)


ENTRIES: list[type[ToolEntry]] = [
    YoutubeSearch,
    YoutubePlayResult,
    YoutubeTogglePause,
    YoutubeToggleFullscreen,
    YoutubeToggleMute,
]
