from collections.abc import Callable
from typing import Any

from tools.browser import (
    goto_url,
    youtube_play_result,
    youtube_search,
    youtube_toggle_fullscreen,
    youtube_toggle_mute,
    youtube_toggle_pause,
)
from tools.system import do_nothing, press_key, set_volume, stop_listening, volume_down, volume_up

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
            "name": "press_key",
            "description": "Send a keystroke to the active window using xdotool. Useful for controlling non-browser applications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "xdotool key name, e.g. 'space', 'Escape', 'ctrl+l'.",
                    },
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "do_nothing",
            "description": "Call this when the command does not match any available tool. Has no effect.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_listening",
            "description": "End the listening session and go to sleep. Call ONLY when the user explicitly asks to stop (e.g. 'stop', 'go to sleep', 'stop listening').",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": "Search YouTube for specific content and return the top results as a numbered list of titles. Do NOT use this to open YouTube — use goto_url for that.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "YouTube search query.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_play_result",
            "description": "Play the YouTube video at the given position in the current page (search results or homepage). Use browser_results from state to match a title to an index.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "1-based position of the video to play.",
                    },
                },
                "required": ["index"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_toggle_pause",
            "description": "Pause or resume the currently playing YouTube video.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_toggle_fullscreen",
            "description": "Toggle fullscreen for the currently playing YouTube video.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_toggle_mute",
            "description": "Mute or unmute the currently playing YouTube video.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "goto_url",
            "description": "Navigate the browser to a URL. Use this to open websites, e.g. goto_url('https://www.youtube.com') to open YouTube.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL to open, e.g. 'https://www.reddit.com'.",
                    },
                },
                "required": ["url"],
            },
        },
    },
]

DISPATCH: dict[str, Callable[..., str]] = {
    "set_volume": set_volume,
    "volume_up": volume_up,
    "volume_down": volume_down,
    "press_key": press_key,
    "do_nothing": do_nothing,
    "stop_listening": stop_listening,
    "youtube_search": youtube_search,
    "youtube_play_result": youtube_play_result,
    "youtube_toggle_pause": youtube_toggle_pause,
    "youtube_toggle_fullscreen": youtube_toggle_fullscreen,
    "youtube_toggle_mute": youtube_toggle_mute,
    "goto_url": goto_url,
}
