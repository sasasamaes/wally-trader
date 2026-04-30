#!/usr/bin/env bash
# Wally Trader cross-platform setup launcher (macOS / Linux / Windows-Git-Bash)
# Equivalente a: python setup.py [--check|--quick]
# Para Windows native usar: .claude\scripts\win\setup.cmd
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "ERROR: Python 3.9+ no encontrado en PATH" >&2
  echo "  macOS:   brew install python3" >&2
  echo "  Linux:   sudo apt install python3 python3-pip" >&2
  echo "  Windows: instalar desde python.org y marcar 'Add to PATH'" >&2
  exit 99
fi

exec "$PY" "$SCRIPT_DIR/setup.py" "$@"
