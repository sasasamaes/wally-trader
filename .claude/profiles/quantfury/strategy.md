# Estrategia: Quantfury BTC-Stack

> El objetivo es maximizar BTC, no USD. Cada decisión se evalúa en sats.

> 🚨 **Backtest 60d 2026-04-30**: Mean Reversion 15m BTC dio **-49.81pp vs HODL** en este período
> (strategy -34.83% vs HODL +14.98%). La regla del strategy "outperformance <-2% mensual → PAUSAR
> profile 30 días" se activaría inmediatamente. **Acción obligatoria**: pre-flight HODL check antes
> de cada entry + regime gate ADX<20 hard. Ver `docs/backtest_findings_2026-04-30.md`.

## 🚨 Pre-flight checks (obligatorios, agregados 2026-04-30)

Antes de cada entry:

```bash
# 1. Regime gate — solo MR en RANGE_CHOP
/regime
# → ADX(14) 1H debe ser <20. Si ADX ≥ 20 → NO entrar MR (igual que retail).

# 2. HODL outperformance check (rolling 30d)
bash .claude/scripts/btc_outperform.py --period 30d
# → si outperformance <-2% acumulado → PAUSAR profile 30 días (regla del rules.md)
```

| Test | Threshold | Acción si falla |
|---|---|---|
| Regime ADX 1H | < 20 | NO MR — esperar regime |
| HODL outperformance 30d | > -2% | PAUSAR profile 30 días |
| TRENDING UP detectado | — | Prefer **HODL pasivo** > entries activos |

**TRENDING UP regla especial**: si régimen es TREND_LEVE/FUERTE alcista, considera que
HODL pasivo replica spot con cero esfuerzo. Solo activar trading si tu setup es
**direccionalmente alineado** (LONGS en TRENDING UP). NO contrariar a la dirección
del spot — el backtest demuestra que perderías BTC stack.

## Parámetros core

| Parámetro | Valor | Razón |
|---|---|---|
| Risk per trade | **2% del BTC** (0.0002 BTC en 0.01 BTC inicial) | Igual que retail USD pero medido en BTC |
| SL distance | 1.5 × ATR (igual que retail) | Adapta a vol BTC |
| TP1 (40%) | 2.5R → BE | Mismo ratio retail |
| TP2 (40%) | 4.0R | Mismo ratio retail |
| TP3 (20%) | 6.0R OR trail EMA(20) | Pero cuidado con HODL benchmark |
| Leverage | **5x** (cap Quantfury) | Suficiente para Mean Reversion |
| Max trades/día | 3 | Disciplina |
| Target diario | **+0.5% BTC** o > spot return diario | Outperform spot HODL |

## Estrategia base: Mean Reversion 15m (igual que retail)

Reusa los **4 filtros** de Mean Reversion de retail/Binance:

LONG:
1. Donchian Low(15) ±0.1%
2. RSI <35
3. BB lower toque
4. Vela cierra verde

SHORT:
1. Donchian High(15) ±0.1%
2. RSI >65
3. BB upper toque
4. Vela cierra roja

**Diferencia clave:** la decisión LONG/SHORT también se evalúa contra el régimen del momento.

## Régimen → estrategia (con BTC outperform check)

### TRENDING UP (BTC subiendo)
- HODL > tradear longs (longs replican spot pero con SL = 50/50)
- **Estrategia:** SOLO shorts en pullbacks técnicos. Captura pullback + vuelve a stack.
- LONG solo si setup excepcional (4/4 + multifactor>+70 + ML>70).
- Tradeo poco. Mejor stack natural.

### TRENDING DOWN (BTC bajando)
- HODL < trading shorts (shorts ganan BTC mientras spot baja)
- **Estrategia:** SHORT direccional + cerrar arriba. Re-entry LONG en confirmación de reversal.
- Esta es la fase donde más BTC stackeas.
- Cuidado: shorts consumen funding fee si negativo (verificar Quantfury fees).

### RANGE (BTC lateral)
- HODL = breakeven en USD = neutral en BTC
- **Estrategia:** Mean Reversion 15m a ambos lados (longs y shorts en bordes Donchian).
- **MEJOR fase para tradear** — captura ambas direcciones.
- Outperform vs HODL es realista aquí.

### VOLATILE (BTC con wicks grandes)
- HODL = volatilidad sin dirección clara
- **Estrategia:** **NO OPERAR.** Wicks pueden quitar SL o TP.
- Las losses en BTC stack se sienten más que en USD (porque también estás short BTC mientras tu cuenta cae).

## Sizing canónico

