# 🌅 Prompt Matutino COMPLETO — 5:30/6:00 AM MX

Copia-pega este prompt en Claude cada mañana. Cubre análisis, psicología, reglas y disciplina.

---

## 🔥 PROMPT PRINCIPAL (copy-paste)

```
Análisis matutino BTCUSDT.P. Son las 6 AM MX. Ejecuta protocolo completo:

═══ FASE 1: AUTO-CHECK PERSONAL ═══

Pregúntame (respondo SI/NO):
- ¿Dormí 6+ horas anoche?
- ¿Comí algo en última hora?
- ¿Estoy mentalmente claro (sin resaca emocional de pérdida anterior)?
- ¿Tengo hasta 12 MD sin distracciones?
- ¿Cap actual dentro de rango saludable (>$8 si empecé con $10)?

Si cualquiera = NO → recomendar skip hoy + razón.

═══ FASE 2: CONTEXTO GLOBAL (paralelo) ═══

WebFetch simultáneos:
- Fear & Greed 7d: api.alternative.me/fng/?limit=7
- Funding rate: okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP
- CoinGecko sentiment: coingecko.com/api/v3/coins/bitcoin?community_data=true
- 24h/7d/30d: coinpaprika.com/v1/tickers/btc-bitcoin
- Mempool: mempool.space/api/mempool
- Hashrate: bitinfocharts.com/bitcoin/
- Txs 7d: api.blockchain.info/charts/n-transactions?timespan=7days&format=json

═══ FASE 3: CORRELACIONES (tabla) ═══

- ETH 24h change (debe ir en la misma dirección que BTC para confirmar)
- SPX / NASDAQ overnight direction
- DXY (dollar index) direction (-corr con BTC)
- Si ETH va opuesto a BTC → reducir convicción 50%
- Si DXY rompiendo al alza → sesgo bearish crypto

═══ FASE 4: NOTICIAS Y EVENTOS ═══

- ¿Hay FOMC, CPI, NFP, PPI, Powell speech en próximas 6h?
- Si SÍ → NO OPERAR hasta pasado el evento + 1h
- Eventos crypto: ETF decisions, halving, hard forks, Coinbase earnings

═══ FASE 5: DETECCIÓN DE RÉGIMEN ═══

- OHLCV 4H summary 50 bars
- OHLCV 1H summary 24 bars
- Clasifica: RANGE / TRENDING UP / TRENDING DOWN / VOLATILE
- Criterios:
  * RANGE: oscilación < 5% en 48h sin romper niveles
  * TRENDING: higher highs + higher lows (o mirror) diarios
  * VOLATILE: ATR 4H > 2× promedio histórico

═══ FASE 6: ESTRATEGIA SEGÚN RÉGIMEN ═══

- RANGE → Mean Reversion 15m (4 filtros obligatorios)
- TRENDING UP → Donchian Breakout solo LONGS
- TRENDING DOWN → Donchian Breakout solo SHORTS
- VOLATILE → NO OPERAR, descanso

═══ FASE 7: NIVELES TÉCNICOS MULTI-TF ═══

4H: EMA 50/200 para trend macro
1H: Donchian High/Low + estructura
15m:
  - Donchian(15) H/L actualizado (excluir barra forming)
  - BB(20, 2) upper/mid/lower
  - RSI(14) actual
  - ATR(14) actual
  - EMA 50

NIVELES ADICIONALES A DIBUJAR:
  - Previous Day High (PDH) y Low (PDL)
  - Weekly Open
  - VWAP del día (desde UTC 00:00)
  - Fibonacci 0.618 del último swing 1H

═══ FASE 8: MONEY FLOW ═══

- Volumen 5m vs avg 24h (spike >2x = señal)
- Rejection (wick + vol alto) vs Acumulación (body + vol alto)
- Volume profile: ¿dónde está el POC del día?

═══ FASE 9: PATRONES TÉCNICOS ═══

- Dojis, hammers, engulfing en últimas 5 velas 15m y 1H
- Doble techo / doble piso en 1H
- Divergencias RSI vs precio (bullish/bearish)
- Breakouts con retest o fakeouts

═══ FASE 10: POSITION SIZING ═══

Calcula según mi capital actual (revisar trading_log.md):
- Riesgo max por trade = 2% del capital
- Qty = Riesgo_USD / SL_distance_en_USD
- Muestra: margen a usar, leverage sugerido, qty BTC

═══ FASE 11: DIBUJAR EN TRADINGVIEW ═══

1. Limpiar chart: ui_mouse_click 12 619 right → ui_click data-name=remove-drawing-tools
2. Dibujar según estrategia:
   * Mean Reversion: Donchian H/L + BB + zonas entry + MID + SL/TP3 ambos lados
   * Breakout: niveles ruptura + buffer + SL/TP3
3. Añadir niveles extra: PDH/PDL (azul), Weekly Open (morado), VWAP (amarillo)
4. Línea vertical cierre 23:59 MX
5. Texto superior: "REGIMEN: X | ESTRATEGIA: Y | SESGO: Z | Entry en Q"

═══ FASE 12: PLAN DE ENTRADA ═══

Formato:
- Entry zone exacto (precio)
- SL calculado con 2% risk position sizing
- TP1/TP2/TP3 con ATR
- Hora óptima (priorizar MX 06:00-10:00 = London/NY overlap; ventana total 06:00-23:59)
- Los 4 filtros listados que deben alinearse
- Invalidación (qué condiciones cancelan el setup)

═══ FASE 13: CHECKLIST PRE-ENTRY ═══

Lista imprimible que debo tachar antes de apretar COMPRAR/VENDER:
☐ Régimen correcto identificado
☐ 4/4 filtros alineados (no 3/4)
☐ Multi-TF confluence (1H no contradice 15m)
☐ Hora dentro de MX 06:00-23:59
☐ Sin noticia alto impacto en próximas 4h
☐ Correlaciones (ETH) en la misma dirección
☐ SL calculado y listo para poner
☐ TP1/TP2/TP3 calculados
☐ Position size según fórmula 2%
☐ Auto-check personal OK (#Fase 1)
☐ No tengo 2 SLs hoy ya
☐ Firma: _____ hora: __:__

═══ FASE 14: REGLAS DURAS DE SESIÓN ═══

Recordatorio obligatorio:
- Max 3 trades/día
- Después de 1 SL → pausa 30 min OBLIGATORIA (anti revenge)
- 2 SLs consecutivos → PARAR DÍA
- NUNCA mover SL en contra (solo a BE o profit)
- Si pérdida día > 6% → parar y revisar qué fallé
- Si cap < $8 → stop + volver a demo 1 semana

═══ VEREDICTO FINAL ═══

UNA línea clara:
- ENTRAR LONG en [precio] → razón corta
- ENTRAR SHORT en [precio] → razón corta
- ESPERAR SETUP → qué vigilar exactamente
- NO OPERAR HOY → razón (volatil/noticias/auto-check)

═══ FASE 15 (FIN DE DÍA): JOURNAL ═══

Al cerrar sesión pedirme:
- Trades ejecutados (cada uno: entry/exit/razón)
- PnL total día
- Capital antes vs después
- ¿Seguí los 4 filtros en cada trade? SI/NO
- ¿Hora de entradas?
- ¿Qué salió BIEN? (1 cosa concreta)
- ¿Qué MEJORARÍA? (1 cosa concreta)
- Lección #__ del día
Luego actualizar trading_log.md con todo esto.

═══════════════════════════════════════

Devuelve todo estructurado con tablas, emojis para urgencia visual, y veredicto FINAL obvio al terminar.
```

