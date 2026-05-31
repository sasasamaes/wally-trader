---
description: Rule Significance Test — ¿la regla de entrada tiene edge o es ruido?
  (permutation test)
---

Corre el **Rule Significance Test (RST)** sobre una regla de entrada: permuta el timing
de las entradas ~2,000 veces con barras aleatorias (misma regla de salida) y reporta un
p-value. Si la entrada bate al azar (p < 0.05) → tiene edge; si no → puede ser suerte.

Destilado del video "Opus 4.8 + Claude Code + MCP = Algo Trading on Autopilot"
(Algo-trading with Saleh, framework Jesse). La lección central: **una estrategia rentable
NO prueba que su entrada tenga edge** — en un bull year un "always long" gana sin poder
predictivo. El RST separa "¿la entrada tiene edge?" de "¿la estrategia es rentable?".

## Uso

```
/rst [SYMBOL] [TF]
/rst BTCUSDT 30m
/rst ETHUSDT 1h short
```

## Pasos

1. **Correr el test** (estrategia built-in `donchian_ema`, la del video):
   ```bash
   .claude/scripts/.venv/bin/python .claude/scripts/rule_significance.py \
       --symbol BTCUSDT --tf 30m --days 365 --strategy donchian_ema --side long --n 2000 --json
   ```
   - Pagina hasta `--days` de historia Binance Futures (default 365).
   - Genera las entradas con Donchian breakout + filtro EMA(200).
   - Permuta `--n` entradas aleatorias (mismo exit Donchian/ATR) → distribución nula.
   - `p_value = fracción de variantes aleatorias que igualan/superan la real`.

2. **Interpretar el veredicto:**
   - **PASS** (p < 0.05, exit 0) → la entrada tiene edge. Continuar a backtest + OOS + Monte Carlo.
   - **FAIL** (p ≥ 0.05, exit 2) → la entrada NO se distingue del azar. Iterar las reglas de
     entrada ANTES de gastar tiempo en sizing/exits/backtest.
   - **INSUFFICIENT** → <3 entradas, muestra ínfima.

## Flags útiles

- `--days N` — historia a paginar (más data = test más robusto, pero más lento)
- `--n N` — # permutaciones (default 2000; 400-800 para iteración rápida)
- `--side long|short`
- `--don-len`, `--ema-len`, `--sl-mult`, `--max-hold` — parámetros de la estrategia built-in
- `--metric mean_return|total_return|sharpe`
- `--bars-file PATH` — usar OHLCV propio (lista de dicts `{t,o,h,l,c,v}`) en vez de fetch

## Notas honestas

- El RST valida la ENTRADA, no la rentabilidad. PASS no garantiza profit; FAIL sí descarta edge.
- Para validar una estrategia distinta a `donchian_ema`, importa `significance_test()` desde
  el script y pásale tus `entry_indices` + `exit_fn` (ver docstring).
- Es el **primer gate** del flujo de validación: RST → backtest → OOS → Monte Carlo → veredicto.

$ARGUMENTS
