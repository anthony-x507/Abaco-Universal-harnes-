#!/usr/bin/env bash
# Install Universal on this Mac from a source checkout or unzipped release.
# This is not Universal.app (that is built on macOS with scripts/build_macos.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This installer is for macOS." >&2
  exit 1
fi

if ! command -v python3 >/dev/null; then
  echo "Install Python 3.11+ from https://www.python.org/downloads/macos/" >&2
  exit 1
fi

pyver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit(f"Python 3.11+ required, found {sys.version.split()[0]}")
PY

if ! command -v bun >/dev/null; then
  echo "Installing Bun…"
  curl -fsSL https://bun.sh/install | bash
  export PATH="$HOME/.bun/bin:$PATH"
fi

python3 -m pip install -e ".[desktop]"
(
  cd web
  bun install
  bun run build
)

if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — add UNIVERSAL_LLM_API_KEY for live models."
fi

echo
echo "Installed. Demo window (no API key):"
echo "  python3 -m universal desktop --demo"
echo "Factory only:"
echo "  python3 -m universal serve --demo --host 127.0.0.1 --port 43124"
echo "Then open http://127.0.0.1:43124"
