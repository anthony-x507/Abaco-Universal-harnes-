#!/usr/bin/env bash
# Verify a sealed harness audit bundle with the same HMAC key.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROOF="${1:-$ROOT/audit/output/proof.sealed.json}"

if [[ ! -f "$PROOF" ]]; then
  echo "missing proof: $PROOF" >&2
  exit 1
fi

python3 -m universal audit --verify "$PROOF"
