"""Encrypted card vault. The signed core is the only writer and decryptor.

Purchases are simulated. Nothing is sent to a merchant.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from universal.paths import user_data_dir
from universal.permission_gate import ask_permission
from universal.rules import is_enforced

CARD_NAME = re.compile(r"^[A-Za-z0-9 _.-]{1,64}$")
DIGITS = re.compile(r"^\d{12,19}$")


def wallet_path() -> Path:
    return user_data_dir() / "wallet.json"


def wallet_key_path() -> Path:
    return user_data_dir() / "wallet.key"


def _load_key() -> bytes:
    path = wallet_key_path()
    if path.is_file():
        return path.read_bytes()
    key = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return key


def _keystream(key: bytes, iv: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hmac.new(key, iv + counter.to_bytes(8, "big"), hashlib.sha256).digest())
        counter += 1
    return bytes(out[:length])


def encrypt_secret(text: str) -> str:
    key = _load_key()
    iv = secrets.token_bytes(16)
    data = text.encode("utf-8")
    cipher = bytes(a ^ b for a, b in zip(data, _keystream(key, iv, len(data)), strict=True))
    tag = hmac.new(key, iv + cipher, hashlib.sha256).digest()
    return base64.b64encode(iv + tag + cipher).decode("ascii")


def decrypt_secret(blob: str) -> str:
    raw = base64.b64decode(blob.encode("ascii"))
    iv, tag, cipher = raw[:16], raw[16:48], raw[48:]
    key = _load_key()
    expected = hmac.new(key, iv + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        raise ValueError("wallet blob failed integrity check")
    data = bytes(a ^ b for a, b in zip(cipher, _keystream(key, iv, len(cipher)), strict=True))
    return data.decode("utf-8")


def _load() -> dict[str, object]:
    path = wallet_path()
    if not path.is_file():
        return {"cards": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"cards": {}}
    cards = data.get("cards") if isinstance(data, dict) else None
    return {"cards": cards if isinstance(cards, dict) else {}}


def _save(data: dict[str, object]) -> None:
    path = wallet_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def save_card(*, card_name: str, card_number: str, expiry: str, cvv: str) -> dict[str, object]:
    name = card_name.strip()
    number = re.sub(r"\s+", "", card_number)
    if not CARD_NAME.match(name):
        return {"ok": False, "error": "card_name is invalid"}
    if not DIGITS.match(number):
        return {"ok": False, "error": "card_number must be 12–19 digits"}
    if not re.match(r"^\d{2}/\d{2}$", expiry.strip()):
        return {"ok": False, "error": "expiry must be MM/YY"}
    if not re.match(r"^\d{3,4}$", cvv.strip()):
        return {"ok": False, "error": "cvv is invalid"}
    data = _load()
    cards = data["cards"]
    assert isinstance(cards, dict)
    cards[name] = {
        "encrypted": encrypt_secret(json.dumps({"card_number": number, "expiry": expiry.strip(), "cvv": cvv.strip()})),
        "last4": number[-4:],
        "created": datetime.now(timezone.utc).isoformat(),
    }
    _save(data)
    return {"ok": True, "card_name": name, "last4": number[-4:]}


def list_cards() -> dict[str, object]:
    data = _load()
    cards = data["cards"]
    assert isinstance(cards, dict)
    names = sorted(str(name) for name in cards)
    return {"ok": True, "cards": names}


def delete_card(card_name: str) -> dict[str, object]:
    data = _load()
    cards = data["cards"]
    assert isinstance(cards, dict)
    if card_name not in cards:
        return {"ok": False, "error": f"card {card_name!r} not found"}
    del cards[card_name]
    _save(data)
    return {"ok": True, "deleted": card_name}


def simulate_purchase(*, card_name: str, amount: float, merchant: str) -> dict[str, object]:
    if amount <= 0:
        return {"ok": False, "error": "amount must be positive"}
    merchant = merchant.strip()
    if not merchant:
        return {"ok": False, "error": "merchant is required"}
    if is_enforced("no_purchase_without_permission"):
        decision = ask_permission(
            action="Allow a simulated purchase with a stored card",
            details=f"Card: {card_name}\nMerchant: {merchant}\nAmount: {amount}",
            agent="wallet",
            rule_id="no_purchase_without_permission",
        )
        if not decision.granted:
            return {"ok": False, "blocked": True, "error": decision.reason or "Purchase blocked"}
    data = _load()
    cards = data["cards"]
    assert isinstance(cards, dict)
    row = cards.get(card_name)
    if not isinstance(row, dict):
        return {"ok": False, "error": f"card {card_name!r} not found"}
    last4 = str(row.get("last4") or "")
    if not last4:
        secret = json.loads(decrypt_secret(str(row["encrypted"])))
        last4 = str(secret.get("card_number", ""))[-4:]
    return {
        "ok": True,
        "simulated": True,
        "card_name": card_name,
        "merchant": merchant,
        "amount": amount,
        "last4": last4,
        "note": "No payment network was contacted.",
    }
