---
name: punkchainer-playbook
description: Use cuando vayas a validar/copiar una señal de la comunidad punkchainer's o cuando necesites checklist operativo SMC pre-entry. Consolida los 3 protocolos comunitarios — (1) 4-Pilar Entry Checklist Neptune SMC (LONG/SHORT), (2) Saturday Precision Protocol (rules de fin de semana low-volume), (3) Reglas de Oro (no perseguir precio, filtro Adjusted, alts +0.5% buffer). Crítico para profile bitunix; complementa skill `punkchainer-glossary` (DUREX/GORRAS) y `neptune-community-config` (configs indicadores).
---

# Punkchainer Playbook — protocolos operativos comunidad

> 3 protocolos críticos que la comunidad punkchainer's usa antes de tirar el clic. Sin estos, las señales son ruido. Con estos, son edge.

## 🛡️ 1. Checklist de Entrada — 4 Pilares Neptune SMC

> "Antes de abrir CUALQUIER operación, verifica que se cumplan estos 4 Pilares. Cuantas más confluencias, mayor la probabilidad de éxito."

### 🟢 LONG — Confirmaciones requeridas

| # | Pilar | Qué buscas en Neptune SMC |
|---|---|---|
| 1 | **Zona de Interés** | Bullish OB activo (verde) o Bullish FVG sin mitigar |
| 2 | **Barrida de Liquidez** | "Bullish Raid Found" label O **SSL Touched** (sweep de mínimo previo) |
| 3 | **Cambio de Dirección** | **Bullish CHoCH** confirmado (línea verde quiebre estructura bajista) |
| 4 | **Confirmación Extra** | **Bullish SFP Created** (Swing Failure Pattern alcista, mecha que falla en romper bajo + cierre adentro) |

**Entry trigger:** **50% (Mid-Line)** del FVG/OB validado.
**SL:** debajo del mínimo del Sweep (en alts: **+0.5% buffer extra**).
**TP1:** EQH (Equal High) más cercano.
**TP2:** Buyside Liquidity zone superior.

### 🔴 SHORT — Confirmaciones requeridas

| # | Pilar | Qué buscas en Neptune SMC |
|---|---|---|
| 1 | **Zona de Interés** | Bearish OB activo (rojo) o Bearish FVG sin mitigar |
| 2 | **Barrida de Liquidez** | "Bearish Sweep Area" O **BSL Touched** (sweep de máximo previo) |
| 3 | **Cambio de Dirección** | **Bearish CHoCH** confirmado |
| 4 | **Confirmación Extra** | **Bearish SFP Created** (mecha que falla en romper alto + cierre adentro) |

**Entry trigger:** Bearish Breaker o Bearish FVG cercano (mid-line).
**SL:** sobre el máximo del Sweep (alts: **+0.5% buffer**).
**TP1:** EQL (Equal Low).
**TP2:** Sellside Liquidity zone.

### 🔥 Tip clave (regla de no-trade)

> **Si NO hay al menos 3 de los 4 pilares marcados → operación de "Baja Probabilidad" → quedarse FUERA.**

En el pipeline bitunix esto se traduce en gate hard:
- **4/4 pilares** → APPROVE con MAX conviction
- **3/4 pilares** → APPROVE con HALF size (1% en vez de 2%)
- **<3/4 pilares** → REJECT, anota en `signals_received.md`

## ⚠️ 2. Reglas de Oro — qué NUNCA hacer

### a) No perseguir el precio
Si la vela ya está extendida y el oscilador Neptune marca sobrecompra/sobreventa extrema → **espera al pullback** al FVG/OB de menor temporalidad. Entrar tarde con el momentum agotado = stop-loss casi garantizado.

### b) Filtro Adjusted (CHoCH solo válido con cuerpo)
Un CHoCH marcado por **mecha sola sin cuerpo de cierre** NO es válido como pilar 3.
- ✅ Vela cierra con cuerpo más allá del nivel → CHoCH confirmado
- ❌ Solo mecha tocó/cruzó pero cuerpo regresó → wick fake, descartar

En Neptune SMC config: usar **Algorithmic Logic: Adjustable (5)** para que el detector sea estricto.

### c) Alts low-cap → +0.5% buffer SL
En altcoins de baja capitalización, los wicks son monstruosos. Si el sweep low fue 1.000, no pongas SL en 0.999. Pon SL en **0.995** (0.5% extra).
Razón: mercados ilíquidos hacen "doble barrida" antes del move real, especialmente fines de semana.

