---
name: risk-quant
description: Use cuando necesites position sizing más sofisticado que el flat 2% — VaR/CVaR histórico para ajuste adaptativo según volatilidad realizada, o Risk Parity para distribuir riesgo igualmente entre assets multi-asset (FTMO/fotmarkets). Complementa /risk con métricas cuantitativas profesionales.
---

# Risk Quant — VaR/CVaR + Risk Parity

## Cuándo usarla

**VaR/CVaR position sizing (todos los profiles):**
- Cuando el régimen es VOLATILE o ATR explotó (ej. post-FOMC).
- Cuando quieres protección dinámica vs el flat 2%.
- Especialmente importante en **FTMO** (3% daily limit muy restrictivo).

**Risk Parity (FTMO/fotmarkets multi-asset):**
- Antes de seleccionar el A-grade entre 6 assets, validar que el asset elegido NO esté sobre-volátil.
- Comparar setups equivalentes: el asset con weight RP más alto = riesgo mejor distribuido.

## VaR/CVaR — concepto

- **VaR 95%**: en el 95% de los casos, la pérdida será MENOR que este nivel. En el 5% peor de los días, será mayor o igual.
- **CVaR 95%** (Conditional VaR / Expected Shortfall): la pérdida promedio condicional a estar en ese 5% peor.
- CVaR es siempre más conservador que VaR — mejor para risk management estricto.

**Sizing fórmula:**
```
target_loss_usd = capital × target_var_pct
notional_max    = target_loss_usd / |VaR|
margin_used     = notional_max / leverage
```

Si VaR sube (alta volatilidad), notional_max baja → menos size, automáticamente.

## Risk Parity — concepto

Equal Risk Contribution: cada asset contribuye **el mismo** riesgo total al portfolio.

```
weight_i = (1 / vol_i) / sum(1 / vol_j)
risk_contrib_i = weight_i × vol_i = constante para todos
```

EURUSD (vol 0.4%) recibirá ~37% del notional. NAS100 (vol 1.5%) solo ~10%. Ese es el ajuste correcto.

## Cómo invocarlas

```bash
# A. VaR/CVaR sizing
python3 .claude/scripts/risk_var.py \
  --bars-file /tmp/bars1h.json \
  --capital 18.09 \
  --leverage 10 \
  --target-var-pct 1.5

# B. Risk Parity multi-asset (con bars dir)
python3 .claude/scripts/risk_parity.py \
  --bars-dir /tmp/bars/ \
  --window 20 \
  --capital 10000

# B alt: con vols pre-calculados (formato CSV)
python3 .claude/scripts/risk_parity.py \
  --vols "BTC:0.023,ETH:0.031,EURUSD:0.004,NAS100:0.015"
```

```
# Slash commands (CC/OC/Hermes)
/risk-var
/risk-parity
```

## Reglas profile-specific

| Profile | target-var-pct | Notas |
|---|---|---|
| `retail` (Binance) | 1.5% | Capital pequeño, edge protegido |
| `retail-bingx` | 1.5% | Igual que retail |
| `ftmo` | 0.5% | 3% daily limit muy restrictivo, protección extra |
| `fotmarkets` (fase 1) | 5% | Bonus money, escalation aggressive |
| `fotmarkets` (fase 2) | 3% | Crecimiento controlado |
| `fotmarkets` (fase 3) | 1.5% | Capital significativo, protección estándar |

## Comparación con `/risk` tradicional

| Métrica | `/risk` (flat 2%) | `/risk-var` (VaR-based) |
|---|---|---|
| Adaptación a vol | ❌ Estática | ✅ Auto-ajusta cuando ATR explota |
| Sample requerido | 0 (regla pura) | 20+ bars |
| Conservador en post-FOMC | ❌ Igual size que día normal | ✅ Reduce 50%+ automático |
| Cisne negro | ⚠️ Flat puede ser holgado | ⚠️ VaR histórico subestima novedad |
| Velocidad cálculo | Instant | <1s |

**Recomendación práctica:**
- En días normales: `/risk` (más simple).
- Post-evento alto impacto / régimen volatile: `/risk-var` (protección automática).
- En FTMO: SIEMPRE `/risk-var` (3% daily es demasiado restrictivo para flat 2%).

## Pitfalls

1. **VaR histórico no captura cisne negro** — un evento sin precedente histórico (FOMC sorpresa, fork) puede romper el modelo. Por eso CVaR es preferible cuando importa la cola.
2. **Sample size <30** → VaR poco confiable. El helper warning lo dice; usar más bars.
3. **Risk parity asume independencia** — no captura correlación BTC-ETH (~0.85). Para ajuste real usar covariance matrix (no implementado todavía).
4. **NO reemplaza el SL real** — VaR es input para sizing; el SL técnico (1.5×ATR del nivel) sigue siendo gating.

## Verificación

```bash
# El VaR debe ser negativo y decreciente (más extremo) al aumentar confidence
python3 .claude/scripts/risk_var.py --bars-file /tmp/bars.json --capital 100 --confidence 95 --json | jq '.var.var_95_pct'
python3 .claude/scripts/risk_var.py --bars-file /tmp/bars.json --capital 100 --confidence 99 --json | jq '.var.var_99_pct'
# Esperado: |var_99| > |var_95|
```
