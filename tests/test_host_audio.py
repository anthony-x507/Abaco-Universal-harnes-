"""Host recorder fallback used when the webview has no getUserMedia."""

from __future__ import annotations

import base64
import sys
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.host_audio import HostAudioError, HostRecorder
from universal.server import create_app


def _silence_wav(path: Path, frames: int = 1600) -> None:
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * frames)


def test_host_recorder_writes_wav_via_command() -> None:
    def fake_command(dest: Path) -> list[str]:
        _silence_wav(dest)
        return [sys.executable, "-c", "import time; time.sleep(30)"]

    recorder = HostRecorder()
    recorder._start_avfoundation = lambda _dest: False  # type: ignore[method-assign]
    recorder._command = fake_command  # type: ignore[method-assign]
    recorder.start()
    assert recorder.recording()
    data = recorder.stop()
    assert data[:4] == b"RIFF"
    assert len(data) > 44
    assert not recorder.recording()


def test_host_recorder_rejects_double_start(monkeypatch) -> None:
    recorder = HostRecorder()
    recorder._av_recorder = object()
    try:
        recorder.start()
        raise AssertionError("expected HostAudioError")
    except HostAudioError as exc:
        assert "already" in str(exc).lower()
    finally:
        recorder._av_recorder = None


def test_record_endpoints(platform: Universal, monkeypatch, tmp_path: Path) -> None:
    wav = tmp_path / "clip.wav"
    _silence_wav(wav)
    started = {"n": 0}

    def fake_start() -> None:
        started["n"] += 1

    def fake_stop() -> bytes:
        return wav.read_bytes()

    monkeypatch.setattr("universal.host_audio.start_host_recording", fake_start)
    monkeypatch.setattr("universal.host_audio.stop_host_recording", fake_stop)
    client = TestClient(create_app(platform, demo=True))
    start = client.post("/v1/record/start")
    assert start.status_code == 200
    assert start.json()["status"] == "recording"
    assert started["n"] == 1
    stop = client.post("/v1/record/stop")
    assert stop.status_code == 200
    body = stop.json()
    assert body["name"] == "clip.wav"
    assert body["mime"] == "audio/wav"
    assert base64.b64decode(body["data"])[:4] == b"RIFF"
