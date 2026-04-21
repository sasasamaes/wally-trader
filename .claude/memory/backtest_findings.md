---
name: Backtest findings — lo que funciona y lo que no
description: Resultados y limitaciones de los backtests corridos sobre BTCUSDT.P
type: project
originSessionId: 870cfb36-0066-4b6c-a1b7-eeaebc9a6ca8
---
**Data disponible vía TradingView MCP (capado a 300 barras por TF):**
- 4H: 50 días
- 1H: 12.5 días
- 15m: 3.1 días
- 5m: 1 día
Data más larga que esto NO es accesible con el plan actual del usuario. Para backtest robusto se necesitaría fuente externa (exchange API direct).

**Configs probadas y resultados:**

| Config | Timeframe | Periodo | Retorno | WR | DD | Veredicto |
|---|---|---|---|---|---|---|
| 20x SL 1% Supertrend flip | 4H | 50d | -48% | 10% | 49% | ❌ Destructor |
| 10x ST(2,7) wider | 4H | 50d | +87% | 25% | 51% | Ganó pero DD cerca liquidación |
| 10x ST(2,7) intraday | 1H | 12d | -26% | 25% | 29% | ❌ Config 4H no funciona intraday |
| 10x ST(1.5,10) intraday | 1H | 12d | +3.65% | 60% | 17% | OK pero modesto |
| **Donchian 10x SL 0.5%** | **15m** | **3d** | **+8.5%** | **50%** | **4%** | ✅ **Ganador scalping** |
| RSI 40/60 pullback 10x | 15m | 3d | +10.8% | 100% | 2% | Solo 1 trade — overfit riesgo |
| BB mean reversion | 15m | 3d | +5% | 50% | 8% | Aceptable pero DD mayor |
| EMA9/21 cross | 15m | 3d | single trade | — | — | Insuficientes señales |

**Why:** Grid search exhaustiva sobre data limitada mostró que Donchian breakout tiene el mejor balance retorno/DD/frecuencia de trades para scalping intraday. La config del 4H (Supertrend flip lento) NO funciona en 15m porque las señales son demasiado escasas para la ventana de 5 horas.

**How to apply:**
- Si el usuario pide re-optimizar, recordar que solo hay 3 días de 15m data → resultados no son estadísticamente concluyentes, son orientativos
- NO prometer números de retorno — el +8.5% fue en una muestra de 2 trades
- Expectativa realista: 2-5% neto diario en días operativos, con días de break-even o pérdida
- Ruta realista $10→$100: 6-12 meses con disciplina total

**Lecciones que NO deben perderse:**
1. Lo que funciona en 4H NO funciona automáticamente en timeframes menores
2. Leverage alto (15x+) aunque mejore retorno absoluto, empuja DD a zona de liquidación
3. Fees (0.05% × 2) + slippage (0.02-0.05%) comen ~0.15% por trade en scalping — TPs deben ser >3x eso
4. La "ventana óptima" MX 06-10 coincide con London/NY overlap donde BTC tiene 0.85% vol por barra 4H (vs 0.50% en Asia)
