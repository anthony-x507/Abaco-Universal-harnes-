#!/usr/bin/env bash
# Universal harness audit. Uses python3 -m universal audit (HMAC).
# Do not install @sentinel-proof/cli — that package is not this product.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "========================================"
echo "  Universal harness audit"
echo "  engine: sentinel-proof-v1 (HMAC)"
echo "========================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found" >&2
  exit 1
fi

python3 -m universal audit --doctor
python3 -m universal audit --output "$ROOT/audit/output"

echo ""
echo "Proof:   $ROOT/audit/output/proof.sealed.json"
echo "Report:  $ROOT/audit/output/report.md"
echo "Verify:  python3 -m universal audit --verify $ROOT/audit/output/proof.sealed.json"
