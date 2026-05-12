---
name: asian-range
description: Asian session range + London-open grab/fakeout detector (fotmarkets EURUSD
  5m)
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
<!-- generated from system/commands/asian-range.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /asian-range -->


# /asian-range

Detector standalone para el patrón **Asian range + London grab** — ICT liquidity grab
post-Asian session. Aplicable principalmente a EURUSD y GBPUSD durante la ventana de
Londres (CR 02:00-08:00, ideal CR 07:00-09:00 para fotmarkets).

## Uso

```
/asian-range                       # EURUSD default, requiere --file con bars 5m
/asian-range EURUSD --file <path>  # explícito
```

## Pipeline

1. Computa Asian session high/low (UTC 23:00-08:00 ≈ CR 17:00-02:00)
2. Espera London open candle (anchor = UTC 08:00 o el bar siguiente)
3. Detecta break: una vela cierra fuera del rango asiático (high o low)
4. Detecta grab: cierre de vuelta dentro del rango en ≤ 4 velas → reversal
5. Entry = market en confirmación grab; SL = más allá del sweep + 2 pips; TP = lado
   opuesto del rango asiático

## Ejecutar

```bash
.claude/scripts/.venv/bin/python .claude/scripts/asian_range.py \
  --file ${1:-/tmp/bars5m.json} --check-grab --quick
```

## Estado: SECONDARY — no reemplaza Fotmarkets-Micro

Por decisión del 2026-05-12 (design doc Q2), Asian Range es estrategia secundaria
informativa. La principal del profile fotmarkets sigue siendo Fotmarkets-Micro 5m
(scalping reversal post-pullback).

## Fuente

Design doc 2026-05-12 YouTube bundle, feature E (V3 Alex Ruiz — strategy if I had $100).
