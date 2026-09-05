"""Adaptive language + strict three-line reply policy.

Native on every agent. No persistence and no tools: every normal final answer
stays at most three non-empty lines. ``before_complete`` injects language and
integrator guidance into the single system message; ``after_complete`` enforces
the line budget and, when truncating, may append a localized details offer for
Spanish, English, or French.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from universal.core.plugin import Plugin
from universal.core.types import CompletionResponse, Message

if TYPE_CHECKING:
    from universal.core.agent import Agent

UserLanguage = Literal["es", "en", "fr", "other"]

CONCISE_MAX_NONEMPTY_LINES = 3

# Localized offer reserved as the final line when truncation fires.
DETAILS_QUESTION: dict[str, str] = {
    "es": "¿Quieres detalles?",
    "en": "Do you want details?",
    "fr": "Voulez-vous des détails ?",
}
INTEGRATOR_RESPONSE: dict[str, str] = {
    "es": "Eso lo debe hacer el integrador. Te doy instrucciones.",
    "en": "The integrator must do that. I can provide instructions.",
    "fr": "L’intégrateur doit le faire. Je peux fournir les instructions.",
}

_LANGUAGE_RULE: dict[UserLanguage, str] = {
    "es": (
        "Language: reply solely in Spanish. Never mix languages — do not insert "
        "English or French words, headings, or asides."
    ),
    "en": (
        "Language: reply solely in English. Never mix languages — do not insert "
        "Spanish or French words, headings, or asides."
    ),
    "fr": (
        "Language: reply solely in French. Never mix languages — do not insert "
        "English or Spanish words, headings, or asides."
    ),
    "other": (
        "Language: reply solely in the user's language. Never mix languages — "
        "do not switch mid-reply or add foreign-language asides."
    ),
}

_MODIFICATION_RULE: dict[UserLanguage, str] = {
    "es": (
        "Si el usuario pide modificar la aplicación o el producto, indícale que "
        "el integrador se encarga de los cambios de la app."
    ),
    "en": (
        "If the user asks to modify the app or product, tell them the integrator "
        "handles app changes."
    ),
    "fr": (
        "Si l'utilisateur demande de modifier l'application ou le produit, "
        "indiquez que l'intégrateur gère les changements de l'app."
    ),
    "other": (
        "If the user asks to modify the app or product, tell them — in their "
        "language — that the integrator handles app changes."
    ),
}

_LENGTH_RULE = (
    "Length: keep every normal final answer to at most three non-empty lines, "
    "even when the user asks for details. No preamble, no capability lists, no filler."
)

# Distinctive tokens for deterministic es/en/fr detection in tests and runtime.
# Avoid shared Romance accents (é/í/ó/ú) as sole Spanish signals — they appear in French too.
_SPANISH_MARKERS = (
    "¿",
    "¡",
    "ñ",
    "hola",
    "gracias",
    "por favor",
    "necesito",
    "ayuda",
    "explica",
    "explícame",
    "detalle",
    "detalles",
    "quiero",
    "puedes",
    "cómo",
    "qué",
    "está",
    "español",
    "buenos días",
    "buenas",
    "una explicación",
    "paso a paso",
    "arregla",
    "botón",
)
_FRENCH_MARKERS = (
    "ç",
    "œ",
    "à",
    "â",
    "ê",
    "î",
    "ô",
    "û",
    "ù",
    "ë",
    "ï",
    "bonjour",
    "merci",
    "s'il vous plaît",
    "s'il te plaît",
    "comment",
    "pourquoi",
    "explique",
    "détail",
    "détails",
    "besoin",
    "aide",
    "français",
    "est-ce",
    "je voudrais",
    "pouvez-vous",
    "j'ai besoin",
    "quelle",
    "heure",
    "répare",
    "bouton",
)
_ENGLISH_MARKERS = (
    " the ",
    " you ",
    " please ",
    " thanks ",
    " thank you ",
    " hello ",
    " hi ",
    " help ",
    " need ",
    " explain ",
    " detail ",
    " details ",
    " what ",
    " how ",
    " why ",
    " can you ",
    " could you ",
    " english ",
    " summarize ",
    " understand ",
)
_APP_MODIFICATION_ACTIONS = (
    "arregla",
    "modifica",
    "modificar",
    "cambia",
    "fix",
    "modify",
    "change",
    "répare",
    "modifie",
)
_APP_MODIFICATION_TARGETS = (
    "app",
    "aplicación",
    "application",
    "botón",
    "button",
    "bouton",
)


def latest_user_text(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.role == "user" and message.content.strip():
            return message.content
    return ""


def _marker_hit(text: str, markers: tuple[str, ...]) -> bool:
    folded = f" {text.casefold()} "
    return any(marker.casefold() in folded for marker in markers)


def detect_user_language(messages: list[Message] | str) -> UserLanguage:
    """Detect es/en/fr for deterministic guidance; otherwise ``other``."""
    text = messages if isinstance(messages, str) else latest_user_text(messages)
    if not text.strip():
        return "other"
    if _marker_hit(text, _SPANISH_MARKERS):
        return "es"
    if _marker_hit(text, _FRENCH_MARKERS):
        return "fr"
    if _marker_hit(text, _ENGLISH_MARKERS):
        return "en"
    return "other"


def language_instruction(language: UserLanguage | None = None) -> str:
    lang = language if language is not None else "other"
    return _LANGUAGE_RULE[lang]


def modification_instruction(language: UserLanguage | None = None) -> str:
    lang = language if language is not None else "other"
    return _MODIFICATION_RULE[lang]


def policy_instruction(language: UserLanguage | None = None) -> str:
    """Outgoing system guidance: language + integrator + strict three-line length."""
    lang = language if language is not None else "other"
    return "\n".join(
        (
            language_instruction(lang),
            modification_instruction(lang),
            _LENGTH_RULE,
        )
    )


def details_question_for(language: UserLanguage) -> str | None:
    """Localized details offer for known languages; None for unknown."""
    return DETAILS_QUESTION.get(language)


def is_app_modification_request(messages: list[Message]) -> bool:
    prompt = latest_user_text(messages).casefold()
    return any(action in prompt for action in _APP_MODIFICATION_ACTIONS) and any(
        target in prompt for target in _APP_MODIFICATION_TARGETS
    )


def enforce_concise_text(
    text: str,
    *,
    max_nonempty: int = CONCISE_MAX_NONEMPTY_LINES,
    details_question: str | None = None,
) -> str:
    """Keep at most ``max_nonempty`` non-empty lines.

    When truncation is required and ``details_question`` is set, reserve the
    final non-empty line for that offer (content budget = max_nonempty - 1).
    Unknown languages pass ``details_question=None`` so no foreign-language
    question is appended.
    """
    if not text:
        return text

    nonempty_total = sum(1 for line in text.splitlines() if line.strip())
    if nonempty_total <= max_nonempty:
        return _keep_nonempty_budget(text, max_nonempty)

    content_budget = max_nonempty - 1 if details_question else max_nonempty
    kept = _keep_nonempty_budget(text, content_budget)
    if details_question:
        if kept:
            return f"{kept}\n{details_question}"
        return details_question
    return kept


def _keep_nonempty_budget(text: str, max_nonempty: int) -> str:
    if max_nonempty <= 0:
        return ""
    kept: list[str] = []
    nonempty = 0
    for line in text.splitlines():
        if line.strip():
            if nonempty >= max_nonempty:
                break
            nonempty += 1
            kept.append(line)
        elif nonempty > 0 and nonempty < max_nonempty:
            kept.append(line)
    return "\n".join(kept)


class LanguagePolicyPlugin(Plugin):
    def __init__(self) -> None:
        self._name = "language_policy"

    @property
    def name(self) -> str:
        return self._name

    def before_complete(self, agent: Agent, messages: list[Message]) -> list[Message]:
        language = detect_user_language(messages)
        instruction = policy_instruction(language)
        if not instruction:
            return messages
        policy_msg = Message(role="system", content=instruction)
        if not messages:
            return [policy_msg]
        # Preserve the one-system-message invariant used by provider adapters.
        if messages[0].role == "system":
            first = messages[0]
            combined = Message(
                role="system",
                content=f"{first.content}\n\n{instruction}",
                name=first.name,
                tool_call_id=first.tool_call_id,
                tool_calls=first.tool_calls,
            )
            return [combined, *messages[1:]]
        return [policy_msg, *messages]

    def after_complete(
        self, agent: Agent, messages: list[Message], response: CompletionResponse
    ) -> CompletionResponse:
        language = detect_user_language(messages)
        if is_app_modification_request(messages) and language in INTEGRATOR_RESPONSE:
            return CompletionResponse(
                text=INTEGRATOR_RESPONSE[language],
                tool_calls=list(response.tool_calls),
                model=response.model,
                finish_reason=response.finish_reason,
                raw=response.raw,
            )
        # Always enforce the three-line budget, including explicit detail requests.
        question = details_question_for(language)
        trimmed = enforce_concise_text(response.text, details_question=question)
        if trimmed == response.text:
            return response
        return CompletionResponse(
            text=trimmed,
            tool_calls=list(response.tool_calls),
            model=response.model,
            finish_reason=response.finish_reason,
            raw=response.raw,
        )
