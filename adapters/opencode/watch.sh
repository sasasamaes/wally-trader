#!/usr/bin/env bash
# adapters/opencode/watch.sh
# Watches system/ for changes and regenerates .opencode/ in real-time.
# Requires: brew install fswatch

set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"

if ! command -v fswatch >/dev/null 2>&1; then
  echo "❌ fswatch not installed."
  echo "   Install: brew install fswatch"
  exit 1
fi

echo "👀 Watching $REPO/system/ for changes... (Ctrl+C to stop)"
fswatch -o "$REPO/system/commands" "$REPO/system/agents" "$REPO/system/mcp" | while read -r _; do
  if python3 "$REPO/adapters/opencode/transform.py" 2>&1 | tail -1; then
    echo "  $(date +%H:%M:%S) • re-synced"
  fi
done
