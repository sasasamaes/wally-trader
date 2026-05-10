---
description: Pre-mortem estructurado antes de entrar — fuerza pensar qué mata el trade ANTES de ejecutar
allowed-tools: Bash, Read
---

Pre-mortem es el opuesto de post-mortem: analizás un trade ANTES de ejecutarlo asumiendo que va a perder, y forzás identificar las causas hipotéticas. Si no podés articularlas claramente, el setup no está listo.

Inspirado en el psicólogo Gary Klein: "Asumí que el plan falló. Listá las razones."

## Uso

```
/premortem TONUSDT.P SHORT entry=2.40 sl=2.44 tp=2.355
/premortem BTCUSDT LONG entry=80000 sl=79200 tp=81500
```

## Pasos

### 1. Validación inputs

Parsear el comando:
- Symbol (e.g. TONUSDT.P)
- Side (LONG/SHORT)
- Entry price
- SL price
- TP price (TP1 al menos)

Si falta algo → preguntar antes de proceder.

### 2. Auto-checks técnicos antes del premortem humano

Ejecutar en paralelo (informativos, no bloquean):

```bash
# Macro events ±30min
python3 .claude/scripts/macro_gate.py --check-now

# Session quality (VWAP-flat / Asia chop)
python3 .claude/scripts/session_quality.py --symbol <SYMBOL> --quick

# Correlation guard (overlap con posiciones abiertas)
python3 .claude/scripts/correlation_guard.py --symbol <SYMBOL> --side <SIDE> --quick

# Liq heatmap (where are stops magnetized)
python3 .claude/scripts/liq_heatmap.py --symbol <SYMBOL> --quick
```

Capturar verdicts y reportarlos en el output final.

### 3. Pre-mortem questions (8 preguntas obligatorias)

Forzar respuesta articulada del usuario en cada una. **NO hacer la lista en bullets** — pedir respuesta inline:

```
1. THESIS — ¿En qué se basa este trade? (1 oración)
   → "Continuation SHORT después de break del 24h low con vol decay"

2. INVALIDATION — ¿Qué tendría que pasar para invalidar la thesis?
   → "Close 1H sobre $2.44 con vol >1.5x avg"

3. WORST CASE — Si el SL pega, ¿cuánto pierdo en %capital?
   → "$X = Y% — dentro del 2% por trade"

4. CONFLUENCIA EN CONTRA — ¿Qué señales en contra ignoré?
   → Si no hay nada que reconocer aquí, probablemente no miraste bien.

5. MISSED CATALYSTS — ¿Hay news/eventos próximos que podrían romper el setup?
   → 24h ahead. Si no buscaste → STOP, buscar primero.

6. CORRELATION CHECK — ¿Otras posiciones similares ya abiertas?
   → Output del corr-guard. Si dice WARN/BLOCK = pensar 2 veces.

7. EMOTIONAL CHECK — ¿Estoy entrando por revenge/FOMO/aburrimiento?
   → Si SI, el trade ya está mal antes de ejecutar.

8. STREAK CHECK — ¿Vengo de wins consecutivos? ¿De losses?
   → 3+ wins → reducir size. 2+ losses → cooldown obligatorio.
```

### 4. Decision matrix

Después de las 8 respuestas:

| Condición | Acción |
|---|---|
| Todas respondidas + auto-checks OK | ✅ GO — entry justificado |
| Falta articular thesis O invalidation | ❌ NO GO — setup no maduro |
| Auto-check BLOCK (macro, session, correlation) | ❌ NO GO — gate fail |
| Emotional check = revenge/FOMO | ❌ NO GO — trade tóxico |
| Streak check fail (3+ wins) | 🟡 GO con HALF size |
| Worst case > 2% capital | 🟡 GO con size reducido |

### 5. Output al usuario

```markdown
🔍 PRE-MORTEM — TONUSDT.P SHORT

## Auto-checks
✅ Macro: clear (no events ±30min)
✅ Session: VWAP std 0.42% / range 1.85% — tradeable
✅ Correlation: no open positions — diversified
🟡 Liq heatmap: magnet $2.36 (-1.7%) close to TP1 — favorable

## 8 Preguntas Pre-mortem

1. THESIS:        Continuation short 24h low break + vol decay
2. INVALIDATION:  Close 1H sobre $2.44 con vol > 1.5x
3. WORST CASE:    -$8 = -4% cap (dentro 2% rule)
4. CONFLUENCIA EN CONTRA: Smart Money L/S 1.40 borderline
5. CATALYSTS:     None macro, but London open 14h away — could squeeze
6. CORRELATION:   Clean
7. EMOTIONAL:     Not revenge, last trade was BE (not loss-revenge zone)
8. STREAK:        2 wins + 1 BE — normal range

## Verdict: 🟡 GO con HALF size

Justificación:
- Setup técnico OK, pero Smart Money L/S borderline = riesgo bounce
- HALF size ($25 margin vs $50) = max loss reduced to -$8
- Si TP1 fillea = +$15-20 (still meaningful)
- Si bounces = pérdida controlada

## Comando ejecutar
TONUSDT.P SHORT 20x cross
Margin: $25 (HALF) | Notional: $500 | Qty: 208 TON
SL: $2.44 | TP1: $2.355 (70%) | TP2: $2.32 (30%)
```

## Reglas de uso

- **El user DEBE responder las 8 preguntas** — no aceptar "skipea esto"
- Si user salta el premortem → loggear como `bypass_premortem=Y` en signals_received.csv
- Si user articula thesis VAGA ("BTC va para abajo") → flag y pedir specific
- Si articula INVALIDATION VAGA ("si va contra mí salgo") → flag, pedir nivel exacto

## Por qué funciona

Premortem es validado psicológicamente:
- Forzás "loss-aversion mental simulation" antes del commit emocional
- Identificás riesgos hipotéticos que el cerebro optimista esconde
- El acto de articular pre-mortem reduce trades impulsivos por ~40% (Klein 1998)
- En trading retail, mayor causa de pérdida es entrar SIN thesis clara — esto la fuerza

## Cuándo USAR

- ✅ Antes de cualquier entry NUEVO con margin > 10% capital
- ✅ Después de loss reciente (verifica no es revenge trade)
- ✅ Después de 3+ wins (verifica no es overconfidence)
- ✅ En setups self-generated (`/punk-hunt`) que NO vinieron de Discord
- ❌ NO necesario para entries que ya pasaron `/signal` validation completa

## Cadencia recomendada

`/premortem` debería ser **automático** en agentes:
- `punk-hunt-analyst` invoca al final de FASE 5 antes de propose entry
- `signal-validator` opcional (la validación de 4 filtros ya cubre 80% del premortem)
- Manual via `/premortem <args>` cuando user duda de un setup
