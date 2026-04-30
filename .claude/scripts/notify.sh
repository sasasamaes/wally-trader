#!/usr/bin/env bash
# notify.sh — bash wrapper for notify.py (canonical Python, cross-platform).
# Funciona en macOS (osascript), Linux (notify-send), Windows (plyer/PowerShell).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/notify.py"

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "[NOTIFY] $1: $2" >&2; exit 1  # plain stderr fallback
fi

exec "$PY" "$PY_SCRIPT" "$@"
