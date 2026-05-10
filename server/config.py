from pathlib import Path

import yaml
from pydantic import BaseModel

_CONFIG_FILE = Path(__file__).parent / "config.yml"


class AppConfig(BaseModel):
    enable_vision: bool = True
    max_command_history: int = 5
    max_error_history: int = 3


def load_config() -> AppConfig:
    if _CONFIG_FILE.exists():
        data = yaml.safe_load(_CONFIG_FILE.read_text()) or {}
        return AppConfig(**data)
    return AppConfig()
