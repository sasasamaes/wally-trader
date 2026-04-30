#!/usr/bin/env bash
# chainlink_price.sh — bash wrapper for chainlink_price.py (canonical Python).
# Cross-platform. Use .claude/scripts/win/chainlink_price.cmd for native Windows.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/chainlink_price.py"

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "ERROR: Python 3 not found in PATH" >&2; exit 99
fi

exec "$PY" "$PY_SCRIPT" "$@"
