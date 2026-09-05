"""Native factory plugins: terminal, TTS, STT, vision, search, scraper."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from universal.core.agent import Agent
from universal.core.platform import Universal
from universal.core.types import ToolCall
from universal.plugins.catalog import NATIVE_PLUGIN_NAMES, merge_native_plugin_ids
from universal.plugins.scraper import ScraperPlugin
from universal.plugins.stt import STTPlugin
from universal.plugins.terminal import TerminalPlugin
from universal.plugins.tts import TTSPlugin
from universal.plugins.vision import VisionPlugin
from universal.plugins.web_search import WebSearchPlugin
from universal.providers.openai_compat import OpenAICompatProvider
from tests.conftest import FakeProvider
from tests.native_expect import NATIVE_LABELS, NATIVE_TOOL_NAMES, RESEARCHER_PLUGIN_NAMES


def _call(name: str, **kwargs: object) -> ToolCall:
    return ToolCall(id="t1", name=name, arguments=json.dumps(kwargs))


def test_every_created_agent_gets_native_plugins(platform: Universal) -> None:
    for template_id in ("general", "coder", "researcher"):
        agent = platform.factory.create(template_id, name=f"nat-{template_id}")
        names = agent.plugins.names()
        assert names[: len(NATIVE_PLUGIN_NAMES)] == list(NATIVE_PLUGIN_NAMES)
        tools = {spec.name for spec in agent.plugins.collect_tools()}
        assert set(NATIVE_TOOL_NAMES) <= tools
        if template_id == "researcher":
            assert names == list(RESEARCHER_PLUGIN_NAMES)
            assert "utc_now" in tools
        else:
            assert names == list(NATIVE_PLUGIN_NAMES)
            assert "utc_now" not in tools
            assert "tools" not in agent.plugins


def test_generator_keeps_natives_when_plugins_overridden(platform: Universal) -> None:
    agent = platform.factory.create("general", name="forced", plugins=())
    assert agent.plugins.names() == list(NATIVE_PLUGIN_NAMES)
    assert merge_native_plugin_ids(("tools",)) == (*NATIVE_PLUGIN_NAMES, "tools")


def test_terminal_echo_and_denies_destroyers() -> None:
    plugin = TerminalPlugin()
    out = plugin.invoke_tool(_call("run_command", command="echo Hello native"))
    assert out is not None
    assert "Hello native" in out
    denied = plugin.invoke_tool(_call("run_command", command="rm -rf /"))
    assert denied is not None and denied.startswith("Error:")


def test_tts_uses_argv_not_a_shell_string(monkeypatch) -> None:
    plugin = TTSPlugin()
    monkeypatch.setattr("universal.plugins.tts.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("universal.plugins.tts.sys.platform", "linux")
    captured: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        return MagicMock()

    monkeypatch.setattr("universal.plugins.tts.subprocess.run", fake_run)
    result = plugin.invoke_tool(
        _call("speak", text="hello; rm -rf /", voice="female", speed=1.5)
    )
    assert result is not None and result.startswith("Speaking:")
    argv = captured["argv"]
    assert isinstance(argv, list)
    assert argv[0].endswith("espeak-ng") or argv[0].endswith("espeak")
    assert "hello; rm -rf /" in argv
    assert "-s" in argv


def test_tts_reports_missing_engine(monkeypatch) -> None:
    plugin = TTSPlugin()
    monkeypatch.setattr("universal.plugins.tts.shutil.which", lambda _name: None)
    monkeypatch.setattr("universal.plugins.tts.sys.platform", "linux")
    result = plugin.invoke_tool(_call("speak", text="hello"))
    assert result is not None and "no TTS engine" in result


def test_stt_missing_file_and_missing_whisper(tmp_path: Path, monkeypatch) -> None:
    plugin = STTPlugin()
    missing = plugin.invoke_tool(_call("transcribe", audio_path=str(tmp_path / "none.wav")))
    assert missing is not None and "file not found" in missing
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"RIFF")

    def _missing(_size: str):
        raise RuntimeError("openai-whisper is not installed. pip install 'universal[media]'")

    monkeypatch.setattr(plugin, "_load_model", _missing)
    result = plugin.invoke_tool(_call("transcribe", audio_path=str(audio), model="tiny"))
    assert result is not None
    assert "whisper" in result.lower() or "Error transcribing" in result


def test_stt_reports_missing_ffmpeg_for_non_wav(tmp_path: Path, monkeypatch) -> None:
    plugin = STTPlugin()
    clip = tmp_path / "note.m4a"
    clip.write_bytes(b"\x00\x00\x00\x20ftyp")
    monkeypatch.setattr("universal.plugins.stt.shutil.which", lambda _name: None)
    result = plugin.invoke_tool(_call("transcribe", audio_path=str(clip)))
    assert result is not None
    assert "ffmpeg" in result and "brew install ffmpeg" in result

    wav = tmp_path / "note.wav"
    wav.write_bytes(b"RIFF")
    assert plugin._missing_ffmpeg(wav) is False


def test_vision_demo_caption_and_missing_file(tmp_path: Path) -> None:
    plugin = VisionPlugin()
    agent = Agent(name="v", provider=FakeProvider(), template_id="general")
    plugin.on_attach(agent)
    missing = plugin.invoke_tool(_call("describe_image", image_path=str(tmp_path / "no.jpg")))
    assert missing is not None and "file not found" in missing
    image = tmp_path / "shot.jpg"
    image.write_bytes(b"\xff\xd8\xff")
    caption = plugin.invoke_tool(
        _call("describe_image", image_path=str(image), prompt="What is this?")
    )
    assert caption is not None
    assert caption.startswith("(demo) image: shot.jpg")
    assert "What is this?" in caption


def test_vision_uses_provider_complete_vision(tmp_path: Path) -> None:
    class VisionFake(FakeProvider):
        def complete_vision(self, *, prompt: str, image_b64: str, mime: str = "image/jpeg") -> str:
            assert prompt == "look"
            assert image_b64
            assert mime.startswith("image/")
            return "a red square"

    plugin = VisionPlugin()
    agent = Agent(name="v", provider=VisionFake(), template_id="general")
    plugin.on_attach(agent)
    image = tmp_path / "box.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    result = plugin.invoke_tool(_call("describe_image", image_path=str(image), prompt="look"))
    assert result == "a red square"


def test_web_search_parses_mocked_ddg() -> None:
    plugin = WebSearchPlugin()
    payload = json.dumps(
        {
            "AbstractText": "Python is a language.",
            "RelatedTopics": [{"Text": "Guido van Rossum"}, {"Name": "More"}],
        }
    )
    with patch("universal.plugins.web_search.fetch_text", return_value=payload):
        result = plugin.invoke_tool(_call("search_web", query="python", max_results=2))
    assert result is not None
    assert "[Abstract] Python is a language." in result
    assert "Guido van Rossum" in result


def test_scraper_extracts_text_and_blocks_ssrf() -> None:
    plugin = ScraperPlugin()
    html = "<html><body><script>bad()</script><p>Hello scrape</p></body></html>"
    with patch("universal.plugins.scraper.assert_public_http_url", return_value="https://example.com"):
        with patch("universal.plugins.scraper.fetch_text", return_value=html):
            result = plugin.invoke_tool(_call("scrape_url", url="https://example.com"))
    assert result == "Hello scrape"
    blocked = plugin.invoke_tool(_call("scrape_url", url="http://127.0.0.1/secret"))
    assert blocked is not None and "Error scraping" in blocked
    blocked_file = plugin.invoke_tool(_call("scrape_url", url="file:///etc/passwd"))
    assert blocked_file is not None and "Error scraping" in blocked_file


def test_openai_compat_complete_vision_uses_same_client() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.payload: dict | None = None

        def post(self, url, json=None, headers=None):
            self.payload = json
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {
                "choices": [{"message": {"content": "cat on a mat"}, "finish_reason": "stop"}],
                "model": "gpt-4o",
            }
            return response

    client = FakeClient()
    provider = OpenAICompatProvider(
        base_url="http://127.0.0.1:9/v1",
        api_key="local",
        model="gpt-4o",
        client=client,  # type: ignore[arg-type]
    )
    text = provider.complete_vision(prompt="describe", image_b64="abc", mime="image/png")
    assert text == "cat on a mat"
    assert client.payload is not None
    content = client.payload["messages"][0]["content"]
    assert content[0]["text"] == "describe"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_native_plugin_labels_on_general(platform: Universal) -> None:
    agent = platform.factory.create("general", name="labels-native")
    assert agent.plugin_labels() == NATIVE_LABELS
