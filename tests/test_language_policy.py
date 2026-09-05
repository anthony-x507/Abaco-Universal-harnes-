"""Language-policy native plugin: adaptive language and strict three-line replies."""

from __future__ import annotations

from universal.core.agent import Agent
from universal.core.platform import Universal
from universal.core.types import CompletionResponse, Message, ToolCall
from universal.plugins.catalog import NATIVE_PLUGIN_NAMES
from universal.plugins.language_policy import (
    DETAILS_QUESTION,
    INTEGRATOR_RESPONSE,
    LanguagePolicyPlugin,
    detect_user_language,
    details_question_for,
    enforce_concise_text,
    is_app_modification_request,
    language_instruction,
    modification_instruction,
    policy_instruction,
)
from universal.templates.catalog import get_template
from tests.conftest import FakeProvider


def _nonempty_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def test_language_policy_is_last_native_plugin() -> None:
    assert "language_policy" in NATIVE_PLUGIN_NAMES
    assert NATIVE_PLUGIN_NAMES[-1] == "language_policy"
    assert "identity" in NATIVE_PLUGIN_NAMES


def test_every_created_agent_gets_language_policy(platform: Universal) -> None:
    for template_id in ("general", "researcher", "coder"):
        agent = platform.factory.create(template_id, name=f"lp-{template_id}")
        names = agent.plugins.names()
        assert "language_policy" in names
        assert "identity" in names
        assert LanguagePolicyPlugin().tools() == []
        assert agent.plugins.get("language_policy").tools() == []
        assert names.index("language_policy") == len(NATIVE_PLUGIN_NAMES) - 1
        assert names.index("identity") < names.index("language_policy")
        assert "Language Policy" in agent.plugin_labels()
        if template_id != "researcher":
            assert names[-1] == "language_policy"


def test_language_policy_exposes_no_tools() -> None:
    plugin = LanguagePolicyPlugin()
    assert plugin.name == "language_policy"
    assert plugin.tools() == []


def test_detect_user_language_spanish_english_french_and_other() -> None:
    assert detect_user_language("Hola, ¿puedes ayudarme por favor?") == "es"
    assert detect_user_language("Hello, can you please help me?") == "en"
    assert detect_user_language("Bonjour, pouvez-vous m'aider s'il vous plaît?") == "fr"
    assert detect_user_language("Quelle heure est-il?") == "fr"
    assert detect_user_language("こんにちは、手伝ってください") == "other"
    assert detect_user_language([Message(role="user", content="Explícame los detalles")]) == "es"
    assert detect_user_language([Message(role="user", content="Please explain the details")]) == "en"
    assert detect_user_language([Message(role="user", content="Explique les détails")]) == "fr"


def test_policy_instruction_embeds_language_and_integrator_rules() -> None:
    cases = (
        ("es", "reply solely in Spanish"),
        ("en", "reply solely in English"),
        ("fr", "reply solely in French"),
        ("other", "reply solely in the user's language"),
    )
    for lang, sole in cases:
        text = policy_instruction(lang)  # type: ignore[arg-type]
        assert sole in text
        assert "Never mix languages" in text
        assert "three non-empty lines" in text
        assert language_instruction(lang) in text  # type: ignore[arg-type]
        assert modification_instruction(lang) in text  # type: ignore[arg-type]
        folded = text.casefold()
        assert (
            "integrator" in folded
            or "integrador" in folded
            or "intégrateur" in folded
        )


def test_before_complete_injects_adaptive_language_and_keeps_one_system() -> None:
    plugin = LanguagePolicyPlugin()
    agent = Agent(name="lp", provider=FakeProvider(), template_id="general")
    messages = [
        Message(role="system", content="You are helpful."),
        Message(role="user", content="Hola, necesito ayuda"),
    ]
    out = plugin.before_complete(agent, messages)
    assert out[0].role == "system"
    assert out[0].content.startswith("You are helpful.\n\n")
    assert "reply solely in Spanish" in out[0].content
    assert "Never mix languages" in out[0].content
    assert "integrador" in out[0].content
    assert policy_instruction("es") in out[0].content
    assert out[1].role == "user"
    assert sum(message.role == "system" for message in out) == 1


def test_before_complete_english_and_french_system_instructions() -> None:
    plugin = LanguagePolicyPlugin()
    agent = Agent(name="lp", provider=FakeProvider(), template_id="general")

    en = plugin.before_complete(
        agent,
        [
            Message(role="system", content="Base."),
            Message(role="user", content="Please explain what happened"),
        ],
    )
    assert sum(message.role == "system" for message in en) == 1
    assert "reply solely in English" in en[0].content
    assert "integrator handles app changes" in en[0].content

    fr = plugin.before_complete(
        agent,
        [
            Message(role="system", content="Base."),
            Message(role="user", content="Bonjour, explique le problème"),
        ],
    )
    assert sum(message.role == "system" for message in fr) == 1
    assert "reply solely in French" in fr[0].content
    assert "intégrateur" in fr[0].content


