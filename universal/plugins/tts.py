"""Text-to-speech with voice and speed. Uses the OS speech engine when present."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

from universal.core.plugin import Plugin
from universal.core.types import ToolCall, ToolSpec
from universal.plugins._support import parse_tool_args

VOICES = ("default", "male", "female")
SPEEDS = (0.5, 0.8, 1.0, 1.2, 1.5, 2.0)
MAC_VOICES = {"male": "Alex", "female": "Victoria", "default": "Alex"}
LINUX_VOICES = {"male": "en+m3", "female": "en+f3", "default": "en"}


class TTSPlugin(Plugin):
    """Speak text. Never interpolates the text into a shell string."""

    def __init__(self) -> None:
        self._name = "tts"

    @property
    def name(self) -> str:
        return self._name

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="speak",
                description="Speak text aloud with optional voice (male/female/default) and speed.",
                parameters={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to speak"},
                        "voice": {
                            "type": "string",
                            "enum": list(VOICES),
                            "description": "Voice type (male, female, default)",
                        },
                        "speed": {
                            "type": "number",
                            "enum": list(SPEEDS),
                            "description": "Speaking speed (0.5 = slow, 2.0 = fast)",
                        },
                    },
                    "required": ["text"],
                },
            )
        ]

    def invoke_tool(self, call: ToolCall) -> str | None:
        if call.name != "speak":
            return None
        args = parse_tool_args(call)
        text = str(args.get("text") or "").strip()
        if not text:
            return "Error: text is required"
        voice = str(args.get("voice") or "default")
        if voice not in VOICES:
            voice = "default"
        try:
            speed = float(args.get("speed") if args.get("speed") is not None else 1.0)
        except (TypeError, ValueError):
            speed = 1.0
        if speed not in SPEEDS:
            nearest = min(SPEEDS, key=lambda value: abs(value - speed))
            speed = nearest
        return self._speak(text, voice, speed)

    def _speak(self, text: str, voice: str, speed: float) -> str:
        try:
            if sys.platform == "darwin":
                return self._speak_macos(text, voice, speed)
            if sys.platform.startswith("linux"):
                return self._speak_linux(text, voice, speed)
            if os.name == "nt":
                return self._speak_windows(text, voice, speed)
            return "Error: TTS is not supported on this OS"
        except Exception as exc:
            return f"Error speaking: {exc}"

    def _speak_macos(self, text: str, voice: str, speed: float) -> str:
        if not shutil.which("say"):
            return "Error: no TTS engine found (install macOS 'say')"
        rate = max(80, int(speed * 175))
        self._run(["say", "-v", MAC_VOICES[voice], "-r", str(rate), text])
        return f"Speaking: {text} (voice={voice}, speed={speed}x)"

    def _speak_linux(self, text: str, voice: str, speed: float) -> str:
        espeak = shutil.which("espeak-ng") or shutil.which("espeak")
        if espeak:
            wpm = max(80, int(speed * 175))
            self._run([espeak, "-s", str(wpm), "-v", LINUX_VOICES[voice], text])
            return f"Speaking: {text} (voice={voice}, speed={speed}x)"
        spd = shutil.which("spd-say")
        if spd:
            rate = max(-100, min(100, int((speed - 1.0) * 100)))
            self._run([spd, "-r", str(rate), text])
            return f"Speaking: {text} (voice={voice}, speed={speed}x)"
        return "Error: no TTS engine found (install espeak-ng, espeak, or speech-dispatcher)"

    def _speak_windows(self, text: str, voice: str, speed: float) -> str:
        rate = max(-10, min(10, int((speed - 1.0) * 10)))
        gender = "female" if voice == "female" else "male"
        script = (
            "$speak = New-Object -ComObject SAPI.SpVoice; "
            "$voices = @($speak.GetVoices()); "
            f"if ($voices.Count -gt 1 -and '{gender}' -eq 'female') {{ $speak.Voice = $voices[1] }}; "
            f"$speak.Rate = {rate}; "
            "$speak.Speak([Console]::In.ReadToEnd())"
        )
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if not powershell:
            return "Error: no TTS engine found (PowerShell / SAPI)"
        self._run([powershell, "-NoProfile", "-Command", script], input_text=text)
        return f"Speaking: {text} (voice={voice}, speed={speed}x)"

    @staticmethod
    def _run(argv: list[str], *, input_text: str | None = None) -> None:
        subprocess.run(
            argv,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
            input=input_text,
        )
