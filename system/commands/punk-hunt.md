---
description: Caza autónoma de oportunidades en bitunix — escanea 10 cripto, elige el mejor setup ahora con metodología punkchainer, score ≥70 requerido [solo bitunix]
allowed-tools: Agent, Bash
---

Caza autónoma de oportunidades para profile `bitunix`. A diferencia de `/signal` (valida señal externa de Discord) y `/punk-morning` (prep pre-sesión), este comando **genera su propia recomendación**:

1. Escanea las 10 criptos del watchlist punkchainer's
2. Aplica scoring 0-100 (4 filtros + multifactor + 4-Pilar SMC + régimen)
3. Si el TOP candidato tiene score ≥70 → propone entry/SL/TP completo y auto-loggea a `signals_received.md` vía pipeline `/signal`
4. Si no hay setup A-grade → ESPERAR (próxima ejecución en ~1h)

**Filosofía:** modo híbrido. La filosofía estricta de bitunix es "copy-validated" (señales de Discord), pero este comando suple los huecos cuando no hay señales en Discord o cuando querés tradear cada hora con tu propia lógica usando el mismo edge punkchainer's (Neptune + 4-Pilar SMC + DUREX).

## Cadencia recomendada

Manual cada hora (CR 06:00-23:00). Idealmente:
- **CR 06:00-08:00** — antes del overlap London/NY (volumen creciendo)
- **CR 09:00-15:00** — overlap activo (mejor liquidez, setups más limpios)
- **CR 15:00-20:00** — NY tarde (menor convicción)
- **CR 20:00-23:00** — Asia early (warn — solo A-grade absoluto)

**Recomendación**: limitarte a 6-8 invocaciones/día. Si querés automatizar:
```
/loop 60m /punk-hunt
```
(usa `/loop` para auto-invocar cada 60 min, max 12 ticks → para con Ctrl+C)

## Pasos que ejecuta Claude

1. **Profile guard (hard fail):**
   ```bash
   PROFILE=$(python3 .claude/scripts/profile.py get | awk '{print $1}')
   if [ "$PROFILE" != "bitunix" ]; then
     echo "❌ /punk-hunt es exclusivo de profile bitunix. Profile activo: $PROFILE"
     exit 1
   fi
   ```

2. **Pre-checks rápidos (NO-GO inmediato si fallan):**
   - `python3 .claude/scripts/macro_gate.py --check-now` → si `blocked: true` → ABORT
   - Daily counter: si `today >= 7` → ABORT (cap diario)
   - Concurrent slots: si `open >= 2` → ABORT (slots llenos)

3. **Despacha al agente `punk-hunt-analyst`** con las fases documentadas en su definición.

4. **Argumento opcional `$ARGUMENTS`:**
   - `--asset SYMBOL` → fuerza scan/análisis sólo de ese asset
   - `--side long|short` → fuerza dirección (default: el agente decide según setup)
   - `--min-score N` → override threshold (default 70)
   - texto libre → contexto extra

## Output esperado

**Caso A — Hay setup ≥70:**
```
🎯 PUNK-HUNT — TOP SETUP encontrado

Asset: SOLUSDT.P | Side: LONG | Score: 76/100
Entry: 145.20 | SL: 144.30 (0.62%) | TP1: 146.80 (1.10%) | TP2: 147.60 | TP3: 149.20
R:R TP1: 1.78 | R:R TP3: 6.45
Régimen: RANGE_CHOP 1H | Multifactor: +58 | 4 filtros: 4/4 | 4-Pilar SMC: 3/4
DUREX trigger: 145.52 (20% recorrido)

Sizing: 1.378 SOL @ leverage 10x | Margin: $20.00 | Risk: $4.00 (2% de $200)

📤 Auto-loggeado a signals_received.md como decision=APROBADO
👉 Para ejecutar manual en Bitunix:
   - SOLUSDT.P LONG @ market o limit 145.20
   - SL: 144.30 | TP escalonados arriba
   - Cuando alcance DUREX trigger 145.52 → mover SL a 145.20
   - Al cerrar: /log-outcome SOLUSDT TP1 146.80 --pnl 2.21
```

**Caso B — No hay setup A-grade:**
```
⏳ PUNK-HUNT — sin oportunidad ahora

Top-3 evaluados:
  1. BTCUSDT.P LONG  → 62/100 (multifactor solo +28, falta confluencia SMC)
  2. SOLUSDT.P SHORT → 58/100 (régimen ambiguo, RSI no extremo)
  3. ETHUSDT.P LONG  → 51/100 (BB no tocada)

Threshold ≥70 no alcanzado. ESPERAR.
Próxima invocación recomendada: ~CR 12:00 (1h).
```

**Caso C — Pre-check abortó:**
```
🚫 PUNK-HUNT — bloqueado

Razón: macro event NFP en 18 min (CR 09:30) — ventana ±30 min NO TRADE
Próxima ventana segura: CR 10:00+
```

## Reglas de seguridad

- **NUNCA** ejecuta el trade en Bitunix — solo loggea la recomendación
- **NUNCA** propone leverage > 10x
- **NUNCA** propone SL > 2% del entry
- Mismo gate macro/concurrente/daily-cap que `/signal`
- Score ≥70 (más estricto que `/signal` ≥60) — porque es entry self-generated, debe sobrar margen

Si hay argumentos, úsalos como contexto adicional al agente:

$ARGUMENTS
