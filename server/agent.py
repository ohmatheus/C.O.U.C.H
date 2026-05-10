import logging

from config import AppConfig
from llm.base import BaseLLMProvider
from snapshot import take_snapshot
from state import AppState, CommandEntry, ErrorEntry
from tools import AppGroup, any_tool_requires_vision, get_dispatch_for, get_tool_defs_for, resolve_groups
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
- When state.youtube.search_results is non-empty and the user asks to play a video (by title, topic, or description), match against those results and call youtube_play_result with the 1-based index. Do NOT search again.
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

    def __init__(self, provider: BaseLLMProvider, language: str, state: AppState, config: AppConfig) -> None:
        self._provider = provider
        self._language = language
        self._state = state
        self._config = config

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
        groups = resolve_groups(groups)
        log.info("classified %r → %s", transcript, [g.value for g in groups])
        return groups

    def _build_system_prompt(self, groups: list[AppGroup]) -> str:
        prompt = _SYSTEM_PROMPT.format(language=self._language)
        context = self._state.to_prompt_context([g.value for g in groups])
        return f"{prompt}\nCurrent state:\n{context}"

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

        take_screenshot = self._config.enable_vision and any_tool_requires_vision(groups)
        screenshot_b64 = take_snapshot(
            self._state,
            [g.value for g in groups],
            take_screenshot,
        )

        if screenshot_b64:
            user_content: str | list[dict] = [
                {"type": "text", "text": transcript},
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": screenshot_b64,
                }},
            ]
        else:
            user_content = transcript

        messages: list[dict] = [{"role": "user", "content": user_content}]
        system = self._build_system_prompt(groups)
        tool_called = False
        tools_called: list[str] = []
        last_tool_name: str | None = None
        errored = False

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
                    last_tool_name = tc.name

                    if tc.name not in dispatch:
                        log.warning("unknown tool: %s", tc.name)
                        result = f"Unknown tool: {tc.name}"
                    else:
                        result = dispatch[tc.name](**tc.arguments, state=self._state)

                    log.info("tool result: %s", result)

                    if result == STOP_SENTINEL:
                        self._state.add_command(
                            CommandEntry(transcript=transcript, tools_called=tools_called + [tc.name], success=True),
                            self._config.max_command_history,
                        )
                        return "session_end"

                    if result == "__do_nothing__":
                        log.info("Nothing to do.")
                        return None

                    tools_called.append(tc.name)
                    tool_called = True
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

        except Exception as exc:
            log.error("agent error: %s", exc)
            errored = True
            self._state.add_error(
                ErrorEntry(message=str(exc), tool=last_tool_name, command=transcript),
                self._config.max_error_history,
            )
            self._state.add_command(
                CommandEntry(transcript=transcript, tools_called=tools_called, success=False),
                self._config.max_command_history,
            )
            return "beep_error"

        self._state.add_command(
            CommandEntry(transcript=transcript, tools_called=tools_called, success=not errored),
            self._config.max_command_history,
        )
        return "beep_ok" if tool_called else None
