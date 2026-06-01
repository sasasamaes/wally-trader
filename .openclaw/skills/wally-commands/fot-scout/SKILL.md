---
name: fot-scout
description: Scanner regime-aware multi-estrategia — escanea los 8 activos fotmarkets,
  elige la mejor estrategia para cada activo AHORA, valida y da entry/SL/TP para MT5
  manual [solo fotmarkets]
version: 1.0.0
metadata:
  openclaw:
    tags:
    - wally-trader
    - command
    - slash
    category: trading-command
    requires_toolsets:
    - terminal
    - subagents
---
<!-- generated from system/commands/fot-scout.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /fot-scout -->


**Fotmarkets scout** — cada corrida escanea los 8 activos del universo fotmarkets, detecta el
régimen por activo y aplica **la estrategia ganadora de ese régimen**, valida con la cadena de
gates, y propone el mejor setup (entry/SL/TP + sizing) para ejecutar **manual en MT5**. Pensado
para correrse varias veces por sesión (o con `/loop`) para crecer la cuenta **$50 → $500** con
disciplina.

## Honestidad (backtest 2026-05-31)

```
Solo Mean Reversion (RANGE_CHOP) sobrevive el spread CFD bonus → único edge VALIDATED.
Breakout / MA-cross / pullback dieron PF ~0.9-1.07 y mueren al spread → edge WEAK,
aparecen como TENTATIVE con "⚠️ edge no validado", NUNCA como GO.
Oro (XAUUSD) fue el mejor activo (~0.89 setups/día, +0.46R IS, WARN OOS).
Sobre $50 esto rinde centavos/día — es semilla compuesta, no ingreso. El comando
dice WAIT honesto cuando no hay edge en vez de forzar un setup de tendencia.
```

## Mapping régimen→estrategia (de fot_strategy_mapping.json)

| Régimen | Estrategia | Edge | Máx status |
|---|---|---|---|
| **RANGE_CHOP** | Mean Reversion (4 filtros) | VALIDATED | 🟢 APPROVED |
| TREND_LEVE | MA-Cross (EMA 9/21) | WEAK | 🟡 TENTATIVE ⚠️ |
| TREND_FUERTE | Donchian Breakout | WEAK | 🟡 TENTATIVE ⚠️ |
| TREND_EXTREMO / VOLATILE | — | NONE | 🚫 STAND ASIDE |

## Pasos que ejecuta Claude

1. **Profile guard (fotmarkets-only):**
   ```bash
   PROFILE=$(python3 .claude/scripts/profile.py get | awk '{print $1}')
   [ "$PROFILE" = "fotmarkets" ] || { echo "❌ /fot-scout solo aplica a fotmarkets. Profile activo: $PROFILE"; exit 1; }
   ```

2. **Guardian pre-flight (ventana, weekend, trades/día, SL consecutivos):**
   ```bash
   python3 .claude/scripts/fotmarkets_guard.py check
   ```
   Si imprime `BLOCK: ...` (exit 1) → comunicar la razón y **PARAR** (no escanear). El guardian
   protege la disciplina: fuera de ventana CR 07:00–10:55, fin de semana, o cap de trades/SL
   alcanzado → no hay nada que cazar hoy.

3. **Correr el router:**
   ```bash
   .claude/scripts/.venv/bin/python .claude/scripts/fot_scout_router.py --json
   ```

4. **Despachar al agente `fot-scout-analyst`** con el JSON para: refinar el quote live del ganador
   (TV MCP), correr la cadena de validación (macro_gate → session_quality → volume_divergence →
   min_rr_gate), armar la narrativa GO/NO-GO + instrucciones MT5, y loggear la propuesta.

5. **Argumento opcional `$ARGUMENTS`:**
   - `--asset SYMBOL` → escanear un solo activo
   - `--show-all` → muestra también buckets WAIT/STAND_ASIDE/NO_SETUP con razón
   - `--experimental-trend` → sube setups de tendencia a TENTATIVE explícito (sin edge validado)
   - texto libre → contexto extra al agente

