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
