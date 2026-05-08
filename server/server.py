import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import yaml
from websockets.asyncio.server import ServerConnection, serve

logging.basicConfig(level=logging.INFO, format="%(asctime)s [server] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open() as f:
        return yaml.safe_load(f)


async def _send(ws: ServerConnection, msg: dict[str, Any]) -> None:
    await ws.send(json.dumps(msg))


async def handle_client(ws: ServerConnection) -> None:
    log.info("client connected: %s", ws.remote_address)
    try:
        async for raw in ws:
            msg: dict[str, Any] = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "ping":
                await _send(ws, {"type": "pong"})
            elif msg_type == "audio":
                # stub — will route to pipeline in step 2
                log.info("audio bytes received: %d bytes", len(msg.get("data", "")))
            elif msg_type == "status":
                log.info("client status: %s", msg.get("data"))
            else:
                log.warning("unknown message type: %s", msg_type)

    except Exception as exc:
        log.error("connection error: %s", exc)
    finally:
        log.info("client disconnected")


async def main() -> None:
    cfg = load_config()
    host: str = cfg["server_host"]
    port: int = cfg["server_port"]
    log.info("starting on %s:%s", host, port)
    async with serve(handle_client, host, port):
        log.info("ready — waiting for client")
        await asyncio.get_running_loop().create_future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
