# Design — Bloque de noticias Forex Factory en `/fot-scout`

**Fecha:** 2026-06-01
**Profile:** fotmarkets-only
**Tipo:** feature pequeño (display, no gating)

## Problema

`/fot-scout` no muestra ningún contexto de noticias macro en su output. La infraestructura
macro ya existe:

- `macro_calendar.py` fetchea Forex Factory (FF). De hecho **FF ya es la fuente activa de
  facto**: TradingEconomics (la fuente primaria) devuelve `410 Gone` todos los días desde
  ~2026-05-29, por lo que el sistema cae al scraper FF, que funciona (cache poblado).
- `macro_gate.py` ofrece tiers HARD/WARN/SOFT (±30min / ±4h / próximas 48h).
- El agente `fot-scout-analyst` ya corre `macro_gate` en su cadena de validación.

**El gap:** el agente `fot-scout-analyst` **casi nunca se despacha** porque la mayoría de
ticks del loop son WAIT (RANGE_CHOP da ~1 setup/día-activo). El router
(`fot_scout_router.py`), que es la fuente de verdad del output del loop, **no toca macro
para nada**. Resultado: en la práctica el usuario **nunca ve noticias** en `/fot-scout`.
Además el whitelist de `macro_calendar.py` es genérico por substring y captura eventos de
divisas irrelevantes para el universo fotmarkets (p.ej. AUD GDP, CAD Employment).

## Decisiones de alcance (confirmadas con el usuario)

1. **Rol de las noticias:** mostrar contexto. Informativo, **no bloquea** ni cambia scoring.
2. **Ventana/relevancia:** próximas **~48h**, filtrado a las divisas de los assets
   **desbloqueados** de la fase actual (Fase 1 → {EUR, USD}). Resalta el evento más cercano.

## Por qué en el router (no en el analyst)

La fuente de verdad del output del loop es el JSON del router (`--json`), porque el analyst
se salta en cada WAIT. Adjuntar el bloque `news` al JSON del router garantiza que las
noticias aparezcan en **todos** los ticks, incluido WAIT.

## Componentes

### 1. Función pura nueva — `shared/wally_core/src/wally_core/macro.py`

```python
def upcoming_relevant(currencies, hours=48, now=None) -> dict
```

- Reusa `_load_cache()` y `next_events()` existentes. **Read-only, offline-safe, NO re-scrapea.**
  (El launchd `com.wally.macro-calendar` refresca FF diario a CR 04:00.)
- Normaliza `country` → código de divisa:
  `"United States"→USD`, `"Euro Area"→EUR`, `"United Kingdom"→GBP`, `"Japan"→JPY`;
  códigos crudos (AUD/CAD/USD/...) se uppercasean tal cual.
- Filtra eventos cuya divisa ∈ `currencies`, dentro de `hours` hacia adelante.
- Ordena por cercanía temporal; calcula `hours_until` por evento y `nearest`.
- Hereda `STALE_HOURS=24`: marca `stale=True` si el cache tiene >24h.

**Retorno:**
```json
{
  "events": [
    {"name": "...", "currency": "USD", "country": "...",
     "date": "2026-06-03", "time_cr": "06:15", "hours_until": 23.1}
  ],
  "nearest": { ...primer evento o null... },
  "stale": false,
  "source": "forexfactory"
}
```

### 2. Wire-in — `fot_scout_router.py`

- Nuevo mapa `ASSET_CURRENCIES`:
  ```
  EURUSD→{EUR,USD}, GBPUSD→{GBP,USD}, USDJPY→{USD,JPY},
  XAUUSD→{USD}, NAS100→{USD}, SPX500→{USD}, BTCUSD→{USD}, ETHUSD→{USD}
  ```
- Junta las divisas de los assets **unlocked** de la fase activa (`PHASE_ALLOWED[phase]`),
  llama `upcoming_relevant(currencies, hours=48)`, y adjunta el bloque `"news"` al `--json`.
- Esto descarta el ruido AUD/CAD automáticamente (no están en el set de divisas relevantes).
- Import de `wally_core` vía el mismo patrón de inyección de path que usa `macro_gate.py`.

### 3. Render en el output de `/fot-scout`

Bloque mostrado por Claude leyendo el JSON, presente en **todos** los casos
(APPROVED / override / WAIT):

```
📰 Forex Factory — próximas 48h (USD/EUR)
   ⏰ 03 jun 06:15 CR · ADP Non-Farm Employment Change (USD) — en ~23h
   (sin otros high-impact relevantes hasta entonces)
```

- `stale` → `⚠️ calendario FF desactualizado (>24h) — refrescá: .venv/bin/python macro_calendar.py`
- sin eventos relevantes → `📰 FF: sin high-impact en 48h para tus assets.`

El bloque se documenta en `system/commands/fot-scout.md` (sección de output esperado) para
que el render sea consistente entre corridas y entre agentes.

## Fuera de alcance (YAGNI)

- ❌ No re-fetch en cada tick (serían ~48 scrapes/día a FF). Solo lee cache.
- ❌ No gating ni cambios de scoring (el usuario eligió informativo).
- ❌ No tocar el agente `fot-scout-analyst`, ni launchd, ni el whitelist de `macro_calendar.py`.

## Tests

En `shared/wally_core/tests/test_macro.py` (o nuevo módulo de test si no existe), para
`upcoming_relevant`, con fixtures sintéticas (sin live-data):

1. Filtrado por divisa (USD/EUR pasan, AUD/CAD se descartan).
2. Normalización `country` → código ("United States"→USD, etc.).
3. Orden por cercanía temporal.
4. `nearest` correcto (primer evento futuro).
5. `hours_until` calculado.
6. Flag `stale` cuando `fetched_at` > 24h.
7. Cache vacío / None → `{events: [], nearest: null, stale: True}`.
8. Eventos fuera de la ventana de `hours` se excluyen.

## Riesgos / caveats

- El cache puede estar stale si el launchd no corrió; el flag `stale` lo comunica y sugiere
  refresh manual. El router NUNCA bloquea por stale (es display).
- FF DOM puede cambiar y romper el scraper, pero eso es responsabilidad de
  `macro_calendar.py` (preexistente), no de este feature. Si el cache está vacío, el bloque
  muestra "sin high-impact" honestamente.
