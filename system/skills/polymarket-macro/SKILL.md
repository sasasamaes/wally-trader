---
name: polymarket-macro
description: Use cuando un agente (morning-analyst, signal-validator) o el usuario quieran añadir el bias macro de Polymarket al análisis BTC. Devuelve composite −100..+100 + tabla de markets relevantes + flags. Solo SI el snapshot está fresh (<2h); si está STALE devuelve el aviso. Es un 5° filtro — nunca convierte un NO-GO técnico en GO.
---

# Polymarket Macro Sentiment

## Cómo usarlo

Ejecutá:

```bash
.claude/scripts/.venv/bin/python -m polymarket.analyzer --json
```

Esto devuelve un JSON con shape:

```json
{
  "status": "FRESH|STALE|NO_DATA|NO_MARKETS",
  "last_snapshot_age_seconds": 1080,
  "composite": 13.7,
  "bucket": "MILD-BULL",
  "markets": [
    {"slug": "...", "prob_now": 0.62, "delta_1h": 0.01, "delta_24h": 0.07, "delta_7d": 0.14, "vol_24h": 2400000, "weight": 0.30, "contribution": 0.036}
  ]
}
```

Si `status` es FRESH → usa los datos. Si es cualquier otra cosa → reportá "PM macro no disponible esta sesión" y NO uses el composite.

## Reglas operativas

1. **Nunca convertir NO-GO en GO.** El composite es 5° filtro — informativo, no definitivo.
2. **Reducir size 25%** si `|composite| > 40` y los 4 filtros técnicos contradicen el bias. Nunca aumentar size por PM.
3. **Composite range** [-100, +100] con buckets:
   - `> +40` STRONG-BULL
   - `+15..+40` MILD-BULL
   - `-15..+15` NEUTRAL
   - `-40..-15` MILD-BEAR
   - `< -40` STRONG-BEAR
4. **Profile-agnostic** — funciona igual para retail / ftmo / fundingpips / quantfury / bitunix.

## Output sugerido para el reporte (humano-leíble)

Cuando inserts esto en un reporte:

```markdown
### PM Macro Sentiment
**Composite:** +13.7 (MILD-BULL) | **Status:** FRESH (poll 18 min ago) | 11 markets

| Market | Prob | Δ24h | Δ7d | Contribución |
|---|---|---|---|---|
| fed-cut-may-2026 | 62% | +7pp | +14pp | +0.036 (BULL) |
| us-recession-2026 | 28% | -5pp | -3pp | +0.055 (BULL) |
| ...
```

## Cuándo activarlo

- En `morning-analyst` durante FASE 2 (Contexto Global) — útil para días con catalysts macro.
- En `signal-validator` cuando la señal es BTC y hay events high-impact próximos (FOMC, CPI, NFP).
- Cuando el usuario invoca `/polymarket` directamente.

## Cuándo NO activarlo

- Status `STALE` o `NO_DATA` → ignorar, no inventar.
- Setups ultra-rápidos (scalp <15min) — el ciclo macro es muy lento.
- Cuando los 4 filtros técnicos ya cierran el caso de forma unánime.

## Detalles técnicos

- Snapshots se acumulan en `.claude/scripts/polymarket/data/snapshots.jsonl` cada hora vía launchd.
- Discovery rota la whitelist de markets cada día CR 04:00.
- Pesos en `polymarket.config.WEIGHT_MAPPING`. Se ajustan cada 30-60 días con `/polymarket-research`.
