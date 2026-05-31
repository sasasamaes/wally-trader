#!/usr/bin/env bash
# Importa candles a la DB de Jesse vía su REST API.
#
# Uso:  ./import_candles.sh <SYMBOL BASE-QUOTE> <EXCHANGE> <START_DATE>
# Ej:   ./import_candles.sh BTC-USDT Binance 2024-01-01
#
# Requisitos: Jesse corriendo (docker compose up -d) y .env con JESSE_PORT/JESSE_PASSWORD.
# NOTA: el endpoint y el flujo de auth pueden variar según la versión de Jesse —
# confirma contra https://docs.jesse.trade/docs/getting-started si falla.
set -euo pipefail

SYMBOL="${1:?símbolo requerido, formato BASE-QUOTE (ej BTC-USDT)}"
EXCHANGE="${2:-Binance}"
START="${3:-2024-01-01}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Carga .env si existe
if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -a; source "$SCRIPT_DIR/.env"; set +a
fi
PORT="${JESSE_PORT:-9000}"
BASE="http://localhost:${PORT}"

echo "→ Importando ${SYMBOL} (${EXCHANGE}) desde ${START} a Jesse en ${BASE}"

# Auth: Jesse usa login local → token. Ajusta según tu versión.
TOKEN="$(curl -s -X POST "${BASE}/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"password\": \"${JESSE_PASSWORD:-changeme}\"}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("auth_token",""))' 2>/dev/null || true)"

if [[ -z "${TOKEN}" ]]; then
  echo "⚠️  No se obtuvo auth_token. Revisa JESSE_PASSWORD en .env y que Jesse esté arriba."
  echo "    Puedes también importar candles desde el dashboard: ${BASE} → Import Candles."
  exit 1
fi

curl -s -X POST "${BASE}/candles/import" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${TOKEN}" \
  -d "{\"exchange\": \"${EXCHANGE}\", \"symbol\": \"${SYMBOL}\", \"start_date\": \"${START}\"}" \
  && echo "" && echo "✓ Solicitud de import enviada. Sigue el progreso en el dashboard ${BASE}."
