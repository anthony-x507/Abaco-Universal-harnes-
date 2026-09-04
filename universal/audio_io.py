"""Load a WAV as the float32 mono 16 kHz array Whisper expects, without ffmpeg."""

from __future__ import annotations

import wave
from pathlib import Path
from typing import Any

WHISPER_RATE = 16_000


def load_wav_mono_16k(path: Path) -> Any:
    import numpy as np
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        rate = wav.getframerate()
        width = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())
    if width == 2:
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif width == 4:
        audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif width == 1:
        audio = np.frombuffer(frames, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {width}")
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    if rate != WHISPER_RATE and len(audio) > 0:
        duration = len(audio) / float(rate)
        target = max(1, int(duration * WHISPER_RATE))
        old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
        new = np.linspace(0.0, 1.0, num=target, endpoint=False)
        audio = np.interp(new, old, audio).astype(np.float32)
    return np.ascontiguousarray(audio, dtype=np.float32)
