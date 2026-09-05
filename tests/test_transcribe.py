from __future__ import annotations

import base64
import json
import wave
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from universal.attachments import apply_attachments
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


def _audio_payload(tmp_path: Path, name: str = "clip.wav") -> tuple[str, str]:
    wav = tmp_path / name
    _silence_wav(wav)
    return name, base64.b64encode(wav.read_bytes()).decode("ascii")


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
    name, payload = _audio_payload(tmp_path)
    client = TestClient(create_app(platform, demo=True))
    response = client.post(
        "/v1/transcribe",
        json={"name": name, "mime": "audio/wav", "data": payload, "model": "tiny"},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "the meeting is at noon"
    assert client.get("/health").json()["whisper"] in {True, False}


def test_attachment_uses_ready_transcript_as_plain_text(
    platform: Universal, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "data"))
    agent = platform.factory.create("general", name="ears")
    platform.factory.start(agent.id)
    name, payload = _audio_payload(tmp_path)
    client = TestClient(create_app(platform, demo=True))
    response = client.post(
        f"/v1/agents/{agent.id}/ask",
        json={
            "prompt": "listen",
            "attachments": [
                {
                    "name": name,
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
    assert user["content"] == "listen\n\nplease schedule Friday"
    assert "Attached audio" not in user["content"]
    assert "Transcript:" not in user["content"]


def test_attachment_does_not_duplicate_transcript_already_in_prompt(
    platform: Universal, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "data"))
    agent = platform.factory.create("general", name="ears-dup")
    platform.factory.start(agent.id)
    name, payload = _audio_payload(tmp_path)
    spoken = "please schedule Friday"
    client = TestClient(create_app(platform, demo=True))
    response = client.post(
        f"/v1/agents/{agent.id}/ask",
        json={
            "prompt": spoken,
            "attachments": [
                {
                    "name": name,
                    "mime": "audio/wav",
                    "kind": "audio",
                    "data": payload,
                    "transcript": spoken,
                }
            ],
        },
    )
    assert response.status_code == 200
    user = next(turn for turn in response.json()["history"] if turn["role"] == "user")
    assert user["content"] == spoken
    assert user["content"].count(spoken) == 1
    assert "Attached audio" not in user["content"]
    assert "Transcript:" not in user["content"]


def test_apply_attachments_audio_is_plain_trimmed_and_keeps_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UNIVERSAL_USER_DATA", str(tmp_path / "data"))
    name, payload = _audio_payload(tmp_path)
    agent = SimpleNamespace(id="agent-a", plugins=SimpleNamespace(all=lambda: []))

    plain = apply_attachments(
        agent,
        "  note  ",
        [{"name": name, "mime": "audio/wav", "kind": "audio", "data": payload, "transcript": "  hi there  "}],
    )
    assert plain == "note\n\nhi there"
    assert "Attached audio" not in plain
    assert "Transcript:" not in plain

    duplicated = apply_attachments(
        agent,
        "hi there",
        [{"name": name, "mime": "audio/wav", "kind": "audio", "data": payload, "transcript": "hi there"}],
    )
    assert duplicated == "hi there"

    appended = apply_attachments(
        agent,
        "listen hi there",
        [{"name": name, "mime": "audio/wav", "kind": "audio", "data": payload, "transcript": "hi there"}],
    )
    assert appended == "listen hi there"

    errored = apply_attachments(
        agent,
        "listen",
        [
            {
                "name": name,
                "mime": "audio/wav",
                "kind": "audio",
                "data": payload,
                "transcript": "Error: openai-whisper is not installed. Solution: pip install 'universal[media]'",
            }
        ],
    )
    assert errored.startswith("listen\n\nError:")
    assert "openai-whisper is not installed" in errored
    assert "Attached audio" not in errored
    assert "Transcript:" not in errored


def test_health_reports_whisper_flag(platform: Universal) -> None:
    body = TestClient(create_app(platform, demo=True)).get("/health").json()
    assert "whisper" in body
    assert isinstance(body["whisper"], bool)
