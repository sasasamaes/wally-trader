#!/usr/bin/env bash
# .claude/scripts/fotmarkets_guard.sh
# Lite Guardian — valida condiciones antes de entrada en profile fotmarkets
#
# Uso:
#   fotmarkets_guard.sh check
#     → imprime "PASS" y sale 0, O "BLOCK: <razón>" y sale 1
#
# Checks:
#   1. Hora MX ∈ [07:00, 10:55]
#   2. Trades hoy < max_trades_per_day de la fase
#   3. SLs consecutivos < max_sl_consecutive de la fase
#   4. No es weekend (sábado/domingo MX)

set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"
PROFILE_DIR="$SCRIPT_DIR/../profiles/fotmarkets"
PHASE_SCRIPT="$SCRIPT_DIR/fotmarkets_phase.sh"
LOG_FILE="$PROFILE_DIR/memory/trading_log.md"

fail() {
  echo "BLOCK: $1"
  exit 1
}

pass() {
  echo "PASS"
  exit 0
}

# Check 1: Ventana horaria MX
HORA_HHMM=$(TZ='America/Mexico_City' date +%H%M)
if [[ "$HORA_HHMM" -lt 700 || "$HORA_HHMM" -gt 1055 ]]; then
  fail "Fuera de ventana operativa MX 07:00-10:55 (hora actual: ${HORA_HHMM:0:2}:${HORA_HHMM:2:2})"
fi

# Check 2: Weekend
DOW=$(TZ='America/Mexico_City' date +%u)   # 1=Mon ... 7=Sun
if [[ "$DOW" -ge 6 ]]; then
  fail "Weekend: mercados Forex cerrados (día $DOW)"
fi

# Check 3: Phase detection
PHASE=$(bash "$PHASE_SCRIPT" 2>/dev/null || echo "1")

# Mapea fase → max_trades y max_sl_consecutive
case "$PHASE" in
  1) MAX_TRADES=1; MAX_SL_CONSEC=1 ;;
  2) MAX_TRADES=2; MAX_SL_CONSEC=2 ;;
  3) MAX_TRADES=3; MAX_SL_CONSEC=2 ;;
  *) fail "Fase desconocida: $PHASE" ;;
esac

# Check 4: Trades hoy
FECHA=$(TZ='America/Mexico_City' date +%Y-%m-%d)
TRADES_HOY=0
if [[ -f "$LOG_FILE" ]]; then
  TRADES_HOY=$(grep -c "^| $FECHA " "$LOG_FILE" 2>/dev/null || echo 0)
  TRADES_HOY=${TRADES_HOY:-0}
fi

if [[ "$TRADES_HOY" -ge "$MAX_TRADES" ]]; then
  fail "Max trades/día alcanzado en Fase $PHASE: $TRADES_HOY/$MAX_TRADES"
fi

# Check 5: SL consecutivos (últimos N trades hoy)
if [[ -f "$LOG_FILE" && "$TRADES_HOY" -ge "$MAX_SL_CONSEC" ]]; then
  # Extrae columna "Resultado" (8ª columna separada por |) de últimos N trades del día
  LAST_N_RESULTS=$(grep "^| $FECHA " "$LOG_FILE" | tail -n "$MAX_SL_CONSEC" \
    | awk -F'|' '{ gsub(/ /, "", $10); print tolower($10) }')

  CONSEC_SL=true
  while IFS= read -r line; do
    if [[ "$line" != "sl" ]]; then
      CONSEC_SL=false
      break
    fi
  done <<< "$LAST_N_RESULTS"

  if [[ "$CONSEC_SL" == "true" ]]; then
    fail "Stop día: $MAX_SL_CONSEC SL consecutivos en Fase $PHASE"
  fi
fi

pass
