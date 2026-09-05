"""Hide model ``<think>`` reasoning from users, history, and streams.

Qwen/DeepSeek-style models emit reasoning inside ``<think>...</think>``.
Those tags are often split across SSE chunks, so a per-chunk regex is not
enough. This module is the single stripper: incremental for streams, and a
plain function for complete strings.
"""

from __future__ import annotations

from universal.core.types import CompletionResponse

OPEN_TAG = "<think>"
CLOSE_TAG = "</think>"


def _find_ci(haystack: str, needle: str) -> int:
    return haystack.lower().find(needle.lower())


def _holdback_len(buffer: str, tag: str) -> int:
    """How many trailing chars might still grow into ``tag``."""
    lowered = buffer.lower()
    target = tag.lower()
    max_n = min(len(lowered), len(target) - 1)
    for size in range(max_n, 0, -1):
        if lowered.endswith(target[:size]):
            return size
    return 0


class ThinkStreamFilter:
    """Stateful filter for token deltas. Drop reasoning; emit visible text."""

    def __init__(self) -> None:
        self._buf = ""
        self._hidden = False
        self._visible = ""

    @property
    def text(self) -> str:
        return self._visible

    def feed(self, chunk: str) -> str:
        if not chunk:
            return ""
        self._buf += chunk
        visible = self._drain(finalize=False)
        self._visible += visible
        return visible

    def flush(self) -> str:
        visible = self._drain(finalize=True)
        self._visible += visible
        return visible

    def _drain(self, *, finalize: bool) -> str:
        out: list[str] = []
        while self._buf:
            if self._hidden:
                idx = _find_ci(self._buf, CLOSE_TAG)
                if idx >= 0:
                    self._buf = self._buf[idx + len(CLOSE_TAG) :]
                    self._hidden = False
                    continue
                if finalize:
                    self._buf = ""
                    break
                keep = _holdback_len(self._buf, CLOSE_TAG)
                self._buf = self._buf[-keep:] if keep else ""
                break
            idx = _find_ci(self._buf, OPEN_TAG)
            if idx >= 0:
                out.append(self._buf[:idx])
                self._buf = self._buf[idx + len(OPEN_TAG) :]
                self._hidden = True
                continue
            if finalize:
                out.append(self._buf)
                self._buf = ""
                break
            keep = _holdback_len(self._buf, OPEN_TAG)
            if keep:
                out.append(self._buf[:-keep])
                self._buf = self._buf[-keep:]
            else:
                out.append(self._buf)
                self._buf = ""
            break
        return "".join(out)


def strip_think_tags(text: str) -> str:
    """Remove complete and unclosed ``<think>`` blocks from ``text``."""
    if not text or "<" not in text:
        return text
    filter_ = ThinkStreamFilter()
    return filter_.feed(text) + filter_.flush()


def apply_to_response(response: CompletionResponse) -> CompletionResponse:
    """Return ``response`` with thinking tags stripped from ``text``."""
    cleaned = strip_think_tags(response.text)
    if cleaned == response.text:
        return response
    return CompletionResponse(
        text=cleaned,
        tool_calls=list(response.tool_calls),
        model=response.model,
        finish_reason=response.finish_reason,
        raw=response.raw,
    )
