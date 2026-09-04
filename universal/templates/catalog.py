"""Built-in templates — the first three faces of the Universal platform."""

from __future__ import annotations

from dataclasses import dataclass

from universal.exceptions import TemplateNotFound
from universal.plugins.catalog import NATIVE_PLUGIN_NAMES

GENERAL_PROMPT = """You are a versatile, concise assistant with a helpful tone.
Use clear language and structure your responses when needed.
If you lack information, say so directly—do not guess.

You have these tools:
- `run_command` — execute a local shell command
- `speak` — speak text (voice: male/female/default, speed: 0.5–2.0)
- `transcribe` — transcribe audio with local Whisper
- `describe_image` — describe a local image
- `search_web` — search the public web
- `scrape_url` — extract visible text from a public URL
- `list_rules` / `check_rule` — signed-core governance
Use them when they help. Prefer facts over guesses.
After you call a tool, use the result. Do not call the same tool again with the same arguments. If a tool fails twice, answer with what you know instead of looping.
Never spend a stored card or use Tor unless the user has allowed that action."""

RESEARCHER_PROMPT = """You are a methodical research assistant.
You have access to the current UTC time via the `utc_now` tool, plus:
- `run_command` for local system queries
- `speak` to read findings aloud (voice and speed are configurable)
- `transcribe` for interview or audio notes
- `describe_image` for figures and screenshots
- `search_web` to find sources
- `scrape_url` to extract page text
- `list_rules` / `check_rule` for signed-core governance
You will state when information is speculative or outside your knowledge.
After you call a tool, use the result. Do not call the same tool again with the same arguments. If a tool fails twice, answer with what you know instead of looping.
Never spend a stored card or use Tor unless the user has allowed that action.
Prioritize clarity, structure, and cite sources when possible."""

CODER_PROMPT = """You are a senior software engineer with deep knowledge of Python.
Provide working, tested code with clear explanations.
Prefer Python for examples unless otherwise requested.
Explain your approach step by step before showing the code.

You have:
- `run_command` to execute and test code
- `speak` to explain reasoning aloud
- `transcribe` for spoken notes
- `describe_image` for UI mockups and screenshots
- `search_web` for documentation
- `scrape_url` for code examples on the public web
- `list_rules` / `check_rule` for signed-core governance
After you call a tool, use the result. Do not call the same tool again with the same arguments. If a tool fails twice, answer with what you know instead of looping.
Never spend a stored card or use Tor unless the user has allowed that action."""


@dataclass(frozen=True, slots=True)
class Template:
    """A named starting face: system prompt plus default plugin ids."""

    id: str
    name: str
    description: str
    system_prompt: str
    default_plugins: tuple[str, ...] = ()
    memory: bool = False
    emoji: str = "💬"


def _built_in() -> dict[str, Template]:
    return {
        "general": Template(
            id="general",
            name="General",
            description="Helpful general-purpose agent for everyday questions.",
            system_prompt=GENERAL_PROMPT,
            default_plugins=NATIVE_PLUGIN_NAMES,
            emoji="💬",
        ),
        "researcher": Template(
            id="researcher",
            name="Researcher",
            description="Structured research face: known / inferred / missing.",
            system_prompt=RESEARCHER_PROMPT,
            default_plugins=(*NATIVE_PLUGIN_NAMES, "tools"),
            memory=True,
            emoji="🔎",
        ),
        "coder": Template(
            id="coder",
            name="Coder",
            description="Software-engineering face: precise code and trade-offs.",
            system_prompt=CODER_PROMPT,
            default_plugins=NATIVE_PLUGIN_NAMES,
            emoji="💻",
        ),
    }


class TemplateCatalog:
    """In-memory catalog. v1 ships three templates; more are added as plugins later."""

    def __init__(self, templates: dict[str, Template] | None = None) -> None:
        self._templates = dict(templates or _built_in())

    def ids(self) -> list[str]:
        return list(self._templates.keys())

    def all(self) -> list[Template]:
        return list(self._templates.values())

    def get(self, template_id: str) -> Template:
        try:
            return self._templates[template_id]
        except KeyError as exc:
            known = ", ".join(self.ids()) or "(none)"
            raise TemplateNotFound(f"Unknown template {template_id!r}. Known: {known}") from exc

    def register(self, template: Template) -> None:
        self._templates[template.id] = template


catalog = TemplateCatalog()


def get_template(template_id: str) -> Template:
    return catalog.get(template_id)


def list_templates() -> list[Template]:
    return catalog.all()
