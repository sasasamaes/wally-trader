---
description: Importa una estrategia desde YouTube/PDF/Twitter/texto y la convierte en reglas JSON ejecutables
allowed-tools: Bash, Read, Write, WebFetch
---

Toma contenido externo de un trader (video YouTube, PDF tesis, hilo Twitter, notas) y lo destila en un set de reglas JSON declarativas que el sistema puede usar para escanear setups.

Inspirado en el video YouTube "Cloud Code + TradingView" donde el host importa la estrategia de Murad (memecoin criteria) y la tesis de Leopold (165 páginas) y las usa para encontrar setups que matchean.

## Uso

```
/strategy-import youtube https://youtube.com/watch?v=XXX
/strategy-import file /path/to/thesis.pdf
/strategy-import file /path/to/notes.md
/strategy-import url https://twitter.com/trader/status/123
/strategy-import text "Long cuando RSI<30 + price below VWAP, target 2R, stop 1R"
```

## Pasos

### Fase 1 — Extracción

Ejecutar el extractor según el tipo de fuente:

```bash
# YouTube (auto-subs vía yt-dlp)
python3 .claude/scripts/strategy_distill.py --youtube <URL> --name <opcional>

# Archivo local (txt/md/pdf — pdf usa pdftotext o PyPDF2)
python3 .claude/scripts/strategy_distill.py --file <PATH> --name <opcional>

# URL genérica (HTML stripped)
python3 .claude/scripts/strategy_distill.py --url <URL> --name <opcional>

# Texto crudo
python3 .claude/scripts/strategy_distill.py --text "<contenido>" --name <opcional>
```

Output: JSON con `slug` y `raw_path`. El texto se guarda en `.claude/strategy_imports/raw/<slug>.txt`.

### Fase 2 — Distilación a rules JSON

Claude lee el texto extraído y produce un JSON estructurado en `.claude/strategy_imports/rules/<slug>.json` siguiendo este schema:

```json
{
  "name": "<slug>",
  "source": "<youtube_url | file_path | text>",
  "summary": "Resumen 2-3 líneas de la estrategia",
  "asset_universe": ["BTCUSDT", "ETHUSDT", ...],   // o ["any_crypto"], ["any_forex"], ["memecoins"]
  "timeframe": "15m | 1h | 4h | 1d",
  "side": "long | short | both",
  "entry_rules": [
    {"id": "rule_1", "type": "indicator", "expr": "RSI(14) < 30"},
    {"id": "rule_2", "type": "price", "expr": "close < VWAP_session"},
    {"id": "rule_3", "type": "structure", "expr": "Higher Low confirmed on 1H"}
  ],
  "exit_rules": {
    "tp1": {"type": "fixed", "expr": "entry * 1.015"},
    "tp2": {"type": "fixed", "expr": "entry * 1.025"},
    "sl": {"type": "fixed", "expr": "entry * 0.99"},
    "trail": {"type": "ema", "params": {"length": 21}}
  },
  "filters": [
    {"id": "macro", "expr": "no high-impact event ±30min"},
    {"id": "session", "expr": "London or NY hours only"}
  ],
  "risk_per_trade_pct": 1.0,
  "max_concurrent": 2,
  "notes_for_human": "Detalles que NO se pueden codificar pero importantes para discreción"
}
```

**Reglas para distilación (Claude debe seguir):**

1. Si la fuente menciona indicadores, **mapearlos a nombres estándar** TradingView (RSI, EMA, MACD, BB, VWAP, ADX, Stochastic).
2. Si menciona un trader específico (Murad, Leopold, etc.) → poner su nombre en `notes_for_human`.
3. Si la estrategia es para un asset universe específico (memecoins, large-cap, oro, forex), declararlo en `asset_universe`.
4. Si menciona timeframes múltiples → usar el principal en `timeframe`, otros en `notes_for_human`.
5. Si NO menciona R:R o sizing → poner defaults razonables (`risk_per_trade_pct: 1.0`, TP 1.5R, SL 1R).
6. **Si el contenido NO es una estrategia** (es solo análisis genérico, opinion, market update) → output con `summary: "NOT_A_STRATEGY: <razón>"` y rules vacías.

### Fase 3 — Reportar al usuario

```markdown
📥 STRATEGY-IMPORT — <slug>

## Fuente
- Tipo: <youtube|file|url|text>
- Origen: <URL o path>
- Tamaño: <N> palabras extraídas

## Resumen distilado
<2-3 líneas explicando la estrategia>

## Asset universe + Timeframe
<assets> | <timeframe>

## Entry rules (<N>)
1. <rule 1>
2. <rule 2>
...

## Exit rules
- TP1: <expr>
- TP2: <expr>
- SL: <expr>

## Filtros
- <filtro 1>
- <filtro 2>

## ✅ Saved to
- Raw text: `.claude/strategy_imports/raw/<slug>.txt`
- Rules JSON: `.claude/strategy_imports/rules/<slug>.json`

## 🎯 Próximos pasos
- `/strategy-scan <slug>` — escanea el universo definido buscando setups que matcheen
- Editá el JSON manualmente para refinar (`vim .claude/strategy_imports/rules/<slug>.json`)
- Re-importar con `/strategy-import` apuntando al mismo source si querés actualizar
```

## Reglas de uso

### NO importar
- **Promesas garantizadas** ("100% win rate") → flag y no importar
- **Esquemas pump-and-dump** disfrazados de estrategia → flag y no importar
- **Estrategias sin lógica clara** (puro storytelling) → output `NOT_A_STRATEGY`

### SÍ importar
- Estrategias técnicas con criterios definibles
- Frameworks de selección (cult coins, asymmetric bets) — codificar lo codificable, lo demás a `notes_for_human`
- Estrategias de gestión de riesgo (sizing, max DD, recovery rules)

### Validación post-import
- Si importás >2 estrategias del mismo trader → consolidar en una sola con todas las reglas combinadas
- Si dos estrategias importadas tienen rules contradictorias en el mismo asset universe → preguntar al usuario cuál prevalece

## Limitaciones honest-first

- **YouTube auto-subs son a veces inexactos** — frases técnicas pueden venir mal transcritas. Si después de la distilación la estrategia parece confusa, leer el raw text manualmente.
- **PDFs scaneados (imágenes) NO se extraen** — necesitan OCR. Convertir a texto antes con `pdftotext` (Poppler) o un servicio externo.
- **Twitter API no está integrada** — `--url` extrae HTML básico, puede capturar solo lo público. Para hilos completos, copiar manualmente el texto y usar `--text`.
- **Strategy importer NO ejecuta trades** — solo guarda rules. La ejecución sigue siendo manual o vía `/strategy-scan` (futuro).

## Casos de uso

1. **Importar estrategia de un trader que sigues:**
   - Su YT: `/strategy-import youtube https://youtube.com/watch?v=XXX`
   - Su tesis PDF: `/strategy-import file ~/Downloads/leopold-thesis.pdf`
   - Su hilo Twitter: copiar texto manual + `/strategy-import text "..."`

2. **Importar tu propia estrategia validada:**
   - Convertir tus notas en archivo `.md`: `/strategy-import file ~/notes/my-strategy.md`
   - Iterar: editar rules JSON manual + re-importar

3. **Backtest de estrategia importada (futuro):**
   - Una vez tenés rules JSON: `/backtest strategy <slug>` (a implementar)
