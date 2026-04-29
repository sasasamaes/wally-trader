#!/bin/bash
# Cron matutino: se ejecuta 5:30 AM L-V para preparar análisis
# Instalación:
#   crontab -e
#   30 5 * * 1-5 ~/Documents/wally-trader/.claude/scripts/daily_cron.sh

LOG="$HOME/Documents/wally-trader/.claude/scripts/cron.log"
FECHA=$(TZ='America/Costa_Rica' date +'%Y-%m-%d %H:%M')

echo "[$FECHA] Cron matutino iniciado" >> "$LOG"

# Notificación macOS para despertar al usuario
osascript -e 'display notification "Rutina de trading 5:30 AM. Abre Claude y pega /morning" with title "🌅 Trading Matutino" sound name "Glass"'

# Si Claude Code CLI está disponible, pre-carga análisis en background
# (Nota: requiere configurar autenticación)
# claude -p "/morning" >> "$LOG" 2>&1 &

echo "[$FECHA] Notificación enviada" >> "$LOG"
