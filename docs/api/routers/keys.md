# Keys router


## `GET /api/v1/keys/llm`

<!-- AUTOGEN:START name=GET-api-v1-keys-llm -->
- **Method** `GET`
- **Path** `/api/v1/keys/llm`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 200

**Request body:**

_No request body._

**Response:** `_(no body)_`
<!-- AUTOGEN:END name=GET-api-v1-keys-llm -->

**Cuándo usar:**
- Mostrar en frontend qué providers tiene configurados el usuario (Anthropic, OpenAI, Google, Ollama)
- Antes de un agente run, verificar que existe la key del provider que vas a usar
- Settings page: lista con `last4` para que el usuario identifique cada key sin exponer el secret

**Reglas Wally Trader que aplican:**
- Las keys se guardan encriptadas con AES-256-GCM en `app/security/encryption.py`
- Solo retorna `last4` + label + timestamps — nunca plaintext
- 1 key por provider por usuario (POST nuevo sobreescribe)

**Ejemplo curl:**

```bash
curl -s -H "X-User-Id: 550e8400-..." http://localhost:8000/api/v1/keys/llm
# [{"id":"...","provider":"anthropic","last4":"abcd","label":"prod","created_at":"...","last_used":"..."}]
```

**Ejemplo TypeScript (fetch):**

```typescript
type LLMKey = { id: string; provider: "anthropic" | "openai" | "google" | "ollama"; last4: string; label: string | null };
const keys: LLMKey[] = await (await fetch(`${API}/api/v1/keys/llm`, { headers: { "X-User-Id": userId } })).json();
```

**Errores típicos en este endpoint:**
- `401` si falta `X-User-Id`

**Ver también:**
- `POST /keys/llm` para registrar
- `POST /agents/{name}/run` consume estas keys


## `POST /api/v1/keys/llm`

<!-- AUTOGEN:START name=POST-api-v1-keys-llm -->
- **Method** `POST`
- **Path** `/api/v1/keys/llm`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 201

**Request body:**

| Campo | Tipo | Required | Default | Descripción |
|---|---|---|---|---|
| `provider` | LLMProvider | ✓ | `—` |  |
| `api_key` | string | ✓ | `—` | Raw API key — never logged. |
| `label` | string \| null | — | `null` | Label |

**Response:** `LLMKeyView`
<!-- AUTOGEN:END name=POST-api-v1-keys-llm -->

**Cuándo usar:**
- Onboarding: el usuario pega su API key de Anthropic / OpenAI / Google
- Rotación de keys (sobreescribe la existente del mismo provider)

**Reglas Wally Trader que aplican:**
- BYOK (Bring Your Own Key) — el SaaS no provee keys, el usuario paga su propia cuota LLM
- La plaintext key NUNCA se devuelve después de POST — solo `last4`. Guárdala fuera del API si la necesitas
- Encripción a nivel application via DEK/KEK (`MASTER_KEK` env var)

**Ejemplo curl:**

```bash
curl -X POST http://localhost:8000/api/v1/keys/llm \
  -H "X-User-Id: 550e8400-..." \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "api_key": "sk-ant-api03-...",
    "label": "prod"
  }'
# 201 Created → {"id":"...","provider":"anthropic","last4":"....","label":"prod",...}
```

**Ejemplo TypeScript (fetch):**

```typescript
const created = await fetch(`${API}/api/v1/keys/llm`, {
  method: "POST",
  headers: { "X-User-Id": userId, "Content-Type": "application/json" },
  body: JSON.stringify({ provider: "anthropic", api_key, label: "prod" }),
});
```

**Errores típicos en este endpoint:**
- `400` con mensaje de `KeyServiceError` — formato de key inválido para el provider

**Ver también:**
- `DELETE /keys/llm/{key_id}` para borrar


## `DELETE /api/v1/keys/llm/key_id`

<!-- AUTOGEN:START name=DELETE-api-v1-keys-llm-key_id -->
- **Method** `DELETE`
- **Path** `/api/v1/keys/llm/{key_id}`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 204

**Request body:**

_No request body._

**Response:** `_(no body)_`
<!-- AUTOGEN:END name=DELETE-api-v1-keys-llm-key_id -->

**Cuándo usar:**
- Usuario rotó la key fuera del provider y quiere limpiar la vieja
- Cancelación de cuenta — borrar todas las keys antes de eliminar al usuario

**Reglas Wally Trader que aplican:**
- Solo borra keys del usuario actual (filtra por `user_id`)

**Ejemplo curl:**

```bash
curl -X DELETE -H "X-User-Id: 550e8400-..." \
  http://localhost:8000/api/v1/keys/llm/9f8b...
# 204 No Content
```

**Ejemplo TypeScript:**

```typescript
await fetch(`${API}/api/v1/keys/llm/${keyId}`, { method: "DELETE", headers: { "X-User-Id": userId } });
```

**Errores típicos en este endpoint:**
- `400` "Invalid key_id" — UUID mal formado
- `404` "Key not found" — la key no existe o no es del usuario actual

**Ver también:**
- `GET /keys/llm` para listar IDs