---

## 📋 Lo que Claude te va a entregar

### 15 Secciones estructuradas:

1. **Auto-check personal** — 5 preguntas SI/NO
2. **Sentiment matrix** — F&G, funding, retail votes
3. **Correlaciones** — ETH, SPX, DXY en tabla
4. **Noticias hoy** — calendar macro + crypto
5. **Régimen actual** — RANGE/TREND/VOLATILE con evidencia
6. **Estrategia del día** — qué operar
7. **Niveles multi-TF** — 4H/1H/15m + VWAP/PDH/PDL/Weekly
8. **Money flow** — spikes, rejection vs acumulación
9. **Patrones** — divergencias, doji, engulfing
10. **Position sizing** — calculado con tu capital exacto
11. **Chart TV actualizado** — limpio + redibujado
12. **Plan de entrada** — entry/SL/TPs exactos
13. **Checklist pre-entry** — 12 items para tachar
14. **Reglas duras** — recordatorio anti-error
15. **VEREDICTO** en 1 línea clara

---

## 🔄 Prompts de seguimiento durante el día

### Al acercarse a zona de entrada:
```
¿4 filtros alineados AHORA en [precio]? 
Checar: RSI actual, BB touch, vela color, hora.
Decisión: entro o espero.
```

### Al ejecutar entrada:
```
Ejecuté [LONG/SHORT] @ [precio] a las MX __:__. 
Actualiza niveles en TV + monitoreo activo.
Dime cuándo mover SL a BE.
```

