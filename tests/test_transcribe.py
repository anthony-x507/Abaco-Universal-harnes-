from __future__ import annotations

import base64
import json
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from universal.core.platform import Universal
from universal.core.types import ToolCall
from universal.plugins.stt import STTPlugin
from universal.server import create_app


def _silence_wav(path: Path, frames: int = 1600) -> None:
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * frames)


def test_wav_is_passed_to_whisper_as_samples(tmp_path: Path) -> None:
    class FakeModel:
        def transcribe(self, audio):
            assert hasattr(audio, "shape")
            return {"text": " hello from whisper "}

    plugin = STTPlugin()
    plugin._load_model = lambda _size: FakeModel()  # type: ignore[method-assign]
    path = tmp_path / "clip.wav"
    _silence_wav(path)
    heard = plugin.invoke_tool(
        ToolCall(id="t", name="transcribe", arguments=json.dumps({"audio_path": str(path)}))
    )
    assert heard == "hello from whisper"


def test_transcribe_endpoint(platform: Universal, monkeypatch, tmp_path: Path) -> None:
    def fake_transcribe(self, audio_path: str, model: str) -> str:  # noqa: ARG001
        assert Path(audio_path).is_file()
        assert model == "tiny"
        return "the meeting is at noon"

    monkeypatch.setattr(STTPlugin, "_transcribe", fake_transcribe)
    wav = tmp_path / "clip.wav"
    _silence_wav(wav)
    payload = base64.b64encode(wav.read_bytes()).decode("ascii")
    client = TestClient(create_app(platform, demo=True))
    response = client.post(
        "/v1/transcribe",
        json={"name": "clip.wav", "mime": "audio/wav", "data": payload, "model": "tiny"},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "the meeting is at noon"
    assert client.get("/health").json()["whisper"] in {True, False}


def test_attachment_uses_ready_transcript(platform: Universal, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "data"))
    agent = platform.factory.create("general", name="ears")
    platform.factory.start(agent.id)
    wav = tmp_path / "clip.wav"
    _silence_wav(wav)
    payload = base64.b64encode(wav.read_bytes()).decode("ascii")
    client = TestClient(create_app(platform, demo=True))
    response = client.post(
        f"/v1/agents/{agent.id}/ask",
        json={
            "prompt": "listen",
            "attachments": [
                {
                    "name": "clip.wav",
                    "mime": "audio/wav",
                    "kind": "audio",
                    "data": payload,
                    "transcript": "please schedule Friday",
                }
            ],
        },
    )
    assert response.status_code == 200
    user = next(turn for turn in response.json()["history"] if turn["role"] == "user")
    assert "please schedule Friday" in user["content"]
    assert "Attached audio clip.wav" in user["content"]


def test_health_reports_whisper_flag(platform: Universal) -> None:
    body = TestClient(create_app(platform, demo=True)).get("/health").json()
    assert "whisper" in body
    assert isinstance(body["whisper"], bool)
