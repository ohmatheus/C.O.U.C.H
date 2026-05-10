import json
import logging
from typing import Any

from llm.base import BaseLLMProvider
from tools import DISPATCH, TOOL_DEFINITIONS
from tools.system import STOP_SENTINEL

log = logging.getLogger(__name__)

_MAX_TOOL_CALLS: int = 5

_SYSTEM_PROMPT = """\
You are C.O.U.C.H, a local voice assistant that controls the user's computer.
You receive voice commands as transcribed speech in {language} and call the available tools to execute them.

Rules:
- Call a tool ONLY when the command clearly matches its description.
- If no tool matches, call do_nothing.
- NEVER call stop_listening unless the user explicitly asks to stop listening.
- To open a website (e.g. "open YouTube", "go to Reddit"), use goto_url. NEVER use youtube_search just to open YouTube.
- Only use youtube_search when the user wants to search for specific content (e.g. "search for cat videos").
- When state.browser_results is non-empty and the user asks to play a video (by title, topic, or description), match against browser_results and call youtube_play_result with the 1-based index. Do NOT search again.
- After goto_url completes, stop — do not call any other tool.
"""


class Agent:
    """Provider-agnostic agentic loop: transcript → tool calls → feedback signal."""

    def __init__(self, provider: BaseLLMProvider, language: str, state: dict[str, Any]) -> None:
        self._provider = provider
        self._language = language
        self._state = state

    def _build_system_prompt(self) -> str:
        prompt = _SYSTEM_PROMPT.format(language=self._language)
        state_summary = json.dumps(self._state, ensure_ascii=False, indent=2)
        return f"{prompt}\nCurrent system state:\n{state_summary}"

    def run(self, transcript: str) -> str | None:
        """Run the agentic loop for one transcript. Blocking — call in executor.

        Returns:
            "beep_ok"      — at least one tool executed successfully
            "beep_error"   — a tool or LLM call raised an exception
            "session_end"  — stop_listening tool was called
            None           — no tool matched (non-command utterance)
        """
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": transcript},
        ]
        system = self._build_system_prompt()
        tool_called = False

        try:
            for _ in range(_MAX_TOOL_CALLS):
                text, tool_calls = self._provider.complete(messages, TOOL_DEFINITIONS, system)

                if not tool_calls:
                    break

                messages.append({
                    "role": "assistant",
                    "content": text,
                    "tool_calls": [
                        {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                        for tc in tool_calls
                    ],
                })

                for tc in tool_calls:
                    log.info("tool call: %s(%s)", tc.name, tc.arguments)

                    if tc.name not in DISPATCH:
                        log.warning("unknown tool: %s", tc.name)
                        result = f"Outil inconnu : {tc.name}"
                    else:
                        result = DISPATCH[tc.name](**tc.arguments, state=self._state)

                    log.info("tool result: %s", result)

                    if result == STOP_SENTINEL:
                        return "session_end"

                    if result == "__do_nothing__":
                        log.info("Nothing to do.")
                        return None

                    tool_called = True
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

        except Exception as exc:
            log.error("agent error: %s", exc)
            return "beep_error"

        return "beep_ok" if tool_called else None
