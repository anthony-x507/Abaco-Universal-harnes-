#!/usr/bin/env bash
# Create Abaco-Harness.dmg from Abaco Harness.app (macOS only).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_BUNDLE="Abaco Harness.app"
DMG_NAME="Abaco-Harness.dmg"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "create_dmg.sh requires macOS (hdiutil)." >&2
  exit 1
fi

if [[ ! -d "${APP_BUNDLE}" ]]; then
  echo "${APP_BUNDLE} not found. Run scripts/build_macos.sh first." >&2
  exit 1
fi

STAGE="$(mktemp -d "${TMPDIR:-/tmp}/abaco-harness-dmg.XXXXXX")"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

cp -R "${APP_BUNDLE}" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

hdiutil create \
  -volname "Abaco Harness" \
  -srcfolder "$STAGE" \
  -ov \
  -format UDZO \
  "$ROOT/${DMG_NAME}"

if [[ -n "${APPLE_SIGNING_IDENTITY:-}" ]]; then
  codesign --force --timestamp --sign "$APPLE_SIGNING_IDENTITY" "$ROOT/${DMG_NAME}" || true
  "$ROOT/scripts/sign_macos.sh" "$ROOT/${APP_BUNDLE}"
fi

echo "${DMG_NAME} is ready at $ROOT/${DMG_NAME}"
