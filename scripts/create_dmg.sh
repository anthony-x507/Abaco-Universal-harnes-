#!/usr/bin/env bash
# Create Universal.dmg from Universal.app (macOS only).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "create_dmg.sh requires macOS (hdiutil)." >&2
  exit 1
fi

if [[ ! -d Universal.app ]]; then
  echo "Universal.app not found. Run scripts/build_macos.sh first." >&2
  exit 1
fi

STAGE="$(mktemp -d "${TMPDIR:-/tmp}/universal-dmg.XXXXXX")"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

cp -R Universal.app "$STAGE/"
ln -s /Applications "$STAGE/Applications"

hdiutil create \
  -volname "Universal" \
  -srcfolder "$STAGE" \
  -ov \
  -format UDZO \
  "$ROOT/Universal.dmg"

echo "Universal.dmg is ready at $ROOT/Universal.dmg"
