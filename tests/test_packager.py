"""ZIP packager writes a real archive without secrets."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from universal.core.platform import Universal
from universal.deploy.github import GitHubDeployTarget
from universal.deploy.packager import ZipPackager
from universal.exceptions import DeployError


def test_packager_writes_zip(platform: Universal, tmp_path: Path) -> None:
    agent = platform.factory.create("general", name="pack-me")
    dest = tmp_path / "agent.zip"
    written = ZipPackager().pack(agent, dest)
    assert written == dest
    assert dest.is_file()
    with zipfile.ZipFile(dest) as archive:
        names = set(archive.namelist())
        assert names == {"manifest.json", "config.json", "system_prompt.txt", "README.txt", "usage.json"}
        usage = json.loads(archive.read("usage.json"))
        assert usage["calls"] == 0
        assert usage["estimated_cost"] == 0
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["product"] == "Universal platform"
        assert manifest["agent"]["id"] == agent.id
        assert manifest["agent"]["template_id"] == "general"
        config = json.loads(archive.read("config.json"))
        assert "API keys are never written" in config["note"]
        assert "sk-" not in archive.read("manifest.json").decode()
        assert "test-key" not in archive.read("config.json").decode()


def test_factory_deploy_zip(platform: Universal, tmp_path: Path) -> None:
    agent = platform.factory.create("coder", name="boxed")
    path = platform.factory.deploy(agent.id, tmp_path / "out.zip")
    assert path.is_file()
    assert zipfile.is_zipfile(path)


def test_github_target_is_a_stub(tmp_path: Path) -> None:
    archive = tmp_path / "x.zip"
    archive.write_bytes(b"pk")
    result = GitHubDeployTarget().deploy(archive)
    assert result.ok is False
    assert "deferred" in result.message.lower()


def test_factory_github_target_raises_without_writing(platform: Universal, tmp_path: Path) -> None:
    agent = platform.factory.create("general", name="gh")
    dest = tmp_path / "gh.zip"
    try:
        platform.factory.deploy(agent.id, dest, target="github")
    except DeployError as exc:
        assert "deferred" in str(exc).lower()
    else:
        raise AssertionError("expected DeployError from GitHub stub")
    assert not dest.exists(), "GitHub stub must not write a ZIP as a side effect"
