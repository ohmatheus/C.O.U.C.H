from collections.abc import Callable
from typing import Any

from tools.browser import search_youtube
from tools.system import do_nothing, set_volume, stop_listening, volume_down, volume_up

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Set the system volume to a specific level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Volume level between 0 and 100.",
                    },
                },
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "volume_up",
            "description": "Increase the system volume by 10%.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "volume_down",
            "description": "Decrease the system volume by 10%.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "do_nothing",
            "description": "Call this when the input is not a recognized command. Has no effect.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_listening",
            "description": "End the listening session and return to standby. Call ONLY when the user explicitly asks to stop (e.g. 'stop listening', 'go to sleep', 'stop', 'stop the session').",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_youtube",
            "description": "Open a YouTube search in the default browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The YouTube search query.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]

# Each callable accepts keyword args from LLM + the mutable state dict.
DISPATCH: dict[str, Callable[..., str]] = {
    "set_volume": set_volume,
    "volume_up": volume_up,
    "volume_down": volume_down,
    "do_nothing": do_nothing,
    "stop_listening": stop_listening,
    "search_youtube": search_youtube,
}
