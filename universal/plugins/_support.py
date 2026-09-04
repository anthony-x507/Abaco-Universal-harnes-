"""Shared helpers for built-in plugins. Not a catalog entry."""

from __future__ import annotations

import ipaddress
import json
import socket
from urllib.parse import urlparse

import httpx

from universal.core.types import ToolCall


def parse_tool_args(call: ToolCall) -> dict:
    try:
        args = json.loads(call.arguments or "{}")
    except json.JSONDecodeError:
        return {}
    return args if isinstance(args, dict) else {}


def assert_public_http_url(url: str) -> str:
    """Reject non-http(s) URLs and private / loopback / link-local targets."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http(s) URLs are allowed")
    host = parsed.hostname or ""
    if not host:
        raise ValueError("URL has no host")
    lowered = host.lower().rstrip(".")
    if lowered in {"localhost", "metadata.google.internal"} or lowered.endswith(".localhost"):
        raise ValueError("Refusing private or metadata host")
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except OSError as exc:
        raise ValueError(f"Cannot resolve host {host!r}") from exc
    if not infos:
        raise ValueError(f"Cannot resolve host {host!r}")
    for info in infos:
        raw = info[4][0]
        ip = ipaddress.ip_address(raw)
        if _blocked_ip(ip):
            raise ValueError(f"Refusing private or reserved address {ip}")
    return url


def _blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def fetch_text(
    url: str,
    *,
    timeout: float = 15.0,
    headers: dict[str, str] | None = None,
    params: dict[str, str | int] | None = None,
) -> str:
    response = httpx.get(
        url,
        headers=headers,
        params=params,
        timeout=timeout,
        follow_redirects=False,
    )
    response.raise_for_status()
    return response.text
