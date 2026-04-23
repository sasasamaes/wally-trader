#!/bin/bash
# Status line para sesión de trading — profile-aware, muestra cap, PnL, hora, ventana, trades

# ─────── Profile detection ───────
PROFILE_SCRIPT="$(dirname "$0")/profile.sh"
PROFILE="retail"
if [[ -x "$PROFILE_SCRIPT" ]]; then
  PROFILE="$(bash "$PROFILE_SCRIPT" get 2>/dev/null || echo "retail")"
fi
# ─────────────────────────────────

# ─────── Notion detection (opcional) ──
# Lee .env y verifica si ambas NOTION_*_DB_ID están llenas
NOTION_TAG=""
ENV_FILE="$(dirname "$0")/../.env"
if [[ -f "$ENV_FILE" ]]; then
  NOTION_RETAIL_DB=$(grep -E '^NOTION_RETAIL_DB_ID=' "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d ' "')
  NOTION_FTMO_DB=$(grep -E '^NOTION_FTMO_DB_ID=' "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d ' "')
  if [[ -n "$NOTION_RETAIL_DB" && -n "$NOTION_FTMO_DB" ]]; then
    NOTION_TAG=" • 📝 Notion ✓"
  fi
fi
# ─────────────────────────────────

# Determinar output según profile
if [[ "$PROFILE" == "ftmo" ]]; then
  CURVE="$(dirname "$0")/../profiles/ftmo/memory/equity_curve.csv"
  if [[ -f "$CURVE" && $(wc -l < "$CURVE") -gt 1 ]]; then
    LAST_EQ="$(tail -n1 "$CURVE" | cut -d',' -f2)"
    DAILY="$(python3 "$(dirname "$0")/guardian.py" --profile ftmo --action status --brief 2>/dev/null || echo "N/A")"
    EA_STATUS=$(python3 "$(dirname "$0")/mt5_bridge.py" ea-status 2>/dev/null || echo "EA N/A")
    echo "[FTMO \$10k] Equity: \$$LAST_EQ  •  $DAILY  •  $EA_STATUS$NOTION_TAG"
  else
    EA_STATUS=$(python3 "$(dirname "$0")/mt5_bridge.py" ea-status 2>/dev/null || echo "EA N/A")
    echo "[FTMO \$10k] Equity: \$10,000 (initial — run /equity)  •  $EA_STATUS$NOTION_TAG"
  fi
  exit 0
fi

# RETAIL path (preserva comportamiento actual)
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

# Single line output (preserva formato retail original + profile tag + notion tag)
printf "%s[RETAIL]%s %s💰 \$%s%s %s(%s\$%s)%s │ 📊 %s/3 │ %s%s%s │ 🕐 MX %s │ %sBTC.P%s%s" \
    "$BOLD" "$RESET" \
    "$BOLD" "$CAP" "$RESET" \
    "$DELTA_COLOR" "$DELTA_SIGN" "$DELTA" "$RESET" \
    "$TRADES_HOY" \
    "$VCOLOR" "$VENTANA" "$RESET" \
    "$HORA_MX" \
    "$YELLOW" "$RESET" \
    "$NOTION_TAG"
