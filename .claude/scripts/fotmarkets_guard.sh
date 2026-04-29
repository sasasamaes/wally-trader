#!/usr/bin/env bash
# .claude/scripts/fotmarkets_guard.sh
# Lite Guardian — valida condiciones antes de entrada en profile fotmarkets
#
# Uso:
#   fotmarkets_guard.sh check
#     → imprime "PASS" y sale 0, O "BLOCK: <razón>" y sale 1
#
# Checks:
#   1. Hora CR ∈ [07:00, 10:55]
#   2. Trades hoy < max_trades_per_day de la fase
#   3. SLs consecutivos < max_sl_consecutive de la fase
#   4. No es weekend (sábado/domingo CR)

set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"
PROFILE_DIR="$SCRIPT_DIR/../profiles/fotmarkets"
PHASE_SCRIPT="$SCRIPT_DIR/fotmarkets_phase.sh"
PROFILE_SCRIPT="$SCRIPT_DIR/profile.sh"
LOG_FILE="$PROFILE_DIR/memory/trading_log.md"

fail() {
  echo "BLOCK: $1"
  exit 1
}

pass() {
  echo "PASS"
  exit 0
}

# Check 0: Verificar que profile activo sea fotmarkets (defensa contra cross-profile invocation)
ACTIVE_PROFILE="$(bash "$PROFILE_SCRIPT" get 2>/dev/null || echo '')"
if [[ "$ACTIVE_PROFILE" != "fotmarkets" ]]; then
  fail "profile activo es '$ACTIVE_PROFILE' (no fotmarkets). Este guard solo aplica cuando fotmarkets está activo."
fi

# Check 1: Ventana horaria CR
# Nota: 10# fuerza base-10 (evita que bash interprete 0638 u 0900 como octal inválido)
HORA_HHMM=$(TZ='America/Costa_Rica' date +%H%M)
if (( 10#$HORA_HHMM < 700 || 10#$HORA_HHMM > 1055 )); then
  fail "Fuera de ventana operativa CR 07:00-10:55 (hora actual: ${HORA_HHMM:0:2}:${HORA_HHMM:2:2})"
fi

# Check 2: Weekend
DOW=$(TZ='America/Costa_Rica' date +%u)   # 1=Mon ... 7=Sun
if [[ "$DOW" -ge 6 ]]; then
  fail "Weekend: mercados Forex cerrados (día $DOW)"
fi

# Check 3: Phase detection
# Importante: si el phase script falla (archivo ausente/corrupto), BLOCK con razón clara.
# No hacer fallback silencioso a "1" — eso esconde configuración rota.
if ! PHASE=$(bash "$PHASE_SCRIPT" 2>&1); then
  fail "No se pudo determinar fase ($PHASE)"
fi

# Mapea fase → max_trades y max_sl_consecutive
case "$PHASE" in
  1) MAX_TRADES=1; MAX_SL_CONSEC=1 ;;
  2) MAX_TRADES=2; MAX_SL_CONSEC=2 ;;
  3) MAX_TRADES=3; MAX_SL_CONSEC=2 ;;
  *) fail "Fase desconocida: $PHASE" ;;
esac

# Check 4: Trades hoy
# Nota: `grep -c` sin matches imprime "0" pero exit 1. Usamos `|| true` para capturar
# el "0" sin que `|| echo 0` duplique el valor (bug clásico de multi-línea).
FECHA=$(TZ='America/Costa_Rica' date +%Y-%m-%d)
TRADES_HOY=0
if [[ -f "$LOG_FILE" ]]; then
  TRADES_HOY=$(grep -c "^| $FECHA " "$LOG_FILE" 2>/dev/null || true)
  TRADES_HOY=${TRADES_HOY:-0}
fi

if [[ "$TRADES_HOY" -ge "$MAX_TRADES" ]]; then
  fail "Max trades/día alcanzado en Fase $PHASE: $TRADES_HOY/$MAX_TRADES"
fi

# Check 5: SL consecutivos (últimos N trades hoy)
if [[ -f "$LOG_FILE" && "$TRADES_HOY" -ge "$MAX_SL_CONSEC" ]]; then
  # Extrae columna "Resultado" (campo $10 — leading | crea empty $1, datos en $2..$14)
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
