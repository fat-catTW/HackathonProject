"""Speech-to-text adapter for MediaTek Breeze-ASR-26."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal
import wave

from ..config import get_settings

SpeechLanguage = Literal["zh", "nan"]


class SpeechAsrUnavailable(RuntimeError):
    """Raised when the ASR runtime dependency is not installed or cannot load."""


def _read_wav(audio_path: str) -> dict:
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - numpy is a runtime dependency
        raise SpeechAsrUnavailable("numpy is required to read WAV audio without ffmpeg.") from exc

    with wave.open(audio_path, "rb") as wav:
        sample_rate = wav.getframerate()
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())

    if sample_width != 2:
        raise SpeechAsrUnavailable("Only 16-bit PCM WAV audio is supported without ffmpeg.")

    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    if sample_rate != 16000:
        target_rate = 16000
        target_length = int(round(audio.shape[0] * target_rate / sample_rate))
        source_positions = np.linspace(0, audio.shape[0] - 1, num=target_length)
        audio = np.interp(source_positions, np.arange(audio.shape[0]), audio).astype(np.float32)
        sample_rate = target_rate
    return {"array": audio, "sampling_rate": sample_rate}


@lru_cache(maxsize=1)
def _load_pipeline():
    settings = get_settings()
    try:
        import torch
        from transformers import pipeline
    except ImportError as exc:  # pragma: no cover - depends on optional runtime packages
        raise SpeechAsrUnavailable(
            "transformers and torch are required for MediaTek Breeze-ASR-26."
        ) from exc

    try:
        kwargs: dict = {
            "task": "automatic-speech-recognition",
            "model": settings.asr_model_id,
        }
        if settings.asr_device == "cuda":
            kwargs["device"] = 0
            kwargs["torch_dtype"] = torch.float16
        elif settings.asr_device == "auto":
            kwargs["device_map"] = "auto"
        else:
            kwargs["device"] = -1
            kwargs["torch_dtype"] = torch.float32
        return pipeline(**kwargs)
    except Exception as exc:  # pragma: no cover - model loading is environment dependent
        raise SpeechAsrUnavailable(str(exc)) from exc


def transcribe(audio_path: str, language: SpeechLanguage) -> str:
    if language == "zh":
        raise SpeechAsrUnavailable("Mandarin speech uses browser Web Speech and should not call ASR.")

    pipe = _load_pipeline()
    audio_input: str | dict = _read_wav(audio_path) if Path(audio_path).suffix.lower() == ".wav" else audio_path
    result = pipe(audio_input, generate_kwargs={"task": "transcribe"})
    if isinstance(result, dict):
        return str(result.get("text", "")).strip()
    return str(result).strip()
