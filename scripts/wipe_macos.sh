#!/usr/bin/env bash
# Wipe every local Universal install and user-data on THIS Mac.
# Two computers never share these folders. GitHub always serves the same Universal.dmg.
# Run this on the Mac that still shows the old Chat face, then install 1.2.3 into /Applications only.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This wipe script is for macOS." >&2
  exit 1
fi

echo "Quitting Universal..."
killall Universal 2>/dev/null || true
pkill -f "/Applications/Universal.app" 2>/dev/null || true
sleep 1

echo "Ejecting mounted Universal DMGs..."
for volume in /Volumes/Universal /Volumes/Universal\ *; do
  [ -d "$volume" ] || continue
  echo "  ejecting $volume"
  hdiutil detach "$volume" -force >/dev/null 2>&1 || true
done

remove_if_exists() {
  local path="$1"
  if [ -e "$path" ]; then
    echo "  removing $path"
    rm -rf "$path"
  fi
}

echo "Removing app bundles and leftover DMGs..."
remove_if_exists "/Applications/Universal.app"
remove_if_exists "$HOME/Downloads/Universal.app"
remove_if_exists "$HOME/Desktop/Universal.app"
remove_if_exists "$HOME/Documents/Universal.app"
remove_if_exists "$HOME/Universal.app"
remove_if_exists "$HOME/Downloads/Universal.dmg"
remove_if_exists "$HOME/Desktop/Universal.dmg"

if command -v mdfind >/dev/null 2>&1; then
  while IFS= read -r found; do
    [ -z "$found" ] && continue
    case "$found" in
      /Volumes/*) echo "  skipping mounted image $found" ;;
      *Universal.app) remove_if_exists "$found" ;;
    esac
  done < <(mdfind 'kMDItemFSName == "Universal.app"' 2>/dev/null || true)
fi

echo "Removing user data (chats, keys, registry)..."
remove_if_exists "$HOME/Library/Application Support/Universal"
remove_if_exists "$HOME/.local/share/universal"
remove_if_exists "$HOME/.universal"
remove_if_exists "$HOME/.abaco_rules.json"

echo "Removing WebKit / HTTP caches..."
shopt -s nullglob
for path in \
  "$HOME/Library/Caches/com.universal"* \
  "$HOME/Library/Caches/Universal" \
  "$HOME/Library/Caches/pywebview" \
  "$HOME/Library/WebKit/com.universal"* \
  "$HOME/Library/WebKit/Universal" \
  "$HOME/Library/HTTPStorages/com.universal"* \
  "$HOME/Library/HTTPStorages/Universal" \
  "$HOME/Library/Saved Application State/"*Universal* \
  "$HOME/Library/Preferences/com.universal"* \
  "$HOME/Library/Preferences/org.pywebview"* \
  "$HOME/Library/Logs/Universal" \
  "$HOME/Library/Application Support/pywebview"
do
  remove_if_exists "$path"
done

echo
echo "This Mac is clean. Next:"
echo "  1. Download ONLY this file:"
echo "     https://github.com/anthony-x507/Abaco-Universal-harnes-/releases/download/v1.2.3/Universal.dmg"
echo "  2. Open the DMG and drag Universal.app to /Applications (not Downloads)."
echo "  3. Eject the DMG. Delete Universal.dmg from Downloads."
echo "  4. Open Spotlight, type Universal, confirm the path is /Applications/Universal.app"
echo "  5. Header must say Abaco Universal Harness and 1.2.3."
echo "     If you see Universal Platform + Templates/Face, you opened a leftover copy."
