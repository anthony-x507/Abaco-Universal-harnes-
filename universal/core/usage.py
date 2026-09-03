"""Per-agent LLM usage: tokens, latency, and a fixed-price cost estimate.

This is not a billing API. Prices are a static table so ZIP exports and the
chat header stay deterministic offline. Echo / fake models cost $0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from universal.core.agent import Agent
    from universal.core.types import CompletionResponse, Message

# USD per 1K tokens: (prompt, completion). Source: public list prices, 2026-01.
MODEL_PRICES_PER_1K: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.01),
    "gpt-4.1-mini": (0.0004, 0.0016),
    "gpt-4.1": (0.002, 0.008),
    "echo": (0.0, 0.0),
    "demo-echo": (0.0, 0.0),
    "fake-model": (0.0, 0.0),
}


def estimate_tokens(text: str) -> int:
    """Rough token count when the provider did not return ``usage``."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def price_for(model: str) -> tuple[float, float]:
    if model in MODEL_PRICES_PER_1K:
        return MODEL_PRICES_PER_1K[model]
    lowered = (model or "").lower()
    if lowered.startswith("gpt-4o-mini"):
        return MODEL_PRICES_PER_1K["gpt-4o-mini"]
    if lowered.startswith("gpt-4o"):
        return MODEL_PRICES_PER_1K["gpt-4o"]
    if lowered.startswith("gpt-"):
        return MODEL_PRICES_PER_1K["gpt-4o-mini"]
    return (0.0, 0.0)


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    prompt_price, completion_price = price_for(model)
    return (prompt_tokens / 1000.0) * prompt_price + (completion_tokens / 1000.0) * completion_price


def tokens_from_response(
    response: CompletionResponse,
    messages: list[Message] | None = None,
) -> tuple[int, int]:
    raw = response.raw if isinstance(response.raw, dict) else {}
    usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    if prompt is not None:
        return int(prompt), int(completion or 0)
    prompt_text = "\n".join(message.content for message in (messages or []))
    return estimate_tokens(prompt_text), estimate_tokens(response.text)


@dataclass
class UsageStats:
    """Cumulative usage for one agent. Lives on the agent, not in the registry."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost: float = 0.0
    last_model: str = ""
    last_latency_ms: float = 0.0
    calls: int = 0

    def add(
        self,
        *,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
        latency_ms: float,
        cost: float,
    ) -> None:
        self.prompt_tokens += max(0, int(prompt_tokens))
        self.completion_tokens += max(0, int(completion_tokens))
        self.estimated_cost += max(0.0, float(cost))
        self.last_model = model
        self.last_latency_ms = max(0.0, float(latency_ms))
        self.calls += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "estimated_cost": round(self.estimated_cost, 6),
            "last_model": self.last_model,
            "last_latency_ms": round(self.last_latency_ms, 2),
            "calls": self.calls,
        }


@dataclass
class StatsCollector:
    """Optional recorder constructed on ``Universal``. Agents keep the totals."""

    prices: dict[str, tuple[float, float]] = field(default_factory=lambda: dict(MODEL_PRICES_PER_1K))

    def cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        if model in self.prices:
            prompt_price, completion_price = self.prices[model]
            return (prompt_tokens / 1000.0) * prompt_price + (completion_tokens / 1000.0) * completion_price
        return estimate_cost(model, prompt_tokens, completion_tokens)

    def record(
        self,
        agent: Agent,
        *,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
        latency_ms: float,
    ) -> None:
        cost = self.cost(model, prompt_tokens, completion_tokens)
        agent.usage.add(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            latency_ms=latency_ms,
            cost=cost,
        )


def record_provider_call(
    agent: Agent,
    response: CompletionResponse,
    *,
    messages: list[Message] | None = None,
    latency_ms: float = 0.0,
) -> None:
    prompt_tokens, completion_tokens = tokens_from_response(response, messages)
    model = response.model or getattr(agent.provider, "model", "") or ""
    cost = estimate_cost(model, prompt_tokens, completion_tokens)
    agent.usage.add(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model=model,
        latency_ms=latency_ms,
        cost=cost,
    )
