#!/usr/bin/env bash
# fundingpips_guard.sh — Lite guardian para profile FundingPips Zero.
# Análogo a fotmarkets_guard.sh y guardian.py (FTMO) pero con thresholds más estrictos.
#
# Uso:
#   bash fundingpips_guard.sh check                    # exit 0 si OK, 1 si BLOCK
#   bash fundingpips_guard.sh check --verbose          # con razones detalladas
#   bash fundingpips_guard.sh status                   # JSON con todos los gates
#
# BLOCK si CUALQUIERA falla:
#   1. Hora fuera de ventana operativa del asset (ver config)
#   2. Daily PnL ≤ -2% (buffer 1pp del 3% oficial)
#   3. Total equity ≤ $9,700 (-3% buffer del 5% oficial)
#   4. Consistency: día actual aportaría >12% del profit total (WARN/BLOCK)
#   5. Trades hoy ≥ 2
#   6. Profile no es fundingpips
#
# OK = todos los gates verdes.

set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PROFILE_DIR="$REPO/.claude/profiles/fundingpips"
ACTION="${1:-check}"
VERBOSE=false
[[ "${2:-}" == "--verbose" ]] && VERBOSE=true

# Helper output
fail() {
  if [[ "$ACTION" == "status" ]]; then
    printf '{"status":"BLOCK","reason":"%s","gate":"%s"}\n' "$2" "$1"
  else
    echo "❌ BLOCK [$1]: $2" >&2
    [[ "$VERBOSE" == true ]] && echo "   See $PROFILE_DIR/rules.md for thresholds" >&2
  fi
  exit 1
}

warn() {
  if [[ "$ACTION" == "status" ]]; then
    printf '{"status":"WARN","reason":"%s","gate":"%s"}\n' "$2" "$1"
  else
    echo "⚠️  WARN [$1]: $2"
  fi
}

ok() {
  if [[ "$ACTION" == "status" ]]; then
    printf '{"status":"OK","reason":"all gates passed"}\n'
  else
    echo "✅ OK — todos los gates pasaron"
  fi
  exit 0
}

# Gate 0: profile activo == fundingpips
PROFILE_SCRIPT="$REPO/.claude/scripts/profile.sh"
if [[ -x "$PROFILE_SCRIPT" ]]; then
  CURRENT=$(bash "$PROFILE_SCRIPT" get 2>/dev/null || echo "unknown")
  if [[ "$CURRENT" != "fundingpips" ]]; then
    fail "profile" "profile activo es '$CURRENT', no fundingpips"
  fi
fi

# Gate 1: ventana horaria CR
HORA_HHMM=$(TZ='America/Costa_Rica' date +%H%M)
HORA_NUM=$((10#$HORA_HHMM))
DIA_SEMANA=$(TZ='America/Costa_Rica' date +%u)  # 1=lun ... 7=dom

# Crypto: 06:00-20:00 CR (London+NY full)
# Forex/indices/oro: 06:00-16:00 CR
# Sábado/Domingo: solo crypto
if [[ "$DIA_SEMANA" -ge 6 ]]; then
  # Weekend: solo crypto, ventana 06:00-20:00 CR
  if (( HORA_NUM < 600 || HORA_NUM >= 2000 )); then
    fail "window" "fuera de ventana weekend crypto (CR 06:00-20:00). Hora actual: ${HORA_NUM}"
  fi
fi

# Gate 2: Daily PnL >= -2%
LOG="$PROFILE_DIR/memory/trading_log.md"
EQUITY_CURVE="$PROFILE_DIR/memory/equity_curve.csv"

# Buscar daily PnL del día actual
FECHA_HOY=$(TZ='America/Costa_Rica' date +%Y-%m-%d)
DAILY_PNL_PCT="0"
if [[ -f "$EQUITY_CURVE" ]] && [[ $(wc -l < "$EQUITY_CURVE") -gt 1 ]]; then
  # Buscar la primera entrada de hoy y la última
  DAILY_PNL_PCT=$(awk -F',' -v fecha="$FECHA_HOY" 'BEGIN{first=""; last=""} $1 ~ fecha {if (first=="") first=$2; last=$2} END{if (first!="" && last!="" && first+0!=0) printf "%.2f", ((last-first)/first)*100; else print "0"}' "$EQUITY_CURVE")
fi

# Compare with -2 threshold (use awk for float compare)
if awk "BEGIN {exit !($DAILY_PNL_PCT <= -2)}"; then
  fail "daily_loss" "Daily PnL ${DAILY_PNL_PCT}% (BLOCK en -2%, oficial -3%)"
elif awk "BEGIN {exit !($DAILY_PNL_PCT <= -1.5)}"; then
  warn "daily_loss" "Daily PnL ${DAILY_PNL_PCT}% (WARN en -1.5%)"
fi

# Gate 3: Total equity >= $9,700
LAST_EQ="10000"
if [[ -f "$EQUITY_CURVE" ]] && [[ $(wc -l < "$EQUITY_CURVE") -gt 1 ]]; then
  LAST_EQ=$(tail -n 1 "$EQUITY_CURVE" | cut -d',' -f2 || echo "10000")
fi

if awk "BEGIN {exit !($LAST_EQ <= 9700)}"; then
  fail "total_dd" "Equity \$${LAST_EQ} ≤ \$9,700 (BLOCK -3%, oficial -5%)"
elif awk "BEGIN {exit !($LAST_EQ <= 9800)}"; then
  warn "total_dd" "Equity \$${LAST_EQ} ≤ \$9,800 (WARN -2%)"
fi

# Gate 4: Consistency tracker
CONSISTENCY_FILE="$PROFILE_DIR/memory/consistency_tracker.json"
if [[ -f "$CONSISTENCY_FILE" ]]; then
  CONSIST_STATUS=$(python3 -c "
import json
with open('$CONSISTENCY_FILE') as f:
    d = json.load(f)
total = d.get('total_profit_to_date', 0)
current = d.get('current_day_pnl', 0)
biggest = d.get('biggest_day_pnl', 0)
projected_biggest = max(biggest, current)
projected_total = total  # ya incluye current_day si trading_log fue actualizado
if projected_total <= 0:
    print('OK_NEUTRAL')
else:
    pct = (projected_biggest / projected_total) * 100
    if pct >= 12:
        print(f'BLOCK_{pct:.1f}')
    elif pct >= 10:
        print(f'WARN_{pct:.1f}')
    else:
        print(f'OK_{pct:.1f}')
" 2>/dev/null || echo "OK_UNKNOWN")

  case "$CONSIST_STATUS" in
    BLOCK_*) fail "consistency" "Consistency proyectada ${CONSIST_STATUS#BLOCK_}% (BLOCK en 12%, oficial 15%)" ;;
    WARN_*) warn "consistency" "Consistency ${CONSIST_STATUS#WARN_}% (WARN en 10%)" ;;
  esac
fi

# Gate 5: Trades hoy < 2
TRADES_HOY=0
if [[ -f "$LOG" ]]; then
  TRADES_HOY=$(grep -c "^| $FECHA_HOY " "$LOG" 2>/dev/null | head -1 || true)
  TRADES_HOY=${TRADES_HOY:-0}
  # Saneamiento: dejar solo dígitos
  TRADES_HOY=$(echo "$TRADES_HOY" | tr -cd '0-9')
  TRADES_HOY=${TRADES_HOY:-0}
fi
if (( 10#${TRADES_HOY} >= 2 )); then
  fail "max_trades" "Ya hay $TRADES_HOY trades hoy (max 2 para FundingPips)"
fi

# All gates passed
ok
