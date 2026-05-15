# Meta router


## `GET /api/v1/ping`

<!-- AUTOGEN:START name=GET-api-v1-ping -->
- **Method** `GET`
- **Path** `/api/v1/ping`
- **Auth** Pública
- **Status codes** 200

**Request body:**

_No request body._

**Response:** `_(no body)_`
<!-- AUTOGEN:END name=GET-api-v1-ping -->

**Cuándo usar:**
- Test de "el router v1 está montado y mi proxy/CORS funciona" (más específico que `/healthz`, que es root)
- Frontend lo llama al boot para confirmar conectividad antes de mostrar el dashboard

**Reglas Wally Trader que aplican:**
- _Ninguna._

**Ejemplo curl:**

```bash
curl -s http://localhost:8000/api/v1/ping
# {"pong":"ok"}
```

**Ejemplo TypeScript (fetch):**

```typescript
const ok = (await fetch(`${API_URL}/api/v1/ping`)).ok;
```

**Errores típicos en este endpoint:**
- `404` si el prefijo `/api/v1` cambió en `core/config.py` y tu cliente está hard-coded

**Ver también:**
- `GET /healthz` — root liveness


## `GET /healthz`

<!-- AUTOGEN:START name=GET-healthz -->
- **Method** `GET`
- **Path** `/healthz`
- **Auth** Pública
- **Status codes** 200

**Request body:**

_No request body._

**Response:** `_(no body)_`
<!-- AUTOGEN:END name=GET-healthz -->

**Cuándo usar:**
- Liveness probe en Kubernetes / Fly.io / Render — debe responder `{"status":"ok"}` en <100ms
- Cliente quiere saber qué versión del API está corriendo (campo `version`)
- Smoke test post-deploy: `curl https://api.wallytrader.com/healthz` debe dar 200

**Reglas Wally Trader que aplican:**
- _Ninguna._ Es público y no requiere auth.

**Ejemplo curl:**

```bash
curl -s http://localhost:8000/healthz
# {"status":"ok","version":"0.1.0"}
```

**Ejemplo TypeScript (fetch):**

```typescript
const r = await fetch(`${API_URL}/healthz`);
const { status, version } = await r.json();
console.log(`API ${version} → ${status}`);
```

**Errores típicos en este endpoint:**
- `503` no lo emite el handler hoy, pero un proxy upstream puede devolverlo si el contenedor está down

**Ver también:**
- `GET /api/v1/ping` — variante v1 que confirma que el router está montado

