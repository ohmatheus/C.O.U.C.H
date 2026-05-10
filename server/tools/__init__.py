from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from tools.browser.chrome.context import chrome_snapshot
from tools.browser.chrome.schema import ENTRIES as _CHROME_ENTRIES
from tools.browser.youtube.context import youtube_snapshot
from tools.browser.youtube.schema import ENTRIES as _YOUTUBE_ENTRIES
from tools.general.schema import ENTRIES as _GENERAL_ENTRIES
from tools.registry import ToolEntry, build_dispatch


class AppGroup(StrEnum):
    GENERAL = "general"
    YOUTUBE = "youtube"
    CHROME = "chrome"
    SPOTIFY = "spotify"
    NOTE = "note"


SnapshotFn = Callable[..., None]


@dataclass
class AppDescriptor:
    group: AppGroup
    tool_entries: list[type[ToolEntry]]
    snapshot_fn: SnapshotFn | None = None
    parents: list[AppGroup] = field(default_factory=list)


APP_REGISTRY: list[AppDescriptor] = [
    AppDescriptor(AppGroup.GENERAL, _GENERAL_ENTRIES),
    AppDescriptor(AppGroup.CHROME, _CHROME_ENTRIES, snapshot_fn=chrome_snapshot),
    AppDescriptor(AppGroup.YOUTUBE, _YOUTUBE_ENTRIES, snapshot_fn=youtube_snapshot, parents=[AppGroup.CHROME]),
]

_PARENTS: dict[AppGroup, list[AppGroup]] = {
    d.group: d.parents for d in APP_REGISTRY if d.parents
}

TOOL_GROUPS: dict[AppGroup, list[type[ToolEntry]]] = {
    d.group: d.tool_entries for d in APP_REGISTRY
}


def get_snapshot_fns(groups: list[str]) -> dict[str, SnapshotFn]:
    return {
        d.group.value: d.snapshot_fn
        for d in APP_REGISTRY
        if d.group.value in groups and d.snapshot_fn is not None
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
