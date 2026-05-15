# Auth — Phase 1 (X-User-Id) + roadmap a Clerk JWT

## Estado actual (Phase 1)

Todos los endpoints `/api/v1/*` requieren el header `X-User-Id: <uuid>` excepto:
- `GET /healthz`
- `GET /api/v1/ping`
- `GET /api/v1/agents`

El header debe contener el UUID de un row existente en `users`. Si falta o es inválido:
- Falta header → `401 Unauthorized` con `{"detail": "Missing X-User-Id header (Clerk JWT verification lands in Phase 1.5)"}`
- UUID mal formado → `400 Bad Request` con `{"detail": "X-User-Id is not a valid UUID"}`
- UUID no existe en DB → `401 Unauthorized` con `{"detail": "Unknown user"}`

**⚠️ NO exponer este API a internet pública con esta config.** El header es trivial de spoofear. Sólo apto para:
- Local dev
- Red privada / VPN
- Pruebas de integración con seed data controlada

Definido en `app/deps.py:get_current_user`.

## Por qué no hay Clerk JWT todavía

Sub-proyecto #1 (Auth) en el roadmap. Una vez wired:
1. Clerk envía webhook `user.created` → endpoint `/api/v1/auth/webhook` crea row en `users`
2. Frontend obtiene JWT de Clerk client SDK
3. `get_current_user` valida JWT (firma + iss + aud + exp) en vez de leer header
4. Header `X-User-Id` queda sólo como fallback para tests (con env var `WALLY_DEV_AUTH_BYPASS=1`)

## Roadmap concreto (Phase 1.5)

Ver spec `docs/superpowers/specs/<future>-auth-clerk-design.md` (no escrito aún). El cambio es self-contained — solo `app/deps.py` + un router nuevo + middleware. Endpoints existentes no cambian su firma pública (siguen aceptando o el JWT en `Authorization: Bearer ...` o el header de bypass para tests).

## Testing local

Crea un user manualmente vía SQL o seed script:

```sql
INSERT INTO users (id, email, clerk_user_id, created_at)
VALUES ('550e8400-e29b-41d4-a716-446655440000', 'dev@local', null, now());
```

Luego usa ese UUID en todas las requests:

```bash
export USER_ID=550e8400-e29b-41d4-a716-446655440000
curl -H "X-User-Id: $USER_ID" http://localhost:8000/api/v1/profiles
```
