#!/usr/bin/env bash
# chainlink_price.sh — pull precio del Chainlink Data Feed (Ethereum mainnet).
#
# Uso:
#   chainlink_price.sh <PAIR> [--compare <tv_price>] [--json]
#
# PAIR: BTC | ETH | LINK | EUR | GBP | XAU
#
# Cache 30s en /tmp/wally_chainlink_<PAIR>.cache para evitar hammear RPCs.
# Fallback automático entre múltiples RPCs públicos sin auth.
# Si --compare <tv_price> se pasa, calcula delta vs el precio TradingView e imprime
# tabla con veredicto (OK / WARN >0.3% / ALERT >1%).
#
# Stdout (sin --json): precio decimal (8 decimales)
# Stdout (con --json): {"pair":"BTC","chainlink":75535.20,"tv":75500.00,"delta_pct":0.046,"verdict":"OK"}
# Exit 0 OK (incluye cache stale), 1 si todos los RPCs fallan y no hay cache, 2 args inválidos

set -uo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <PAIR> [--compare <tv_price>] [--json]" >&2
  echo "  PAIR: BTC | ETH | LINK | EUR | GBP | XAU" >&2
  exit 2
fi

PAIR="$1"
shift
COMPARE=""
JSON_OUT=false
while [ $# -gt 0 ]; do
  case "$1" in
    --compare) COMPARE="$2"; shift 2 ;;
    --json) JSON_OUT=true; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Chainlink Data Feeds — Ethereum mainnet, AggregatorV3 contracts
case "$PAIR" in
  BTC|btc)   ADDR="0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c"; DEC=8 ;;
  ETH|eth)   ADDR="0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"; DEC=8 ;;
  LINK|link) ADDR="0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c"; DEC=8 ;;
  EUR|eur)   ADDR="0xb49f677943BC038e9857d61E7d053CaA2C1734C1"; DEC=8 ;;
  GBP|gbp)   ADDR="0x5c0Ab2d9b5a7ed9f470386e82BB36A3613cDd4b5"; DEC=8 ;;
  XAU|xau)   ADDR="0x214eD9Da11D2fbe465a6fc601a91E62EbEc1a0D6"; DEC=8 ;;
  *) echo "ERROR: par no soportado: $PAIR (BTC|ETH|LINK|EUR|GBP|XAU)" >&2; exit 2 ;;
esac

PAIR_UPPER=$(echo "$PAIR" | tr '[:lower:]' '[:upper:]')
CACHE="/tmp/wally_chainlink_${PAIR_UPPER}.cache"
TTL=30  # 30s

# Cache hit
PRICE=""
if [ -f "$CACHE" ]; then
  AGE=$(($(date +%s) - $(stat -f %m "$CACHE" 2>/dev/null || stat -c %Y "$CACHE" 2>/dev/null || echo 0)))
  if [ "$AGE" -lt "$TTL" ]; then
    PRICE=$(cat "$CACHE")
  fi
fi

# Fetch via RPCs (multi-fallback)
if [ -z "$PRICE" ]; then
  RPCS=(
    "https://1rpc.io/eth"
    "https://eth.llamarpc.com"
    "https://eth-mainnet.public.blastapi.io"
    "https://ethereum.publicnode.com"
  )
  # latestAnswer() selector = 0x50d25bcd
  PAYLOAD="{\"jsonrpc\":\"2.0\",\"method\":\"eth_call\",\"params\":[{\"to\":\"${ADDR}\",\"data\":\"0x50d25bcd\"},\"latest\"],\"id\":1}"

  for RPC in "${RPCS[@]}"; do
    RESP=$(curl -s --max-time 5 -X POST "$RPC" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" 2>/dev/null) || continue

    [ -z "$RESP" ] && continue
    PRICE=$(echo "$RESP" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    h = d.get('result', '')
    if not h or h == '0x0':
        sys.exit(1)
    p = int(h, 16) / 10**${DEC}
    if p <= 0:
        sys.exit(1)
    print(f'{p:.4f}')
except Exception:
    sys.exit(1)
" 2>/dev/null) || PRICE=""
    if [ -n "$PRICE" ]; then
      echo "$PRICE" > "$CACHE"
      break
    fi
  done
fi

# Fallback a cache stale
if [ -z "$PRICE" ] && [ -f "$CACHE" ]; then
  echo "chainlink: usando cache stale (todos los RPCs fallaron)" >&2
  PRICE=$(cat "$CACHE")
fi

if [ -z "$PRICE" ]; then
  echo "ERROR: no se pudo obtener precio Chainlink para $PAIR_UPPER" >&2
  exit 1
fi

# Modo simple — solo precio
if [ -z "$COMPARE" ] && [ "$JSON_OUT" = false ]; then
  echo "$PRICE"
  exit 0
fi

# Modo compare o json
if [ -n "$COMPARE" ]; then
  RESULT=$(python3 -c "
cl = float('$PRICE')
tv = float('$COMPARE')
delta_abs = tv - cl
delta_pct = (delta_abs / cl) * 100 if cl != 0 else 0
abs_pct = abs(delta_pct)
if abs_pct < 0.3:
    verdict = 'OK'
elif abs_pct < 1.0:
    verdict = 'WARN'
else:
    verdict = 'ALERT'
print(f'{delta_pct:.4f}|{verdict}')
")
  DELTA_PCT=$(echo "$RESULT" | cut -d'|' -f1)
  VERDICT=$(echo "$RESULT" | cut -d'|' -f2)
fi

if [ "$JSON_OUT" = true ]; then
  if [ -n "$COMPARE" ]; then
    printf '{"pair":"%s","chainlink":%s,"tv":%s,"delta_pct":%s,"verdict":"%s"}\n' \
      "$PAIR_UPPER" "$PRICE" "$COMPARE" "$DELTA_PCT" "$VERDICT"
  else
    printf '{"pair":"%s","chainlink":%s}\n' "$PAIR_UPPER" "$PRICE"
  fi
  exit 0
fi

# Modo compare humano (tabla simple)
echo "Chainlink ${PAIR_UPPER}/USD : \$${PRICE}"
echo "TradingView ${PAIR_UPPER}    : \$${COMPARE}"
echo "Delta                : ${DELTA_PCT}%   [${VERDICT}]"
case "$VERDICT" in
  OK)    echo "→ Sin discrepancia significativa, precio TV confiable." ;;
  WARN)  echo "→ Discrepancia 0.3-1%, posible lag o exchange-specific. Validar antes de operar." ;;
  ALERT) echo "→ Discrepancia >1%, NO operar hasta confirmar fuente. Posible feed stale o manipulación." ;;
esac
