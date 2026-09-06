#!/usr/bin/env bash
# Create Abaco-Harness.dmg from Abaco Harness.app (macOS only for the image).
#
# Dual-bundle bridge for old clients (do not drop until 1.2.15 / 1.2.16 are gone):
# Packaged updaters on those tags hard-code
#   mount = Path("/Volumes/Universal")
#   src = mount / "Universal.app"
# and raise exactly "Mounted image has no Universal.app" when either is missing.
# v1.2.17 renamed the product to Abaco Harness.app and the volume to
# "Abaco Harness", so those old binaries cannot apply that DMG — chicken and egg.
# This script therefore:
#   1. Copies Abaco Harness.app (canonical; drag this to /Applications)
#   2. Copies the same tree as Universal.app (old updater path)
#   3. Uses -volname Universal so attach lands at /Volumes/Universal
# New updaters (1.2.17+) already search both volume and bundle names.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_BUNDLE="${UNIVERSAL_APP_BUNDLE:-Abaco Harness.app}"
CANONICAL_BUNDLE="Abaco Harness.app"
LEGACY_BUNDLE="Universal.app"
DMG_NAME="Abaco-Harness.dmg"
# 1.2.15 / 1.2.16 look only under /Volumes/Universal.
VOLUME_NAME="Universal"

stage_dmg_payload() {
  local stage="$1"
  mkdir -p "$stage"
  if [[ ! -d "${APP_BUNDLE}" ]]; then
    echo "${APP_BUNDLE} not found. Run scripts/build_macos.sh first." >&2
    return 1
  fi
  rm -rf "${stage}/${CANONICAL_BUNDLE}" "${stage}/${LEGACY_BUNDLE}"
  cp -R "${APP_BUNDLE}" "${stage}/${CANONICAL_BUNDLE}"
  # Same app, old folder name — 1.2.15/1.2.16 look only for Universal.app.
  cp -R "${APP_BUNDLE}" "${stage}/${LEGACY_BUNDLE}"
}

if [[ "${1:-}" == "--stage" ]]; then
  STAGE_DIR="${2:?usage: create_dmg.sh --stage DIR}"
  stage_dmg_payload "$STAGE_DIR"
  echo "Staged ${CANONICAL_BUNDLE} and ${LEGACY_BUNDLE} in ${STAGE_DIR}"
  exit 0
fi

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

stage_dmg_payload "$STAGE"
ln -s /Applications "$STAGE/Applications"

hdiutil create \
  -volname "${VOLUME_NAME}" \
  -srcfolder "$STAGE" \
  -ov \
  -format UDZO \
  "$ROOT/${DMG_NAME}"

if [[ -n "${APPLE_SIGNING_IDENTITY:-}" ]]; then
  codesign --force --timestamp --sign "$APPLE_SIGNING_IDENTITY" "$ROOT/${DMG_NAME}" || true
  "$ROOT/scripts/sign_macos.sh" "$ROOT/${CANONICAL_BUNDLE}"
fi

echo "${DMG_NAME} is ready at $ROOT/${DMG_NAME}"
