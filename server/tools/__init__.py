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


# Child → parent(s): resolving a child automatically includes its parents.
_PARENTS: dict[AppGroup, list[AppGroup]] = {
    AppGroup.YOUTUBE: [AppGroup.CHROME],
}

TOOL_GROUPS: dict[AppGroup, list[type[ToolEntry]]] = {
    AppGroup.GENERAL: _GENERAL_ENTRIES,
    AppGroup.YOUTUBE: _YOUTUBE_ENTRIES,
    AppGroup.CHROME: _CHROME_ENTRIES,
}


def resolve_groups(groups: list[AppGroup]) -> list[AppGroup]:
    """Expand groups with their parents (one level, insertion-ordered, no duplicates)."""
    result = list(groups)
    for group in groups:
        for parent in _PARENTS.get(group, []):
            if parent not in result:
                result.append(parent)
    return result


def _iter_entries(groups: list[AppGroup]) -> list[type[ToolEntry]]:
    seen: set[str] = set()
    result: list[type[ToolEntry]] = []
    for group in groups:
        for entry in TOOL_GROUPS.get(group, []):
            if entry.name not in seen:
                seen.add(entry.name)
                result.append(entry)
    return result


def any_tool_requires_vision(groups: list[AppGroup]) -> bool:
    return any(e.requires_vision for e in _iter_entries(groups))


def get_tool_defs_for(groups: list[AppGroup]) -> list[dict[str, Any]]:
    return [e.to_anthropic_tool() for e in _iter_entries(groups)]


def get_dispatch_for(groups: list[AppGroup]) -> dict[str, Callable[..., str]]:
    return build_dispatch(_iter_entries(groups))
