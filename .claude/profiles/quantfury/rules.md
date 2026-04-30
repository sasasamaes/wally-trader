# Reglas Quantfury — BTC-denominated

> Filosofía única: **éxito = más BTC**, no más USD.

## 1. RISK PER TRADE — 2% del BTC capital

**Cálculo:** `risk_btc = capital_btc × 0.02`

Default capital 0.01 BTC → max loss 0.0002 BTC per trade (≈$15 a $75k/BTC).

| Nivel | Trigger | Acción |
|---|---|---|
| **APPROVE** | Risk ≤ 2% BTC | Ejecutar |
| **REJECT** | Risk > 2% | Reduce size hasta cumplir |

## 2. MAX TRADES POR DÍA — 3

| Nivel | Trigger | Acción |
|---|---|---|
| OK | 0-2 trades | Continúa |
| WARN | 3 trades | "Solo si A-grade" |
| BLOCK | >3 trades | Skip resto día |

## 3. LEVERAGE CAP — 5x effective

Quantfury permite hasta 30x en BTC perp. **Tu sistema cap a 5x.**

| Razón |
|---|
| Capital es propio (no USD) — pérdidas pesan psicológicamente más |
| 5x con SL 2% = max risk 10% del notional, manejable |
| Quantfury cobra spread + funding — leverage alto multiplica esos costos |

## 4. DAILY LOSS BLOCK — -2% en BTC

| Nivel | Trigger | Acción |
|---|---|---|
| OK | Daily PnL > -1% BTC | Continúa |
| WARN | Daily PnL ≤ -1% BTC | "1 trade más solo si excepcional" |
| BLOCK | Daily PnL ≤ -2% BTC | STOP día. Force close abiertos. |

## 5. TOTAL DD BLOCK — -10% del capital BTC inicial

```
Capital inicial: 0.01 BTC
Capital actual: ?
Total DD %: (current - initial) / initial × 100
```

| Nivel | Trigger | Acción |
|---|---|---|
| OK | DD > -5% | OK |
| WARN | DD ≤ -5% | "Estás en zona de riesgo, opera mínimo" |
| BLOCK | DD ≤ -10% | **STOP PROFILE.** Pausa, review, o pasar a HODL. |

## 6. OUTPERFORMANCE TARGET — > 0% mensual vs HODL

**Métrica clave:** después de 30 días de trading activo, tu BTC stack debe ser **mayor** que el de HODL.

| Outperformance 30d | Diagnóstico |
|---|---|
| > +5% | **EXCELENTE** — tu sistema agrega valor real en BTC stack |
| 0% a +5% | OK — ligero edge, sigue iterando |
| -2% a 0% | **WARNING** — tu trading no aporta vs HODL |
| < -2% | **STOP PROFILE.** Pasar a HODL only por 30 días + recalibrar |

`bash .claude/scripts/btc_outperform.py --period 30d` calcula esto automáticamente.

## 7. RÉGIMEN-SPECIFIC RULES

### TRENDING UP (BTC subiendo claramente)
- **Default:** HODL > tradear longs
- LONG solo si setup excepcional (4/4 + multifactor>+70 + ML>70)
- SHORT solo en pullbacks técnicos confirmados (4/4 + RSI>75 al menos)
- WARN: longs en uptrend = replicar HODL (no ganas BTC stack)

### TRENDING DOWN
- **Default:** SHORT direccional cuando 4/4 alineados
- LONG solo en confirmación de reversal (HHs + cierre>EMA200)
- Esta es **la fase oro** para stackear BTC

### RANGE
- Mean Reversion 15m a ambos lados
- Mejor fase para tradear (capturas ambas direcciones)

### VOLATILE
- **NO OPERAR.** Wicks pueden costar más BTC que el TP esperado.

## 8. FUNDING FEES (quantfury-specific)

Quantfury cobra spread (no comisión típica) + funding fee en perp positions.

| Funding rate | Acción |
|---|---|
| +0.01% / 8h o menos | OK, ignorar |
| +0.05% / 8h | WARN si position >24h |
| > +0.1% / 8h | NO abrir longs, considera shorts en su lugar |
| < -0.1% / 8h | NO abrir shorts, considera longs |

Funding negativo = los longs reciben pago = oportunidad LONG si setup OK.

## 9. CROSS-PROFILE EXCLUSION

| Si tienes BTC abierto en... | Acción |
|---|---|
| `retail` (Binance) | **NO operar quantfury BTC** — doble exposición |
| `bitunix` | NO si la señal es BTC |
| `ftmo` | NO si tu trade FTMO es BTC |
| `fundingpips` | NO si tu trade FP es BTC |

Quantfury debe ser **profile dedicado** los días que lo uses.

## 10. SHORT-SPECIFIC RULES

Shorts en quantfury son distintos:

1. **Funding consideration:** check rate antes de open. Si negativo profundo → caro mantener.
2. **Force exit timing:** todos los shorts cerrados a CR 23:59 (anti-overnight).
3. **NO trailing TP:** target FIJO. Cada hora abierta consume funding.
4. **TP ratio menor:** 1:1.5 a 1:2 (vs 1:2.5 de retail) — capturar move más rápido para minimizar funding.

## 11. RE-ENTRY DESPUÉS DE LIQUIDATION/SL

Si pegaste SL en quantfury:
- **NO re-entry en próximas 30min** (anti-revenge en BTC)
- Siempre evaluar régimen + outperformance running antes de re-entry
- Si outperformance running 7d <-2%, no re-entries hoy

## Order de checks pre-entry

```
1. Profile == quantfury? → si no, skip
2. Daily PnL > -2% BTC? → si no, BLOCK
3. Total DD > -10% BTC? → si no, BLOCK PROFILE
4. Trades hoy < 3? → si no, BLOCK
5. Régimen NO es VOLATILE? → si VOLATILE, BLOCK
6. Si TRENDING UP fuerte: ¿setup excepcional? → si no, prefer HODL
7. Funding rate OK para dirección? → si no, ajustar
8. Sin conflict cross-profile BTC? → si no, REJECT
9. Validation score ≥60% (multifactor + ML)? → si no, REJECT
10. Outperformance 7d > -3%? → si no, modo conservador (size half)

→ TODOS OK → APPROVE
```

## 12. EVALUATION MENSUAL OBLIGATORIA

Cada 30 días:
1. Calcular `outperformance_30d` con `btc_outperform.py`
2. Si > +5% → continuar normal
3. Si 0% a +5% → continuar pero marcar para evaluar 60d
4. Si -2% a 0% → modo conservador (risk reducido a 1%)
5. Si < -2% → **PAUSAR PROFILE**, pasar a HODL 30 días, review fundamental

## Disclaimer

Quantfury custodia tu BTC durante trading — NO es self-custody. Riesgo de plataforma existe.
Las pérdidas se realizan en BTC absoluto (sats), no en USD.
Las ganancias también — mide siempre vs HODL.
