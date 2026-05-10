import asyncio
import base64
import functools
import json
import logging
from pathlib import Path
from typing import Any

import yaml
from agent import Agent
from llm import create_provider
from pipeline import Pipeline, load_pipeline
from state import APP_STATE
from tools.browser_manager import BROWSER
from websockets.asyncio.server import ServerConnection, serve

logging.basicConfig(level=logging.INFO, format="%(asctime)s [server] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open() as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


async def handle_client(
    ws: ServerConnection, pipeline: Pipeline, agent: Agent, session_timeout: int
) -> None:
    log.info("client connected: %s", ws.remote_address)
    loop = asyncio.get_running_loop()
    idle_task: asyncio.Task[None] | None = None

    async def _fire_idle() -> None:
        await asyncio.sleep(session_timeout)
        log.info("idle timeout — closing session")
        await ws.send(json.dumps({"type": "session_end"}))

    def _reset_idle() -> None:
        nonlocal idle_task
        if idle_task is not None:
            idle_task.cancel()
        idle_task = asyncio.create_task(_fire_idle())

    def _cancel_idle() -> None:
        nonlocal idle_task
        if idle_task is not None:
            idle_task.cancel()
            idle_task = None

    try:
        async for raw in ws:
            msg: dict[str, Any] = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "status":
                data: str = msg.get("data", "")
                log.info("client status: %s", data)
                if data == "listening":
                    pipeline.start()
                    _reset_idle()
                    await ws.send(json.dumps({"type": "feedback", "data": "beep_ok"}))

            elif msg_type == "audio":
                audio_bytes = base64.b64decode(msg["data"])
                speech = pipeline.feed(audio_bytes)
                if speech is not None:
                    transcript = await loop.run_in_executor(None, pipeline.transcribe, speech)
                    _reset_idle()
                    if transcript:
                        log.info("transcript: %s", transcript)
                        feedback = await loop.run_in_executor(None, agent.run, transcript)
                        if feedback == "session_end":
                            log.info("session closed by agent")
                            _cancel_idle()
                            await ws.send(json.dumps({"type": "session_end"}))
                        elif feedback is not None:
                            await ws.send(json.dumps({"type": "feedback", "data": feedback}))

            else:
                log.warning("unknown message type: %s", msg_type)

    except Exception as exc:
        log.error("connection error: %s", exc)
    finally:
        _cancel_idle()
        log.info("client disconnected")


async def main() -> None:
    cfg = load_config()

    log.info("loading models...")
    pipeline = load_pipeline(cfg)
    log.info("models ready")

    provider = create_provider(cfg)
    agent = Agent(
        provider=provider,
        language=cfg.get("language", "en"),
        state=APP_STATE,
    )

    session_timeout: int = cfg.get("session_timeout", 30)

    chrome_path_cfg: str = cfg.get("browser_chrome_path", "auto")
    if chrome_path_cfg == "auto":
        from tools.browser_manager import find_chrome
        chrome_path: str | None = find_chrome()
        log.info("browser: %s", chrome_path or "Playwright's bundled Chromium")
    elif chrome_path_cfg == "playwright":
        chrome_path = None
    else:
        chrome_path = chrome_path_cfg
    BROWSER.configure(chrome_path=chrome_path)

    from tools.browser import configure as configure_browser
    configure_browser(search_limit=cfg.get("browser_search_limit", 10))

    host: str = cfg["server_host"]
    port: int = cfg["server_port"]
    log.info("starting on %s:%s", host, port)
    handler = functools.partial(handle_client, pipeline=pipeline, agent=agent, session_timeout=session_timeout)
    try:
        async with serve(handler, host, port):
            log.info("ready — waiting for client")
            await asyncio.get_running_loop().create_future()
    finally:
        BROWSER.stop()


if __name__ == "__main__":
    asyncio.run(main())
