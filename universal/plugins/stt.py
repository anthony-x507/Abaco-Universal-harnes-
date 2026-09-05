"""Speech-to-text via optional local Whisper. Torch is not a required dependency."""

from __future__ import annotations

from pathlib import Path

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.plugins._support import parse_tool_args

MODELS = ("tiny", "base", "small", "medium", "large")


class STTPlugin(Plugin):
    """Transcribe an audio file. Loads Whisper only when the tool is used."""

    def __init__(self) -> None:
        self._name = "stt"
        self._models: dict[str, object] = {}

    @property
    def name(self) -> str:
        return self._name

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="transcribe",
                description="Transcribe an audio file to text using local Whisper.",
                parameters={
                    "type": "object",
                    "properties": {
                        "audio_path": {"type": "string", "description": "Path to an audio file"},
                        "model": {
                            "type": "string",
                            "enum": list(MODELS),
                            "description": "Whisper model size (default: tiny)",
                        },
                    },
                    "required": ["audio_path"],
                },
            )
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name != "transcribe":
            return None
        args = parse_tool_args(call)
        audio_path = str(args.get("audio_path") or "").strip()
        model = str(args.get("model") or "tiny")
        return self._transcribe(audio_path, model)

    def _load_model(self, size: str) -> object:
        if size not in MODELS:
            size = "base"
        if size not in self._models:
            try:
                import whisper  # type: ignore[import-not-found]
            except ImportError:
                raise RuntimeError(
                    "openai-whisper is not installed. "
                    "I can try to install it with package_manager (pip, openai-whisper) after you allow it, "
                    "or run: pip install 'universal[media]'"
                ) from None
            self._models[size] = whisper.load_model(size)
        return self._models[size]

    def _audio_for_model(self, path: Path):
        if path.suffix.lower() == ".wav":
            try:
                from universal.audio_io import load_wav_mono_16k

                return load_wav_mono_16k(path)
            except Exception:
                return str(path)
        return str(path)

    def _transcribe(self, audio_path: str, model: str) -> str:
        if not audio_path:
            return "Error: audio_path is required"
        path = Path(audio_path)
        if not path.is_file():
            return f"Error: file not found: {audio_path}"
        try:
            model_obj = self._load_model(model)
            payload = self._audio_for_model(path)
            result = model_obj.transcribe(payload)  # type: ignore[union-attr]
            text = result.get("text") if isinstance(result, dict) else None
            return str(text or "").strip() or "[empty transcript]"
        except Exception as exc:
            return f"Error transcribing: {exc}"


def whisper_available() -> bool:
    try:
        import whisper  # type: ignore[import-not-found]

        return whisper is not None
    except ImportError:
        return False

