#!/usr/bin/env bash
# Sign Universal.app with microphone entitlements.
# A Developer ID is used when APPLE_SIGNING_IDENTITY is set.
# Otherwise the bundle is ad-hoc signed so macOS still lists it under
# Privacy & Security → Microphone (an unsigned .app never appears there).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="${1:-$ROOT/Universal.app}"
ENTITLEMENTS="$ROOT/entitlements.plist"

if [[ ! -d "$APP" ]]; then
  echo "App bundle missing: $APP" >&2
  exit 2
fi

if [[ ! -f "$ENTITLEMENTS" ]]; then
  echo "entitlements.plist missing: $ENTITLEMENTS" >&2
  exit 2
fi

if [[ -z "${APPLE_SIGNING_IDENTITY:-}" ]]; then
  echo "APPLE_SIGNING_IDENTITY unset — ad-hoc signing $APP with microphone entitlement."
  codesign --force --deep --entitlements "$ENTITLEMENTS" --sign - "$APP"
  echo "Ad-hoc signed $APP. After first launch it should appear in Privacy → Microphone."
  exit 0
fi

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
