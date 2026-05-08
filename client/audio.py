import asyncio
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

SAMPLE_RATE: int = 16000
CHANNELS: int = 1
DTYPE: str = "int16"
CHUNK_SIZE: int = 1024  # samples (~64 ms at 16 kHz)

_ASSETS = Path(__file__).parent.parent / "assets"


def open_input_stream(
    queue: asyncio.Queue[bytes],
    loop: asyncio.AbstractEventLoop,
    device: str | int | None = None,
) -> sd.InputStream:
    """Open a persistent mic stream; each CHUNK_SIZE block is pushed to queue."""

    def _callback(indata: np.ndarray, _frames: int, _time: object, _status: sd.CallbackFlags) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, indata.copy().tobytes())

    return sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
        blocksize=CHUNK_SIZE,
        device=device,
        callback=_callback,
    )


def play_feedback(name: str, device: str | int | None = None) -> None:
    """Play assets/{name}.wav synchronously."""
    path = _ASSETS / f"{name}.wav"
    with wave.open(str(path)) as wf:
        rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    data = np.frombuffer(raw, dtype=np.int16)
    sd.play(data, samplerate=rate, device=device)
    sd.wait()
