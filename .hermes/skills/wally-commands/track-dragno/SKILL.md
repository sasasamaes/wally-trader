---
name: track-dragno
description: Track Dragno AI (Bitunix copy bot) trades — append from screenshots and
  show stats + SL -8% counterfactual
version: 1.0.0
metadata:
  hermes:
    tags:
    - wally-trader
    - command
    - slash
    category: trading-command
    requires_toolsets:
    - terminal
    - subagents
---
<!-- generated from system/commands/track-dragno.md by adapters/hermes/transform.py -->
<!-- Hermes invokes via /track-dragno -->


# /track-dragno

Tracks executed trades of the external bot "Dragno AI" on Bitunix and reports
rolling performance with a SL -8% counterfactual.

## Two modes

### Mode A — Append new trades (this turn has image attachments)

When the user has attached one or more screenshots of Bitunix's
"Historial de posiciones" tab in this turn:

1. Visually parse each screenshot row. For every visible trade extract:
   - `date` (YYYY-MM-DD from the "Abrir" timestamp date part)
   - `time_open` (HH:MM:SS from "Abrir")
   - `time_close` (HH:MM:SS from "Hora de cierre")
   - `symbol` (uppercase, e.g. `KITEUSDT`)
   - `side` (`Largo` or `Corto` — script normalizes to LONG/SHORT)
   - `leverage` (e.g. `10X`)
   - `entry` (numeric, "Precio de apertura")
   - `exit` (numeric, "Precio de cierre")
   - `pyg_pct` (signed numeric, "PYG%" — keep the sign)
   - `pyg_usd` (signed numeric, "Posición de PYG" — keep the sign)

2. Build a JSON array with one object per parsed trade.

3. Pipe it to the script:

```bash
echo '<JSON_ARRAY>' | python3 .claude/scripts/dragno_track.py --append-from-stdin
```

The script prints how many new trades were added, the full dashboard, and
regenerates `memory/external_traders/dragno_ai.md`.

### Mode B — Stats only (no images this turn)

Run:

```bash
python3 .claude/scripts/dragno_track.py --stats
```

Prints the dashboard without modifying any files. Exit code 2 if no data
exists yet — pass that through as an informative message.

## Optional argument

`--sl-cap N` — override the counterfactual SL cap (default -8.0). Example:
```bash
python3 .claude/scripts/dragno_track.py --stats --sl-cap -10.0
```

## Output language

Always reply in Spanish (project default). Translate column headers in your
explanations but keep raw `LONG`/`SHORT`/numeric values intact.

$ARGUMENTS
