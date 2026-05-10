from typing import Any

import anthropic

from llm.base import BaseLLMProvider, ToolCall

_MAX_TOKENS: int = 1024


def _to_anthropic_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": t["function"]["name"],
            "description": t["function"]["description"],
            "input_schema": t["function"]["parameters"],
        }
        for t in tools
    ]


def _to_anthropic_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        role = msg["role"]

        if role == "tool":
            tool_results: list[dict[str, Any]] = []
            while i < len(messages) and messages[i]["role"] == "tool":
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": messages[i]["tool_call_id"],
                    "content": messages[i]["content"],
                })
                i += 1
            result.append({"role": "user", "content": tool_results})

        elif role == "assistant" and msg.get("tool_calls"):
            content: list[dict[str, Any]] = []
            if msg.get("content"):
                content.append({"type": "text", "text": msg["content"]})
            for tc in msg["tool_calls"]:
                content.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["arguments"],
                })
            result.append({"role": "assistant", "content": content})
            i += 1

        else:
            result.append({"role": role, "content": msg.get("content", "")})
            i += 1

    return result


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, model: str, api_key: str) -> None:
        self._model = model
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str,
    ) -> tuple[str | None, list[ToolCall]]:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=_to_anthropic_messages(messages),
            tools=_to_anthropic_tools(tools),  # type: ignore[arg-type]
        )

        tool_calls: list[ToolCall] = []
        text: str | None = None
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input)))
            elif block.type == "text":
                text = block.text

        return text, tool_calls
