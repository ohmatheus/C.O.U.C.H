import argparse
import asyncio
import base64
import contextlib
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from openwakeword.model import Model as WakeWordModel
from websockets.asyncio.client import ClientConnection, connect

from audio import CHUNK_SIZE, SAMPLE_RATE, open_input_stream, play_feedback

logging.basicConfig(level=logging.INFO, format="%(asctime)s [client] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

_WAKE_THRESHOLD: float = 0.5


def load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open() as f:
        return yaml.safe_load(f)


def _load_wakeword_model(wake_word: str) -> WakeWordModel:
    return WakeWordModel(
        wakeword_models=[wake_word],
        inference_framework="onnx",
        enable_speex_noise_suppression=False,
    )


async def _send(ws: ClientConnection, msg: dict[str, Any]) -> None:
    await ws.send(json.dumps(msg))


async def _wait_for_wake_word(audio_q: asyncio.Queue[bytes], oww: WakeWordModel) -> None:
    while True:
        chunk = await audio_q.get()
        arr = np.frombuffer(chunk, dtype=np.int16)
        prediction: dict[str, float] = oww.predict(arr)
        if any(score >= _WAKE_THRESHOLD for score in prediction.values()):
            return


async def _stream_from_queue(ws: ClientConnection, audio_q: asyncio.Queue[bytes]) -> None:
    while True:
        chunk = await audio_q.get()
        encoded = base64.b64encode(chunk).decode()
        await _send(ws, {"type": "audio", "data": encoded})


async def _stream_audio(ws: ClientConnection, device: str | int | None) -> None:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[bytes] = asyncio.Queue()
    log.info("mic open — streaming %d-sample chunks at %d Hz", CHUNK_SIZE, SAMPLE_RATE)
    with open_input_stream(queue, loop, device):
        while True:
            chunk = await queue.get()
            encoded = base64.b64encode(chunk).decode()
            await _send(ws, {"type": "audio", "data": encoded})


async def _receive_feedback(
    ws: ClientConnection,
    device: str | int | None,
    session_end: asyncio.Event | None = None,
) -> None:
    loop = asyncio.get_running_loop()
    async for raw in ws:
        msg: dict[str, Any] = json.loads(raw)
        msg_type = msg.get("type")
        if msg_type == "feedback":
            name: str = msg["data"]
            log.info("feedback: %s", name)
            await loop.run_in_executor(None, play_feedback, name, device)
        elif msg_type == "session_end":
            log.info("session closed by server")
            await loop.run_in_executor(None, play_feedback, "beep_close", device)
            if session_end is not None:
                session_end.set()
            return
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

        if args.no_wake:
            send_task = asyncio.create_task(_stream_audio(ws, input_device))
            recv_task = asyncio.create_task(_receive_feedback(ws, feedback_device))
            try:
                await asyncio.gather(send_task, recv_task)
            except asyncio.CancelledError:
                pass
            finally:
                send_task.cancel()
                recv_task.cancel()
            return

        loop = asyncio.get_running_loop()
        log.info("loading wake word model: %s", cfg["wake_word"])
        oww = await loop.run_in_executor(None, _load_wakeword_model, cfg["wake_word"])
        log.info("wake word model ready — say '%s'", cfg["wake_word"])

        audio_q: asyncio.Queue[bytes] = asyncio.Queue()
        with open_input_stream(audio_q, loop, input_device):
            while True:
                await _wait_for_wake_word(audio_q, oww)

                log.info("wake word detected — session open")
                await loop.run_in_executor(None, play_feedback, "beep_ready", feedback_device)
                await _send(ws, {"type": "status", "data": "listening"})

                session_end = asyncio.Event()
                stream_task = asyncio.create_task(_stream_from_queue(ws, audio_q))
                recv_task = asyncio.create_task(_receive_feedback(ws, feedback_device, session_end))

                _, pending = await asyncio.wait(
                    [stream_task, recv_task], return_when=asyncio.FIRST_COMPLETED
                )
                for t in pending:
                    t.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await t

                # Discard buffered audio and reset all OWW internal state
                # (mel-spectrogram buffer, embeddings, prediction scores) so
                # the session's audio doesn't immediately re-trigger detection.
                while not audio_q.empty():
                    audio_q.get_nowait()
                oww.reset()

                await _send(ws, {"type": "status", "data": "ready"})
                log.info("session closed — listening for wake word...")


if __name__ == "__main__":
    asyncio.run(main())
