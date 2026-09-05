"""The three first faces load and produce distinct agents."""

from __future__ import annotations

from universal.core.platform import Universal
from universal.plugins.catalog import NATIVE_PLUGIN_NAMES
from universal.templates.catalog import catalog, get_template, list_templates
from tests.conftest import FakeProvider
from tests.native_expect import RESEARCHER_PLUGIN_NAMES


def test_three_templates_load() -> None:
    ids = set(catalog.ids())
    assert ids == {"general", "researcher", "coder"}
    loaded = list_templates()
    assert {t.id for t in loaded} == ids
    for template_id in ids:
        template = get_template(template_id)
        assert template.system_prompt.strip()
        assert template.name
        assert "system_prompt" not in template.default_plugins
        assert "transcript" not in template.default_plugins
    assert get_template("researcher").default_plugins == RESEARCHER_PLUGIN_NAMES
    assert get_template("general").default_plugins == NATIVE_PLUGIN_NAMES
    assert get_template("coder").default_plugins == NATIVE_PLUGIN_NAMES
    for template_id in ids:
        assert "I can try to install" in get_template(template_id).system_prompt


def test_templates_have_distinct_prompts() -> None:
    prompts = {get_template(tid).system_prompt for tid in catalog.ids()}
    assert len(prompts) == 3


def test_factory_creates_each_template(platform: Universal) -> None:
    for template_id in ("general", "researcher", "coder"):
        agent = platform.factory.create(template_id, name=template_id)
        assert agent.template_id == template_id
        assert "system_prompt" not in agent.plugins
        assert "transcript" not in agent.plugins
        assert agent.system_prompt == get_template(template_id).system_prompt
    assert {info.template_id for info in platform.factory.list()} == {
        "general",
        "researcher",
        "coder",
    }


def test_researcher_includes_tools_plugin(platform: Universal) -> None:
    agent = platform.factory.create("researcher")
    assert "tools" in agent.plugins
    specs = agent.plugins.collect_tools()
    assert any(spec.name == "utc_now" for spec in specs)


def test_general_and_coder_install_native_plugins(platform: Universal) -> None:
    general = platform.factory.create("general")
    coder = platform.factory.create("coder")
    assert general.plugins.names() == list(NATIVE_PLUGIN_NAMES)
    assert coder.plugins.names() == list(NATIVE_PLUGIN_NAMES)


def test_unknown_template_raises(platform: Universal) -> None:
    from universal.exceptions import TemplateNotFound

    try:
        platform.factory.create("not-a-face")
    except TemplateNotFound:
        return
    raise AssertionError("expected TemplateNotFound")


def test_created_agent_answers(platform: Universal, provider: FakeProvider) -> None:
    agent = platform.factory.create("coder", name="dev")
    platform.factory.start(agent.id)
    answer = agent.complete("say hi")
    assert answer.startswith("echo:")
    platform.factory.stop(agent.id)
