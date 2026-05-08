import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import yaml
from websockets.asyncio.client import ClientConnection, connect

logging.basicConfig(level=logging.INFO, format="%(asctime)s [client] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open() as f:
        return yaml.safe_load(f)


async def _send(ws: ClientConnection, msg: dict[str, Any]) -> None:
    await ws.send(json.dumps(msg))


async def main() -> None:
    cfg = load_config()
    url: str = cfg["server_url"]
    log.info("connecting to %s", url)

    async with connect(url) as ws:
        log.info("connected")

        await _send(ws, {"type": "ping"})
        log.info("sent ping")

        raw = await ws.recv()
        response: dict[str, Any] = json.loads(raw)
        log.info("received: %s", response)

        # stay connected — future steps will loop here
        await _send(ws, {"type": "status", "data": "ready"})
        log.info("scaffold OK — connection verified")


if __name__ == "__main__":
    asyncio.run(main())
