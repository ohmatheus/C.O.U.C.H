import json
import logging
from typing import Any

from llm.base import BaseLLMProvider
from tools import AppGroup, get_dispatch_for, get_tool_defs_for
from tools.general.impl import STOP_SENTINEL

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

_ROUTER_PROMPT = """\
You are a command router for a voice assistant. Given a voice command, identify which application(s) it targets.
Available apps:
- GENERAL: volume control, keystrokes, system commands, stopping the assistant
- YOUTUBE: YouTube videos, search, playback
- CHROME: open a website or navigate to a URL
- SPOTIFY: music, playlists, podcasts via Spotify
- NOTE: shopping lists, notes, reminders

Reply with the app name only (e.g. "SPOTIFY"). If multiple apply, comma-separate them (e.g. "GENERAL,YOUTUBE").
Reply in uppercase. No explanation, no punctuation, just the app name(s).
"""


class Agent:
    """Provider-agnostic agentic loop: transcript → tool calls → feedback signal."""

    def __init__(self, provider: BaseLLMProvider, language: str, state: dict[str, Any]) -> None:
        self._provider = provider
        self._language = language
        self._state = state

    def _classify(self, transcript: str) -> list[AppGroup]:
        text, _ = self._provider.complete(
            messages=[{"role": "user", "content": transcript}],
            tools=[],
            system=_ROUTER_PROMPT,
        )
        groups: list[AppGroup] = [AppGroup.GENERAL]
        for token in (text or "").upper().split(","):
            token = token.strip()
            try:
                group = AppGroup(token.lower())
                if group not in groups:
                    groups.append(group)
            except ValueError:
                pass
        log.info("classified %r → %s", transcript, [g.value for g in groups])
        return groups

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
        try:
            groups = self._classify(transcript)
        except Exception as exc:
            log.error("classifier error: %s", exc)
            groups = list(AppGroup)

        tool_defs = get_tool_defs_for(groups)
        dispatch = get_dispatch_for(groups)

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": transcript},
        ]
        system = self._build_system_prompt()
        tool_called = False

        try:
            for _ in range(_MAX_TOOL_CALLS):
                text, tool_calls = self._provider.complete(messages, tool_defs, system)

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

                    if tc.name not in dispatch:
                        log.warning("unknown tool: %s", tc.name)
                        result = f"Unknown tool: {tc.name}"
                    else:
                        result = dispatch[tc.name](**tc.arguments, state=self._state)

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
