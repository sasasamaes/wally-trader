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
