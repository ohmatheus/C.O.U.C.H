from typing import Any

APP_STATE: dict[str, Any] = {
    "active_app": None,
    "volume": 60,
    "is_playing": False,
    "last_search": None,
    "last_error": None,
    "command_history": [],
}
