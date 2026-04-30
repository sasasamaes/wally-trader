# Estrategia: FundingPips-Conservative

> Más conservadora que FTMO-Conservative. 5% max DD = sin margen para experimentar.

## Parámetros core

| Parámetro | Valor | Razón |
|---|---|---|
| Risk per trade | **0.3%** ($30 sobre $10k) | 5% max DD = ~16 SLs antes de blow up |
| SL distance | **0.4% del entry** | Igual que FTMO, capturado por ATR×1.5 normalmente |
| TP1 (50%) | **1.5R** = 0.6% del entry | Más conservador que FTMO TP1=1.5R, hits más frecuentes |
| TP2 (50%) | **2.5R** = 1.0% del entry | Moderado, captura el move sin codiciar |
| Trailing TP3 | NO USAR | En FundingPips el runner pesa demasiado en consistency |
| Leverage usable | **10x effective** (de 50x cap) | Usa solo 20% del leverage disponible |
| Max trades/día | **2** | Permite recovery si primer trade da SL |
| Target diario | **0.5-0.7%** | Sostenible bi-weekly: ~7-10% per cycle |

## Por qué solo 2 trades/día y TP fijo (no trailing)

**Consistency rule (15%):** el día más profitable NO puede exceder 15% del profit total acumulado. Si haces +3% en un día y luego solo sumas pequeños profits, ese día queda como "outlier" y bloquea el payout.

→ Mejor distribución uniforme: **0.5-0.7% diario consistente** que un día de +3% y otros de 0%.

## Filtros de entrada (4/4 obligatorios)

Mismos que Mean Reversion 15m del retail, **adaptados al asset**:

### Para crypto (BTCUSD/ETHUSD):
1. Precio toca Donchian Low(15) ±0.1% (LONG) o High (SHORT)
2. RSI(14) <35 (LONG) o >65 (SHORT)
3. Low/High de vela toca BB(20,2) inferior/superior
4. Vela cierra verde (LONG) / roja (SHORT)

### Para forex majors:
1. Donchian Low(15) ±0.05% (más tight que crypto, vol menor)
2. RSI(14) <30 (LONG) — forex requiere extremo más fuerte
3. BB(20,2) toque
4. Vela cierra en dirección + cierre fuera de las últimas 3 barras

### Para indices (NAS100/SPX500):
- Solo LONG en pullback a Donchian Low (equity tiene drift positivo)
- 4 filtros igual que crypto pero con TF 5m (más volatilidad intra-día)
- **NO operar dentro de 30min antes/después de FOMC/CPI/NFP**

### Para XAUUSD (oro):
- Igual que forex pero con SL más amplio (1.5×ATR + 0.1% buffer)
- Sensible a DXY → si DXY >0.5%/día, sesgo SHORT en oro

## Selección A-grade entre 20+ assets

```
1. Filtrar por sesión activa (descartar Asia low-vol salvo crypto)
2. Aplicar 4 filtros sobre el TF base (15m crypto/forex, 5m indices)
3. Para los que pasen 4/4:
   - /multifactor    → score (positivo=long, negativo=short)
   - /ml             → ML score TP-first
   - /chainlink      → cross-check si crypto/forex
4. Ranking final = (multifactor*0.5 + ML*0.3 + sentiment_align*0.2)
5. PICK el #1
6. /risk-var --target-var-pct 0.5 --capital 10000 → calcular size
7. Verificar guardian (fundingpips_guard.sh)
8. Si todos los gates pass → EJECUTAR (manual en MT5)
```

## Cuándo NO operar (regla #1: el edge es no perder)

**Skip días automáticamente cuando:**
- Régimen VOLATILE en >50% de los assets candidatos
- 1+ noticia high-impact en próximas 6h (FOMC/CPI/NFP/Powell/ECB)
- Ningún asset con multifactor >+50 o <-50 (todos en zona FLAT)
- Ya tienes 2 trades hoy (independiente del resultado)
- Daily PnL ≤ -2% (BLOCK)
- Total DD ≤ -3% (BLOCK)
- Consistency tracker dice día actual >12% del profit total → STOP

## Position sizing tabla rápida (cuenta $10k, risk 0.3%)

| Asset | Entry típico | SL distance | Lots correcto |
|---|---|---|---|
| BTCUSD | 75,000 | 300 USD (0.4%) | 0.10 |
| ETHUSD | 2,200 | 9 USD (0.4%) | 1.5 |
| EURUSD | 1.0850 | 30 pips (0.4%) | 0.10 |
| GBPUSD | 1.2700 | 35 pips (0.4%) | 0.08 |
| USDJPY | 150.50 | 50 pips (0.4%) | 0.06 |
| XAUUSD | 2,650 | 10 USD (0.4%) | 0.30 |
| NAS100 | 21,000 | 80 pts (0.4%) | 0.10 |
| SPX500 | 5,800 | 23 pts (0.4%) | 0.20 |

**Verificación:** siempre correr `/risk-var` con `--target-var-pct 0.5` antes de ejecutar. Es el sizing canónico.

## Ventana operativa por asset

| Asset | Ventana óptima CR | Ventana descartada |
|---|---|---|
| BTCUSD/ETHUSD | 06:00-20:00 (London+NY) | 21:00-05:00 (Asia, vol baja) |
| Forex majors | 06:00-15:00 (London+NY overlap) | Asia |
| Forex JPY pairs | 18:00-23:00 (Tokyo) | London/NY (vol baja) |
| Indices | 14:30-20:30 (NY equities) | Resto |
| XAUUSD | 06:00-15:00 | Resto (sigue forex) |

## Force exit

- Crypto: CR 20:00 (NY close), opcional 23:59 si setup excepcional
- Forex/indices/oro: **CR 16:00 sin excepción**

## Comparación FTMO vs FundingPips

| Concepto | FTMO-Conservative | FundingPips-Conservative |
|---|---|---|
| Risk per trade | 0.5% | **0.3%** |
| SL distance | 0.4% | 0.4% |
| TP1 R:R | 1.5R | **1.5R** (igual, pero al 50% del size) |
| TP3 trailing | Sí (EMA20) | **NO — incompatible con consistency** |
| Max trades/día | 3 | **2** |
| Target diario | 1.5% | **0.5-0.7%** (consistency-friendly) |
| Daily loss BLOCK | -2% | **-2%** (igual buffer) |
| Total DD BLOCK | -7% (de 10%) | **-3% (de 5%)** ← MÁS estricto |
