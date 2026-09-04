#!/usr/bin/env bash
# Sign Universal.app when APPLE_SIGNING_IDENTITY is set. No-op otherwise.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="${1:-$ROOT/Universal.app}"

if [[ -z "${APPLE_SIGNING_IDENTITY:-}" ]]; then
  echo "APPLE_SIGNING_IDENTITY unset — leaving $APP unsigned."
  exit 0
fi

if [[ ! -d "$APP" ]]; then
  echo "App bundle missing: $APP" >&2
  exit 2
fi

ENTITLEMENTS="$ROOT/entitlements.plist"
codesign --force --deep --timestamp --options runtime \
  --entitlements "$ENTITLEMENTS" \
  --sign "$APPLE_SIGNING_IDENTITY" \
  "$APP"

if [[ -n "${APPLE_ID:-}" && -n "${APPLE_TEAM_ID:-}" && -n "${APPLE_APP_PASSWORD:-}" && -f "$ROOT/Universal.dmg" ]]; then
  xcrun notarytool submit "$ROOT/Universal.dmg" \
    --apple-id "$APPLE_ID" \
    --team-id "$APPLE_TEAM_ID" \
    --password "$APPLE_APP_PASSWORD" \
    --wait
  xcrun stapler staple "$ROOT/Universal.dmg"
fi

echo "Signed $APP"
