#!/bin/bash
# Status line para sesión de trading — profile-aware, muestra cap, PnL, hora, ventana, trades

# ─────── Profile detection ───────
PROFILE_SCRIPT="$(dirname "$0")/profile.sh"
PROFILE="retail"
if [[ -x "$PROFILE_SCRIPT" ]]; then
  PROFILE="$(bash "$PROFILE_SCRIPT" get 2>/dev/null || echo "retail")"
fi
# ─────────────────────────────────

# ─────── FX rate USD→CRC (Costa Rica colones) ───────
FX_SCRIPT="$(dirname "$0")/fx_rate.sh"
USD_CRC_RATE=""
if [[ -x "$FX_SCRIPT" ]]; then
  USD_CRC_RATE="$(bash "$FX_SCRIPT" 2>/dev/null)"
fi

# Convierte $USD a string ₡CRC con format "8,241" o "4.7M" si > 1M
usd_to_crc() {
  local usd="$1"
  if [[ -z "$USD_CRC_RATE" || -z "$usd" ]]; then
    echo ""
    return
  fi
  python3 -c "
usd = float('${usd}'); rate = float('${USD_CRC_RATE}'); crc = usd * rate
if crc >= 1_000_000:
    print(f'≈₡{crc/1_000_000:.1f}M')
elif crc >= 10_000:
    print(f'≈₡{crc:,.0f}')
else:
    print(f'≈₡{crc:,.0f}')
" 2>/dev/null
}
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
    CRC_TAG="$(usd_to_crc "$LAST_EQ")"
    [[ -n "$CRC_TAG" ]] && CRC_TAG=" $CRC_TAG"
    DAILY="$(python3 "$(dirname "$0")/guardian.py" --profile ftmo --action status --brief 2>/dev/null || echo "N/A")"
    EA_STATUS=$(python3 "$(dirname "$0")/mt5_bridge.py" ea-status 2>/dev/null || echo "EA N/A")
    echo "[FTMO \$10k] Equity: \$$LAST_EQ$CRC_TAG  •  $DAILY  •  $EA_STATUS$NOTION_TAG"
  else
    CRC_TAG="$(usd_to_crc "10000")"
    [[ -n "$CRC_TAG" ]] && CRC_TAG=" $CRC_TAG"
    EA_STATUS=$(python3 "$(dirname "$0")/mt5_bridge.py" ea-status 2>/dev/null || echo "EA N/A")
    echo "[FTMO \$10k] Equity: \$10,000$CRC_TAG (initial — run /equity)  •  $EA_STATUS$NOTION_TAG"
  fi
  exit 0
fi

