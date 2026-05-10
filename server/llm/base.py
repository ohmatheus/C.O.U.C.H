from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


class BaseLLMProvider(ABC):
    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str,
    ) -> tuple[str | None, list[ToolCall]]:
        """Single LLM call. Returns (text, tool_calls) in canonical form.

        messages: canonical OpenAI-style history (no system message — passed separately).
        tools: Anthropic-native tool dicts (name, description, input_schema).
        system: system prompt string.
        """
        ...