### d) BTC manda en alts
- Si **BTC cae fuerte** → 🚫 prohibido buscar LONGS en alts low-cap
- Si **BTC lateraliza** → 🟢 luz verde para alts (descorrelación temporal)
- Si **BTC bombea fuerte** → cuidado con SHORTS de alts (correlación positiva en bull-impulse)

## 🐺 3. Saturday Precision Protocol — fin de semana low-volume

> "El fin de semana el volumen baja y la manipulación sube. Para no caer en la trampa, sigue este protocolo antes de cada clic."

Aplicable **sábado y domingo** (cripto 24/7 pero institucionales OFF). Más estricto que pipeline normal.

### Fase 1 — Filtro Mayor (contexto 1H/4H) 🧐
Antes de bajar a 15m, en 4H/1H verifica:
- 📍 **¿Dónde estamos?** ¿Zona de Oferta (premium >50%) o Demanda (discount <50%)?
- 👑 **Dirección del Rey:** estado de BTC determina alts (regla de Oro #d arriba)

Si BTC está en confluencia HTF clara → continuar. Si BTC está en chop o noticia macro próxima → **stand-aside**.

### Fase 2 — Escaneo 15m (gatillo) 🎯
En el TF de entry, busca **EN ORDEN**:
1. 🧹 **Barrida (Raid):** mecha que toma liquidez (sweep alto/bajo previo)
2. 🔄 **CHoCH:** Neptune marca quiebre de estructura — **NO entres antes**
3. ✅ **BOS:** si tras CHoCH precio rompe el siguiente pivote, tendencia confirmada → entry válido

Si falta cualquiera → **NO entrada**, sigue mirando.

### Fase 3 — Lectura del Oscilador Neptune 📊
- 🚫 **Si oscilador marca sobrecompra/sobreventa** (mechas rojas/verdes extremas, hyper wave en extremo) → **NO persigas**, espera reversión a zona neutral
- 🎯 **Entrada ideal:** retroceso al FVG 15m **CON** oscilador regresando a zona neutral (entre las Confluences Lines)

### Fase 4 — Low Caps 🎢
Si vas a operar alts volátiles fin de semana:
- ⚙️ **Apalancamiento:** si BTC opera 20x, alts → **10x máximo**. Movimiento % es 2-3x mayor.
- 🏹 **Entry tipo Sniper:** NO mercado. **Limit order** un poco más allá de las mechas anteriores. El sábado el mercado ama "barrer" 2 veces antes de salir.

### Fase 5 — Gestión de salida 🛡️
- 💰 **Breakeven Rápido (DUREX adaptado):** en lugar del 20% del recorrido (regla DUREX entre semana), fin de semana → **mover SL a entry cuando precio recorra 1:1 (1R)**. Los retrocesos sabatinos son traicioneros.
- 🥷 Razón: sábados los wicks regresan a entry mucho más frecuente que entre semana, mejor BE rápido y luego runner.

### Resumen Saturday vs weekday

| Concepto | Lunes-Viernes | Sábado-Domingo |
|---|---|---|
| Pillars mínimos | 3/4 | **4/4 obligatorio** |
| Leverage en alts | 10x | **5x cap** |
| DUREX trigger | 20% recorrido o TP1 | **1R (1:1)** |
| Tipo de entry | Market o Limit | **Solo Limit "sniper"** |
| BTC dump → alts | Caso por caso | **🚫 0 longs alts** |
| Macro news | Reduce size | **Stand-aside total** |

## Integración con pipeline bitunix

En `/signal` agent, después de los 4 filtros técnicos retail (RSI/Donchian/BB/cierre), añadir como **gate 5** el 4-pilar checklist:

```
[Filtros 1-4 técnicos retail] → [4-pilar Neptune SMC] → [Multi-Factor + ML] → [Chainlink] → APPROVE/REJECT
```

Si fecha == sábado/domingo → activar Saturday Precision Protocol en lugar de gates normales.

## Referencias cruzadas

- **DUREX (move SL → BE):** skill `@punkchainer-glossary`
- **Configs exactas Neptune indicadores:** skill `@neptune-community-config`
- **Placeholders alertas/webhooks:** skill `@neptune-alert-placeholders`
- **SMC/ICT fundamentos:** skill `@smart-money-ict`
- **Implementación bitunix:** `.claude/profiles/bitunix/strategy.md`

## Disclaimer

Este playbook NO es estrategia probada en backtest propio — es metodología comunitaria. Antes de operar tamaño real, valida en paper trading con `/backtest` que la lógica 4-pilar tenga edge en TU universo de assets.
