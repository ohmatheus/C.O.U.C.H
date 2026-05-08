import logging
from typing import Any

import numpy as np
import torch
from faster_whisper import WhisperModel
from silero_vad import VADIterator, load_silero_vad

log = logging.getLogger(__name__)

_SAMPLE_RATE: int = 16000
_VAD_CHUNK: int = 512  # samples — Silero VAD requirement at 16kHz
_VAD_CHUNK_BYTES: int = _VAD_CHUNK * 2  # int16 = 2 bytes per sample


class Pipeline:
    """Silero VAD → faster-whisper STT pipeline for one server session."""

    def __init__(
        self,
        whisper: WhisperModel,
        vad_model: torch.nn.Module,
        language: str,
        vad_threshold: float = 0.3,
        min_silence_ms: int = 800,
    ) -> None:
        self._whisper = whisper
        self._language = language
        self._vad_iter = VADIterator(
            vad_model,
            threshold=vad_threshold,
            sampling_rate=_SAMPLE_RATE,
            min_silence_duration_ms=min_silence_ms,
        )
        self._speech_buffer: list[np.ndarray] = []
        self._in_speech: bool = False
        self._leftover: bytes = b""

    def start(self) -> None:
        """Reset state for a new session."""
        self._vad_iter.reset_states()
        self._speech_buffer.clear()
        self._in_speech = False
        self._leftover = b""

    def feed(self, raw: bytes) -> np.ndarray | None:
        """Feed a raw int16 audio chunk. Returns speech audio when an utterance ends."""
        data = self._leftover + raw
        offset = 0
        result: np.ndarray | None = None

        while offset + _VAD_CHUNK_BYTES <= len(data):
            chunk_bytes = data[offset : offset + _VAD_CHUNK_BYTES]
            offset += _VAD_CHUNK_BYTES

            arr = np.frombuffer(chunk_bytes, dtype=np.int16)
            tensor = torch.from_numpy(arr.copy()).float() / 32768.0
            event: dict[str, int] | None = self._vad_iter(tensor, return_seconds=False)

            if event and "start" in event:
                self._in_speech = True
                self._speech_buffer.clear()

            if self._in_speech:
                self._speech_buffer.append(arr)

            if event and "end" in event:
                self._in_speech = False
                if self._speech_buffer:
                    result = np.concatenate(self._speech_buffer)
                    self._speech_buffer.clear()

        self._leftover = data[offset:]
        return result

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe an int16 audio array. Blocking — run in executor."""
        audio_f32 = audio.astype(np.float32) / 32768.0
        segments, _ = self._whisper.transcribe(
            audio_f32,
            language=self._language,
            beam_size=5,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()


def load_pipeline(config: dict[str, Any]) -> Pipeline:
    log.info("loading Silero VAD...")
    vad_model = load_silero_vad()

    model_name: str = config["whisper_model"]
    device: str = config.get("whisper_device", "cpu")
    compute_type = "int8" if device == "cpu" else "int8_float16"
    log.info("loading faster-whisper %s on %s...", model_name, device)
    whisper = WhisperModel(model_name, device=device, compute_type=compute_type)

    language: str = config.get("language", "fr")
    return Pipeline(whisper, vad_model, language)
