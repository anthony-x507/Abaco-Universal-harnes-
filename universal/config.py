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
    directly in tests. The live key may live in user-data ``llm.json``
    (mode 0600). The packager never copies that file into a ZIP.
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
        from universal.llm_store import load_llm_settings

        persisted = load_llm_settings()
        env_url = os.environ.get(ENV_BASE_URL, "").strip()
        env_key = os.environ.get(ENV_API_KEY, "").strip()
        env_model = os.environ.get(ENV_MODEL, "").strip()
        env_org = os.environ.get(ENV_ORGANIZATION, "").strip()
        persisted_timeout = persisted.get("llm_timeout")
        if not timeout_raw and isinstance(persisted_timeout, (int, float)):
            timeout = float(persisted_timeout)
        return cls(
            llm_base_url=env_url or str(persisted.get("llm_base_url") or "").strip() or DEFAULT_BASE_URL,
            llm_api_key=env_key or str(persisted.get("llm_api_key") or "").strip(),
            llm_model=env_model or str(persisted.get("llm_model") or "").strip() or DEFAULT_MODEL,
            llm_timeout=timeout,
            llm_organization=env_org or str(persisted.get("llm_organization") or "").strip(),
        )

    def with_updates(
        self,
        *,
        llm_base_url: str | None = None,
        llm_api_key: str | None = None,
        llm_model: str | None = None,
        llm_timeout: float | None = None,
        llm_organization: str | None = None,
    ) -> Settings:
        """Return a copy with selected fields replaced. Empty API key keeps the current key."""
        return Settings(
            llm_base_url=llm_base_url.strip() if llm_base_url else self.llm_base_url,
            llm_api_key=llm_api_key.strip() if llm_api_key is not None and llm_api_key.strip() else self.llm_api_key,
            llm_model=llm_model.strip() if llm_model else self.llm_model,
            llm_timeout=llm_timeout if llm_timeout is not None else self.llm_timeout,
            llm_organization=llm_organization.strip() if llm_organization is not None else self.llm_organization,
        )

    def require_live(self) -> None:
        """Raise if this settings object cannot make a live provider call."""
        from universal.providers.catalog import is_local_base_url

        missing: list[str] = []
        if not self.llm_base_url:
            missing.append(ENV_BASE_URL)
        if not self.llm_api_key and not is_local_base_url(self.llm_base_url):
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
