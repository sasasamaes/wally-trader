#!/usr/bin/env bash
# .claude/scripts/fotmarkets_phase.sh
# Uso:
#   fotmarkets_phase.sh           — imprime fase actual (1|2|3) leyendo phase_progress.md
#   fotmarkets_phase.sh capital   — imprime capital actual
#   fotmarkets_phase.sh detail    — imprime fase + capital + rango de fase
#   fotmarkets_phase.sh check <N> — verifica que capital N cae en la fase actual

set -euo pipefail

PROGRESS_FILE="$(dirname "$0")/../profiles/fotmarkets/memory/phase_progress.md"

# Parse capital_current del YAML embebido en el markdown
# Validaciones defensivas: archivo presente, campo presente, valor numérico.
# Sin estas validaciones, un phase_progress.md corrupto retorna silenciosamente
# phase 1 (empty → awk 0) o phase 3 (texto → awk string comparison).
get_capital() {
  if [[ ! -f "$PROGRESS_FILE" ]]; then
    echo "ERROR: phase_progress.md no encontrado en $PROGRESS_FILE" >&2
    exit 1
  fi
  local cap
  cap="$(grep -E '^capital_current:' "$PROGRESS_FILE" | head -1 | awk '{print $2}' | tr -d ' ')"
  if [[ -z "$cap" ]]; then
    echo "ERROR: capital_current no encontrado en phase_progress.md" >&2
    exit 1
  fi
  if ! [[ "$cap" =~ ^-?[0-9]+(\.[0-9]+)?$ ]]; then
    echo "ERROR: capital_current no numérico: '$cap'" >&2
    exit 1
  fi
  echo "$cap"
}

# Determina fase según thresholds de config.md
phase_for_capital() {
  local cap="$1"
  awk -v c="$cap" 'BEGIN {
    if (c < 100) print 1
    else if (c < 300) print 2
    else print 3
  }'
}

cmd="${1:-phase}"

case "$cmd" in
  phase|"")
    cap="$(get_capital)"
    phase_for_capital "$cap"
    ;;
  capital)
    get_capital
    ;;
  detail)
    cap="$(get_capital)"
    phase="$(phase_for_capital "$cap")"
    case "$phase" in
      1) echo "phase=1 capital=$cap range=[0,100) next_threshold=100" ;;
      2) echo "phase=2 capital=$cap range=[100,300) next_threshold=300" ;;
      3) echo "phase=3 capital=$cap range=[300,∞) next_threshold=none" ;;
    esac
    ;;
  check)
    test_cap="${2:-}"
    if [[ -z "$test_cap" ]]; then
      echo "ERROR: uso: fotmarkets_phase.sh check <capital>" >&2
      exit 2
    fi
    phase_for_capital "$test_cap"
    ;;
  *)
    echo "Uso: fotmarkets_phase.sh [phase|capital|detail|check <N>]" >&2
    exit 2
    ;;
esac
