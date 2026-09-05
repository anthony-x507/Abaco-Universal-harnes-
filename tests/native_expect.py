"""Shared expectations for factory-default native plugins."""

from __future__ import annotations

from universal.plugins.catalog import NATIVE_PLUGIN_NAMES

NATIVE_TOOL_NAMES = (
    "run_command",
    "speak",
    "transcribe",
    "describe_image",
    "search_web",
    "scrape_url",
    "list_rules",
    "check_rule",
    "set_objective",
    "mission_status",
    "create_team",
    "delegate_task",
    "deepseek_monitor",
    "draft_contract",
    "seal_proof",
    "propose_improvement",
    "package_manager",
    "self_modify",
    "show_identity",
    "list_capabilities",
    "set_response_style",
)

NATIVE_LABELS = [
    "Terminal: run_command",
    "Tts: speak",
    "Stt: transcribe",
    "Vision: describe_image",
    "Web Search: search_web",
    "Scraper: scrape_url",
    "Rule Enforcer: list_rules, check_rule",
    "Navigator: set_objective, plan_steps, complete_step, report_obstacle, report_deviation, suggest_path, checkpoint, mission_status",
    "Team: create_team, delegate_task, team_status, team_checkpoint, resume_team, share_note, read_team_notes",
    "Strategist: deepseek_monitor",
    "Proof: draft_contract, record_oracle, challenge_requirement, seal_proof, proof_status",
    "Improvement: propose_improvement, accept_improvement, reject_improvement, list_improvements",
    "Package Manager: package_manager",
    "Self Modify: self_modify",
    "Identity: show_identity, list_capabilities",
    "Response Style: set_response_style",
]

RESEARCHER_PLUGIN_NAMES = (*NATIVE_PLUGIN_NAMES, "tools")
RESEARCHER_LABELS = [*NATIVE_LABELS, "Tools: utc_now"]
