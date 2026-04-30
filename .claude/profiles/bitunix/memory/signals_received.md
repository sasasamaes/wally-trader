# Bitunix — Signals received & decisions

> Cada señal de la comunidad punkchainer's, su validación, y outcome.
> Útil para medir hit_rate_filtered vs hit_rate_blind y mejorar filtros.

## Format de cada entrada

```
## YYYY-MM-DD HH:MM — SYMBOL Direction Leverage

**Señal recibida:** entry X, SL Y, TP Z, leverage Lx
**Source:** punkchainer Discord (PunkAlgo bot / canal #punkchainer)
**Validación sistema:**
  - 4 filtros: N/4
  - Multi-Factor: ±N (DIRECTION)
  - ML XGBoost: N
  - Régimen: RANGE/TRENDING/VOLATILE
  - Chainlink delta: N% (OK/WARN/ALERT)
**Validation Score:** N/100
**Decisión:** EJECUTADO size full / EJECUTADO size 50% / SKIP
**Resultado real (si ejecutado):** TP1/TP2/SL/manual at price Z, PnL $X
**Resultado hipotético (si SKIP):** ¿hubiera sido WIN? (verificar 24h después)
**Aprendizaje:** una línea con la lección
```

## Histórico

(vacío hasta primera señal procesada)

---

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
