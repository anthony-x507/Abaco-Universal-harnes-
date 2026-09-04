#!/usr/bin/env bash
# Generate Universal.icns from the SPA logo.
# On macOS uses sips + iconutil. Elsewhere falls back to scripts/make_icon.py.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LOGO="${1:-web/src/assets/logo.png}"
if [[ ! -f "$LOGO" ]]; then
  echo "logo missing: $LOGO" >&2
  exit 2
fi

if [[ "$(uname -s)" == "Darwin" ]] && command -v sips >/dev/null && command -v iconutil >/dev/null; then
  rm -rf Universal.iconset
  mkdir Universal.iconset
  sips -z 16 16 "$LOGO" --out Universal.iconset/icon_16x16.png >/dev/null
  sips -z 32 32 "$LOGO" --out Universal.iconset/icon_16x16@2x.png >/dev/null
  sips -z 32 32 "$LOGO" --out Universal.iconset/icon_32x32.png >/dev/null
  sips -z 64 64 "$LOGO" --out Universal.iconset/icon_32x32@2x.png >/dev/null
  sips -z 128 128 "$LOGO" --out Universal.iconset/icon_128x128.png >/dev/null
  sips -z 256 256 "$LOGO" --out Universal.iconset/icon_128x128@2x.png >/dev/null
  sips -z 256 256 "$LOGO" --out Universal.iconset/icon_256x256.png >/dev/null
  sips -z 512 512 "$LOGO" --out Universal.iconset/icon_256x256@2x.png >/dev/null
  sips -z 512 512 "$LOGO" --out Universal.iconset/icon_512x512.png >/dev/null
  sips -z 1024 1024 "$LOGO" --out Universal.iconset/icon_512x512@2x.png >/dev/null
  iconutil -c icns Universal.iconset -o Universal.icns
  echo "Universal.icns created with sips + iconutil"
  exit 0
fi

python3 "$ROOT/scripts/make_icon.py"
