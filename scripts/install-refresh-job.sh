#!/usr/bin/env bash
#
# Install (or reinstall) the weekly `contention refresh` launchd job for this checkout.
# Run with --uninstall to remove it.

set -euo pipefail

LABEL=local.contention.refresh
REPO=$(cd "$(dirname "$0")/.." && pwd)
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true

if [[ "${1:-}" == "--uninstall" ]]; then
  rm -f "$TARGET"
  echo "Removed the weekly refresh job."
  exit 0
fi

UV=$(command -v uv) || { echo "uv not found on PATH; install it first." >&2; exit 1; }
mkdir -p "$HOME/Library/LaunchAgents" "$REPO/artefacts"
sed -e "s|__REPO__|$REPO|g" -e "s|__UV__|$UV|g" "$REPO/scripts/launchd/$LABEL.plist" > "$TARGET"
plutil -lint "$TARGET" >/dev/null
launchctl bootstrap "$DOMAIN" "$TARGET"

echo "Installed: contention refresh runs Sundays at 03:00."
echo "Run it now with: launchctl kickstart $DOMAIN/$LABEL"
echo "Output goes to $REPO/artefacts/run-<UTC timestamp>.launchd.log"
