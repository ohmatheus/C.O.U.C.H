#!/usr/bin/env python3
"""Generate beep WAV files for audio feedback.

Usage:
    python generate_beeps.py              # regenerate all beeps
    python generate_beeps.py beep_ok      # regenerate one beep

Called automatically by install.sh. Also usable standalone to
customize tones — edit the BEEPS dict below.
"""

import math
import struct
import sys
import wave
from pathlib import Path

_ASSETS = Path(__file__).parent

SAMPLE_RATE = 44100

BEEPS: dict[str, tuple[float, float]] = {
    "beep_ready": (880.0, 0.15),   # high pitch — "listening"
    "beep_ok":    (660.0, 0.12),   # mid pitch  — "done"
    "beep_error": (330.0, 0.25),   # low pitch  — "error"
    "beep_close": (520.0, 0.20),   # falling pitch — "session closed"
}


def _sine_wave(freq: float, duration: float, sample_rate: int) -> bytes:
    n = int(sample_rate * duration)
    samples = [
        int(32767 * math.sin(2 * math.pi * freq * t / sample_rate))
        for t in range(n)
    ]
    return struct.pack(f"<{n}h", *samples)


def generate(name: str) -> None:
    freq, duration = BEEPS[name]
    data = _sine_wave(freq, duration, SAMPLE_RATE)
    path = _ASSETS / f"{name}.wav"
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(data)
    print(f"generated {path}")


def main() -> None:
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(BEEPS)
    for name in targets:
        if name not in BEEPS:
            print(f"unknown beep: {name!r}  (choices: {', '.join(BEEPS)})", file=sys.stderr)
            sys.exit(1)
        generate(name)


if __name__ == "__main__":
    main()
