"""Built-in templates — the first three faces of the Universal platform."""

from __future__ import annotations

from dataclasses import dataclass

from universal.exceptions import TemplateNotFound

GENERAL_PROMPT = """You are a general-purpose agent on the Universal platform.
Answer clearly and directly. If you are unsure, say so. Prefer short,
actionable replies unless the user asks for depth."""

RESEARCHER_PROMPT = """You are a research agent on the Universal platform.
Break questions into what is known, what is inferred, and what is missing.
Flag uncertainty. Ask a clarifying question when the request is underspecified.
Do not invent citations."""

CODER_PROMPT = """You are a software-engineering agent on the Universal platform.
Write correct, minimal code. Explain trade-offs when they matter. Do not claim
to have run commands you did not run. Prefer the language the user is using."""


@dataclass(frozen=True, slots=True)
class Template:
    """A named starting face: system prompt plus default plugin ids."""

    id: str
    name: str
    description: str
    system_prompt: str
    default_plugins: tuple[str, ...] = ()


def _built_in() -> dict[str, Template]:
    return {
        "general": Template(
            id="general",
            name="General",
            description="Helpful general-purpose agent for everyday questions.",
            system_prompt=GENERAL_PROMPT,
            default_plugins=(),
        ),
        "researcher": Template(
            id="researcher",
            name="Researcher",
            description="Structured research face: known / inferred / missing.",
            system_prompt=RESEARCHER_PROMPT,
            default_plugins=("tools",),
        ),
        "coder": Template(
            id="coder",
            name="Coder",
            description="Software-engineering face: precise code and trade-offs.",
            system_prompt=CODER_PROMPT,
            default_plugins=(),
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
