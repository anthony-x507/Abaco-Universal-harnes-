"""Runtime settings loaded from environment variables. No secrets in the repo."""

from __future__ import annotations

import os
from dataclasses import dataclass

from universal.exceptions import ConfigError

ENV_BASE_URL = "UNIVERSAL_LLM_BASE_URL"
ENV_API_KEY = "UNIVERSAL_LLM_API_KEY"
ENV_MODEL = "UNIVERSAL_LLM_MODEL"
ENV_TIMEOUT = "UNIVERSAL_LLM_TIMEOUT"
ENV_ORGANIZATION = "UNIVERSAL_LLM_ORGANIZATION"

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT = 60.0


@dataclass(frozen=True, slots=True)
class Settings:
    """OpenAI-compatible HTTP client settings.

    Construct with ``Settings.from_env()`` for live use, or pass values
    directly in tests. The API key is never written to disk by the packager.
    """

    llm_base_url: str = DEFAULT_BASE_URL
    llm_api_key: str = ""
    llm_model: str = DEFAULT_MODEL
    llm_timeout: float = DEFAULT_TIMEOUT
    llm_organization: str = ""

    @classmethod
    def from_env(cls) -> Settings:
        timeout_raw = os.environ.get(ENV_TIMEOUT, "").strip()
        try:
            timeout = float(timeout_raw) if timeout_raw else DEFAULT_TIMEOUT
        except ValueError as exc:
            raise ConfigError(f"{ENV_TIMEOUT} must be a number, got {timeout_raw!r}") from exc
        return cls(
            llm_base_url=os.environ.get(ENV_BASE_URL, DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL,
            llm_api_key=os.environ.get(ENV_API_KEY, "").strip(),
            llm_model=os.environ.get(ENV_MODEL, DEFAULT_MODEL).strip() or DEFAULT_MODEL,
            llm_timeout=timeout,
            llm_organization=os.environ.get(ENV_ORGANIZATION, "").strip(),
        )

    def require_live(self) -> None:
        """Raise if this settings object cannot make a live provider call."""
        missing: list[str] = []
        if not self.llm_base_url:
            missing.append(ENV_BASE_URL)
        if not self.llm_api_key:
            missing.append(ENV_API_KEY)
        if not self.llm_model:
            missing.append(ENV_MODEL)
        if missing:
            raise ConfigError(
                "Live completions need "
                + ", ".join(missing)
                + ". See README and .env.example."
            )

    def public_dict(self) -> dict[str, str | float]:
        """Serialize settings with the API key redacted — safe for ZIP manifests."""
        return {
            "llm_base_url": self.llm_base_url,
            "llm_api_key": "***" if self.llm_api_key else "",
            "llm_model": self.llm_model,
            "llm_timeout": self.llm_timeout,
            "llm_organization": self.llm_organization,
        }
