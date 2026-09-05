"""Save chat uploads and turn images/audio into text the agent can use."""

from __future__ import annotations

import base64
import json
import re
import uuid
from pathlib import Path
from typing import Any

from universal.core.types import ToolCall
from universal.documents import extract_text
from universal.paths import user_data_dir

SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def uploads_dir(agent_id: str) -> Path:
    path = user_data_dir() / "uploads" / agent_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(agent_id: str, name: str, data_b64: str) -> Path:
    raw = base64.b64decode(data_b64, validate=False)
    stem = SAFE_NAME.sub("_", Path(name).name) or "upload"
    dest = uploads_dir(agent_id) / f"{uuid.uuid4().hex[:8]}-{stem}"
    dest.write_bytes(raw)
    return dest


def _invoke(agent: Any, tool: str, **kwargs: object) -> str | None:
    call = ToolCall(id="upload", name=tool, arguments=json.dumps(kwargs))
    for plugin in agent.plugins.all():
        result = plugin.invoke_tool(call)
        if result is not None:
            return result
    return None


def _is_actionable_stt_error(text: str) -> bool:
    lowered = text.lower()
    return text.startswith("Error") or "not installed" in lowered


def _prompt_already_has_transcript(prompt: str, heard: str) -> bool:
    """True when the UI already put the transcript into the composer prompt."""
    text = prompt.strip()
    heard = heard.strip()
    if not text or not heard:
        return False
    if text == heard:
        return True
    return text.endswith(f" {heard}")


def _audio_block(prompt: str, name: str, path: Path, heard: str | None) -> str | None:
    """Return plain trimmed transcript text — never Attached/Transcript labels."""
    text = (heard or "").strip()
    if not text or text == "[empty transcript]":
        return (
            f"Error: no transcript for {name}. "
            f"Solution: retry after installing Whisper (`pip install 'universal[media]'`), "
            f"or convert the clip to .wav. Saved at {path}."
        )
    if _is_actionable_stt_error(text):
        return text
    if _prompt_already_has_transcript(prompt, text):
        return None
    return text


def apply_attachments(agent: Any, prompt: str, attachments: list[dict[str, str]]) -> str:
    """Write uploads to disk. Images go through vision; audio through STT."""
    if not attachments:
        return prompt
    blocks: list[str] = []
    for item in attachments:
        name = str(item.get("name") or "upload")
        mime = str(item.get("mime") or "")
        kind = str(item.get("kind") or "")
        data = str(item.get("data") or "")
        if not data:
            continue
        path = save_upload(agent.id, name, data)
        image = kind == "image" or mime.startswith("image/")
        audio = kind == "audio" or mime.startswith("audio/")
        if image:
            seen = _invoke(
                agent,
                "describe_image",
                image_path=str(path),
                prompt=prompt.strip() or "Describe this image in detail.",
            )
            blocks.append(f"[Attached image {name}]\n{seen or f'Saved image at {path}'}")
        elif audio:
            heard = str(item.get("transcript") or "").strip() or _invoke(
                agent, "transcribe", audio_path=str(path), model="tiny"
            )
            block = _audio_block(prompt, name, path, heard)
            if block:
                blocks.append(block)
        else:
            extracted = extract_text(path)
            if extracted:
                blocks.append(f"[Attached file {name}]\n{extracted}")
            else:
                blocks.append(f"[Attached file {name} saved at {path}]")
    extras = "\n\n".join(blocks)
    text = prompt.strip()
    if text and extras:
        return f"{text}\n\n{extras}"
    return extras or text