## Output esperado

**Caso A — Setup APPROVED (Mean Reversion en RANGE_CHOP):**
```markdown
📈 $50 / $500 (10%) — Fase 1
🎯 FOT-SCOUT — mejor setup AHORA

🟢 LONG XAUUSD (regime RANGE_CHOP, Mean Reversion, score 78/100)
   Entry: 2345.20 | SL: 2343.20 (20 pips) | TP: 2349.20 (R:R 2.0)
   Lots: 0.01 (APROX — validar pip value en MT5) | Risk: $0.50 (1%)
   ⚠️ XAUUSD OOS WARN — edge real pero frágil; paper-first

👉 MT5 manual: XAUUSD LONG @ 2345.20, SL 2343.20, TP 2349.20
   Al cerrar: /journal para loggear el outcome real
```

**Caso B — Solo candidatos bloqueados (override):**
```markdown
🔒 FOT-SCOUT — setup válido pero activo bloqueado en Fase 1
   LONG BTCUSD score 75 — desbloqueá conscientemente (override ya en config)
```

**Caso C — WAIT honesto:**
```markdown
⏳ FOT-SCOUT — sin setup con edge AHORA
   BTCUSD: RANGE_CHOP pero MR sin trigger (4 filtros no alineados)
   XAUUSD: TREND_EXTREMO → stand aside
   Próxima corrida: ~30-60 min. (Trend setups visibles con --show-all, marcados ⚠️.)
```

### 📰 Bloque de noticias (TODOS los casos)

Leído del campo `news` del JSON del router. Se muestra en APPROVED, override y WAIT.

```markdown
📰 Forex Factory — próximas 48h (USD/EUR)
   ⏰ 03 jun 06:15 CR · ADP Non-Farm Employment Change (USD) — en ~23h
   (sin otros high-impact relevantes hasta entonces)
```

- `news.events` vacío → `📰 FF: sin high-impact en 48h para tus assets.`
- `news.stale == true` → añadir `⚠️ calendario FF desactualizado (>24h) — refrescá: .claude/scripts/.venv/bin/python .claude/scripts/macro_calendar.py`
- Las divisas mostradas son las de los activos DESBLOQUEADOS escaneados (Fase 1 → USD/EUR).
- **Informativo** — nunca convierte un WAIT en GO ni bloquea (el gate real sigue siendo
  `macro_gate` en la cadena del agente).

## Cadencia recomendada

Manual cada 30–60 min, o auto-loop:
```
/loop 30m /fot-scout
```
La mayoría de ticks serán **WAIT** — es correcto y disciplinado (RANGE_CHOP da ~1 setup/día-activo).

## Reglas de seguridad

- **NUNCA** ejecuta el trade — solo propone. Ejecución manual en MT5.
- **NUNCA** recomienda un setup de tendencia como GO (edge no validado al spread).
- Sizing phase-aware (risk 1%/2%/2%), nunca más alto. Si lots < 0.01 → UNTRADEABLE_SIZE.
- Override de oro/BTC/ETH en Fase 1 es config-level y documentado (config.md + backtest 2026-04-30).
- yfinance (FX/índices) tiene ~15 min delay → el agente refina el quote del ganador con TV live
  antes de dar la entrada; si el setup decayó → NO-GO.
- **Edge no backtesteado por activo:** si un candidato APROBADO trae `edge_backtested: false`
  (activo del subset curado sin entrada en `per_asset_edge`), el render añade
  `⚠️ edge no backtesteado en este activo — paper-first`. El MR-RANGE_CHOP es edge de clase
  validado, pero ese activo puntual no se backtesteó aún. Usar `mt5_symbol` del candidato para
  las instrucciones de ejecución en MT5 (p.ej. `US100Cash`, `GOLD`, `OILCash`).

Si argumentos:

$ARGUMENTS
