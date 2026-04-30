---
name: multifactor-scoring
description: Use cuando necesites un score 0-100 cuantitativo del setup actual combinando Momentum (RSI+ADX+EMA), Volatility (ATR percentile), Trend Quality (EMA alignment), y Volume (spike ratio). Complementa al ML XGBoost — coincidencia entre ambos = conviction máxima; divergencia = flag.
---

# Multi-Factor Scoring — meta-score 0-100

## Cuándo usarla

**Pre-entry validation (después de los 4 filtros):**
- Calcula un score numérico que confirma o desafía la decisión técnica.
- Reduce dependencia exclusiva del ML XGBoost (que puede sobre-fit).
- Permite ranking objetivo entre múltiples setups candidatos.

**Trade selection en multi-asset:**
- En profile FTMO/fotmarkets, comparar los multi-factor scores de cada asset y elegir el ganador objetivamente.

**Cross-validation con ML:**
- Si ML score >60 + multifactor >70 → conviction máxima, full size
- Si ML alto pero multifactor bajo → flag, reducir size 50% o skip
- Si multifactor alto pero ML bajo → flag (probablemente régimen distinto al training del ML)

## Cómo invocarla

```bash
# Helper directo
python3 .claude/scripts/multifactor_score.py --bars-file /tmp/bars15m.json
python3 .claude/scripts/multifactor_score.py --bars-file /tmp/bars.json --side long
python3 .claude/scripts/multifactor_score.py --bars-file /tmp/bars.json --json
```

```
# Slash command (CC/OpenCode/Hermes)
/multifactor
```

## Componentes del score

| Factor | Rango | Cómo se calcula |
|---|---|---|
| **Momentum** | -25 a +25 | RSI(14) + ADX direccional + EMA20 vs EMA50 slope. Fuerza trend × dirección. |
| **Volatility** | 0 a +25 | ATR(14) percentile vs últimos 90 bars. Sweet spot: 30-70% (ni dormido ni explotando). |
| **Trend Quality** | -25 a +25 | EMA20 > EMA50 > EMA200 (full bull = +25), inverso (full bear = -25), mixed = ±15 o 0. |
| **Volume** | 0 a +25 | Spike ratio bar actual / avg 20 bars. >2x = +22, 1-2x = +10, <1x = +3. |

**Score TOTAL** = Momentum + TrendQuality + (Vol + Volume) × sign(M+T)
Range: -100 a +100. Negativo = bearish bias.

## Conviction labels

- **ALTA** (|score| >= 70): full conviction, full size si los 4 filtros también alineados.
- **MEDIA** (|score| 50-70): conviction moderada, size 75%.
- **BAJA** (|score| 30-50): borderline, requiere 4/4 filtros perfectos + ML alto.
- **FLAT** (|score| < 30): setup débil, esperar.

## Reglas de uso con ML

```
multifactor    ML       acción
─────────────  ────  ──────────────────────────────
>= 70          >= 60     MAX conviction, full size
50-70          >= 60     conviction MEDIA, size 75%
>= 70          < 40      DIVERGEN, reduce size 50% o skip
< 30           any       setup débil, esperar
50-70          40-60     borderline, necesita 4/4 filtros perfectos
```

## Pitfalls conocidos

1. **Volatility en bars sintéticos** → puede dar 100%-ile si no hay suficiente histórico. Mínimo 100 bars para percentile decente.
2. **Volume puede ser 0** en feeds forex/index TV — score volume será 0, no rompe nada pero conviction máxima imposible (cap 75 sin volume).
3. **ADX simplificado:** el helper usa proxy `avg_move/ATR`, no DI+/DI- formal. Para precisión absoluta usar `/regime` que tiene ADX completo.
4. **No es signal de entry** — solo conviction sobre setup ya identificado. Los 4 filtros siguen siendo gating.

## Verificación

```bash
# Sanity: score debe variar entre -100 y +100
python3 .claude/scripts/multifactor_score.py --bars-file /tmp/test_bars.json --json | jq '.total_score'
```
