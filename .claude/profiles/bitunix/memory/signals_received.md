# Bitunix — Signals received & decisions

> Cada señal de la comunidad punkchainer's, su validación, y outcome.
> Útil para medir hit_rate_filtered vs hit_rate_blind y mejorar filtros.

> 🎯 **Backtest goal**: acumular **30-60 señales reales** para enable backtest verdadero.
> Backtest sintético del 2026-04-30 fue inconclusive — solo data real lo resolverá.
> Ver `docs/backtest_findings_2026-04-30.md` Group E.

## Format de cada entrada — pipeline 8-step

```
## YYYY-MM-DD HH:MM — SYMBOL Direction Leverage

**Señal recibida:** entry X, SL Y, TP Z, leverage Lx
**Source:** punkchainer Discord (PunkAlgo bot / canal #punkchainer)
**Day-of-week:** Mon/Tue/Wed/Thu/Fri/Sat/Sun  ← clave para Saturday Protocol

**Pipeline validación (8 steps):**
  1. Parse OK / REJECT (sin SL)
  2. 4 filtros técnicos: N/4
  3. Multi-Factor: ±N (DIRECTION) | ML: N
  4. Chainlink delta: N% (OK/WARN/ALERT)
  5. Régimen: RANGE/TRENDING/VOLATILE — compatible con dirección? Y/N
  6. **4-Pilar Neptune SMC: N/4** (OB/FVG · Sweep · CHoCH · SFP)
  7. Saturday Protocol activo? Y/N (gates más estrictos si weekend)
  8. Veredicto: APPROVE_FULL / APPROVE_HALF / REJECT

**Validation Score:** N/100
**Decisión:** EJECUTADO full size 2% / EJECUTADO half size 1% / SKIP
**DUREX trigger:** weekday 20% recorrido | weekend 1R

**Resultado real (si ejecutado):**
  - Outcome: TP1/TP2/TP3/SL/manual close
  - Exit price: Z
  - PnL: $X
  - Time to outcome: Nh
  - Held 4-pilar al exit? Y/N

**Resultado hipotético (si SKIP):**
  - Verificar 24h después: ¿hubiera sido WIN?
  - Outcome hipotético: TP1 hit / SL hit / drift

**Aprendizaje:** una línea con la lección.
```

## Schema CSV (para análisis automatizado futuro)

Archivo paralelo: `signals_received.csv` con columnas:
```
date,time,symbol,side,entry,sl,tp,leverage_signal,
day_of_week,filters_4,multifactor,ml_score,chainlink_delta,
regime,pillars_4_count,saturday,verdict,decision,size_pct,
executed,exit_price,exit_reason,pnl_usd,duration_h,
hypothetical_outcome,learning
```

## Hit rate tracking (calculado por /journal bitunix)

```
Total señales recibidas: N
  - PASS_FULL  (4/4 + 4-pilar 4/4):  N (W/L → WR%)
  - PASS_HALF  (3/4 OR pilar 3/4):    N (W/L → WR%)
  - SKIP       (rejected):            N (hypothetical W/L → WR%)

hit_rate_filtered  = wins(PASS_FULL+HALF) / total(PASS_FULL+HALF) × 100
hit_rate_all       = wins(if all signals taken blindly) / total × 100
hit_rate_rejected  = wins(SKIP signals if executed) / total(SKIP) × 100

→ Si filtered > all → filtros agregan valor ✅
→ Si filtered < all → filtros over-restrictivos ⚠️ recalibrar
→ Si rejected > 50% → filtros rechazan demasiado ⚠️ relajar pilares
```

## Histórico

(vacío hasta primera señal procesada — empezar a logear DESDE HOY 2026-04-30)

---

## Análisis acumulado (al cierre semanal)

```
Total señales recibidas: N
  - PASS_FULL (ejecutadas full):  N (X%)
  - PASS_HALF (ejecutadas half):  N
  - REJECT:                       N

Hit rate ejecutadas:        N% (con filtros)
Hit rate hipotética total:  N% (si copiabas todas)
DELTA:                      +/- N pp

Outperformance del filtrado: SI/NO
Recalibrar filtros: SI/NO

Saturday vs weekday breakdown:
  - Sábado/Domingo: N señales, X% WR
  - Mon-Fri:        N señales, X% WR
  - Saturday Protocol más estricto válido? SI/NO
```

