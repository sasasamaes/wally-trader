/**
 * Backend API client.
 *
 * Phase 1 quirk: auth uses `X-User-Id` header (dev stub). Phase 1.5 will
 * replace with Clerk JWTs verified by the API. The client surface stays
 * the same — only the header injection swaps to a Bearer token.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_V1 = `${BASE}/api/v1`;

function headers(): HeadersInit {
  const userId = typeof window !== "undefined" ? localStorage.getItem("wally_user_id") : null;
  return {
    "Content-Type": "application/json",
    ...(userId ? { "X-User-Id": userId } : {}),
  };
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }
  return (await res.json()) as T;
}

// ── LLM keys ───────────────────────────────────────────────────────────

export type LLMProvider = "anthropic" | "openai" | "google" | "ollama";

export interface LLMKey {
  id: string;
  provider: LLMProvider;
  last4: string;
  label: string | null;
  created_at: string;
  last_used: string | null;
}

export async function listLLMKeys(): Promise<LLMKey[]> {
  const res = await fetch(`${API_V1}/keys/llm`, { headers: headers() });
  return handle<LLMKey[]>(res);
}

export async function addLLMKey(input: {
  provider: LLMProvider;
  api_key: string;
  label?: string;
}): Promise<LLMKey> {
  const res = await fetch(`${API_V1}/keys/llm`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(input),
  });
  return handle<LLMKey>(res);
}

export async function deleteLLMKey(keyId: string): Promise<void> {
  const res = await fetch(`${API_V1}/keys/llm/${keyId}`, {
    method: "DELETE",
    headers: headers(),
  });
  if (!res.ok && res.status !== 204) {
    throw new ApiError(res.status, await res.text());
  }
}

// ── Agents ─────────────────────────────────────────────────────────────

export interface AgentMeta {
  name: string;
  description: string;
  requires_profile: boolean;
  input_schema: Record<string, unknown>;
}

export async function listAgents(): Promise<AgentMeta[]> {
  const res = await fetch(`${API_V1}/agents`, { headers: headers() });
  return handle<AgentMeta[]>(res);
}

export interface AgentRunInput {
  provider: LLMProvider;
  model: string;
  input: Record<string, unknown>;
  profile_id?: string;
  temperature?: number;
  max_tokens?: number;
}

export type AgentEvent =
  | { type: "run_started"; run_id: string; agent: string }
  | { type: "text"; delta: string }
  | {
      type: "usage";
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
      cost_usd: number;
      provider: string;
      model: string;
    }
  | { type: "error"; error: string }
  | { type: "done" };

/**
 * Run an agent and yield SSE events as they arrive.
 *
 * Note: `fetch` + `ReadableStream` is preferred over `EventSource` because
 * EventSource is GET-only and we need to POST a JSON body. The wire format
 * is the same: `data: <json>\n\n`.
 */
export async function* runAgent(
  name: string,
  body: AgentRunInput,
  signal?: AbortSignal,
): AsyncGenerator<AgentEvent> {
  const res = await fetch(`${API_V1}/agents/${name}/run`, {
    method: "POST",
    headers: { ...headers(), Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  if (!res.body) {
    throw new ApiError(500, "No response body");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE messages are separated by blank lines
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);

      // Each line in a message: "field: value" — we only care about `data:`
      const dataLines = raw
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trimStart());

      if (dataLines.length === 0) continue;
      const data = dataLines.join("\n");
      try {
        yield JSON.parse(data) as AgentEvent;
      } catch {
        // Malformed event — skip silently to avoid crashing the consumer
      }
    }
  }
}