# FUNDINGPIPS path (Zero $10k — direct funded MT5)
if [[ "$PROFILE" == "fundingpips" ]]; then
  SCRIPT_DIR="$(dirname "$0")"
  CURVE="$SCRIPT_DIR/../profiles/fundingpips/memory/equity_curve.csv"
  LOG="$SCRIPT_DIR/../profiles/fundingpips/memory/trading_log.md"

  # Equity actual (default $10,000 si curve vacía)
  if [[ -f "$CURVE" && $(wc -l < "$CURVE") -gt 1 ]]; then
    LAST_EQ="$(tail -n1 "$CURVE" | cut -d',' -f2)"
  else
    LAST_EQ="10000.00"
  fi

  # Total DD vs balance inicial fijo $10k
  DD_PCT=$(python3 -c "eq=float('${LAST_EQ}'); init=10000; print(f'{((eq-init)/init)*100:+.2f}')" 2>/dev/null || echo "0.00")

  # Daily PnL (compara primera entrada de hoy con última)
  FECHA=$(TZ='America/Costa_Rica' date +%Y-%m-%d)
  DAILY_PCT="0.00"
  if [[ -f "$CURVE" ]] && [[ $(wc -l < "$CURVE") -gt 1 ]]; then
    DAILY_PCT=$(awk -F',' -v f="$FECHA" 'BEGIN{first="";last=""} $1 ~ f {if(first=="") first=$2; last=$2} END{if(first!="" && last!="" && first+0!=0) printf "%+.2f", ((last-first)/first)*100; else print "0.00"}' "$CURVE")
  fi

  # Trades hoy
  TRADES_HOY=0
  if [[ -f "$LOG" ]]; then
    TRADES_HOY=$(grep -c "^| $FECHA " "$LOG" 2>/dev/null || true)
    TRADES_HOY=${TRADES_HOY:-0}
  fi

  # Conversión a CRC
  CRC_TAG="$(usd_to_crc "$LAST_EQ")"
  [[ -n "$CRC_TAG" ]] && CRC_TAG=" $CRC_TAG"

  # Ventana CR 06:00-16:00 (forex/indices) — crypto extiende a 20:00
  HORA_CR=$(TZ='America/Costa_Rica' date +%H:%M)
  HORA_HHMM=$(TZ='America/Costa_Rica' date +%H%M)
  HORA_NUM=$((10#$HORA_HHMM))
  if (( HORA_NUM >= 600 && HORA_NUM < 1600 )); then
    VENTANA="🟢 VENT"
  elif (( HORA_NUM >= 1600 && HORA_NUM < 2000 )); then
    VENTANA="🟡 CRYPTO"
  else
    VENTANA="🔴 OFF"
  fi

  # Color del DD según severidad
  DD_COLOR=""
  if awk "BEGIN {exit !($DD_PCT <= -3)}"; then
    DD_COLOR="🔴"  # BLOCK zone
  elif awk "BEGIN {exit !($DD_PCT <= -2)}"; then
    DD_COLOR="🟡"  # WARN zone
  else
    DD_COLOR="🟢"
  fi

  echo "[FUNDINGPIPS \$10k] \$$LAST_EQ$CRC_TAG | DD ${DD_COLOR}${DD_PCT}% | Daily ${DAILY_PCT}% | $VENTANA CR $HORA_CR | $TRADES_HOY/2 trades$NOTION_TAG"
  exit 0
fi

# FOTMARKETS path
if [[ "$PROFILE" == "fotmarkets" ]]; then
  SCRIPT_DIR="$(dirname "$0")"
  PROGRESS="$SCRIPT_DIR/../profiles/fotmarkets/memory/phase_progress.md"
  LOG="$SCRIPT_DIR/../profiles/fotmarkets/memory/trading_log.md"

  CAP=$(grep -E '^capital_current:' "$PROGRESS" 2>/dev/null | awk '{print $2}' | tr -d ' ')
  CAP=${CAP:-30.00}

  PHASE=$(bash "$SCRIPT_DIR/fotmarkets_phase.sh" 2>/dev/null || echo "1")
  case "$PHASE" in
    1) NEXT_THRESHOLD="→\$100"; MAX_TRADES=1 ;;
    2) NEXT_THRESHOLD="→\$300"; MAX_TRADES=2 ;;
    3) NEXT_THRESHOLD="estándar"; MAX_TRADES=3 ;;
  esac

  HORA_CR=$(TZ='America/Costa_Rica' date +%H:%M)
  FECHA=$(TZ='America/Costa_Rica' date +%Y-%m-%d)

  TRADES_HOY=0
  if [[ -f "$LOG" ]]; then
    TRADES_HOY=$(grep -c "^| $FECHA " "$LOG" 2>/dev/null || true)
    TRADES_HOY=${TRADES_HOY:-0}
  fi

  # Ventana 07:00-11:00 (octal-safe con 10#)
  HORA_HHMM=$(TZ='America/Costa_Rica' date +%H%M)
  if (( 10#$HORA_HHMM >= 700 && 10#$HORA_HHMM <= 1055 )); then
    VENTANA="🟢 VENT"
  elif (( 10#$HORA_HHMM > 1055 && 10#$HORA_HHMM <= 1100 )); then
    VENTANA="🟡 CLOSE"
  else
    VENTANA="🔴 OFF"
  fi

  CRC_TAG="$(usd_to_crc "$CAP")"
  [[ -n "$CRC_TAG" ]] && CRC_TAG=" $CRC_TAG"
  echo "[FOTMARKETS] \$$CAP$CRC_TAG | Fase $PHASE ($NEXT_THRESHOLD) | $VENTANA CR $HORA_CR | $TRADES_HOY/$MAX_TRADES trades$NOTION_TAG"
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

# Hora CR (UTC-6)
HORA_CR=$(TZ='America/Costa_Rica' date +%H:%M)
HORA_NUM=$(TZ='America/Costa_Rica' date +%H)
HORA_NUM=${HORA_NUM#0}  # remove leading zero

# Ventana CR 06:00-23:59 (cripto 24/7, trader no duerme con trade abierto)
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
FECHA=$(TZ='America/Costa_Rica' date +%Y-%m-%d)
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

# Conversión a CRC
CRC_TAG="$(usd_to_crc "$CAP")"
[[ -n "$CRC_TAG" ]] && CRC_DISPLAY=" $CRC_TAG" || CRC_DISPLAY=""

# Single line output (preserva formato retail original + profile tag + CRC + notion tag)
printf "%s[RETAIL]%s %s💰 \$%s%s%s %s(%s\$%s)%s │ 📊 %s/3 │ %s%s%s │ 🕐 CR %s │ %sBTC.P%s%s" \
    "$BOLD" "$RESET" \
    "$BOLD" "$CAP" "$RESET" "$CRC_DISPLAY" \
    "$DELTA_COLOR" "$DELTA_SIGN" "$DELTA" "$RESET" \
    "$TRADES_HOY" \
    "$VCOLOR" "$VENTANA" "$RESET" \
    "$HORA_CR" \
    "$YELLOW" "$RESET" \
    "$NOTION_TAG"