def test_before_complete_other_language_uses_generic_same_language_guidance() -> None:
    plugin = LanguagePolicyPlugin()
    agent = Agent(name="lp", provider=FakeProvider(), template_id="general")
    out = plugin.before_complete(
        agent,
        [
            Message(role="system", content="Base."),
            Message(role="user", content="帮我改一下应用"),
        ],
    )
    assert sum(message.role == "system" for message in out) == 1
    assert "reply solely in the user's language" in out[0].content
    assert "Never mix languages" in out[0].content
    assert "integrator handles app changes" in out[0].content


def test_after_complete_truncates_and_preserves_metadata() -> None:
    plugin = LanguagePolicyPlugin()
    agent = Agent(name="lp", provider=FakeProvider(), template_id="general")
    long_text = "one\ntwo\nthree\nfour\nfive"
    raw = {"id": "resp-1"}
    calls = [ToolCall(id="c1", name="run_command", arguments="{}")]
    response = CompletionResponse(
        text=long_text,
        tool_calls=calls,
        model="demo",
        finish_reason="tool_calls",
        raw=raw,
    )
    # No user message → other language → truncate without foreign details question.
    out = plugin.after_complete(agent, [], response)
    assert out.text == "one\ntwo\nthree"
    assert len(_nonempty_lines(out.text)) == 3
    assert out.tool_calls == calls
    assert out.model == "demo"
    assert out.finish_reason == "tool_calls"
    assert out.raw == raw


def test_after_complete_reserves_localized_details_question_when_truncating() -> None:
    plugin = LanguagePolicyPlugin()
    agent = Agent(name="lp", provider=FakeProvider(), template_id="general")
    long_text = "one\ntwo\nthree\nfour\nfive"
    cases = (
        ("Hola, necesito una explicación", "es"),
        ("Please help me understand this", "en"),
        ("Bonjour, j'ai besoin d'aide", "fr"),
    )
    for prompt, lang in cases:
        response = CompletionResponse(text=long_text, model="demo")
        out = plugin.after_complete(
            agent, [Message(role="user", content=prompt)], response
        )
        lines = _nonempty_lines(out.text)
        assert len(lines) == 3
        assert lines[0] == "one"
        assert lines[1] == "two"
        assert lines[2] == DETAILS_QUESTION[lang]
        assert details_question_for(lang) == DETAILS_QUESTION[lang]  # type: ignore[arg-type]


def test_after_complete_unknown_language_truncates_without_foreign_question() -> None:
    plugin = LanguagePolicyPlugin()
    agent = Agent(name="lp", provider=FakeProvider(), template_id="general")
    response = CompletionResponse(text="a\nb\nc\nd\ne", model="demo")
    out = plugin.after_complete(
        agent, [Message(role="user", content="请详细说明一下")], response
    )
    assert out.text == "a\nb\nc"
    for question in DETAILS_QUESTION.values():
        assert question not in out.text
    assert details_question_for("other") is None


def test_still_caps_when_user_asks_for_details() -> None:
    plugin = LanguagePolicyPlugin()
    agent = Agent(name="lp", provider=FakeProvider(), template_id="general")
    messages = [Message(role="user", content="Explícalo paso a paso y con detalle")]
    response = CompletionResponse(text="one\ntwo\nthree\nfour\nfive", model="demo")
    out = plugin.after_complete(agent, messages, response)
    lines = _nonempty_lines(out.text)
    assert len(lines) == 3
    assert lines[-1] == DETAILS_QUESTION["es"]


def test_app_modification_returns_localized_integrator_answer() -> None:
    plugin = LanguagePolicyPlugin()
    agent = Agent(name="lp", provider=FakeProvider(), template_id="general")
    cases = (
        ("Arregla el botón de audio", "es"),
        ("Fix the audio button", "en"),
        ("Répare le bouton audio", "fr"),
    )
    for prompt, language in cases:
        messages = [Message(role="user", content=prompt)]
        assert is_app_modification_request(messages)
        response = CompletionResponse(text="wrong language\nand too much detail")
        out = plugin.after_complete(agent, messages, response)
        assert out.text == INTEGRATOR_RESPONSE[language]
        assert len(_nonempty_lines(out.text)) <= 3


def test_enforce_concise_text_helper() -> None:
    assert enforce_concise_text("a\n\nb\nc\nd") == "a\n\nb\nc"
    assert enforce_concise_text("only") == "only"
    assert enforce_concise_text("") == ""
    assert (
        enforce_concise_text("a\nb\nc\nd", details_question="Do you want details?")
        == "a\nb\nDo you want details?"
    )
    assert (
        enforce_concise_text("a\nb\nc", details_question="Do you want details?")
        == "a\nb\nc"
    )


def test_agent_complete_applies_language_policy_enforcement() -> None:
    provider = FakeProvider(reply="line1\nline2\nline3\nline4\nline5")
    agent = Agent(name="lp", provider=provider, template_id="general")
    agent.attach_plugin(LanguagePolicyPlugin())
    assert agent.complete("Please summarize this") == (
        f"line1\nline2\n{DETAILS_QUESTION['en']}"
    )


def test_templates_encode_language_concise_and_integrator_rules() -> None:
    for template_id in ("general", "researcher", "coder"):
        prompt = get_template(template_id).system_prompt
        assert "Reply solely in the user's language" in prompt
        assert "Never mix languages" in prompt
        assert "at most 3 lines" in prompt
        assert "even when the user asks for details" in prompt
        assert "integrator handles app changes" in prompt