### Ante duda durante el trade:
```
[Precio actual]. Estoy [LONG/SHORT] desde [precio entry].
¿Mantener plan o ajustar? Analiza estructura.
```

### Si hay 2 SLs:
```
2 SLs hoy. Activando regla de parada.
Analiza qué fallé en ambos. Lección del día.
```

### Cierre de sesión:
```
Cierre MX 17:00. Resumen completo:
- Trades del día
- PnL total
- Capital final
- Actualiza trading_log.md con journal
```

---

## ⚡ Quick Commands (prisa)

### Check rápido (30 segundos):
```
Quick: precio BTC, régimen hoy, ¿hay setup válido ahora?
```

### Monitoreo posición:
```
Long/Short @ [precio]. Estado unrealized + acción.
```

### Revisión semanal (domingo):
```
Review semana: lee trading_log últimos 7 días.
Calcula WR, PF, avg win, avg loss, max DD.
Identifica 1 patrón a cambiar la próxima semana.
```

---

## 🧠 Checklist físico (IMPRIMIR Y PEGAR AL MONITOR)

```
╔═══════════════════════════════════════════╗
║    PRE-ENTRY CHECKLIST — TÁCHALOS         ║
╠═══════════════════════════════════════════╣
║  PERSONAL                                 ║
║  ☐ Dormí 6+ horas                         ║
║  ☐ Desayuné algo                          ║
║  ☐ Estoy mentalmente claro                ║
║  ☐ No estoy "recuperando" pérdida         ║
║                                           ║
║  CONTEXTO                                 ║
║  ☐ Régimen identificado (R/T/V)           ║
║  ☐ Sin noticias high impact 4h            ║
║  ☐ ETH en dirección a mi bias             ║
║  ☐ Hora MX 06:00-23:59 (no dormir open)   ║
║                                           ║
║  SETUP                                    ║
║  ☐ 4/4 filtros alineados                  ║
║  ☐ 1H no contradice 15m                   ║
║  ☐ Volumen confirma                       ║
║                                           ║
║  EJECUCIÓN                                ║
║  ☐ SL calculado (____)                    ║
║  ☐ TP1 (____)  TP2 (____)  TP3 (____)     ║
║  ☐ Tamaño posición 2% risk ($____)        ║
║  ☐ Listo para poner orden completa        ║
║                                           ║
║  LÍMITES DEL DÍA                          ║
║  ☐ <3 trades ejecutados hoy               ║
║  ☐ <2 SLs consecutivos hoy                ║
║  ☐ PnL día > -6%                          ║
║                                           ║
║  Firma: _________  Hora: __:__            ║
╚═══════════════════════════════════════════╝
```

