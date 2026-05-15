# Errors — convenciones HTTP

Todos los errores devuelven JSON con `{"detail": "<mensaje>"}` (formato FastAPI default).

| Status | Cuándo se emite hoy | Ejemplo body |
|---|---|---|
| `400 Bad Request` | UUID mal formado en path o query (`profile_id`, `signal_id`, `key_id`, `run_id`) | `{"detail": "Invalid profile_id"}` |
| `401 Unauthorized` | Header `X-User-Id` falta o el UUID no existe en `users` | `{"detail": "Missing X-User-Id header (...)"}` o `{"detail": "Unknown user"}` |
| `404 Not Found` | Resource no existe O existe pero pertenece a otro usuario (información leak protection) | `{"detail": "Profile not found"}`, `{"detail": "Signal not found"}`, `{"detail": "Run not found"}`, `{"detail": "Key not found"}` |
| `409 Conflict` | Constraint de unicidad: `profiles.slug` duplicado, `equity_points (profile_id, date)` ya existe | `{"detail": "Profile with slug 'retail' already exists"}` |
| `422 Unprocessable Entity` | Validación de schema Pydantic — tipos, rangos, enums | `{"detail":[{"type":"greater_than","loc":["body","entry"],"msg":"Input should be greater than 0",...}]}` |
| `500 Internal Server Error` | Excepción no capturada — bug del backend | `{"detail":"Internal Server Error"}` (en producción no se filtra el stack trace) |
| `201 Created` | POST exitoso a recurso nuevo (signals, profiles, keys) | (con response body del recurso creado) |
| `204 No Content` | DELETE exitoso (keys, profiles) | (sin body) |

## Manejo en frontend (TypeScript pattern)

```typescript
async function apiCall<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    ...init,
    headers: { ...(init?.headers ?? {}), "X-User-Id": userId },
  });
  if (r.status === 204) return undefined as T;
  const body = await r.json();
  if (!r.ok) {
    // Body shape varies: 4xx-custom = {detail: string}, 422 = {detail: ValidationError[]}
    const msg = typeof body.detail === "string"
      ? body.detail
      : `Validation error: ${JSON.stringify(body.detail)}`;
    throw new APIError(r.status, msg);
  }
  return body as T;
}

class APIError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
```

## Diferencia 401 vs 404

Importante: cuando un signal/profile/run existe pero pertenece a OTRO usuario, devolvemos `404` (no `403`). Esto evita leak de "este recurso existe pero no es tuyo" que un atacante podría usar para enumerar IDs ajenos. La auth-failure para "no estás autenticado" es `401`; "no encontré nada accesible para vos" es `404`.

## Errores SSE (`POST /agents/{name}/run`)

Cuando un run falla mid-stream, el SSE emite un evento `error`:

```
event: error
data: {"type":"error","error":"<descripción>"}
```

El response HTTP sigue siendo `200 OK` porque el stream se abrió correctamente. El frontend debe inspeccionar cada evento, no solo el status code inicial.

Casos típicos del evento `error`:
- LLM provider devolvió 401 → "Anthropic authentication failed"
- Quota agotada → "Provider rate limit exceeded"
- Input inválido para el agent → "regime agent requires 'symbol' in input"
- Timeout interno → "LLM call timed out after 120s"
