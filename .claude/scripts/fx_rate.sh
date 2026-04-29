#!/bin/bash
# fx_rate.sh — pull USD→CRC rate del día con cache 1h en /tmp.
# Output stdout: solo el rate (ej: "455.53"). Sin newline extra.
# Stderr: msg si fallback usado.
# Exit 0 si OK (live o cached), 1 si todo falla y se usa hardcode.

CACHE="/tmp/wally_fx_cache_usd_crc.json"
TTL=3600  # 1h

# Helper: lee CRC del JSON cacheado
read_crc() {
  grep -oE '"CRC":[0-9.]+' "$CACHE" 2>/dev/null | head -1 | cut -d':' -f2
}

# 1) Cache fresca → usar directo
if [[ -f "$CACHE" ]]; then
  AGE=$(($(date +%s) - $(stat -f %m "$CACHE" 2>/dev/null || stat -c %Y "$CACHE" 2>/dev/null || echo 0)))
  if (( AGE < TTL )); then
    CRC=$(read_crc)
    if [[ -n "$CRC" ]]; then
      printf "%s" "$CRC"
      exit 0
    fi
  fi
fi

# 2) Refresh API
RESP=$(curl -s --max-time 4 'https://open.er-api.com/v6/latest/USD' 2>/dev/null)
if [[ -n "$RESP" ]] && echo "$RESP" | grep -q '"CRC"'; then
  echo "$RESP" > "$CACHE"
  CRC=$(read_crc)
  if [[ -n "$CRC" ]]; then
    printf "%s" "$CRC"
    exit 0
  fi
fi

# 3) Fallback: cache stale si existe
if [[ -f "$CACHE" ]]; then
  CRC=$(read_crc)
  if [[ -n "$CRC" ]]; then
    echo "fx_rate: usando cache stale (API offline)" >&2
    printf "%s" "$CRC"
    exit 0
  fi
fi

# 4) Sin nada → hardcode aproximación (~promedio histórico CRC 2024-2026)
echo "fx_rate: API offline y sin cache, usando hardcode 510" >&2
printf "510"
exit 1
