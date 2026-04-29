# Estrategia: Fotmarkets-Micro

Scalping de reversión tras pullback, en dirección de tendencia 15m.
Sweet spot para overlap London/NY con capital micro y ventana 4h.

## 1. Filosofía

- **No somos trend-followers puros** (entraríamos tarde con capital insuficiente).
- **No somos mean-reverters contra-trend** (arriesgado en overlap London/NY).
- **Somos pullback traders**: entramos DESPUÉS de que el precio rebota levemente contra la tendencia, en dirección de la misma.

## 2. Timeframes

| Rol | TF | Para qué |
|---|---|---|
| Contexto | 1H | Ver estructura macro del día |
| Confirmación | 15m | Definir dirección de tendencia (EMA 50/200) |
| Entry | 5m | Timing de entrada exacta |

## 3. Filtros de entrada (4 obligatorios, todos simultáneos)

### LONG

1. **Trend:** `EMA50(15m) > EMA200(15m)` AND `close(15m) > EMA50(15m)`
2. **Momentum:** `RSI(14, 5m)` ∈ **[35, 55]** (rebote desde OS, no extremo)
3. **Estructura:** precio a **≤0.15%** de soporte clave:
   - Donchian Low(20) en 5m, O
   - Pivot clásico S1 del día, O
   - EMA50(15m) actuando como dynamic support
4. **Confirmación:** última vela 5m cerrada **verde** con cuerpo **>60%** del rango total (open-close vs high-low)

### SHORT

1. **Trend:** `EMA50(15m) < EMA200(15m)` AND `close(15m) < EMA50(15m)`
2. **Momentum:** `RSI(14, 5m)` ∈ **[45, 65]** (rebote desde OB)
3. **Estructura:** precio a ≤0.15% de resistencia clave (Donchian High 20, Pivot R1, o EMA50 dynamic resistance)
4. **Confirmación:** vela 5m cerrada **roja** con cuerpo >60%

## 4. Stop Loss

- **Método:** ATR-based
- **Cálculo:** `SL = entry ± (ATR(14, 5m) × 1.2)`
- **Floor por asset** (evita que el spread se coma el SL):

| Asset | Min SL pips |
|---|---|
| EURUSD | 8 |
| GBPUSD | 10 |
| USDJPY | 10 |
| XAUUSD | 20 (= $2) |
| NAS100 | 25 points |
| SPX500 | 4 points |
| BTCUSD | 50 pips |
| ETHUSD | 40 pips |

Si ATR × 1.2 < floor del asset → usar el floor.

## 5. Take Profit (phase-aware)

### Fase 1 ($30–$100): bala única
- TP único a **2.0R** del entry (cierre total 100% de la posición)
- Sin partials (complejidad innecesaria con 0.01 lote)

### Fase 2 ($100–$300): partials
- Si precio alcanza **1.0R** sin haber tocado TP1 → mover SL a BE preventivamente (proteger ganancia flotante)
- TP1 a **2.0R** (cierra 50%, confirma SL en BE)
- TP2 a **3.5R** (cierra 50% restante)

### Fase 3 ($300+): partials extendidos
- TP1 a **2.0R** (40%)
- TP2 a **3.5R** (40%, mueve SL a TP1)
- TP3 a **5.0R** (20%, SL trailing a TP2) — **o** trailing dinámico EMA(20) en 15m

**Variante TP3 — Trailing EMA(20) 15m** (recomendado si ADX(14, 15m) > 25 al cerrar TP2):
- En vez de SL discreto a TP2, dejar runner con trail dinámico
- Cada close 15m → recalcula EMA(20). Si próximo close cruza EMA en contra → exit
- Helper: `python3 .claude/scripts/trailing_stop.py --side <long|short> --entry X --current Y --file /tmp/bars15m.json`
- Captura más del trend cuando ADX confirma momentum sostenido

## 6. Position sizing (phase-aware)

```
risk_usd = capital × risk_per_trade_pct / 100
sl_pips = abs(entry - SL) en pips del asset
lots = risk_usd / (sl_pips × pip_value_per_lot)
lots = floor(lots, 2 decimales)  # MT5 rounding
if lots < 0.01 → ABORTAR (trade imposible con min lot)
```

**Ejemplo Fase 1, EURUSD:**
- Capital $30, risk 10% = $3
- SL = 10 pips
- pip_value(EURUSD, 0.01 lot) = $0.10 → pip_value por lote = $10
- lots = $3 / (10 × $10) = **0.03 lotes**
- Margin required @ 1:500: $30 × 0.03 × 100 / 500 = $1.80 (fácilmente cubierto)

## 7. Hard stops (invalidaciones)

1. `ATR(14, 5m) > 2× promedio 50 velas` → NO operar (régimen volatile)
2. Spread EURUSD > 3 pips → NO operar (condición anormal, probablemente pre-noticia)
3. 15 min antes de noticia roja (NFP, FOMC, CPI) → cierre preventivo + no reentrar 30 min
4. Jueves 07:00–09:00 CR si hay ECB meeting → NO operar en EUR pairs

## 8. Checklist pre-entry

- [ ] Profile activo = fotmarkets (verificar statusline)
- [ ] Hora CR ∈ [07:00, 10:55]
- [ ] Asset ∈ allowed_assets de la fase actual
- [ ] Filtro 1: Trend ✓
- [ ] Filtro 2: Momentum ✓
- [ ] Filtro 3: Estructura ✓
- [ ] Filtro 4: Confirmación vela ✓
- [ ] Hard stops: ninguno activo
- [ ] Trades hoy < max_trades_per_day de la fase
- [ ] SL consecutivos < max_sl_consecutive de la fase
- [ ] Position sizing calculado con risk phase-aware
- [ ] Spread actual aceptable

12/12 → GO.
Menos → NO-GO.
