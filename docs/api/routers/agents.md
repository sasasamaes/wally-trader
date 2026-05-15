# Agents router


## `GET /api/v1/agents`

<!-- AUTOGEN:START name=GET-api-v1-agents -->
- **Method** `GET`
- **Path** `/api/v1/agents`
- **Auth** Pública
- **Status codes** 200

**Request body:**

_No request body._

**Response:** `_(no body)_`
<!-- AUTOGEN:END name=GET-api-v1-agents -->

**Cuándo usar:**
- Frontend descubre dinámicamente qué agentes existen sin hardcodear nombres
- Antes de llamar `POST /agents/{name}/run`, validar que el nombre existe (evita 404)
- Onboarding: mostrar al usuario qué agentes tiene disponibles + qué inputs requiere cada uno

**Reglas Wally Trader que aplican:**
- 6 agentes registrados hoy: `regime`, `risk`, `signal_validator`, `multifactor`, `journal`, `sentiment`
- `requires_profile=true` significa que el endpoint `run` necesita `profile_id` en el body
- **Endpoint público** — único route v1 que no requiere `X-User-Id` (otros lo necesitan)

**Ejemplo curl:**

```bash
curl -s http://localhost:8000/api/v1/agents
# [{"name":"regime","description":"...","input_schema":{...},"requires_profile":false}, ...]
```

**Ejemplo TypeScript (fetch):**

```typescript
type AgentMeta = { name: string; description: string; input_schema: object; requires_profile: boolean };

const agents: AgentMeta[] = await (await fetch(`${API}/api/v1/agents`)).json();
```

**Errores típicos en este endpoint:**
- Lista vacía nunca debería pasar — significa que `app.agents.AGENTS` quedó sin entradas

