"""DeepSeek Harness monitor. Public GitHub + DuckDuckGo. Not a fourth template.

There is no 7 AM daemon. A scan runs when the factory is asked, then the
last report is stored under user data.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx

from universal.notifications import add_notice
from universal.paths import user_data_dir
from universal.rules import is_enforced

GITHUB_API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
DDG_URL = "https://api.duckduckgo.com/"
USER_AGENT = "Universal-platform-strategist"
RULE_ID = "strategist_deepseek_tracking"

# Official slugs. Missing repos are recorded, not invented.
WATCHED: tuple[tuple[str, str], ...] = (
    ("harness", "deepseek-ai/deepseek-harness"),
    ("coder", "deepseek-ai/DeepSeek-Coder"),
    ("chat", "deepseek-ai/DeepSeek-Chat"),
)

FEATURE_WORDS = (
    "sandbox",
    "plugin",
    "schedule",
    "orchestrat",
    "session",
    "filesystem",
    "cordis",
    "everything is a plugin",
)
BREAKING_WORDS = ("breaking change", "deprecate", "removed", "incompatible")
ARCH_WORDS = ("architect", "refactor", "restructure", "cordis")

Fetcher = Callable[[str], tuple[int, Any]]


def report_path() -> Path:
    folder = user_data_dir() / "strategist"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "deepseek.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_report() -> dict[str, Any] | None:
    path = report_path()
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def save_report(payload: dict[str, Any]) -> dict[str, Any]:
    path = report_path()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _default_fetch(url: str) -> tuple[int, Any]:
    response = httpx.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
        timeout=12.0,
        follow_redirects=True,
    )
    if response.headers.get("content-type", "").startswith("application/json"):
        try:
            return response.status_code, response.json()
        except ValueError:
            return response.status_code, {"error": "invalid json"}
    return response.status_code, response.text


def _repo_payload(key: str, slug: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": key,
        "repo": slug,
        "name": data.get("name"),
        "full_name": data.get("full_name") or slug,
        "description": data.get("description") or "",
        "stars": int(data.get("stargazers_count") or 0),
        "forks": int(data.get("forks_count") or 0),
        "updated_at": data.get("updated_at"),
        "url": data.get("html_url") or f"https://github.com/{slug}",
        "language": data.get("language"),
    }


def _scan_repo(key: str, slug: str, fetch: Fetcher) -> dict[str, Any]:
    status, body = fetch(f"{GITHUB_API}/repos/{slug}")
    if status == 404:
        return {"key": key, "repo": slug, "missing": True, "error": "not_found"}
    if status != 200 or not isinstance(body, dict):
        return {"key": key, "repo": slug, "missing": True, "error": f"http_{status}"}
    return _repo_payload(key, slug, body)


def _scan_releases(key: str, slug: str, fetch: Fetcher) -> list[dict[str, Any]]:
    status, body = fetch(f"{GITHUB_API}/repos/{slug}/releases?per_page=5")
    if status != 200 or not isinstance(body, list):
        return []
    rows: list[dict[str, Any]] = []
    for rel in body:
        if not isinstance(rel, dict):
            continue
        rows.append(
            {
                "repo": key,
                "tag": rel.get("tag_name") or "",
                "name": rel.get("name") or "",
                "body": str(rel.get("body") or "")[:500],
                "published_at": rel.get("published_at"),
                "url": rel.get("html_url"),
            }
        )
    return rows


def _file_text(slug: str, path: str, fetch: Fetcher) -> str:
    for branch in ("master", "main"):
        status, body = fetch(f"{RAW}/{slug}/{branch}/{path}")
        if status == 200 and isinstance(body, str) and body.strip():
            return body
    return ""


def analyze_changes(readme: str, package_json: str) -> list[dict[str, str]]:
    blob = f"{readme}\n{package_json}".lower()
    found: list[dict[str, str]] = []
    if any(word in blob for word in FEATURE_WORDS):
        found.append(
            {
                "type": "architecture",
                "message": "README or package.json talks about plugins, sandboxes, or scheduling.",
            }
        )
    if any(word in blob for word in BREAKING_WORDS):
        found.append(
            {
                "type": "breaking",
                "message": "Docs mention a breaking change, deprecation, or removal.",
            }
        )
    if any(word in blob for word in ARCH_WORDS):
        found.append(
            {
                "type": "architecture",
                "message": "Docs mention an architecture or Cordis-style plugin core.",
            }
        )
    if "everything is a plugin" in blob:
        found.append(
            {
                "type": "architecture",
                "message": "DeepSeek Harness treats the model, tools, loop, and UI as plugins.",
            }
        )
    return found


def compare_with_universal(harness: dict[str, Any] | None, changes: list[dict[str, str]]) -> list[dict[str, str]]:
    """Compare DSH with Universal. Product name stays Universal platform."""
    rows: list[dict[str, str]] = []
    desc = str((harness or {}).get("description") or "").lower()
    change_text = " ".join(item.get("message", "") for item in changes).lower()
    if "everything is a plugin" in desc or "everything is a plugin" in change_text:
        rows.append(
            {
                "feature": "plugin_surface",
                "status": "DSH makes the UI and agent loop plugins. Universal keeps a signed factory and native Python plugins.",
                "recommendation": "Do not move the factory into Node. Watch DSH plugin ideas that fit a signed core (sandbox, schedule).",
                "priority": "high",
            }
        )
    if "sandbox" in change_text:
        rows.append(
            {
                "feature": "sandbox",
                "status": "DSH documents a sandbox plugin. Universal’s terminal is a local shell with destroyer guards.",
                "recommendation": "Treat a sandbox as complementary, not a replacement for run_command.",
                "priority": "medium",
            }
        )
    stars = int((harness or {}).get("stars") or 0)
    if stars >= 1000:
        rows.append(
            {
                "feature": "visibility",
                "status": f"The official DSH repo has {stars} GitHub stars. That is popularity, not a missing Universal tool.",
                "recommendation": "Keep Universal’s locks (one registry, one provider, accept-not-completions). Steal ideas, not architecture.",
                "priority": "low",
            }
        )
    if not rows:
        rows.append(
            {
                "feature": "watch",
                "status": "No complementary DSH capability stood out from the last scan.",
                "recommendation": "Scan again after a new DSH release notes drop.",
                "priority": "low",
            }
        )
    return rows


def _popularity(fetch: Fetcher, stars: int) -> dict[str, Any]:
    status, body = fetch(f"{DDG_URL}?q=DeepSeek+Harness&format=json&no_html=1")
    mention = 0
    abstract = ""
    if status == 200 and isinstance(body, dict):
        abstract = str(body.get("Abstract") or body.get("AbstractText") or "")
        related = body.get("RelatedTopics") or []
        mention = len(related) if isinstance(related, list) else 0
        if abstract:
            mention += 1
    return {
        "stars": stars,
        "mention_count": mention,
        "abstract": abstract[:280],
        "source": "github_stars+duckduckgo",
        "twitter": "not_available",
    }


def _notify_new_releases(previous: dict[str, Any] | None, current: dict[str, Any]) -> None:
    old_tags = {f"{row.get('repo')}:{row.get('tag')}" for row in (previous or {}).get("new_releases") or []}
    fresh = [
        row
        for row in current.get("new_releases") or []
        if isinstance(row, dict) and f"{row.get('repo')}:{row.get('tag')}" not in old_tags and row.get("tag")
    ]
    if not fresh:
        return
    top = fresh[0]
    add_notice(
        agent_id="strategist",
        kind="deepseek",
        message=f"DeepSeek Harness release {top.get('tag')}: {str(top.get('name') or top.get('body') or 'new release')[:160]}",
    )


def empty_report(*, blocked: bool = False, reason: str = "") -> dict[str, Any]:
    return {
        "ok": not blocked,
        "blocked": blocked,
        "reason": reason,
        "scanned": False,
        "scanned_at": None,
        "harness": None,
        "coder": None,
        "chat": None,
        "repos": {},
        "new_releases": [],
        "updated_at": None,
        "changes_detected": [],
        "popularity": None,
        "comparisons": [],
        "product": "Universal platform",
    }


def scan_deepseek(*, refresh: bool = False, fetch: Fetcher | None = None) -> dict[str, Any]:
    if not is_enforced(RULE_ID):
        cached = load_report()
        payload = dict(cached) if cached else empty_report(blocked=True, reason=f"{RULE_ID} is off")
        payload["ok"] = False
        payload["blocked"] = True
        payload["reason"] = f"{RULE_ID} is off"
        return payload
    cached = load_report()
    if cached and not refresh:
        return cached
    getter = fetch or _default_fetch
    repos: dict[str, Any] = {}
    releases: list[dict[str, Any]] = []
    for key, slug in WATCHED:
        repos[key] = _scan_repo(key, slug, getter)
        if not repos[key].get("missing"):
            releases.extend(_scan_releases(key, slug, getter))
    harness = repos.get("harness") if not repos.get("harness", {}).get("missing") else None
    readme = _file_text("deepseek-ai/deepseek-harness", "README.md", getter) if harness else ""
    package = _file_text("deepseek-ai/deepseek-harness", "package.json", getter) if harness else ""
    changes = analyze_changes(readme, package)
    comparisons = compare_with_universal(harness, changes)
    stars = int((harness or {}).get("stars") or 0)
    payload = {
        "ok": True,
        "blocked": False,
        "reason": "",
        "scanned": True,
        "scanned_at": _now(),
        "harness": harness,
        "coder": repos.get("coder") if not repos.get("coder", {}).get("missing") else None,
        "chat": repos.get("chat") if not repos.get("chat", {}).get("missing") else None,
        "repos": repos,
        "new_releases": releases,
        "updated_at": (harness or {}).get("updated_at"),
        "changes_detected": changes,
        "popularity": _popularity(getter, stars),
        "comparisons": comparisons,
        "product": "Universal platform",
    }
    _notify_new_releases(cached, payload)
    return save_report(payload)


def format_report(payload: dict[str, Any]) -> str:
    if payload.get("blocked"):
        return f"error: DeepSeek tracking is off ({payload.get('reason')})"
    if not payload.get("harness") and not payload.get("scanned"):
        return "No DeepSeek scan yet. Ask again after a scan, or use Settings → Scan DeepSeek."
    lines = ["DeepSeek Harness monitor (Universal platform)"]
    harness = payload.get("harness") or {}
    if harness:
        lines.append(f"Repo: {harness.get('full_name')}  stars={harness.get('stars')}  updated={harness.get('updated_at')}")
        if harness.get("url"):
            lines.append(str(harness["url"]))
    else:
        missing = (payload.get("repos") or {}).get("harness") or {}
        lines.append(f"Harness repo missing: {missing.get('error') or 'unknown'}")
    releases = payload.get("new_releases") or []
    if releases:
        lines.append("Releases:")
        for row in releases[:3]:
            lines.append(f"- {row.get('repo')} {row.get('tag')} {row.get('published_at')}")
    for row in payload.get("comparisons") or []:
        lines.append(f"{row.get('feature')}: {row.get('status')} → {row.get('recommendation')}")
    pop = payload.get("popularity") or {}
    if pop:
        lines.append(f"Mentions (DuckDuckGo): {pop.get('mention_count')}  X/Twitter: not wired")
    return "\n".join(lines)