Si NO puedes tachar TODOS los 15 → **NO ENTRES**.

---

## 📊 Journal template diario

```
═══ JOURNAL TRADING — FECHA: ______ ═══

Capital INICIO: $______
Capital FIN: $______
Delta: $______ (___%)

Régimen del día: RANGE / TREND UP / TREND DOWN / VOLATILE
Estrategia usada: Mean Reversion / Breakout / NO OPERÉ

──────────────────────────────────────
TRADE #1
Setup: __________________________
Entry: $_____ a las __:__ MX
SL:    $_____ (calculado -__.__% → risk $_____)
TP1:   $_____ (cerrar 40%, SL→BE)
TP2:   $_____ (cerrar 40%)
TP3:   $_____ (runner 20%)

Exit:  $_____ a las __:__ MX
Razón: TP1 / TP2 / TP3 / SL / TIME / MANUAL
PnL:   $______

¿Seguí TODOS los 4 filtros? SI / NO
¿Seguí checklist físico? SI / NO
Hora de entrada dentro de MX 06:00-23:59? SI / NO
──────────────────────────────────────
[Trade #2 si hubo...]

═══ REVISIÓN ═══

1. Qué salió BIEN (1 cosa concreta):
   _____________________________

2. Qué MEJORARÍA (1 cosa concreta):
   _____________________________

3. Lección #___:
   _____________________________

4. Emociones del día (1 palabra):
   _____________________________

5. Mañana cambiaría: ________________
```

---

## 📅 Revisión SEMANAL (domingos 10 AM)

```
═══ REVIEW SEMANAL — SEMANA DEL ___ al ___ ═══

MÉTRICAS:
- Total trades: ___
- Winners: ___ (___%)
- Losers: ___ (___%)
- PF (profit_total/loss_total): ___
- Avg win: $___
- Avg loss: $___
- Largest win: $___
- Largest loss: $___
- Max drawdown intra-semana: ___%

CAPITAL:
- Lunes: $___
- Viernes: $___
- Delta: $___ (___%)

PATRONES:
- Días con más wins: ____________
- Hora con más wins: ____________
- Setups que FUNCIONARON: ____________
- Setups que FALLARON: ____________

1 CAMBIO para próxima semana:
_________________________________

OBJETIVO siguiente semana:
_________________________________
```

---

## 🚨 Reglas de emergencia (leer si estás en tilt)

Si notas que:
- Estás revisando el chart cada 2 minutos
- Te sientes ansioso después de un SL
- Quieres "recuperar" rápido
- Pensaste en aumentar leverage
- Estás operando fuera de tu ventana horaria
- Ya perdiste 3+ trades hoy

**STOP. Cierra la app. Aléjate 2 horas mínimo.**

El mercado sigue abierto mañana. Tu cuenta no sobrevive el pánico.

---

## 🎯 Uso del prompt

1. **Copy-paste** el PROMPT PRINCIPAL arriba al iniciar Claude cada mañana
2. Claude ejecutará las 15 fases y te dará veredicto claro
3. Tú tachas el checklist físico (imprímelo)
4. Operas SOLO si todo OK
5. Al cerrar día → usa prompt de "Cierre de sesión"
6. Domingos → usa prompt de "Review semana"

**Tiempo total diario:**
- Análisis matutino: 10 min
- Vigilancia mercado: esporádica
- Ejecución entry: 2 min
- Cierre día: 5 min
- **Total: ~20 min/día**

Mucho menos que un trabajo normal. Pero con la disciplina de un francotirador.

---

## 💎 Mantra del día

> **"El mejor trade del año es el que NO hiciste por falta de setup."**

> **"Un SL pequeño respetado es una victoria. Un SL movido es el principio del fin."**

> **"Tu cuenta crece por lo que NO haces, tanto como por lo que haces."**
