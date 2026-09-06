#!/usr/bin/env bash
# Build the Abaco Coding Harness desktop bundle. On macOS this produces Abaco Coding Harness.app.
# Plugins (terminal, TTS, STT, vision, search, scraper) ship in the Python package;
# they are not copied as a second tree. Release builds bundle openai-whisper for STT.
# The Python package, console script, and env vars stay `universal` / UNIVERSAL_*.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_BUNDLE="Abaco Coding Harness.app"

# ffmpeg may live in Homebrew. Append so Actions/setup-python stays first.
if [[ -d /opt/homebrew/bin ]]; then
  export PATH="${PATH}:/opt/homebrew/bin"
fi

echo "Building Abaco Coding Harness icons from the Ábaco mark…"
chmod +x scripts/make_icns.sh scripts/make_icon.py scripts/download_node.sh scripts/sign_macos.sh
./scripts/make_icns.sh
./scripts/download_node.sh

echo "Building Abaco Coding Harness web face…"
(
  cd web
  bun install
  bun run build
)

if [[ ! -f web/dist/index.html ]]; then
  echo "web/dist/index.html missing after build" >&2
  exit 1
fi
if ! grep -q "Abaco Coding Harness" web/dist/index.html; then
  echo "web/dist is the old face (missing Abaco Coding Harness)" >&2
  exit 1
fi
if grep -q "Abaco Universal Harness" web/dist/index.html; then
  echo "web/dist still has the old Abaco Universal Harness product name" >&2
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
  echo "Not macOS — skipping ${APP_BUNDLE} (PyInstaller .app is Darwin-only)."
  echo "Checking the desktop factory + SPA on this machine…"
  python3 -m universal desktop --check --demo
  echo "On a Mac, re-run this script to produce ${APP_BUNDLE}."
  exit 0
fi

# ffmpeg is a runtime helper on the user's Mac, not a build input: PyInstaller does
# not bundle system binaries, so a missing ffmpeg here must never fail the release.
# Recorded WAV goes through universal/audio_io.py, which decodes without ffmpeg.
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "note: ffmpeg is not on PATH. WAV transcription still works; other formats"
  echo "note: need 'brew install ffmpeg' on the machine running ${APP_BUNDLE}."
fi

if ! python3 -c "import whisper" >/dev/null 2>&1; then
  echo "openai-whisper is required before packaging ${APP_BUNDLE}." >&2
  echo "Install: python3 -m pip install -e '.[desktop,media]'" >&2
  exit 1
fi

echo "Packaging ${APP_BUNDLE} with PyInstaller…"
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
  --name "Abaco Coding Harness" \
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

rm -rf "${APP_BUNDLE}"
if [[ -d "dist/${APP_BUNDLE}" ]]; then
  mv "dist/${APP_BUNDLE}" .
else
  echo "PyInstaller did not produce dist/${APP_BUNDLE}" >&2
  exit 1
fi

rm -rf build dist "Abaco Coding Harness.spec"
python3 - <<'PY'
from pathlib import Path
import plistlib
path = Path("Abaco Coding Harness.app/Contents/Info.plist")
if path.is_file():
    data = plistlib.loads(path.read_bytes())
    data["CFBundleName"] = "Abaco Coding Harness"
    data["CFBundleDisplayName"] = "Abaco Coding Harness"
    data["NSMicrophoneUsageDescription"] = (
        "Abaco Coding Harness needs the microphone to record voice notes and transcribe them with Whisper."
    )
    data["NSCameraUsageDescription"] = (
        "Abaco Coding Harness can attach a photo from the camera roll when you pick a file."
    )
    path.write_bytes(plistlib.dumps(data))
    print("Info.plist: display name and microphone usage string added")
PY
./scripts/sign_macos.sh "${APP_BUNDLE}"
echo "${APP_BUNDLE} is in the repo root. Drag it to Applications to install."
echo "Next: scripts/create_dmg.sh"