**Ver también:**
- `POST /api/v1/agents/{name}/run` — para correr uno
- [SCENARIOS.md#1-morning-routine](../SCENARIOS.md) — usa `regime` para detectar régimen del día


## `POST /api/v1/agents/name/run`

<!-- AUTOGEN:START name=POST-api-v1-agents-name-run -->
- **Method** `POST`
- **Path** `/api/v1/agents/{name}/run`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 200, 200, 404

**Request body:**

| Campo | Tipo | Required | Default | Descripción |
|---|---|---|---|---|
| `provider` | LLMProvider | ✓ | `—` |  |
| `model` | string | ✓ | `—` | Provider-specific model id, e.g. claude-sonnet-4-6 |
| `input` | object | — | `—` | Agent-specific input payload (symbol, bars, etc.). |
| `profile_id` | string \| null | — | `null` | Optional profile UUID for context isolation. |
| `temperature` | number | — | `0.4` | Temperature |
| `max_tokens` | integer | — | `2048` | Max Tokens |

**Response:** `_(no body)_`
<!-- AUTOGEN:END name=POST-api-v1-agents-name-run -->

**Cuándo usar:**
- Disparar el análisis de uno de los 6 agentes y consumir su salida en streaming (SSE)
- Reemplazo programático del slash command equivalente: `/regime`, `/risk`, `/signal`, `/multifactor`, `/journal`, `/sentiment`
- Frontend de chat o dashboard: muestra tokens en vivo a medida que el LLM los emite

**Reglas Wally Trader que aplican:**
- Requiere que el usuario tenga una LLM key registrada (`POST /keys/llm`) para el `provider` solicitado, salvo `ollama`
- Cada run consume tokens y graba un row en `agent_run` (cost_usd se calcula via `app/llm_gateway/pricing.py`)
- `profile_id` es obligatorio para agentes con `requires_profile=true` (ver `GET /api/v1/agents`)

**Eventos SSE emitidos (en orden):**

| `event` | `data.type` | Payload |
|---|---|---|
| `run_started` | `run_started` | `{"run_id": "<uuid>", "agent": "<name>"}` |
| `text` | `text` | `{"delta": "<incremental text chunk>"}` (puede llegar muchos) |
| `usage` | `usage` | `{"prompt_tokens":N, "completion_tokens":N, "cost_usd":F}` |
| `done` | `done` | `{}` (terminal exitoso) |
| `error` | `error` | `{"error": "<msg>"}` (terminal con falla) |

Guarda el `run_id` del primer evento — si el stream se corta puedes recuperar el resultado vía `GET /api/v1/agents/runs/{run_id}`.

**Ejemplo curl:**

```bash
curl -N -X POST http://localhost:8000/api/v1/agents/regime/run \
  -H "X-User-Id: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "model": "claude-sonnet-4-6",
    "input": {"symbol": "BTCUSDT", "timeframe": "1h"},
    "temperature": 0.2,
    "max_tokens": 1024
  }'
# Stream:
# event: run_started
# data: {"type":"run_started","run_id":"..."}
#
# event: text
# data: {"type":"text","delta":"Régimen actual: RANGE_CHOP..."}
# ...
# event: done
# data: {"type":"done"}
```

**Ejemplo TypeScript (fetch + SSE manual):**

```typescript
const r = await fetch(`${API}/api/v1/agents/regime/run`, {
  method: "POST",
  headers: { "X-User-Id": userId, "Content-Type": "application/json" },
  body: JSON.stringify({
    provider: "anthropic",
    model: "claude-sonnet-4-6",
    input: { symbol: "BTCUSDT", timeframe: "1h" },
  }),
});
const reader = r.body!.getReader();
const decoder = new TextDecoder();
let runId: string | undefined;
let buffer = "";
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  for (const line of buffer.split("\n\n")) {
    if (!line.startsWith("data: ")) continue;
    const event = JSON.parse(line.slice(6));
    if (event.type === "run_started") runId = event.run_id;
    if (event.type === "text") process.stdout.write(event.delta);
    if (event.type === "done") return;
    if (event.type === "error") throw new Error(event.error);
  }
  buffer = buffer.endsWith("\n\n") ? "" : buffer;
}
```

**Errores típicos en este endpoint:**
- `404` "Unknown agent '<name>'" — typo o agente no registrado
- `400` "Invalid profile_id" — el UUID está mal formado
- `400` "Invalid provider" — provider no es `anthropic` / `openai` / `google` / `ollama`
- Evento `error` mid-stream — la API key del provider falló (`401` upstream) o se acabó la cuota

**Ver también:**
- `GET /api/v1/agents/runs/{run_id}` — recupera resultado si el SSE se cortó
- `POST /api/v1/keys/llm` — debes registrar la key del provider primero
- [SCENARIOS.md#2-validar-señal-discord](../SCENARIOS.md)


## `GET /api/v1/agents/runs/run_id`

<!-- AUTOGEN:START name=GET-api-v1-agents-runs-run_id -->
- **Method** `GET`
- **Path** `/api/v1/agents/runs/{run_id}`
- **Auth** Requiere `X-User-Id: <uuid>` header
- **Status codes** 200

**Request body:**

_No request body._

**Response:** `AgentRunSummary`
<!-- AUTOGEN:END name=GET-api-v1-agents-runs-run_id -->

**Cuándo usar:**
- El SSE de un run anterior se cortó (red inestable, navegador cerrado) — recupera el resultado completo
- Auditoría: revisar qué se le pidió a un agente, cuánto costó, cuánto duró
- Replay para debugging: ¿por qué el agente devolvió X output con Y input?

**Reglas Wally Trader que aplican:**
- Solo retorna runs del usuario actual (filtra por `user_id`)
- `output_md` es el markdown final concatenado; `error` está populado si terminó en `error`

**Ejemplo curl:**

```bash
curl -s -H "X-User-Id: 550e8400-..." \
  http://localhost:8000/api/v1/agents/runs/9f8b... | jq
# {
#   "id": "9f8b...",
#   "agent_name": "regime",
#   "status": "completed",
#   "provider": "anthropic",
#   "model": "claude-sonnet-4-6",
#   "prompt_tokens": 421,
#   "completion_tokens": 87,
#   "cost_usd": 0.00138,
#   "duration_ms": 2104,
#   "output_md": "Régimen: RANGE_CHOP...",
#   "error": null
# }
```

**Ejemplo TypeScript (fetch):**

```typescript
type AgentRunSummary = { id: string; agent_name: string; status: string; output_md: string | null; cost_usd: number | null };
const run: AgentRunSummary = await (await fetch(`${API}/api/v1/agents/runs/${runId}`, {
  headers: { "X-User-Id": userId },
})).json();
```

**Errores típicos en este endpoint:**
- `400` "Invalid run_id" — UUID mal formado
- `404` "Run not found" — el run no existe O pertenece a otro usuario

**Ver también:**
- `POST /api/v1/agents/{name}/run` — para crear runs nuevos

