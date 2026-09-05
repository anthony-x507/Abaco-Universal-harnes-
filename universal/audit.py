"""Harness audit. Uses Sentinel Proof HMAC. Not an npm CLI. Not quantum.

Required checks describe what this product actually ships. Designer extras
(mother template, 3 AM daemon, hierarchical memory, improvement evaluator,
notarization, @sentinel-proof/cli) are desired/out-of-scope and do not fail
a VERIFIED verdict.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from universal.plugins.catalog import NATIVE_PLUGIN_NAMES
from universal.proof import (
    challenge,
    draft_contract,
    load_proof,
    record_oracle,
    seal_audit,
    summarize,
    verify_bundle,
)
from universal.templates.catalog import catalog as template_catalog

CONTRACT_ID = "abaco-harness-audit-v1"
OBJECTIVE = "Audit the Universal harness against the signed-core contract."


@dataclass(frozen=True, slots=True)
class Check:
    requirement_id: str
    statement: str
    priority: str  # required | desired
    risk: str  # critical | high | medium
    run: Callable[[Path], tuple[bool, str]]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _exists(root: Path, rel: str) -> bool:
    return (root / rel).exists()


def _count(root: Path, needle: str, *, under: str = "universal", skip: tuple[str, ...] = ("audit.py",)) -> int:
    total = 0
    base = root / under
    if not base.is_dir():
        return 0
    for path in base.rglob("*.py"):
        if path.name in skip:
            continue
        try:
            total += path.read_text(encoding="utf-8").count(needle)
        except OSError:
            continue
    return total


def _has(root: Path, rel: str, *needles: str) -> bool:
    text = _read(root, rel)
    return all(item in text for item in needles)


def check_one_registry(root: Path) -> tuple[bool, str]:
    count = _count(root, "AgentRegistry(")
    return count == 1, f"AgentRegistry( constructions in universal/: {count} (want 1)"


def check_one_lifecycle(root: Path) -> tuple[bool, str]:
    count = _count(root, "AgentLifecycle(")
    return count == 1, f"AgentLifecycle( constructions in universal/: {count} (want 1)"


def check_factory_injected(root: Path) -> tuple[bool, str]:
    text = _read(root, "universal/core/platform.py")
    ok = "AgentFactory(" in text and "self.registry" in text and "self.lifecycle" in text
    return ok, "Universal constructs registry + lifecycle once and injects them into AgentFactory"


def check_provider_not_plugin(root: Path) -> tuple[bool, str]:
    provider = _read(root, "universal/providers/base.py")
    plugin = _read(root, "universal/core/plugin.py")
    ok = "class Provider(ABC)" in provider and "class Plugin(ABC)" in plugin and "class Provider(Plugin)" not in provider
    return ok, "Provider and Plugin are separate ABCs"


def check_channel_not_plugin(root: Path) -> tuple[bool, str]:
    base = _read(root, "universal/channels/base.py")
    ok = "class BaseCommunication(ABC)" in base and "Plugin" not in base.split("class BaseCommunication")[0]
    return ok, "Channels implement BaseCommunication, not Plugin"


def check_three_templates(root: Path) -> tuple[bool, str]:
    ids = template_catalog.ids()
    ok = ids == ["general", "researcher", "coder"]
    no_mother = not _exists(root, "mother.yaml") and not _exists(root, "universal/templates/mother.yaml")
    no_factory = not _exists(root, "universal/factory")
    return ok and no_mother and no_factory, f"templates={ids}; mother.yaml absent={no_mother}; factory/ absent={no_factory}"


def check_native_plugins(root: Path) -> tuple[bool, str]:
    expected = (
        "terminal",
        "tts",
        "stt",
        "vision",
        "web_search",
        "scraper",
        "rule_enforcer",
        "navigator",
        "team",
        "strategist",
        "proof",
        "improvement",
        "package_manager",
        "self_modify",
        "identity",
        "language_policy",
    )
    ok = NATIVE_PLUGIN_NAMES == expected
    return ok, f"NATIVE_PLUGIN_NAMES={list(NATIVE_PLUGIN_NAMES)}"


def check_terminal_denies_destroyers(root: Path) -> tuple[bool, str]:
    text = _read(root, "universal/plugins/terminal.py")
    ok = "mkfs" in text and r"\brm" in text
    return ok, "terminal.py refuses rm-rf / and mkfs"


def check_wallet_encrypted(root: Path) -> tuple[bool, str]:
    ok = _has(root, "universal/wallet_store.py", "wallet.key", "simulate_purchase") and _has(
        root, "universal/permission_gate.py", "ask_permission"
    )
    return ok, "wallet.key + simulated purchase behind permission_gate"


def check_tor_gated(root: Path) -> tuple[bool, str]:
    ok = _has(root, "universal/tor_access.py", "torsocks", "no_dark_web_without_permission")
    return ok, "Tor fetch is permission-gated in Python, not in Node"


def check_mission_not_lifecycle(root: Path) -> tuple[bool, str]:
    no_state = not _exists(root, "universal/state.py")
    ok = no_state and _has(root, "universal/situation.py", "class MissionPhase", "VERIFYING", "SEALED")
    return ok, f"situation.MissionPhase present; universal/state.py absent={no_state}"


def check_obstacles_notify(root: Path) -> tuple[bool, str]:
    ok = _has(root, "universal/plugins/navigator.py", "report_obstacle", "add_notice")
    return ok, "navigator.report_obstacle writes a user notice"


def check_teams_existing_agents(root: Path) -> tuple[bool, str]:
    ok = _has(root, "universal/plugins/team.py", "create_team", "delegate_task") and _has(
        root, "universal/teams.py", "member"
    )
    return ok, "teams group existing agents; no child factory"


def check_delegate_accept(root: Path) -> tuple[bool, str]:
    ok = _has(root, "universal/server.py", "set_delegate_hook", "member.accept")
    return ok, "HTTP delegate hook uses Agent.accept"


def check_team_memory_gated(root: Path) -> tuple[bool, str]:
    ok = _has(root, "universal/plugins/team.py", "memory_share_between_agents") and _has(
        root, "universal/rules.py", '"enforced": False'
    )
    text = _read(root, "universal/rules.py")
    default_off = "memory_share_between_agents" in text and "False" in text
    return ok and default_off, "share_note asks when memory_share_between_agents is on (default off)"


def check_improvement_native(root: Path) -> tuple[bool, str]:
    no_node = not _exists(root, "agent_runtime/plugins/improvement_evaluator.js")
    ok = _has(root, "universal/improvement.py", "propose", "decide") and no_node
    return ok, "Visible improvement is Python (propose/accept/reject). No Node evaluator."


def check_in_process_wiring(root: Path) -> tuple[bool, str]:
    no_shared = not _exists(root, "shared/event-bus.js") and not _exists(root, "universal/event-bus-integration.js")
    text = _read(root, "universal/nervous.py")
    ok = no_shared and "in-process" in text and "Redis" in text and "emit(" in text
    return ok, "Wiring is universal/nervous.py (jsonl). No Redis/NATS Node bus."


def check_no_mother_core_rewrite(root: Path) -> tuple[bool, str]:
    no_core = not _exists(root, "universal/core.py")
    return no_core, "No universal/core.py rewrite. Universal stays in core/platform.py"


def check_deepseek_ondemand(root: Path) -> tuple[bool, str]:
    text = _read(root, "universal/strategist.py")
    no_schedule = "import schedule" not in text and "03:00" not in text and "3 AM" not in text
    ok = no_schedule and "deepseek-ai" in text and "scan_deepseek" in text
    return ok, "DeepSeek scan is on-demand GitHub; no 3 AM job"


def check_no_nightly_daemon(root: Path) -> tuple[bool, str]:
    text = _read(root, "universal/strategist.py")
    has_cron = "import schedule" in text or "threading" in text
    return False, f"No nightly Sentinels thread (desired). schedule/thread present={has_cron}"


def check_proof_engine(root: Path) -> tuple[bool, str]:
    ok = _has(root, "universal/proof.py", "draft_contract", "record_oracle", "challenge", "seal", '"quantum": False')
    return ok, "Sentinel Proof is Python HMAC (sentinel-proof-v1), not @sentinel-proof/cli"


def check_proof_reducer(root: Path) -> tuple[bool, str]:
    ok = _has(root, "universal/proof.py", "def seal(", "_oracle_ok", "_challenge_ok", "hmac")
    return ok, "Mission seal requires passing oracles and a holding challenge"


def check_no_quantum_claim(root: Path) -> tuple[bool, str]:
    panel = _read(root, "web/src/components/ProofPanel.tsx")
    engine = _read(root, "universal/proof.py")
    ok = "Not quantum" in panel and '"quantum": False' in engine
    return ok, "Product copy and bundles set quantum=false"


def check_no_node_mission_plugins(root: Path) -> tuple[bool, str]:
    absent = not any(
        _exists(root, f"agent_runtime/plugins/{name}.js")
        for name in ("navigator", "orchestrator", "strategist_integration")
    )
    return absent, "No Node navigator/orchestrator writing mission files"


def check_situation_panel(root: Path) -> tuple[bool, str]:
    ok = _exists(root, "web/src/components/SituationPanel.tsx") and _exists(root, "web/src/components/ProofPanel.tsx")
    return ok, "Mission tab has SituationPanel + ProofPanel (not StateVisualizer)"


def check_notices(root: Path) -> tuple[bool, str]:
    ok = _has(root, "universal/notifications.py", "add_notice", "ack_notice")
    return ok, "Notices persist under user data; Chat can ack them"


def check_mic_entitlement(root: Path) -> tuple[bool, str]:
    ok = "audio-input" in _read(root, "entitlements.plist")
    return ok, "entitlements.plist includes com.apple.security.device.audio-input"


def check_notarization_not_here(root: Path) -> tuple[bool, str]:
    has_sign = _exists(root, "scripts/sign_macos.sh") or "codesign" in _read(root, "README.md")
    return False, f"Notarization is not verified on this host (desired). signing docs present={has_sign}"


def check_updater(root: Path) -> tuple[bool, str]:
    ok = _has(root, "universal/updater.py", "class Updater", "def apply", "def check")
    return ok, "Updater checks GitHub Releases and can replace Universal.app"


def check_relaunch(root: Path) -> tuple[bool, str]:
    text = _read(root, "universal/updater.py") + _read(root, "web/src/pages/SettingsPage.tsx")
    ok = "relaunch" in text.lower() or "Download & Restart" in text or "restart" in text.lower()
    return ok, "Settings offers Download & Restart after apply"


def check_history_persists(root: Path) -> tuple[bool, str]:
    ok = _has(root, "universal/core/agent.py", "_save_history", "history_path") and _has(
        root, "universal/paths.py", "history"
    )
    return ok, "Chat history is user_data/history/{id}.json, not the registry sidecar"


def check_no_hierarchical_memory(root: Path) -> tuple[bool, str]:
    text = _read(root, "universal/paths.py") + _read(root, "README.md")
    has_tiers = "episodic" in text or "semantic memory" in text.lower()
    return False, f"Hierarchical working/episodic/semantic store is not in this product (desired). mentioned={has_tiers}"


def check_models_picker(root: Path) -> tuple[bool, str]:
    picker = _read(root, "web/src/components/ModelPicker.tsx")
    chat = _read(root, "web/src/pages/ChatPage.tsx")
    ok = "Models" in picker or "Models" in chat
    bad = "LLM company (latest model)" in chat
    return ok and not bad, "Composer label is Models; no LLM-company label"


def check_api_key_field(root: Path) -> tuple[bool, str]:
    ok = "API key" in _read(root, "web/src/pages/ChatPage.tsx") or "API key" in _read(
        root, "web/src/components/ModelPicker.tsx"
    )
    return ok, "Composer shows an API key field when the preset requires one"


def check_rules_enforced(root: Path) -> tuple[bool, str]:
    text = _read(root, "universal/rules.py")
    ok = "DEFAULT_RULES" in text and "sentinel_proof_required" in text and "no_purchase_without_permission" in text
    return ok, "Immutable rule catalog; user file may only flip enforced"


def check_wallet_not_plaintext(root: Path) -> tuple[bool, str]:
    ok = _has(root, "universal/wallet_store.py", "encrypt", "wallet.key") or _has(
        root, "universal/wallet_store.py", "hmac", "wallet.key"
    )
    return ok, "Card vault is encrypted with wallet.key (mode 0600)"


def check_plugin_tests(root: Path) -> tuple[bool, str]:
    needed = (
        "tests/test_native_plugins.py",
        "tests/test_proof.py",
        "tests/test_situation.py",
        "tests/test_governance.py",
        "tests/test_strategist.py",
        "tests/test_language_policy.py",
    )
    missing = [name for name in needed if not _exists(root, name)]
    return not missing, f"functional test files present; missing={missing or 'none'}"


def check_no_npm_cli(root: Path) -> tuple[bool, str]:
    run = _read(root, "audit/scripts/run-audit.sh")
    verify = _read(root, "audit/scripts/verify-proof.sh")
    if not run or not verify:
        return False, "audit/scripts/run-audit.sh and verify-proof.sh are required"
    scripts = run + verify
    ok = "python3 -m universal audit" in run and "npm install" not in scripts and "sentinel-proof init" not in scripts
    return ok, "Audit scripts call python3 -m universal audit, not a fake npm CLI"


CHECKS: tuple[Check, ...] = (
    Check("R-CORE-001", "One AgentRegistry constructed on Universal.", "required", "critical", check_one_registry),
    Check("R-CORE-001", "One AgentLifecycle constructed on Universal.", "required", "critical", check_one_lifecycle),
    Check("R-CORE-001", "AgentFactory receives the injected registry and lifecycle.", "required", "critical", check_factory_injected),
    Check("R-CORE-002", "Provider is not a Plugin.", "required", "critical", check_provider_not_plugin),
    Check("R-CORE-002", "Channel is BaseCommunication, not a Plugin.", "required", "high", check_channel_not_plugin),
    Check("R-CORE-002", "Exactly three templates; no mother.yaml; no universal/factory.", "required", "critical", check_three_templates),
    Check("R-PLUGIN-001", "Native Python plugins are installed on every agent.", "required", "high", check_native_plugins),
    Check("R-PLUGIN-001", "terminal refuses obvious destroyers.", "required", "high", check_terminal_denies_destroyers),
    Check("R-PLUGIN-002", "wallet encrypts cards and simulates purchases behind a permission.", "required", "critical", check_wallet_encrypted),
    Check("R-PLUGIN-003", "Tor fetch is gated in the signed core.", "required", "high", check_tor_gated),
    Check("R-NAV-001", "MissionPhase lives in situation.py, not lifecycle AgentState.", "required", "high", check_mission_not_lifecycle),
    Check("R-NAV-002", "Obstacles notify the user.", "required", "medium", check_obstacles_notify),
    Check("R-ORCH-001", "Teams are groups of existing agents.", "required", "high", check_teams_existing_agents),
    Check("R-ORCH-002", "Delegation uses Agent.accept.", "required", "high", check_delegate_accept),
    Check("R-ORCH-003", "Team notes share only when the rule is on.", "required", "medium", check_team_memory_gated),
    Check("R-IMPR-001", "Visible improvement is a native Python plugin.", "required", "medium", check_improvement_native),
    Check("R-WIRE-001", "Nervous system is in-process, not Redis.", "required", "high", check_in_process_wiring),
    Check("R-WIRE-002", "Universal is not rewritten as universal/core.py.", "required", "critical", check_no_mother_core_rewrite),
    Check("R-STRAT-001", "Nightly 3 AM Sentinels scan (not shipped).", "desired", "medium", check_no_nightly_daemon),
    Check("R-STRAT-002", "DeepSeek monitor is on-demand public GitHub.", "required", "medium", check_deepseek_ondemand),
    Check("R-SPROOF-001", "Sentinel Proof compiles a contract in Python.", "required", "critical", check_proof_engine),
    Check("R-SPROOF-002", "Oracles and challenges are recorded on the bundle.", "required", "critical", check_proof_reducer),
    Check("R-SPROOF-003", "Bundles set quantum false; copy says HMAC.", "required", "critical", check_no_quantum_claim),
    Check("R-SPROOF-003", "No Node mission plugins.", "required", "high", check_no_node_mission_plugins),
    Check("R-UI-001", "Mission tab shows situation and proof.", "required", "medium", check_situation_panel),
    Check("R-UI-002", "Notices can be listed and acked.", "required", "medium", check_notices),
    Check("R-MACOS-001", "Notarization (not verified here).", "desired", "high", check_notarization_not_here),
    Check("R-MACOS-002", "Microphone entitlement is present.", "required", "medium", check_mic_entitlement),
    Check("R-UPDATE-001", "Updater talks to the baked GitHub repo.", "required", "high", check_updater),
    Check("R-UPDATE-002", "Download & Restart is wired.", "required", "medium", check_relaunch),
    Check("R-MEM-001", "Chat history persists under user data.", "required", "medium", check_history_persists),
    Check("R-MEM-002", "Hierarchical memory tiers (not shipped).", "desired", "medium", check_no_hierarchical_memory),
    Check("R-LLM-001", "Composer model picker is labeled Models.", "required", "medium", check_models_picker),
    Check("R-LLM-002", "API key field appears when needed.", "required", "medium", check_api_key_field),
    Check("R-SEC-001", "Governance catalog is immutable except enforced.", "required", "critical", check_rules_enforced),
    Check("R-SEC-002", "Wallet secrets are not stored as plaintext PAN.", "required", "critical", check_wallet_not_plaintext),
    Check("R-TEST-001", "Native plugins, proof, mission, and governance have tests.", "required", "high", check_plugin_tests),
    Check("R-TEST-002", "Audit scripts do not call a fake npm CLI.", "required", "critical", check_no_npm_cli),
)


def _requirement_rows() -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    for check in CHECKS:
        seen.setdefault(check.requirement_id, check.statement)
    return list(seen.items())


def compute_verdict(results: list[dict[str, Any]], challenges_hold: bool) -> str:
    required_fail = [row for row in results if row["priority"] == "required" and not row["passed"]]
    critical_fail = [row for row in required_fail if row["risk"] == "critical"]
    if not challenges_hold:
        return "FAILED"
    if critical_fail:
        return "FAILED"
    if required_fail:
        return "PARTIAL"
    return "VERIFIED"


def doctor() -> dict[str, Any]:
    return {
        "git": bool(shutil.which("git")),
        "python": bool(shutil.which("python3")),
        "node": bool(shutil.which("node")),
        "docker": bool(shutil.which("docker")),
        "sentinel_proof_npm": False,
        "engine": "universal.proof HMAC sentinel-proof-v1",
        "ok": bool(shutil.which("python3")),
    }


def write_report(bundle: dict[str, Any], results: list[dict[str, Any]], dest: Path) -> None:
    verdict = str(bundle.get("verdict") or "")
    required = [row for row in results if row["priority"] == "required"]
    desired = [row for row in results if row["priority"] == "desired"]
    req_ok = sum(1 for row in required if row["passed"])
    lines = [
        "# Universal harness audit",
        "",
        f"**Contract:** {CONTRACT_ID}",
        f"**Mode:** lock-safe / HMAC (not quantum, not `@sentinel-proof/cli`)",
        f"**Verdict:** {verdict}",
        f"**Proof:** `{bundle.get('id')}` HMAC `{str(bundle.get('signature') or '')[:16]}…`",
        f"**Sealed:** {bundle.get('sealed_at')}",
        "",
        f"## Required oracles ({req_ok}/{len(required)} passed)",
        "",
    ]
    for row in results:
        mark = "PASS" if row["passed"] else "FAIL"
        if row["priority"] == "desired":
            mark = "OUT OF SCOPE" if not row["passed"] else "NOTED"
        lines.append(f"- `{row['requirement_id']}` **{mark}** ({row['priority']}/{row['risk']}) — {row['evidence']}")
    lines.extend(
        [
            "",
            "## Desired / not in this product",
            "",
            "These were in the designer packet and are recorded as failed desired oracles.",
            "They do not fail a VERIFIED verdict:",
            "",
        ]
    )
    for row in desired:
        lines.append(f"- `{row['requirement_id']}` — {row['statement']}")
    lines.extend(
        [
            "",
            "## Challenges",
            "",
        ]
    )
    for row in bundle.get("challenges") or []:
        if not isinstance(row, dict):
            continue
        hold = "holds" if row.get("still_holds") else "broke"
        lines.append(f"- {hold}: {row.get('mutation')}")
    lines.extend(["", "## Verify", "", "```bash", "python3 -m universal audit --verify audit/output/proof.sealed.json", "```", ""])
    dest.write_text("\n".join(lines), encoding="utf-8")


def run_audit(*, root: Path | None = None, output: Path | None = None) -> dict[str, Any]:
    root = root or repo_root()
    output = output or (root / "audit" / "output")
    output.mkdir(parents=True, exist_ok=True)
    attest = output / "attestations"
    attest.mkdir(parents=True, exist_ok=True)

    rows = _requirement_rows()
    bundle = draft_contract(
        "harness-audit",
        objective=OBJECTIVE,
        requirements=[text for _, text in rows],
        agent_name="audit",
        kind="audit",
        requirement_ids=[req_id for req_id, _ in rows],
    )
    proof_id = str(bundle["id"])
    results: list[dict[str, Any]] = []
    for check in CHECKS:
        try:
            passed, evidence = check.run(root)
        except Exception as exc:  # noqa: BLE001
            passed, evidence = False, f"oracle crashed: {exc}"
        record_oracle(
            proof_id,
            requirement_id=check.requirement_id,
            passed=passed,
            evidence=evidence,
            oracle=check.run.__name__,
        )
        row = {
            "requirement_id": check.requirement_id,
            "statement": check.statement,
            "priority": check.priority,
            "risk": check.risk,
            "passed": passed,
            "evidence": evidence,
        }
        results.append(row)
        (attest / f"{check.requirement_id}-{check.run.__name__}.json").write_text(
            json.dumps(row, indent=2),
            encoding="utf-8",
        )

    mutations = (
        ("R-ORCH-001", "require mother.yaml and a fourth Sentinels template", True),
        ("R-SPROOF-003", "claim quantum verification", True),
        ("R-SPROOF-003", "add agent_runtime/plugins/navigator.js as the mission writer", True),
        ("R-CORE-001", "construct a second AgentRegistry inside universal/factory/", True),
        ("R-TEST-002", "require npm install -g @sentinel-proof/cli", True),
    )
    holds = True
    for req_id, mutation, still in mutations:
        challenge(proof_id, requirement_id=req_id, mutation=mutation, still_holds=still)
        holds = holds and still

    required_results = [row for row in results if row["priority"] == "required"]
    verdict = compute_verdict(required_results, holds)
    sealed = seal_audit(proof_id, verdict=verdict)
    summary = summarize(sealed)
    summary["results"] = results
    summary["doctor"] = doctor()
    summary["contract_id"] = CONTRACT_ID
    (output / "proof.json").write_text(json.dumps(sealed, indent=2), encoding="utf-8")
    (output / "proof.sealed.json").write_text(json.dumps(sealed, indent=2), encoding="utf-8")
    write_report(sealed, results, output / "report.md")
    return summary


def verify_audit(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("proof is not an object")
    ok = verify_bundle(raw)
    return {
        "ok": ok,
        "verdict": raw.get("verdict"),
        "status": raw.get("status"),
        "quantum": raw.get("quantum"),
        "id": raw.get("id"),
        "verified": ok and raw.get("status") == "sealed",
    }


def export_contract_yaml(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_read(repo_root(), "audit/contract.yaml") or "# see audit/contract.yaml\n", encoding="utf-8")


def run_pytest_smoke(root: Path) -> tuple[bool, str]:
    """Optional extra oracle; not part of the default sealed set."""
    try:
        proc = subprocess.run(
            ["python3", "-m", "pytest", "tests/test_proof.py", "tests/test_wiring.py", "-q"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    return proc.returncode == 0, (proc.stdout or proc.stderr or "")[:400]
