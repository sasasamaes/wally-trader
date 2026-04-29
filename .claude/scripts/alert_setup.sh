#!/bin/bash
# Monitor de setup: chequea cada 60s si los 4 filtros se alinean, notifica si sí.
# Uso: ./alert_setup.sh [duración_horas]  (default 6h)

DURATION_HOURS=${1:-6}
DURATION_SEC=$((DURATION_HOURS * 3600))
START=$(date +%s)
END=$((START + DURATION_SEC))

echo "🔔 Alerta activa por $DURATION_HOURS horas — busca setup 4/4 filtros"
echo "PID: $$ (guarda este número para matar el proceso con: kill $$)"

while [ "$(date +%s)" -lt "$END" ]; do
    # Placeholder: aquí iría lógica real de chequeo via MCP
    # Por ahora solo notifica cada hora "monitor activo"
    HORA=$(TZ='America/Costa_Rica' date +%H:%M)

    # TODO: integrar con MCP TV para leer precio + Donchian + RSI + BB
    # Si 4/4 filtros alinean → osascript notify

    sleep 60
done

osascript -e 'display notification "Monitor de setup expirado" with title "Trading Alert"'
