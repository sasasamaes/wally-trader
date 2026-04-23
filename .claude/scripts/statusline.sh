#!/bin/bash
# Status line para sesión de trading — muestra cap, PnL, hora, ventana, trades

MEMORY_DIR="$HOME/.claude/projects/<project-path-encoded>/memory"
TRADING_LOG="$MEMORY_DIR/trading_log.md"

# Capital: busca "Capital actual: $X.XX" o "PnL neto: +$X.XX" para inferir progreso
CAP=""
if [ -f "$TRADING_LOG" ]; then
    # Patrón preferido: "Capital actual: $X.XX"
    CAP=$(grep -oE 'Capital (actual|running|final)[: ]+\$[0-9]+\.[0-9]+' "$TRADING_LOG" 2>/dev/null | tail -1 | grep -oE '[0-9]+\.[0-9]+')
    # Fallback: "$X.XX" al final de "Capital: $X → $X" pattern
    [ -z "$CAP" ] && CAP=$(grep -oE 'Capital:.*\$[0-9]+\.[0-9]+' "$TRADING_LOG" 2>/dev/null | tail -1 | grep -oE '\$[0-9]+\.[0-9]+' | tail -1 | tr -d '$')
    # Fallback 2: último valor dinero del log
    [ -z "$CAP" ] && CAP=$(grep -oE '\$[0-9]+\.[0-9]+' "$TRADING_LOG" 2>/dev/null | tail -1 | tr -d '$')
fi
CAP=${CAP:-13.63}

# Hora MX (UTC-6)
HORA_MX=$(TZ='America/Mexico_City' date +%H:%M)
HORA_NUM=$(TZ='America/Mexico_City' date +%H)
HORA_NUM=${HORA_NUM#0}  # remove leading zero

# Ventana MX 06:00-23:59 (cripto 24/7, trader no duerme con trade abierto)
if [ "$HORA_NUM" -ge 6 ] 2>/dev/null && [ "$HORA_NUM" -le 23 ] 2>/dev/null; then
    VENTANA="🟢 VENT"
    VCOLOR=$'\e[0;32m'
    # Aviso de cierre próximo (22:00-23:59)
    if [ "$HORA_NUM" -ge 22 ] 2>/dev/null; then
        VENTANA="🟡 CLOSE"
        VCOLOR=$'\e[0;33m'
    fi
else
    # 00:00-05:59 = fuera de ventana (dormir)
    VENTANA="🔴 OFF"
    VCOLOR=$'\e[0;31m'
fi

# Fecha + trades hoy
FECHA=$(TZ='America/Mexico_City' date +%Y-%m-%d)
TRADES_HOY=0
if [ -f "$TRADING_LOG" ]; then
    TRADES_HOY=$(grep -c "${FECHA}" "$TRADING_LOG" 2>/dev/null)
    TRADES_HOY=${TRADES_HOY:-0}
fi

# Colors
RESET=$'\e[0m'
BOLD=$'\e[1m'
YELLOW=$'\e[0;33m'
GREEN=$'\e[0;32m'

# Delta desde $10 inicial
INICIAL="10.00"
DELTA=$(echo "scale=2; $CAP - $INICIAL" | bc 2>/dev/null || echo "0")
if awk "BEGIN {exit !($CAP >= $INICIAL)}"; then
    DELTA_COLOR=$GREEN
    DELTA_SIGN="+"
else
    DELTA_COLOR=$'\e[0;31m'
    DELTA_SIGN=""
fi

# Single line output (no newlines)
printf "%s💰 \$%s%s %s(%s\$%s)%s │ 📊 %s/3 │ %s%s%s │ 🕐 MX %s │ %sBTC.P%s" \
    "$BOLD" "$CAP" "$RESET" \
    "$DELTA_COLOR" "$DELTA_SIGN" "$DELTA" "$RESET" \
    "$TRADES_HOY" \
    "$VCOLOR" "$VENTANA" "$RESET" \
    "$HORA_MX" \
    "$YELLOW" "$RESET"
