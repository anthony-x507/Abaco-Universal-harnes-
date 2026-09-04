#!/usr/bin/env bash
# Build the Mac release using the scripts that already exist.
# Notarization needs Apple credentials on a Mac. This Linux tree cannot staple.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "1/4 web build (if bun is present)"
if command -v bun >/dev/null 2>&1; then
  (cd web && bun run build)
fi

echo "2/4 macOS app"
if [[ -f scripts/build_macos.sh ]]; then
  ./scripts/build_macos.sh
else
  echo "scripts/build_macos.sh missing" >&2
  exit 1
fi

echo "3/4 sign (skipped without APPLE_SIGNING_IDENTITY)"
if [[ -n "${APPLE_SIGNING_IDENTITY:-}" && -f scripts/sign_macos.sh ]]; then
  ./scripts/sign_macos.sh
else
  echo "sign skipped"
fi

echo "4/4 dmg"
if [[ -f scripts/create_dmg.sh ]]; then
  ./scripts/create_dmg.sh
else
  echo "create_dmg.sh missing — packager still writes Universal.dmg on a Mac runner"
fi

if command -v codesign >/dev/null 2>&1 && [[ -d Universal.app ]]; then
  codesign -vvv Universal.app || true
else
  echo "codesign/notarize not available on this host (expected on Linux CI)"
fi
