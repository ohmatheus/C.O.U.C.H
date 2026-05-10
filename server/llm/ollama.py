import uuid
from typing import Any

import ollama

from llm.base import BaseLLMProvider, ToolCall


def _to_ollama_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for msg in messages:
        role = msg["role"]
        if role == "assistant" and msg.get("tool_calls"):
            result.append({
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": [
                    {"function": {"name": tc["name"], "arguments": tc["arguments"]}}
                    for tc in msg["tool_calls"]
                ],
            })
        elif role == "tool":
            result.append({"role": "tool", "content": msg["content"]})
        else:
            result.append({"role": role, "content": msg.get("content", "")})
    return result


class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: str, keepalive: int) -> None:
        self._model = model
        self._keepalive = keepalive

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str,
    ) -> tuple[str | None, list[ToolCall]]:
        ollama_messages = [{"role": "system", "content": system}] + _to_ollama_messages(messages)
        response = ollama.chat(
            model=self._model,
            messages=ollama_messages,
            tools=tools,
            options={"keep_alive": self._keepalive},
        )
        msg = response.message
        if not msg.tool_calls:
            return msg.content, []

        return msg.content, [
            ToolCall(
                id=str(uuid.uuid4()),
                name=tc.function.name,
                arguments=dict(tc.function.arguments),
            )
            for tc in msg.tool_calls
        ]
