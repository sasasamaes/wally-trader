# Wally Trader API — Manual

Manual del backend FastAPI en `api/`. **Estado:** Phase 1 — auth via header `X-User-Id` (no Clerk JWT todavía), no exponer a internet pública.

## Quick start

```bash
cd api
uv sync
# crea api/.env con DATABASE_URL, MASTER_KEK, ANTHROPIC_API_KEY (ver AUTH.md)
uv run alembic upgrade head
uv run uvicorn app.main:app --reload    # http://localhost:8000
```

Swagger UI: http://localhost:8000/docs (solo en dev/staging, no en producción).

## Documentación

- **[MANUAL.md](MANUAL.md)** — Tabla de los 19 endpoints implementados con 1-line "cuándo usar"
- **[routers/](routers/)** — Detalle de cada endpoint (request/response/ejemplos curl + TypeScript)
- **[SCENARIOS.md](SCENARIOS.md)** — 8 flujos típicos Wally Trader
- **[CLI_TO_API.md](CLI_TO_API.md)** — Mapeo `/comando` CLI → endpoints API
- **[AUTH.md](AUTH.md)** — Cómo funciona el header `X-User-Id` hoy
- **[ERRORS.md](ERRORS.md)** — Status codes y ejemplos de cuerpo JSON

## Mantenimiento

Las secciones marcadas `<!-- AUTOGEN:START name=<id> -->` ... `<!-- AUTOGEN:END name=<id> -->` se regeneran con:

```bash
python docs/api/_generate_stubs.py
```

CI corre `--check` y falla si los .md están out of sync. Si tu PR cambia un endpoint, regenera y comitea los .md también.
