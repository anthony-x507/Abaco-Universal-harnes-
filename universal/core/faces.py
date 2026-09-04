"""Stable and random faces for agents. Not a plugin."""

from __future__ import annotations

import hashlib
import random

FACES: tuple[str, ...] = (
    "💬",
    "🔎",
    "💻",
    "😊",
    "😎",
    "🤖",
    "🧠",
    "🦊",
    "🐱",
    "🦉",
    "🐲",
    "⭐",
    "🔥",
    "🌱",
    "🎯",
)


def pick_face(explicit: str | None = None) -> str:
    text = (explicit or "").strip()
    if text:
        return text
    return random.choice(FACES)


def face_for(agent_id: str, emoji: str = "") -> str:
    text = (emoji or "").strip()
    if text:
        return text
    digest = hashlib.sha256(agent_id.encode("utf-8")).digest()
    return FACES[digest[0] % len(FACES)]
