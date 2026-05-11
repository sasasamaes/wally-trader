# Bitunix Copy-Validated — Trading log

**Account status:** ACTIVE
**Provider:** [Bitunix](https://bitunix.com) — exchange crypto perpetual futures
**Referral code:** punkchainer
**Capital inicial:** $200.00 USD (recalibrado 2026-05-04 — capital real punkchainer's copy-validated)
**Fecha de registro:** 2026-05-04

## Resumen rápido

- Señales recibidas: 0 vía Discord (operativa discrecional propia)
- Trades ejecutados: 3 (todas 2026-05-10)
- WR día: 100% (3W/0L)
- Capital actual: ~$224.21 (pre-rebalance $199.42 + PnL día +$24.79)
- PnL semana: +$137.16 (rebalance $112.37 + hoy +$24.79)
- DD máximo: 0%

## Trades ejecutados

| Fecha | Hora CR | Asset | Dir | Entry | SL | TP | Lots | Resultado | PnL $ | R | Validation Score | Notas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

(vacío hasta primer trade)

## Reglas vigentes

- Risk per signal: 2% ($4.00 sobre $200)
- Max signals/día: 3
- Min validation score: 60% (FLAG en 50-60% con half-size)
- Max leverage: 10x (override de 20x)
- Daily BLOCK: 3 SLs (-6%)
- Profile DD limit: 30%
- Auto-blacklist asset: 2 SLs consecutivos en mismo asset

---

## 2026-05-09 11:30 CR — CAPITAL REBALANCE

**Acción:** Retiro $242 USD para facturas (income real del trading)

**Estado:**
- Capital pre-retiro: $442.45 (after +$112.95 session profits)
- **Capital actual: $200**
- Retirado a uso personal: $242 ✓

**Adjustes aplicados:**
- Risk per signal: 2% = $4.00 (era $8.85)
- Daily block: 6% = $12 (era $26.55)
- HALF size mode: $2.50 margin (era $5.50)
- FULL size mode: $5.00 margin (era $11)
- Standard size: $11 (era $22) — solo si signal A+

**Filosofía confirmada:**
> Bitunix profile = income real para vivir/facturas
> Strategy: extraer profits cuando capital crezca, mantener trading capital lean
> Disciplina: no perseguir grandes positions, retornos compuestos

**Próximas reglas de scaling:**
- Capital $200-300: standard $5-7 margin per signal
- Capital $300-500: standard $11-13 margin per signal  
- Capital $500-700: subir a $20 margin solo en A+ signals
- Cualquier momento >$300 por encima de baseline → considerar retiro a wallet/uso


---

## 2026-05-09 → 2026-05-10 — TONUSDT.P SHORT (BE close ⚪)

**Trade:**
- Entry: $2.3997 (sat 11:59 CR)
- Exit:  $2.3997 (sun 10:30 CR aprox.) → **BE manual close**
- Hold: ~3h drawdown profundo + bounce a entry → cierre defensivo
- Position: 402.9 TON SHORT @ 20x cross | Margin $49

**P&L:**
- **Realizado: $0.00** (BE)
- Fee inicial: -$0.58 (taker market)
- **Net: -$0.58**

**Origen:** Self-generated `/punk-hunt` scan (score 75/100)
- LH+LL 4/4 en 15m
- ATR 1.33%
- Vol $96M 24h
- 24h chg -8% (momentum continuation thesis)

**Por qué falló la thesis:**
1. Entry justo encima del 24h low ($2.379) — bounce técnico predecible
2. Smart Money L/S 1.62 (longs cargados arriba) → empujaron precio en contra
3. Vol decay rápido (0.27x → 0.18x en 1h) = setup degradándose
4. Magnet $2.36 (descubierto post-trade vía /liq-heatmap nuevo) nunca se alcanzó

**Decisiones operativas:**
1. ✅ NO promediaste cuando estaba -$12.61 (-25.7% margin) — disciplina
2. ✅ NO movías SL caóticamente — paciencia
3. ✅ Holdeaste cuando yo recomendé cut → resulted in BE save vs -$13 lock
4. ✅ Saliste apenas regresó a entry → preserve capital, no greed

**Lección sistémica para `/punk-hunt`:**
> Setup score ≥75 NO es suficiente si:
> - Smart Money L/S > 1.4 en dirección opuesta a tu trade
> - Entry está dentro de 2% del 24h low/high (riesgo bounce alto)
> - Magnet de liquidaciones está a >5% de distancia
> 
> Próxima iteración del scan debe incorporar L/S filter como hard veto + liq-heatmap proximity como soft filter.

**Estado capital:**
- Pre-trade: $200.00
- Post-trade: **$199.42** (-$0.58 fee)
- Day P&L: -0.29% (≈ flat)
- Daily block (-6%): NO breached ✅

**Slot summary día:**
- Slots usados: 1/2
- Trades ejecutados: 1
- Win rate día: 0/1 (BE no cuenta como win ni loss)

**Estadísticas semanales (sem 2026-W19):**
- Trades cerrados: 9 (8W / 0L / 1BE)
- WR weekly: 89% (excluyendo BE)
- Capital trajectory: $200 → $442.45 → $200 (post-withdraw $242) → $199.42
- Net realized week: +$112.37 (descontando fees y considerando withdrawal)

**Disciplina mark:**
- ⭐ Día neutral exitoso. En zona donde otros traders revenge-tradean tras drawdown, vos cerraste limpio y respetaste el sistema.

---

## 2026-05-10 — TRADING DAY + DEV SESSION

**Type:** HYBRID (3 trades reales + bundle 2 shipped)
**Capital pre-session:** $199.42
**Capital post-session:** ~$224.21 (estimado, +$24.79 PnL)
**Signals received:** 3 (todas auto-generadas/discrecionales)
**Trades ejecutados:** 3 (3W / 0L)
**PnL día:** **+$24.79 USDT** (+12.4% sobre $200)
**WR:** 100% (3/3)

### Trades del día (Bitunix screenshots)

| # | Asset | Dir | Leverage | Margin Mode | Entry Time | Exit Time | Entry | Exit | PYG% | PYG USD |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | SUIUSDT | SHORT | 20X | Cruzada | 11:04:16 | (cerrado) | 1.2873 | n/v | n/v | **+$4.47** |
| 2 | VIRTUALUSDT | SHORT | 20X | Cruzada | 11:11:33 | 14:17:35 | 0.9131 | 0.9082 | +8.33% | **+$2.01** |
| 3 | CETUSUSDT | SHORT | 20X | Cruzada | 13:04:20 | 20:20:09 | 0.03746 | 0.03671 | +37.84% | **+$18.31** |

**Total realized:** +$24.79 USDT

### Observaciones

- **3 shorts, 3 wins** — alineación direccional consistente con día bajista BTC (master del live dijo "no creíble el alza sin volumen")
- **20X leverage Cruzada** — sigue filosofía bitunix income reality (margin sizing real, no flat 2%)
- **CETUSUSDT = trade estrella** — +37.84% en 7h. Held intra-sesión sin override discrecional
- **No fueron del bot Dragno AI** — fueron entries propios del operador
- Comparable con el bot Dragno AI tracked hoy: el bot hizo +$1.05 en $50 (+2%). Yo hice +$24.79 en $200 (+12.4%). **6x mejor performance relativo.**

**Type:** HYBRID
**Capital:** $199.42 → ~$224.21 (+12.4%)
**PnL día:** +$24.79 (verificar exit final SUI cuando esté disponible)
**Signals received:** 0 vía /signal Discord (auto-loggeo)
**Trades ejecutados:** 3 (operativa discrecional propia)

**Highlights del día:**
- **Dragno AI external bot analysis** — bot copy-trading sobre Bitunix.
  - Performance histórica medida: WR 57%, PF 1.69
  - Counterfactual con SL -8% aplicado: **+80% PnL improvement** vs comportamiento actual
  - Hipótesis: el bot deja correr losers más allá de un punto donde el R:R ya colapsó
- **Shipped `/track-dragno`** (Bundle 1 extension) — tracker manual del bot: CSV + dashboard + counterfactual scenario engine
- **Shipped Live Insights Bundle 2** (5 features extraídas del Dragno master live stream `Be8IYJLgdYA`):
  - Feature A: USDT.D inverse-correlation tracker
  - Feature B: Macro multi-tier blackout (HARD/WARN/SOFT/OK)
  - Feature C: Volume/OBV divergence pre-entry check
  - Feature D: Auto-MUGRE switch on macro WARN/SOFT en `/punk-hunt`
  - Feature E: Fib extension exhaustion alert

**Commits:** 23 commits / 49 nuevos tests, all green / pushed a origin/main.

**Pending para mañana (2026-05-11):**
1. Live-test los nuevos wirings de agentes (FASE 0.6/0.7/0.8 en `trade-validator` + `signal-validator`)
2. Verificar que `/regime` muestre contexto USDT.D
3. Verificar que `/morning` muestre estado Fib extension
4. **Primer trade real con el macro-tier gate activo** — ojo a HARD/WARN/SOFT durante validación

**Behavioral notes:**
- ✅ Zero overtrading risk hoy (cero trades ejecutados — focus en infra)
- ⚠️ Sesión de dev larga (23 commits). Considerar **fatiga mental** mañana antes de jalar gatillo en señales. Si la cabeza no está fresca CR 06:00 → arrancar más tarde o skipear el día.
- ✅ Disciplina sistémica: invertir un día completo en infrastructure → ROI compuesto en próximas semanas.

**Capital trajectory:**
- Pre-session: $199.42
- Post-session: $199.42 (unchanged, sin exposure)
- Day P&L: $0.00 / 0.00%
- Daily block: N/A (no trades)

**Disciplina mark:**
- 🛠️ Dev day. No es trading mark, pero builder mark. La infraestructura desplegada hoy (macro-tier gate, USDT.D context, OBV divergence, Fib exhaustion, Dragno tracker) es palanca para próximas 4+ semanas de operativa.
