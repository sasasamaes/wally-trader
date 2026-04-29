#!/bin/bash
# Script de notificaciones macOS para alertas de trading
# Uso: ./notify.sh "título" "mensaje" [sonido]

TITULO="${1:-Trading Alert}"
MENSAJE="${2:-Revisa el chart}"
SONIDO="${3:-Glass}"

# Notificación nativa macOS con sonido
osascript -e "display notification \"${MENSAJE}\" with title \"${TITULO}\" sound name \"${SONIDO}\""

# Log para historial
FECHA=$(TZ='America/Costa_Rica' date +'%Y-%m-%d %H:%M:%S')
echo "[${FECHA}] ${TITULO}: ${MENSAJE}" >> ~/Documents/wally-trader/.claude/scripts/notifications.log
