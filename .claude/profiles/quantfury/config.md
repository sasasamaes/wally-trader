# Profile: QUANTFURY (BTC-denominated trading)

**Capital inicial:** **0.01 BTC** (≈$750 USD a $75k/BTC — ajustable)
**Plataforma:** [Quantfury](https://quantfury.com) — broker app crypto-native
**Unit of account:** **BTC (no USD)** — todo el tracking se hace en BTC
**Asset operable:** BTC/USD (long/short — sí permite shorts vs USD)
**Leverage:** 5x effective (Quantfury hard cap depende del asset)

## Filosofía operativa — CRÍTICA Y DISTINTA

> **El objetivo no es ganar USD. Es ganar BTC.**

### Por qué esto cambia TODO el sistema

En todos los demás profiles:
```
- Capital: USD
- PnL: USD
- Sharpe: USD
- Métrica clave: % return USD
```

En quantfury:
```
- Capital: BTC (sats)
- PnL: BTC (sats)
- Sharpe: BTC
- Métrica clave: % return BTC AND outperformance vs HODL
```

### Ejemplo concreto

Imagina que tienes 0.01 BTC al inicio del mes. BTC sube 10% en USD. Tres escenarios:

| Escenario | Acción | BTC final | USD final | Outperformance |
|---|---|---|---|---|
| **HODL** | No tradear | 0.0100 BTC | $825 | 0% (baseline) |
| **Trade ganador** | Long BTC, +5% en USD | 0.0095 BTC | $864.40 | **-5% en BTC** ❌ |
| **Trade ganador real** | Long BTC, +15% en USD | 0.0104 BTC | $945.45 | **+4% en BTC** ✅ |

**Conclusión:** para "ganar BTC" tu trade tiene que **outperform** simplemente HODLing. Si BTC sube 10% y tú haces +5% USD, en BTC has perdido stack.

### Implicaciones para la estrategia

1. **Long BTC con tu mismo capital BTC** = duplicas exposure direccional. Si LONG funciona pero solo se mueve igual al spot, no ganaste BTC stack-wise.
2. **Short BTC** = la única forma de ganar BTC en bear market sin perder spot exposure.
3. **Trades direccionales** deben superar el spot return en el período tradeado.
4. **Mejor approach:** combinar shorts en VOLATILE down-moves + longs en pullbacks técnicos fuertes (capturar el move + luego vuelves a estar en BTC).

## Universo de assets

**Solo BTCUSDT** (o BTCUSD según naming Quantfury) — long/short.

NO operar otros assets aquí — el profile completo está diseñado around BTC stacking.

## Reglas duras (ver `rules.md`)

| Regla | Valor | Tipo |
|---|---|---|
| Risk per trade | **2% del BTC capital** (0.0002 BTC en 0.01 BTC) | hard cap |
| Max trades/día | 3 | BLOCK |
| Leverage usado | **5x** (effective, dentro del cap Quantfury) | safety |
| BTC outperformance target | **> 0% mensual** vs HODL | objetivo |
| Daily loss BLOCK | -2% en BTC | STOP día |
| Total DD BLOCK | -10% en BTC del capital inicial | STOP profile |
| Ventana | 24/7 (cripto) | INFO |

## Workflow distinto

### Cuando HODL es mejor que tradear

Si el régimen es TRENDING UP fuerte:
- HODL > tradear (porque cualquier trade direccional con SL es 50/50, mientras HODL captura 100% del move)
- En trending up, **SOLO operar shorts en pullbacks** (capturar pullback + volver a BTC stack)

Si el régimen es TRENDING DOWN:
- Trade SHORT direccional (gana BTC mientras spot baja)
- O ESTAR FUERA en USD/USDC y volver a BTC al fondo

Si el régimen es RANGE:
- Mean Reversion 15m igual que retail (gana ambas direcciones)

Si el régimen es VOLATILE:
- NO operar — wicks pueden costar BTC stack significativo

### Métrica diaria

```bash
# /journal en quantfury calcula:
- BTC PnL del día (en sats)
- USD equivalent (informativo)
- BTC HODL benchmark del mismo período
- BTC outperformance: (your_btc_return - hodl_btc_return)
```

Si outperformance es NEGATIVO durante 30+ días → considerar pasar a HODL only.

## Setup inicial

```bash
# 1. Descargar Quantfury app (iOS/Android/desktop)
#    https://quantfury.com

# 2. Verificación KYC + depósito inicial
#    Depositar 0.01 BTC desde wallet propio (cold/hot wallet)
#    NOTA: Quantfury custodia el BTC durante trading, retorna a wallet al retirar

# 3. Llenar credenciales en .env (read-only para tracking):
#    QUANTFURY_API_KEY=<...>     (si Quantfury ofrece API — verificar al activar)

# 4. Switch profile
/profile quantfury

# 5. Verificar statusline
bash .claude/scripts/statusline.sh
# → [QUANTFURY] ₿0.0100 (≈$750.00) | vs HODL +0.00% | ...

# 6. Primer test con 0.0001 BTC (1% del capital)
/morning                      # análisis 15m BTC, igual que retail
# Si setup A-grade → ejecutar manual en Quantfury app (size en BTC)
```

## Diferencias críticas vs profile retail (Binance)

| Concepto | retail (Binance) | quantfury |
|---|---|---|
| Capital | USD ($18.09) | **BTC (0.01)** |
| PnL tracking | USD | **BTC (sats)** |
| Métrica clave | % return USD | **% return BTC + vs HODL** |
| Filosofía | Multiplicar USD | **Stack más sats** |
| Long bias | OK (BTC trending) | NO necesariamente — verifica vs HODL |
| Short BTC | Capital risk USD | **Único modo de ganar sats en bear market** |
| Statusline | $18.09 ≈ ₡8,241 | ₿0.0100 ≈ $750 (vs HODL +X%) |

## Reglas cross-profile

1. **NO operar BTC en quantfury + retail simultáneo.** Doble exposición direccional.
2. **NO copiar señales bitunix de BTC** si tienes posición quantfury BTC.
3. **NO tomar trade BTC en ftmo/fundingpips** si quantfury tiene posición — quadruple exposición.
4. Si quieres maximizar BTC stack: dedica QUANTFURY exclusivamente. Cierra otros BTC.

## Métricas adicionales (helper específico)

`/journal quantfury` calcula:
- **BTC return del período** (week/month/all-time)
- **HODL benchmark return** del mismo período (BTC USD start vs end)
- **Outperformance** = (you - HODL)
- **Active vs passive** decisión: si outperformance promedio mensual <2%, considera HODL

`bash .claude/scripts/btc_outperform.py --equity-csv <path> --period 30d` — calcula outperformance mensual.

## Plan declarado del usuario

> "Mi capital es en BTC y gano BTC, no $."

Esto significa:
1. **No medir éxito en USD** — distorsiona la realidad
2. **HODL es el benchmark** — si no superas HODL, no estás "ganando"
3. **Best-case:** acumular BTC stack durante bull market (longs durante pullbacks) + bear market (shorts puntuales)

## Disclaimer

Quantfury no permite leverage extremo (típicamente 1-5x) — sistema configurado a 5x cap.
Las posiciones short consumen funding fee (puede ser positivo o negativo según mercado).
Mide TODO en BTC — la psicología cambia cuando dejas de pensar en USD.

> "Bitcoin is the unit. USD is the noise."
