# Bitunix Copy-Validated — Trading log

**Account status:** ACTIVE
**Provider:** [Bitunix](https://bitunix.com) — exchange crypto perpetual futures
**Referral code:** punkchainer
**Capital inicial:** $200.00 USD (recalibrado 2026-05-04 — capital real punkchainer's copy-validated)
**Fecha de registro:** 2026-05-04

## Resumen rápido

- Señales recibidas: 0
- Señales validadas (PASS): 0
- Señales rechazadas (REJECT): 0
- Trades ejecutados: 0
- Hit rate filtered: N/A
- Hit rate all-blind: N/A
- Outperformance vs blind copy: N/A
- Capital actual: $200.00
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