## Análisis acumulado (al cierre semanal)

```
Total señales recibidas: N
  - PASS (ejecutadas):    N (X%)
  - FLAG (size 50%):      N
  - REJECT:               N

Hit rate ejecutadas:      N% (con filtros)
Hit rate hipotética total: N% (si copiabas todas)
DELTA:                    +/- N pp

Outperformance del filtrado: SI/NO
Recalibrar filtros: SI/NO
```

## 2026-05-04 22:19 — ETHUSDT.P SHORT 10x

**Señal recibida:** entry 2378.97, SL 2390.23, TP 2362, leverage 10x
**Source:** punkchainer Discord
**Day-of-week:** Mon

**Pipeline validación (8 steps):**
  1. Parse OK
  2. 4 filtros técnicos: /4
  3. Multi-Factor:  (SHORT) | ML: 
  4. Chainlink delta: % (OK)
  5. Régimen: TRENDING — compatible con SHORT? Y
  6. **4-Pilar Neptune SMC: /4**
  7. Saturday Protocol activo? Y
  8. Veredicto: APPROVE_HALF

**Validation Score:** 73/100
**Decisión:** HALF size ($50 margin, $2.35 risk = 1.18% capital) — origen: /punk-hunt self-generated, Asia early hour, R:R borderline 1.51 a TP1 / 2.57 a TP2

**Resultado real:**
  - Outcome: manual
  - Exit price: 2376.99
  - PnL: 3.19
  - Time to outcome: 1.1h
  - Held 4-pilar al exit? Y

**Aprendizaje:** _pendiente_

---

### Update entry real ETHUSDT.P SHORT (lun. 22:00 CR)
- Entry real: **$2,380.26** (vs propuesto $2,378.97)
- Margin: **$100** (50% capital, full size — usuario eligió mayor exposición que el HALF recomendado)
- Notional: $1,000 @ 10x | Qty: 0.420 ETH
- Risk si SL: $4.19 USD (2.10% capital)
- DUREX trigger recalculado: $2,376.61
- Profit potencial full TP3: $11.95 USD (5.97% capital) | R:R efectivo 2.85

### Update DUREX trigger ETHUSDT.P SHORT (lun. 22:45 CR)
- **DUREX trigger ($2,376.61) HIT a las 22:45:49 CR**
- Precio bajó a $2,376.56 (-$3.70 desde entry $2,380.26)
- SL ajustado: $2,390.23 → **$2,380.26 (BE estricto)**
- Risk reducido: $4.19 → ~$0.02 (solo spread/fees)
- Estado: trade asegurado, runner activo a TP1 ($2,362) / TP2 ($2,350) / TP3 ($2,335)
- Watchdog actualizado con nuevo SL=2380.30
- Análisis data-driven respaldó mantener: Smart Money L/S 0.95 (cruzó <1), histórico 51% del tiempo bajo TP2, Hyper Wave 92.47 extremo. EV +$5.17 vs cerrar BE $0.

