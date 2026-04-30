# Reglas Bitunix Copy-Validated

> Filosofía: el edge no es seguir señales — es **rechazar las malas**.

## 1. RISK PER COPIED SIGNAL — 2% del capital

**Cálculo:** `risk_usd = capital × 0.02`

Default capital $50 → max loss $1.00 per signal.

| Nivel | Trigger | Acción |
|---|---|---|
| **APPROVE** | Risk ≤ 2% | Ejecutar |
| **REJECT** | Risk > 2% (señal pide más) | NO copiar — ajustar size local hasta cumplir 2% |

## 2. MAX COPIED SIGNALS POR DÍA — 3

Aunque haya 10 señales en Discord, max 3/día. Disciplina anti-FOMO.

| Nivel | Trigger | Acción |
|---|---|---|
| **OK** | 0-2 trades hoy | OK siguiente |
| **WARN** | Ya 2 trades hoy | "Solo 1 más, asegúrate sea A-grade" |
| **BLOCK** | 3 trades hoy | Skip resto del día |

## 3. MIN VALIDATION SCORE — 60%

**Compositición del score (0-100):**
- 4/4 filtros técnicos: 25 puntos
- Multi-Factor en dirección: hasta 25 puntos (proporcional al |score|)
- ML XGBoost en dirección: hasta 25 puntos
- Régimen compatible: 15 puntos
- Chainlink valida: 10 puntos

| Nivel | Trigger | Acción |
|---|---|---|
| **MAX_GO** | Score ≥80 | Ejecutar size full (2%) |
| **GO** | Score 60-80 | Ejecutar size full (2%) |
| **FLAG** | Score 50-60 | Ejecutar size HALF (1%) — borderline |
| **REJECT** | Score <50 | SKIP — log a signals_received.md |

## 4. LEVERAGE CAP — 10x (override hard)

Las señales de la comunidad pueden decir 20x. **Tu sistema OVERRIDE a 10x.**

| Señal pide | Tu ejecutas |
|---|---|
| 5x | 5x (igual) |
| 10x | 10x (igual) |
| 15x | 10x (cap) |
| 20x | 10x (cap) |
| 50x+ | **REJECT** — leverage absurdo, no hay setup que justifique |

**Razón:** a 20x, un wick de 5% liquida tu posición ANTES del SL (que típicamente es 2-3%). El edge de la señal se preserva con leverage menor — solo el ratio del PnL en USD baja.

## 5. DAILY LOSS BLOCK — 3 SLs (≈-6%)

| Trigger | Acción |
|---|---|
| 1 SL hoy | Continuar normal |
| 2 SLs hoy | **WARN**: "Cuidado, próxima decisión es la última del día" |
| 3 SLs hoy | **BLOCK**: STOP día. No más copia hasta mañana. |

## 6. MAX DD DEL CAPITAL — 30%

Si tu equity cae a 70% del capital de start de profile ($35 si empezaste con $50):
- **STOP**: cerrar profile, hacer review
- Posibles causas: filtros mal calibrados, comunidad en mal momento, leverage demasiado agresivo
- Recomendación: pausar 1 semana + revisar `signals_received.md` para encontrar patrón

## 7. AUTO-BLACKLIST ASSET — 2 SLs consecutivos

Si el mismo asset (ej. MSTRUSDT) te da 2 SLs consecutivos en la misma semana:
- Auto-blacklist por 7 días
- No copiar señales de ese asset aunque la comunidad las publique
- Razón: probablemente el asset está en régimen no-tradeable temporalmente

## 8. ASSET CONFLICT CROSS-PROFILE

| Si ya tienes posición ABIERTA en... | Y la señal Bitunix es de... | Acción |
|---|---|---|
| retail BTC | BTC perpetual | **REJECT** — doble exposición |
| ftmo BTCUSD | BTCUSDT.P | **REJECT** |
| fundingpips BTCUSD | BTCUSDT.P | **REJECT** |
| quantfury BTC | BTCUSDT.P | **REJECT** |
| retail BTC | ETH (correlado +0.85) | **WARN** — correlación alta |
| retail BTC | EURUSD (no correlado) | OK |

Sistema chequea con `pending_orders.json` y `mt5_state.json` de los demás profiles.

## 9. TIME WINDOW — preferir London/NY overlap

Aunque cripto es 24/7, el flujo institucional está en London/NY overlap (CR 06:00-15:00).

| Hora CR | Acción |
|---|---|
| 06:00-15:00 | **OK** — ventana óptima |
| 15:00-20:00 | OK con menor convicción (NY tarde) |
| 20:00-24:00 | WARN — Asia early, vol cae |
| 00:00-06:00 | **REJECT** — Asia death zone, evitar copy |

## 10. SIGNAL EXPIRY — 4 horas max

Si la señal apareció hace >4h, es "fuera de timing":
- El precio ya se movió (entry de la señal puede no ser válido)
- Liquidez puede haber cambiado
- **REJECT** — esperar próxima señal o pasar al día siguiente

## Order de checks pre-execución

```
1. Profile == bitunix? → si no, este flow no aplica
2. Daily counter <3? → si no, BLOCK
3. Daily PnL > -6%? → si no, BLOCK
4. Total DD > -30%? → si no, BLOCK PROFILE
5. Asset no blacklisted? → si no, BLOCK
6. Sin conflict cross-profile? → si no, REJECT
7. Hora dentro ventana? → si no, WARN/REJECT según hora
8. Señal <4h vieja? → si no, REJECT
9. Validation score ≥50? → si no, REJECT
10. Leverage capped a 10x? → SI

→ TODOS OK → APPROVE con size según score
```
