"""In-process wiring. Not Redis, not NATS, not a second registry.

The event log is the nervous system: notices, proofs, improvements, and
circuit trips write here. The UI reads ``GET /v1/events``.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

from universal.paths import user_data_dir

T = TypeVar("T")
MAX_EVENTS = 200


class CircuitOpen(Exception):
    """The provider circuit is open. Do not retry immediately."""


class CircuitBreaker:
    def __init__(self, name: str, *, max_failures: int = 3, reset_after: float = 30.0) -> None:
        self.name = name
        self.max_failures = max_failures
        self.reset_after = reset_after
        self.failures = 0
        self.state = "closed"
        self.next_attempt = 0.0

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "failures": self.failures,
            "max_failures": self.max_failures,
        }

    def reset(self) -> None:
        self.failures = 0
        self.state = "closed"
        self.next_attempt = 0.0

    def execute(self, fn: Callable[[], T]) -> T:
        now = time.time()
        if self.state == "open" and now < self.next_attempt:
            raise CircuitOpen(f"{self.name} is open until {self.next_attempt:.0f}")
        if self.state == "open":
            self.state = "half_open"
        try:
            result = fn()
        except Exception:
            self.failures += 1
            if self.failures >= self.max_failures:
                self.state = "open"
                self.next_attempt = now + self.reset_after
                emit("circuit.open", name=self.name, failures=self.failures)
            raise
        self.reset()
        return result


_provider_breaker = CircuitBreaker("provider")


def provider_breaker() -> CircuitBreaker:
    return _provider_breaker


def events_path() -> Path:
    return user_data_dir() / "events.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit(kind: str, **payload: Any) -> dict[str, Any]:
    row = {"at": _now(), "kind": kind, **payload}
    path = events_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def list_events(*, limit: int = 80) -> list[dict[str, Any]]:
    path = events_path()
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-max(1, min(limit, MAX_EVENTS)) :]:
        try:
            raw = json.loads(line)
        except ValueError:
            continue
        if isinstance(raw, dict):
            rows.append(raw)
    return rows


def health_snapshot() -> dict[str, Any]:
    return {
        "bus": "in-process",
        "redis": False,
        "nats": False,
        "events": len(list_events(limit=MAX_EVENTS)),
        "circuit": provider_breaker().snapshot(),
        "store": "user_data/events.jsonl + situation/ + proofs/",
    }