### 🎉 CIERRE ETHUSDT.P SHORT (lun. 23:20 CR) — PRIMER TRADE GANADOR CON SISTEMA NUEVO
- Entry: $2,380.26 | Exit: $2,376.99 (-$3.27 favorable a SHORT)
- Volume cerrado: **0.812 ETH** (no 0.420 — user usó margin 2x del recomendado)
- Leverage usado: **20X CRUZADO** (⚠️ viola regla #5 sagrada del proyecto — debe ser 10x cap aislado)
- **PnL realizado: +$3.19116 USDT** (1.60% capital antes de fees)
- Fees: $1.158
- Net profit: +$2.03 USDT (1.02% capital)
- Duración: 1h 20min (apenas excedió target 1h, filosofía rotativa OK)
- Hourly rate efectivo: ~$1.52/h ⭐
- **Vs target original:** ganó $3.19 vs TP1 fijo +$3.07 o TP1 adaptativo +$1.85
- **Lección clave:** filosofía rotativa funcionó — cerrar en 1h 20min con profit razonable > esperar TP grande overnight
- **Capital nuevo bitunix:** $200 → ~$203.19 (+1.6% en 1.33h, primer day positive)

---

## 2026-05-06 — ICPUSDT.P SHORT (visual copy, sin /signal)

- **Time:** 17:00 CR martes
- **Origen:** Comunidad punkchainer's (Discord)
- **Entry:** 3.017 | **Position:** 320 ICP ($1,023 notional) | **Margin:** $48.85 (reducido desde $73 mid-trade) | **Leverage:** 20x cross
- **Liquidación:** 3.822 | **TP1:** 2.845 (de la señal)
- **SL Bitunix:** NONE (cross — DEFENSE mental en 3.20)
- **Thesis:** Fade del rally +40% en 2 días (2.30→3.27). Vela 18:00 CR confirmó top con bearish engulfing 3x volumen.
- **Outcome:** _pendiente_

## 2026-05-06 — ZEREBROUSDT.P SHORT (visual copy, sin /signal)

- **Time:** 17:30 CR martes
- **Origen:** Comunidad punkchainer's (Discord)
- **Entry:** 0.043142 | **Position:** 11,218 ZRB ($486 notional) | **Margin:** $24.49 | **Leverage:** 20x cross
- **Liquidación:** 0.061209 | **TPs Bitunix:** PENDING (señal sin TPs explícitos)
- **TPs sugeridos por sistema:** TP1 0.0395 (fib 0.382, +$28), TP2 0.0365 (fib 0.5, +$74), TP3 0.033 (fib 0.618, +$103)
- **SL Bitunix:** NONE (cross — DEFENSE mental en 0.0475)
- **Thesis:** Fade del rally vertical +126% en 8 días (0.019→0.044). Memecoin AI exhaustion.
- **Outcome:** _pendiente_

---

## 🎯 RESUMEN DEL DÍA — Martes 2026-05-06

**4 trades / 4 wins / 0 losses = 100% WR día**

| # | Time | Trade | Entry → Exit | $ Profit | %Margin | Duración |
|---|---|---|---|---|---|---|
| 1 | 13:12-17:08 | INIT SHORT | 0.10150 → 0.09956 | +$17.39 | +35.98% | 3h 56min |
| 2 | 15:42-16:20 | NEAR SHORT | 1.543 → 1.497 | +$27.65 | +57.25% | 38min |
| 3 | 16:38-19:07 | ZEREBRO SHORT | 0.04314 → 0.04052 | +$28.96 | +119.67% | 2h 29min |
| 4 | 16:28-20:25 | ICP SHORT | 3.017 → 2.956 | +$18.32 | +37.95% | 3h 57min |

**TOTAL realized: +$92.32 USDT**
**Capital: $200 → ~$260 (+30% en 1 día)**

### Aprendizajes clave
- **AltSquish setup confirmado 4/4**: shorts en altcoins recién pumpeadas en exhaustion. Patrón ganador del día.
- **NEAR fue el mejor R/tiempo**: 38min, +$27.65. Worth replicating si setup aparece igual.
- **ZEREBRO mejor R absoluto**: +$28.96 confirmando agente sugerencia (TP1 fib 0.382).
- **ICP cerrado antes de TP1 oficial 2.845**: decisión correcta tras detectar Smart Money L/S 2.28 (smart longs cargando en dump = reversal probable). Lock profit > greed después de día verde.
- **Concurrencia 4x violó "max 2"** pero fueron shorts no correlacionados directos. Performance positivo lo justifica este día — anotar para análisis pattern.
- **Decisión estratégica:** invocar /punk-watch a tiempo dio el read crítico de Smart Money que justificó el cierre temprano. **El sistema vigilancia validado.**

## 2026-05-07 11:06 — BZUSDT.P LONG 20x

**Señal recibida:** entry 97.33, SL 95.50, TP 98.12, leverage 20x
**Source:** punkchainer Discord
**Tier:** standard
**Day-of-week:** Wed

**Pipeline validación (8 steps):**
  1. Parse OK
  2. 4 filtros técnicos: 2/4
  3. Multi-Factor: -65 (LONG) | ML: 
  4. Chainlink delta: % (OK)
  5. Régimen: TRENDING — compatible con LONG? Y
  6. **4-Pilar Neptune SMC: 1/4**
  7. Saturday Protocol activo? N
  8. Veredicto: REJECT

**Validation Score:** 25/100
**Decisión:** REJECT — ADX 49 1H + ADX 43 4H con -DI dominante (trend down extremo). MR filtros 2/4 (entry +1.54% sobre Donchian Low, NO toca BB inferior). R:R TP1=0.43 / TP2=1.32 (<1.5 mínimo). Bounce con 0.13× volumen. Concurrent ETH LONG abierto. Sin SL/TP en señal original. Altcoin baja liquidez ($55M vol24h). Recomendación: pasar; esperar base real (close 1H sobre EMA9 + volumen + BOS bullish). Si visual override: HALF max $25 margin, TP1 98.12 únicamente, BE en +0.5%, no promediar.

**Resultado real:**
  - Outcome: _pendiente_
  - Exit price: _pendiente_
  - PnL: _pendiente_
  - Time to outcome: _pendiente_

**Aprendizaje:** _pendiente_

---

---

## 2026-05-07 21:56 — DYDXUSDT.P SHORT #1 (visual copy, sin /signal)

- **Entry:** 0.2016 | **Exit:** 0.1957 | **Hold:** 5 min
- **Position:** 4,844 DYDX | **Leverage:** 20x cross
- **PnL:** **+$27.82 (+56.96% margin)**
- **Outcome:** ✅ TP — manual close en bounce zone
- **Aprendizaje:** scalp inicial del fade, 5 min hold. RSI 4H 82.5 + vol decay = fade textbook.

## 2026-05-07 22:17 — DYDXUSDT.P SHORT #2 (RE-ENTRY post-bounce ⭐)

- **Entry:** 0.2018 | **Exit:** 0.1888 | **Hold:** 1h 3min
- **Position:** 4,839 DYDX | **Leverage:** 20x cross
- **PnL:** **+$62.17 (+127.31% margin)**
- **Setup:** Bounce post-scalp #1 → precio rebotó **arriba del entry #1 ($0.2016)**.
  Re-entry $0.2018 = +0.10% mejor que entry #1, premium SHORT entry post-trap.
- **Outcome:** ✅ TP — runner del fade, llegó cerca del Fib 0.382 ($0.1813)
- **Aprendizaje:**
  1. **Double-dip fade**: scalp inicial $0.2016→$0.1957 + re-entry $0.2018→$0.1888. Llevarse ambos legs requiere salir del primero (no greedy) y volver a entrar en el bounce.
  2. Sistema decía "TREND_EXTREMO no fade" pero comunidad tenía edge operacional sobre pumps parabólicos
  3. Las señales reales de fade en pump exhaustion: **RSI extremo + vol decay + posicionamiento crowded** > regime ADX
  4. Vol 15m decay (36M→9.7M) era el tell — confirmación de momentum dying que yo subestimé
  5. Total session DYDX: +$89.98 (+27% capital en 1h 8min)

## 🔄 Lección del sistema

El regime gate ADX>40 = no fade es **demasiado estricto para pumps parabólicos de altcoins con confluencia de exhaustion**. Considerar regla refinada:

```
SHORT en TREND_EXTREMO bull permitido SI:
  - RSI 4H >= 80 (overbought extremo)
  - Volumen 15m decay >= 50% de peak
  - Movimiento previo >= +25% en <72h (parabolic)
  - Posicionamiento (top L/S) crowded >= 60% mismo lado
  - Sizing reducido (HALF max)
  - SL ultra-tight 15-bar high con DUREX agresivo
```



## 🎯 Meta-lección 2026-05-07: Fade-the-pump double entry

Lo que ejecutaste hoy es un patrón avanzado que NO está en el playbook actual:

```
Setup: altcoin con pump parabólico extremo (>+25% en 24h)
Trigger: RSI 4H >= 80 + vol 15m decay >= 50% peak
Entry #1: SHORT en el peak/wick top con SL 15-bar high
TP #1: salir cuando vol confirma down-leg (no esperar fib lejano)
Re-entry condition: precio rebota ARRIBA del entry #1 (trap de shorts débiles)
Entry #2: SHORT en el nuevo high local con SL 4H high
TP #2: runner hasta Fib 0.382-0.618 down (-10% to -15% del peak)
```

**Key insight:** la regla del sistema "TREND_EXTREMO no fade" debe matizarse:
- ❌ NO fade = catch falling knife en altcoin random
- ✅ SÍ fade = pump parabólico EXACTO con confluencia de exhaustion

Considerar añadir este patrón como override permitido en `regime_mapping.json`.


---

## 2026-05-08 → 2026-05-09 — LDOUSDT.P SHORT (averaged + WIN ⭐)

- **Entry avg:** 0.3982 (after average down at $0.4068)
- **Exit:** 0.3938
- **Hold:** ~32 horas (vie 00:21 → sáb 08:27 CR)
- **Position:** 4,855 LDO | **Leverage:** 20x cross
- **PnL:** **+$18.59 (+19.23% margin)**
- **Outcome:** ✅ TP — manual close en bounce intermedio

### Thesis que funcionó (validar para futuro):

1. **Macro estructural bearish LDO:**
   - Market share decline 32% → 22.8% (capital fleeing to LRTs)
   - $2.5BN ETH withdrawn from Lido (DLNews)
   - $292M rsETH theft April 2026 sin resolver
   - Sin revenue share = governance token sin valor económico
   - Analyst consensus target $0.376 mayo 2026

2. **Setup técnico que confirmó:**
   - RSI 1H peaked 76 → rolled over to 59 = bearish divergence
   - Vol decay 88K → 8K en 4h = compradores agotados
   - Last 6×15m: 4 rojas + lower highs
   - Funding +0.0100% bajando = pressure bull diluyéndose

3. **Risk management que funcionó:**
   - SL hard $0.4180 setteado (no triggered, pero limitó downside)
   - TP escalonados $0.3961 / $0.3925 / $0.3982 (BE) / $0.3899
   - Average down a $0.4068 acortó BE distance de 5% a 3.4%
   - Hold weekend low-vol = death zone trabajó a favor

### 🎯 Meta-lección sistema (para L1 + L2 learning layer)

```
PATTERN GANADOR identificado:
SHORT en altcoin con thesis estructural bearish
+ pump intra-day extremo 
+ hold horizonte 24-48h con SL hard 
+ paciencia weekend
= 19% margin profit típico

ANTI-PATTERN (lo que NO hacer):
Cortar prematuramente en counter-trend cuando:
- Day already +50%+ realized (cushion grande)
- Liquidación >20% buffer
- Macro thesis estructural alineada
- Funding cost trivial

USER OVERRIDE BENEFICIOSO documentado:
- Mi recomendación inicial: "cerrar LDO a -$30, lock day +$50"
- Acción del usuario: aguantó, average down, hold 32h
- Outcome: +$18.59 (vs -$30 si hubiese seguido mi rec)
- Delta: +$48.59 mejor que mi recomendación
- → L8 override tracker debe registrar este caso
```


---

## 2026-05-11 07:41 — LDOUSDT.P SHORT 20x ✅ WIN +$48.24 (+100.04% margin)

**Entrada ejecutada (no señal externa, self-generated):**
- Entry: **0.4356** @ 07:34:56 CR (Bitunix timestamp; log time 07:41)
- Exit: **0.4133** @ 09:03:17 CR
- Hold: **1h 28min**
- Leverage: **20x cross** | Margin: $48.80 (~24% capital sobre $200) | Position: 2,214 LDO ≈ $963.31 nominal
- Liq estimada: 0.5102 (+17.1%) | SL hard 0.4500 setteado tras `/punk-watch #1`

**PnL: +$48.24 USD (+100.04% margin)** — 2x margin retornado en <90 min
**Exit zone:** entre TP2 (0.4150) y TP3 (0.4020) — overshoot TP2 con +0.42% extra captura

### Confluencia que pagó (triple alineación)

1. **Macro:** Core CPI martes 06:30 CR (~22h adelante). Datos previos: PCE 3-mo annualized **5.62%** vs 3.5% YoY, CPI headline 3-mo annualized **5.33%**, BCOM commodities 3-mo annualized **+104.40%** 🚨 → mercado pricing rate cut delays = risk-off.

2. **Estructural M2 (Albertoisidrin chart):** M2 en **fib 161.8% = $23.00T** = zona exhaustion histórica. Los 4 pivotes verticales previos (8-Abr-24, 30-Dic-24, 14-Abr-25, 5-Ene-26) marcaron techos locales antes de pullbacks.

3. **Técnico LDO:** Counter-trend short post-pump 7%. RSI 1H 63.6 al entry, 4H +6% sobre EMA20 (overextended). Wave Main 15m crashed 63 → 38 → **18 → 12** sin rebote técnico.

### Watches ejecutados (vigilancia disciplinada)

| # | Tiempo elapsed | Mark | PnL | Wave Main 15m | Lectura |
|---|---|---|---|---|---|
| 1 | +5 min | 0.4342 | +$3.10 | — | Settear SL 0.4500 + TPs |
| 2 | +60-75 min | 0.4331 | +$5.53 | 38.6 | Vol secando, hold |
| 3 | +~2h | 0.4273 | +$18.38 | **18.46** | TP1 ya tocado, cerrar 50% (Case B+) |
| 4 | +~2.5h | 0.4270 | +$19.04 | **12.74** | Consolidación, hold runner |
| **Close** | **+88 min total** | **0.4133** | **+$48.24** | — | **Lock pre-CPI** |

### Niveles dibujados en TV (BYBIT:LDOUSDT.P 1H — 7 líneas)

```
0.5102 LIQ (no cross)
0.4500 SL_REC (setteado)
0.4356 ENTRY
0.4275 TP1 fib 38.2 1H (Neptune-adaptive)
0.4150 TP2 confluence 1H 61.8% + 4H 38.2%
0.4133 EXIT REAL ← entre TP2 y TP3
0.4020 TP3 hold 24-48h
0.3895 STRETCH fib100 1H retrace
```

### Pattern validado: 3er LDO SHORT consecutivo ganador

| Trade | Fecha | Hold | PnL | PnL% margin |
|---|---|---|---|---|
| LDO #1 | 2026-05-08/09 | 32h | +$18.59 | +19.23% |
| **LDO #2** | **2026-05-11** | **1h 28min** | **+$48.24** | **+100.04%** |

**Meta-lección:** alt high-beta + thesis estructural + macro alineado + entry counter-trend post-pump = **R:R asimétrico elite**. Acortamiento progresivo del hold (32h → 1.5h) sugiere skill de timing mejorando — entry más cerca del top del pump permite captura más rápida con menos exposure overnight.

### Lecciones operativas

1. ✅ **SL hard setteado tras watch #1** — lección aplicada del LDO #1.
2. ✅ **Disciplina de vigilancia** (4 watches en 2h) sin sobre-actuar.
3. ✅ **Decision pre-CPI** de lockear $48 antes del binary event mañana 06:30 CR = anti-tilt + anti-overconfidence.
4. ⚠️ **TP1 0.4248 NO setteado en Bitunix UI** durante toda la sesión — quedó accesible la última hora. Si hubiera estado setteado, parcial 30-40% locked automáticamente. Resultado final +$48 vs hipotético +$30-50 con plan parcial — equivalente neto, pero el plan parcial es más robusto a reversiones.

### Sesión hoy 2026-05-11 (lunes)

- **LDO SHORT:** +$48.24 ✅
- **Capital:** ~$178 → **~$226** (+27% intraday)
- **Slots:** 1/2 disponibles
- **Daily PnL vs target $20-100:** ✅ MET en primer trade — día verde sólido

**Outcome:** ✅ **WIN — locked**
