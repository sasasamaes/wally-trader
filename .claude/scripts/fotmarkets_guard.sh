#!/usr/bin/env bash
# fotmarkets_guard.sh — bash wrapper for fotmarkets_guard.py (canonical Python).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/fotmarkets_guard.py"

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "BLOCK: Python 3 not found" >&2; exit 1
fi

exec "$PY" "$PY_SCRIPT" "$@"
