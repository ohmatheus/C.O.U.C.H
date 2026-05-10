from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class AppContext(BaseModel, ABC):
    """Abstract base for all per-app context snapshots injected into the LLM prompt."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    group: ClassVar[str]

    @abstractmethod
    def render(self) -> str: ...


class CommandEntry(BaseModel):
    transcript: str
    tools_called: list[str]
    success: bool


class ErrorEntry(BaseModel):
    message: str
    tool: str | None = None
    command: str | None = None


class AppState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    active_app: str | None = None
    volume: int = 60
    is_playing: bool = False
    command_history: list[CommandEntry] = []
    error_history: list[ErrorEntry] = []
    contexts: list[AppContext] = []

    def get_context(self, group: str) -> AppContext | None:
        return next((c for c in self.contexts if c.group == group), None)

    def set_context(self, ctx: AppContext) -> None:
        self.contexts = [c for c in self.contexts if c.group != ctx.group] + [ctx]

    def clear_context(self, group: str) -> None:
        self.contexts = [c for c in self.contexts if c.group != group]

    def add_command(self, entry: CommandEntry, max_history: int) -> None:
        self.command_history.append(entry)
        self.command_history = self.command_history[-max_history:]

    def add_error(self, entry: ErrorEntry, max_errors: int) -> None:
        self.error_history.append(entry)
        self.error_history = self.error_history[-max_errors:]

    def to_prompt_context(self, groups: list[str]) -> str:
        group_set = set(groups)
        lines: list[str] = [
            f"volume={self.volume}  active_app={self.active_app or 'none'}  is_playing={self.is_playing}"
        ]
        for ctx in self.contexts:
            if ctx.group in group_set:
                section = ctx.render()
                if section:
                    lines.append(section)
        if self.command_history:
            lines.append("\nRecent commands:")
            for i, cmd in enumerate(self.command_history, 1):
                status = "✓" if cmd.success else "✗"
                tools = " + ".join(cmd.tools_called) or "—"
                lines.append(f'  [{i}] "{cmd.transcript}" → {tools} {status}')
        if self.error_history:
            lines.append("\nRecent errors:")
            for err in self.error_history:
                loc = f"{err.tool}: " if err.tool else ""
                ctx_str = f' (from: "{err.command}")' if err.command else ""
                lines.append(f"  {loc}{err.message}{ctx_str}")
        return "\n".join(lines)


APP_STATE = AppState()
