#!/usr/bin/env bash
# Wipe every local Abaco Harness / leftover Universal install and user-data on THIS Mac.
# Two computers never share these folders. GitHub always serves the same Abaco-Harness.dmg.
# Application Support stays under Universal so a wipe still clears the existing registry.
# Run this on the Mac that still shows the old Chat face, then install into /Applications only.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This wipe script is for macOS." >&2
  exit 1
fi

echo "Quitting Abaco Harness..."
killall "Abaco Harness" 2>/dev/null || true
killall Universal 2>/dev/null || true
pkill -f "/Applications/Abaco Harness.app" 2>/dev/null || true
pkill -f "/Applications/Universal.app" 2>/dev/null || true
sleep 1

echo "Ejecting mounted Abaco Harness / leftover Universal DMGs..."
for volume in "/Volumes/Abaco Harness" /Volumes/Universal /Volumes/Universal\ *; do
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
for bundle in "Abaco Harness.app" "Universal.app"; do
  remove_if_exists "/Applications/${bundle}"
  remove_if_exists "$HOME/Downloads/${bundle}"
  remove_if_exists "$HOME/Desktop/${bundle}"
  remove_if_exists "$HOME/Documents/${bundle}"
  remove_if_exists "$HOME/${bundle}"
done
remove_if_exists "$HOME/Downloads/Abaco-Harness.dmg"
remove_if_exists "$HOME/Desktop/Abaco-Harness.dmg"
remove_if_exists "$HOME/Downloads/Universal.dmg"
remove_if_exists "$HOME/Desktop/Universal.dmg"

if command -v mdfind >/dev/null 2>&1; then
  while IFS= read -r found; do
    [ -z "$found" ] && continue
    case "$found" in
      /Volumes/*) echo "  skipping mounted image $found" ;;
      *"Abaco Harness.app"|*Universal.app) remove_if_exists "$found" ;;
    esac
  done < <(mdfind 'kMDItemFSName == "Abaco Harness.app" || kMDItemFSName == "Universal.app"' 2>/dev/null || true)
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
  "$HOME/Library/Caches/Abaco Harness" \
  "$HOME/Library/Caches/pywebview" \
  "$HOME/Library/Caches/"*pywebview* \
  "$HOME/Library/Caches/"*pyinstaller* \
  "$HOME/Library/Caches/"*PyInstaller* \
  "$HOME/Library/WebKit/com.universal"* \
  "$HOME/Library/WebKit/Universal" \
  "$HOME/Library/WebKit/Abaco Harness" \
  "$HOME/Library/WebKit/"*pywebview* \
  "$HOME/Library/WebKit/"*pyinstaller* \
  "$HOME/Library/WebKit/"*PyInstaller* \
  "$HOME/Library/HTTPStorages/com.universal"* \
  "$HOME/Library/HTTPStorages/Universal" \
  "$HOME/Library/HTTPStorages/Abaco Harness" \
  "$HOME/Library/HTTPStorages/"*pywebview* \
  "$HOME/Library/HTTPStorages/"*pyinstaller* \
  "$HOME/Library/HTTPStorages/"*PyInstaller* \
  "$HOME/Library/Saved Application State/"*Universal* \
  "$HOME/Library/Saved Application State/"*Abaco* \
  "$HOME/Library/Preferences/com.universal"* \
  "$HOME/Library/Preferences/org.pywebview"* \
  "$HOME/Library/Logs/Universal" \
  "$HOME/Library/Logs/Abaco Harness" \
  "$HOME/Library/Application Support/pywebview"
do
  remove_if_exists "$path"
done

echo
echo "This Mac is clean. Next:"
echo "  1. Download ONLY this file from Releases:"
echo "     Abaco-Harness.dmg"
echo "  2. Open the DMG and drag Abaco Harness.app to /Applications (not Downloads)."
echo "  3. Eject the DMG. Delete Abaco-Harness.dmg from Downloads."
echo "  4. Open Spotlight, type Abaco Harness, confirm the path is /Applications/Abaco Harness.app"
echo "  5. Header must say Abaco Harness."
echo "     If you see Universal Platform + Templates/Face, you opened a leftover copy."
