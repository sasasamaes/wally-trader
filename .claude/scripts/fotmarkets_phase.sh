#!/usr/bin/env bash
# fotmarkets_phase.sh — bash wrapper for fotmarkets_phase.py (canonical Python).
# Cross-platform: macOS/Linux native, Windows via Git Bash.
# Use .claude/scripts/win/fotmarkets_phase.cmd for native Windows.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/fotmarkets_phase.py"

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "ERROR: Python 3 not found in PATH" >&2; exit 99
fi

exec "$PY" "$PY_SCRIPT" "$@"
