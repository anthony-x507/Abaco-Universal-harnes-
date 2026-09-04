"""Immutable governance catalog. The user file may only flip ``enforced``."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from universal.paths import user_data_dir

ENV_RULES_FILE = "UNIVERSAL_RULES_FILE"

DEFAULT_RULES: tuple[dict[str, object], ...] = (
    {
        "id": "no_system_delete",
        "description": "Do not delete system files without confirmation.",
        "enforced": True,
    },
    {
        "id": "ask_before_self_modify",
        "description": "Ask before changing the evolvable runtime.",
        "enforced": True,
    },
    {
        "id": "no_external_sharing",
        "description": "Do not share user data with third parties.",
        "enforced": True,
    },
    {
        "id": "no_ui_modification",
        "description": "Do not change the signed UI without consent.",
        "enforced": True,
    },
    {
        "id": "no_purchase_without_permission",
        "description": "Never spend stored card details without an explicit allow.",
        "enforced": True,
    },
    {
        "id": "no_dark_web_without_permission",
        "description": "Use Tor only after the user allows that fetch.",
        "enforced": True,
    },
)

RULE_IDS = tuple(str(row["id"]) for row in DEFAULT_RULES)


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    description: str
    enforced: bool

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "description": self.description, "enforced": self.enforced}


def default_rules_path() -> Path:
    env = os.environ.get(ENV_RULES_FILE, "").strip()
    if env:
        return Path(env)
    return user_data_dir() / "abaco_rules.json"


def home_rules_path() -> Path:
    return Path.home() / ".abaco_rules.json"


def _parse_overrides(path: Path) -> dict[str, bool]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    rows = raw.get("rules") if isinstance(raw, dict) else None
    if not isinstance(rows, list):
        return {}
    overrides: dict[str, bool] = {}
    for row in rows:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        if "enforced" in row:
            overrides[str(row["id"])] = bool(row["enforced"])
    return overrides


def load_rules() -> list[Rule]:
    overrides = _parse_overrides(default_rules_path())
    if not os.environ.get("UNIVERSAL_USER_DATA", "").strip() and not os.environ.get(ENV_RULES_FILE, "").strip():
        overrides.update(_parse_overrides(home_rules_path()))
    rules = [
        Rule(
            id=str(row["id"]),
            description=str(row["description"]),
            enforced=overrides.get(str(row["id"]), bool(row["enforced"])),
        )
        for row in DEFAULT_RULES
    ]
    return rules


def is_enforced(rule_id: str) -> bool:
    for rule in load_rules():
        if rule.id == rule_id:
            return rule.enforced
    return True


def _catalog_payload(overrides: dict[str, bool]) -> dict[str, object]:
    return {
        "version": "1.0",
        "rules": [
            {
                "id": row["id"],
                "description": row["description"],
                "enforced": overrides.get(str(row["id"]), bool(row["enforced"])),
            }
            for row in DEFAULT_RULES
        ],
    }


def ensure_rules_file() -> Path:
    """Write the catalog. Existing ``enforced`` flags are kept; new ids are added."""
    path = default_rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _catalog_payload(_parse_overrides(path))
    text = json.dumps(payload, indent=2) + "\n"
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass
    home = home_rules_path()
    if (
        home != path
        and not home.is_file()
        and not os.environ.get(ENV_RULES_FILE, "").strip()
        and not os.environ.get("UNIVERSAL_USER_DATA", "").strip()
    ):
        try:
            home.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            home.chmod(0o600)
        except OSError:
            pass
    return path


def rules_payload() -> dict[str, object]:
    return {
        "version": "1.0",
        "file": str(default_rules_path()),
        "rules": [rule.to_dict() for rule in load_rules()],
    }