```bash
# Capital: 0.01 BTC, risk 2% = 0.0002 BTC max loss

# Caso LONG en BTCUSD @ $75,000 con SL en $74,250 (-1%):
# - SL distance: 1% del entry
# - Notional max @ 5x leverage: 0.0002 / 0.01 = 0.02 BTC notional
# - Margin used: 0.02 / 5 = 0.004 BTC (40% del capital — algo alto pero OK con SL tight)
# - PnL si TP1 (2.5R): +0.0005 BTC = +5% del capital BTC

# Verificación: si el move USD es +2.5% y BTC sube 1% en mismo período:
#   - PnL BTC trade: +5% (de tu posición)
#   - HODL benchmark: +0% en BTC (si no operaras, tendrías mismo BTC)
#   - Outperformance: +5% en BTC ✅
```

## Outperformance benchmark (métrica única)

Cada trade se evalúa NO solo por su PnL absoluto, sino por **vs alternative** (HODL):

```python
trade_btc_pnl    = +0.0005 BTC
trade_period     = 4 hours

# Cuánto cambió el spot en esas 4h
btc_spot_start   = 75000
btc_spot_end     = 75500
btc_spot_change_pct = +0.67%

# HODL benchmark en MISMO PERIODO (si no hubiera tradeado, tendría 0.01 BTC)
hodl_btc_change  = 0 BTC (no cambia stack)
hodl_usd_change  = +0.67% en USD value (informativo)

# Comparación:
your_btc_return    = +5%   (de la posición tradeada)
hodl_btc_return    = 0%
outperformance     = +5%
```

Si la suma de outperformance mensual <2% → **considera pasar a HODL only** (tu trading no aporta valor neto).

Helper: `bash .claude/scripts/btc_outperform.py --period 30d` calcula esto desde `equity_curve.csv` + spot data.

## Reglas especiales para SHORT

Shorts en quantfury son distintos a otros profiles:

1. **Funding fees:** algunos pares pagan/cobran funding cada 8h. Si negativo y mantienes >24h, costo significativo.
2. **No usar trailing TP3 en shorts** — el target tiene que ser FIJO porque cada hora con la posición abierta consume funding.
3. **Force exit timing:** cerrar TODOS los shorts a CR 23:59 (mismo límite "no dormir con trade").
4. **NO short en TRENDING UP excepcional** — pullback que no se confirma = SL pegado + funding fee acumulado = doble cost.

## Comparación con retail (Binance USD)

| Concepto | retail | quantfury |
|---|---|---|
| Capital base | $18.09 USD | 0.01 BTC (~$750) |
| Risk per trade | 2% USD = $0.36 | 2% BTC = 0.0002 BTC |
| TP target | en % USD del entry | en % BTC del entry (mismo en práctica) |
| Métrica éxito | $20 → $25 (+25%) | 0.01 BTC → 0.011 BTC (+10% en BTC, vs HODL +0%) |
| Long bias | OK por trending up | Cuidado, replica HODL |
| Métrica clave única | WR, PF, Sharpe USD | + outperformance vs HODL |

## Cuándo NO operar (filtros adicionales)

**Skip días automáticamente cuando:**
- Régimen TRENDING UP fuerte + no hay pullback claro → HODL es mejor
- Régimen VOLATILE con wicks >2% en bars 15m → riesgo de stop-out asimétrico
- Funding rate Bitunix/Binance perpetual >+0.1% (longs sobrepagados) y vas LONG → costoso
- Outperformance del último 7d <-3% → tu sistema está fallando, pausa + review

## Métricas a trackear (más allá del WR/PF tradicional)

`/journal quantfury` reporta:

```
BTC stack inicial:        0.01000000 BTC
BTC stack actual:         0.01045000 BTC (+0.00045 = +4.5%)
USD equivalent:           $784 (vs $750 inicial = +4.5% USD)

HODL benchmark (mismo período):
  Hubieras tenido:        0.01000000 BTC (sin cambio en stack)
  USD HODL value:         $785 (BTC sube 4.7% en período)

Outperformance:
  vs HODL en BTC:         +4.5% (ganaste sats)
  vs HODL en USD:         -0.1% (USD HODL está por encima)
  
Veredicto:               STACKEANDO ✅
                         (en bear/range = excelente; en bull tracking = OK)
```

## Force exit (cripto 24/7 pero…)

- CR 23:59 max para todos los trades — disciplina anti-overnight wicks
- Si hay setup excepcional + capital pequeño <0.005 BTC → considerar 1 trade overnight con SL TIGHT
- Default: cerrar todo antes de las 23:59 igual que retail
