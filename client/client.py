import argparse
import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import Any

import yaml
from websockets.asyncio.client import ClientConnection, connect

from audio import CHUNK_SIZE, SAMPLE_RATE, open_input_stream, play_feedback

logging.basicConfig(level=logging.INFO, format="%(asctime)s [client] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open() as f:
        return yaml.safe_load(f)


async def _send(ws: ClientConnection, msg: dict[str, Any]) -> None:
    await ws.send(json.dumps(msg))


async def _stream_audio(ws: ClientConnection, device: str | int | None) -> None:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[bytes] = asyncio.Queue()
    log.info("mic open — streaming %d-sample chunks at %d Hz", CHUNK_SIZE, SAMPLE_RATE)
    with open_input_stream(queue, loop, device):
        while True:
            chunk = await queue.get()
            encoded = base64.b64encode(chunk).decode()
            await _send(ws, {"type": "audio", "data": encoded})


async def _receive_feedback(ws: ClientConnection, device: str | int | None) -> None:
    loop = asyncio.get_running_loop()
    async for raw in ws:
        msg: dict[str, Any] = json.loads(raw)
        msg_type = msg.get("type")
        if msg_type == "feedback":
            name: str = msg["data"]
            log.info("feedback: %s", name)
            await loop.run_in_executor(None, play_feedback, name, device)
        elif msg_type == "status":
            log.info("server status: %s", msg.get("data"))
        else:
            log.warning("unknown message type: %s", msg_type)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-wake", action="store_true", help="skip wake word (dev mode)")
    args = parser.parse_args()

    cfg = load_config()
    url: str = cfg["server_url"]

    input_device: str | None = cfg.get("input_device") or None
    feedback_device: str | None = cfg.get("feedback_device") or None
    if input_device == "default":
        input_device = None
    if feedback_device == "default":
        feedback_device = None

    log.info("connecting to %s", url)
    async with connect(url) as ws:
        log.info("connected")
        await _send(ws, {"type": "status", "data": "ready"})

        if not args.no_wake:
            log.info("wake word not yet implemented — use --no-wake to stream directly")
            return

        send_task = asyncio.create_task(_stream_audio(ws, input_device))
        recv_task = asyncio.create_task(_receive_feedback(ws, feedback_device))
        try:
            await asyncio.gather(send_task, recv_task)
        except asyncio.CancelledError:
            pass
        finally:
            send_task.cancel()
            recv_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
