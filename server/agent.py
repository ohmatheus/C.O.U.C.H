import json
import logging
from typing import Any

import ollama
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
    """Ollama agentic loop: transcript → tool calls → feedback signal."""

    def __init__(self, model: str, keepalive: int, language: str, state: dict[str, Any]) -> None:
        self._model = model
        self._keepalive = keepalive
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
            "beep_error"   — a tool or Ollama call raised an exception
            "session_end"  — stop_listening tool was called
            None           — no tool matched (non-command utterance)
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": transcript},
        ]
        tool_called = False

        try:
            for _ in range(_MAX_TOOL_CALLS):
                response = ollama.chat(
                    model=self._model,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    options={"keep_alive": self._keepalive},
                )
                msg = response.message
                if not msg.tool_calls:
                    break

                messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls})

                for call in msg.tool_calls:
                    name = call.function.name
                    args: dict[str, Any] = dict(call.function.arguments)
                    log.info("tool call: %s(%s)", name, args)

                    if name not in DISPATCH:
                        log.warning("unknown tool: %s", name)
                        result = f"Outil inconnu : {name}"
                    else:
                        result = DISPATCH[name](**args, state=self._state)

                    log.info("tool result: %s", result)

                    if result == STOP_SENTINEL:
                        return "session_end"

                    if result == "__do_nothing__":
                        log.info("Nothing to do.")
                        return None

                    tool_called = True
                    messages.append({"role": "tool", "content": result})

        except Exception as exc:
            log.error("agent error: %s", exc)
            return "beep_error"

        return "beep_ok" if tool_called else None
