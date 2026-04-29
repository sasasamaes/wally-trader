#!/bin/bash
# Hook Stop: auto-commit del journal si hay cambios al cerrar Claude

cd ~/Documents/trading || exit 0

# Solo si es repo git
[ -d .git ] || exit 0

# Verifica cambios específicos en archivos de journal/tracking
CHANGED=$(git diff --name-only HEAD 2>/dev/null | grep -E "DAILY_TRADING_JOURNAL|trading_log")

if [ -n "$CHANGED" ]; then
    FECHA=$(TZ='America/Costa_Rica' date +%Y-%m-%d)
    git add DAILY_TRADING_JOURNAL.md 2>/dev/null
    git commit -m "journal: auto-save sesión ${FECHA}" --no-verify 2>/dev/null
    echo "✓ Journal auto-commit"
fi

exit 0
