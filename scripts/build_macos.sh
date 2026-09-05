#!/usr/bin/env bash
# Build the Universal desktop bundle. On macOS this produces Universal.app.
# Plugins (terminal, TTS, STT, vision, search, scraper) ship in the Python package;
# they are not copied as a second tree. Release builds bundle openai-whisper for STT.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# ffmpeg may live in Homebrew. Append so Actions/setup-python stays first.
if [[ -d /opt/homebrew/bin ]]; then
  export PATH="${PATH}:/opt/homebrew/bin"
fi

echo "Building Universal icons from the Ábaco mark…"
chmod +x scripts/make_icns.sh scripts/make_icon.py scripts/download_node.sh scripts/sign_macos.sh
./scripts/make_icns.sh
./scripts/download_node.sh

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
if ! grep -q "Abaco Universal Harness" web/dist/index.html; then
  echo "web/dist is the old face (missing Abaco Universal Harness)" >&2
  exit 1
fi
if grep -R -q "Write in the middle column" web/dist; then
  echo "web/dist still has the pre-Design Chat copy" >&2
  exit 1
fi
if ! grep -R -q "How can I help you today" web/dist; then
  echo "web/dist is missing the current Chat composer" >&2
  exit 1
fi

if ! python3 -c "import universal.desktop" >/dev/null 2>&1; then
  echo "Install the package first: python3 -m pip install -e '.[desktop,media]'" >&2
  exit 1
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Not macOS — skipping Universal.app (PyInstaller .app is Darwin-only)."
  echo "Checking the desktop factory + SPA on this machine…"
  python3 -m universal desktop --check --demo
  echo "On a Mac, re-run this script to produce Universal.app."
  exit 0
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg not found on PATH (required for Whisper STT in Universal.app)." >&2
  echo "Install ffmpeg (e.g. brew install ffmpeg) so it is on PATH, then re-run." >&2
  exit 1
fi

if ! python3 -c "import whisper" >/dev/null 2>&1; then
  echo "openai-whisper is required before packaging Universal.app." >&2
  echo "Install: python3 -m pip install -e '.[desktop,media]'" >&2
  exit 1
fi

echo "Packaging Universal.app with PyInstaller…"
python3 -m pip install -q 'pyinstaller>=6.0' 'pywebview>=5.0'

# onedir + windowed → a real .app. Collect whisper package code + data for STT.
# Do not add a second factory tree. The package is imported as universal.
ICON_ARGS=()
if [[ -f Universal.icns ]]; then
  ICON_ARGS+=(--icon Universal.icns --add-data "Universal.icns:.")
fi
DATA_ARGS=(--add-data "agent_runtime:agent_runtime")
if [[ -x Resources/node/bin/node ]]; then
  DATA_ARGS+=(--add-data "Resources/node:node")
fi

python3 -m PyInstaller \
  --noconfirm \
  --windowed \
  --name Universal \
  "${ICON_ARGS[@]}" \
  "${DATA_ARGS[@]}" \
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
  --collect-submodules=whisper \
  --collect-data=whisper \
  app.py

rm -rf Universal.app
if [[ -d dist/Universal.app ]]; then
  mv dist/Universal.app .
else
  echo "PyInstaller did not produce dist/Universal.app" >&2
  exit 1
fi

rm -rf build dist Universal.spec
python3 - <<'PY'
from pathlib import Path
import plistlib
path = Path("Universal.app/Contents/Info.plist")
if path.is_file():
    data = plistlib.loads(path.read_bytes())
    data["NSMicrophoneUsageDescription"] = (
        "Universal needs the microphone to record voice notes and transcribe them with Whisper."
    )
    data["NSCameraUsageDescription"] = (
        "Universal can attach a photo from the camera roll when you pick a file."
    )
    path.write_bytes(plistlib.dumps(data))
    print("Info.plist: microphone usage string added")
PY
./scripts/sign_macos.sh Universal.app
echo "Universal.app is in the repo root. Drag it to Applications to install."
echo "Next: scripts/create_dmg.sh"
