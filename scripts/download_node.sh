#!/usr/bin/env bash
# Fetch a macOS Node binary into Resources/node for the signed app.
# Linux / CI skip this — serve uses the system node.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "download_node.sh is for macOS. On this machine the runtime uses PATH node."
  exit 0
fi

ARCH="$(uname -m)"
case "$ARCH" in
  arm64) DIST="darwin-arm64" ;;
  x86_64) DIST="darwin-x64" ;;
  *) echo "Unsupported Mac arch: $ARCH" >&2; exit 1 ;;
esac

VERSION="20.18.1"
PREFIX="node-v${VERSION}-${DIST}"
DEST="$ROOT/Resources/node"
mkdir -p "$DEST"
if [[ -x "$DEST/bin/node" ]]; then
  echo "Node already present at $DEST/bin/node"
  exit 0
fi

curl -fsSL "https://nodejs.org/dist/v${VERSION}/${PREFIX}.tar.gz" | tar -xz -C "$DEST" --strip-components=1
test -x "$DEST/bin/node"
echo "Bundled $PREFIX into Resources/node"
