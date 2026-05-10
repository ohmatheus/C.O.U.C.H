from collections.abc import Callable
from enum import StrEnum
from typing import Any

from tools.browser.chrome.schema import ENTRIES as _CHROME_ENTRIES
from tools.browser.youtube.schema import ENTRIES as _YOUTUBE_ENTRIES
from tools.general.schema import ENTRIES as _GENERAL_ENTRIES
from tools.registry import ToolEntry, build_dispatch


class AppGroup(StrEnum):
    GENERAL = "general"
    YOUTUBE = "youtube"
    CHROME = "chrome"
    SPOTIFY = "spotify"
    NOTE = "note"


TOOL_GROUPS: dict[AppGroup, list[type[ToolEntry]]] = {
    AppGroup.GENERAL: _GENERAL_ENTRIES,
    AppGroup.YOUTUBE: _YOUTUBE_ENTRIES,
    AppGroup.CHROME: _CHROME_ENTRIES,
}


def get_tool_defs_for(groups: list[AppGroup]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for group in groups:
        for entry in TOOL_GROUPS.get(group, []):
            if entry.name not in seen:
                seen.add(entry.name)
                result.append(entry.to_anthropic_tool())
    return result


def get_dispatch_for(groups: list[AppGroup]) -> dict[str, Callable[..., str]]:
    seen: set[str] = set()
    entries: list[type[ToolEntry]] = []
    for group in groups:
        for entry in TOOL_GROUPS.get(group, []):
            if entry.name not in seen:
                seen.add(entry.name)
                entries.append(entry)
    return build_dispatch(entries)
