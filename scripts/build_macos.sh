#!/usr/bin/env bash
# Build the Universal desktop bundle. On macOS this produces Universal.app.
# Plugins (terminal, TTS, STT, vision, search, scraper) ship in the Python package;
# they are not copied as a second tree. Whisper is optional and is not bundled.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Building Universal icons from the Ábaco mark…"
chmod +x scripts/make_icns.sh scripts/make_icon.py
./scripts/make_icns.sh

echo "Building Universal web face…"
(
  cd web
  bun install
  bun run build
)

if [[ ! -f web/dist/index.html ]]; then
  echo "web/dist/index.html missing after build" >&2
  exit 1
fi

if ! python3 -c "import universal.desktop" >/dev/null 2>&1; then
  echo "Install the package first: python3 -m pip install -e '.[desktop]'" >&2
  exit 1
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Not macOS — skipping Universal.app (PyInstaller .app is Darwin-only)."
  echo "Checking the desktop factory + SPA on this machine…"
  python3 -m universal desktop --check --demo
  echo "On a Mac, re-run this script to produce Universal.app."
  exit 0
fi

echo "Packaging Universal.app with PyInstaller…"
python3 -m pip install -q 'pyinstaller>=6.0' 'pywebview>=5.0'

# onedir + windowed → a real .app. Do not hide-import whisper (optional extra, huge).
# Do not add a second factory tree. The package is imported as universal.
ICON_ARGS=()
if [[ -f Universal.icns ]]; then
  ICON_ARGS+=(--icon Universal.icns --add-data "Universal.icns:.")
fi

python3 -m PyInstaller \
  --noconfirm \
  --windowed \
  --name Universal \
  "${ICON_ARGS[@]}" \
  --add-data "web/dist:web/dist" \
  --add-data "version.json:." \
  --hidden-import=uvicorn.logging \
  --hidden-import=uvicorn.loops.auto \
  --hidden-import=uvicorn.protocols.http.auto \
  --hidden-import=uvicorn.protocols.websockets.auto \
  --hidden-import=uvicorn.lifespan.on \
  --hidden-import=webview \
  --hidden-import=bs4 \
  --collect-submodules=universal \
  app.py

rm -rf Universal.app
if [[ -d dist/Universal.app ]]; then
  mv dist/Universal.app .
else
  echo "PyInstaller did not produce dist/Universal.app" >&2
  exit 1
fi

rm -rf build dist Universal.spec
echo "Universal.app is in the repo root. Drag it to Applications to install."
echo "Next: scripts/create_dmg.sh"
