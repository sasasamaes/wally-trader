#!/usr/bin/env bash
# fx_rate.sh — bash wrapper for fx_rate.py (canonical Python).
# Cross-platform: macOS/Linux/Windows-Git-Bash. Use .claude/scripts/win/fx_rate.cmd for native Windows.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/fx_rate.py"

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "510" ; exit 1  # hardcode fallback if no python
fi

exec "$PY" "$PY_SCRIPT" "$@"
