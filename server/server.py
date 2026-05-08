import asyncio
import base64
import functools
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from websockets.asyncio.server import ServerConnection, serve

from pipeline import Pipeline, load_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [server] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open() as f:
        return yaml.safe_load(f)


def _transcribe_and_log(pipeline: Pipeline, audio: np.ndarray) -> None:
    transcript = pipeline.transcribe(audio)
    if transcript:
        log.info("transcript: %s", transcript)


async def handle_client(ws: ServerConnection, pipeline: Pipeline) -> None:
    log.info("client connected: %s", ws.remote_address)
    loop = asyncio.get_running_loop()
    try:
        async for raw in ws:
            msg: dict[str, Any] = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "status":
                data: str = msg.get("data", "")
                log.info("client status: %s", data)
                if data == "listening":
                    pipeline.start()
                    await ws.send(json.dumps({"type": "feedback", "data": "beep_ok"}))

            elif msg_type == "audio":
                audio_bytes = base64.b64decode(msg["data"])
                speech = pipeline.feed(audio_bytes)
                if speech is not None:
                    loop.run_in_executor(None, _transcribe_and_log, pipeline, speech)

            else:
                log.warning("unknown message type: %s", msg_type)

    except Exception as exc:
        log.error("connection error: %s", exc)
    finally:
        log.info("client disconnected")


async def main() -> None:
    cfg = load_config()

    log.info("loading models...")
    pipeline = load_pipeline(cfg)
    log.info("models ready")

    host: str = cfg["server_host"]
    port: int = cfg["server_port"]
    log.info("starting on %s:%s", host, port)
    async with serve(functools.partial(handle_client, pipeline=pipeline), host, port):
        log.info("ready — waiting for client")
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())
