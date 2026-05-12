---
name: pullback
description: Detect impulse → pullback → continuation pattern for the active profile's
  default symbol (standalone, not wired to punk-smart yet)
version: 1.0.0
metadata:
  openclaw:
    tags:
    - wally-trader
    - command
    - slash
    category: trading-command
    requires_toolsets:
    - terminal
    - subagents
---
<!-- generated from system/commands/pullback.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /pullback -->


# /pullback

Detector standalone para el patrón **impulso → pullback → continuación** — útil cuando el
régimen es TREND_LEVE/FUERTE (ADX ≥ 25) y Mean Reversion no aplica.

## Uso

```
/pullback                        # asset default del profile, TF 15m
/pullback BTCUSDT 1h             # asset y TF custom
/pullback ETHUSDT 15m --adx 32   # con ADX conocido (skip auto-detect)
```

## Pipeline

1. Carga bars OHLCV del símbolo+TF (200 últimas por default)
2. Calcula ADX(14) — exige ≥ 25 (gate)
3. Detecta el impulso más reciente (3+ velas mismo color, ATR por barra ≥ 0.96 × media)
4. Detecta pullback hacia fib 0.382–0.618 (invalida si pasa 0.786)
5. Confirma continuación con primera vela impulse-color post-pullback
6. Devuelve entry / SL / 3 TPs / confidence 0-100

## Ejecutar

```bash
.claude/scripts/.venv/bin/python .claude/scripts/pullback_detector.py \
  --symbol ${1:-BTCUSDT} --tf ${2:-15m} --quick
```

## Output

```
PULLBACK LONG conf=72 entry=108.50 sl=104.25
TPs: 125.00 / 144.50 / 175.30
```

Si `NO_SIGNAL` → razón explícita (no impulse / no pullback / no continuation yet).

## Estado: STANDALONE — no integrado a `/punk-smart` v2

Por decisión del 2026-05-12 (design doc), antes de wirearlo al router debe correr backtest
comparativo vs MA Crossover en TREND_LEVE.

## Fuente

Design doc 2026-05-12 YouTube bundle, feature A (V1 Alex Ruiz — patrón impulso-pullback-continuación).
