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
// ── Profiles ───────────────────────────────────────────────────────────

export interface ProfileMetrics {
  trade_count: number;
  closed_trade_count: number;
  win_count: number;
  loss_count: number;
  win_rate_pct: number;
  avg_win_usd: number;
  avg_loss_usd: number;
  profit_factor: number | null;
  total_pnl_usd: number;
  capital_current: number;
  capital_initial: number;
  daily_pnl_pct_last: number | null;
  max_dd_pct: number | null;
}

export interface Profile {
  id: string;
  slug: string;
  name: string;
  kind: string;
  capital_initial: number;
  capital_current: number;
  currency: string;
  config_json: Record<string, unknown>;
  strategy_json: Record<string, unknown>;
  rules_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  metrics?: ProfileMetrics | null;
}

export async function listProfiles(includeMetrics = true): Promise<Profile[]> {
  const res = await fetch(
    `${API_V1}/profiles?include_metrics=${includeMetrics}`,
    { headers: headers() },
  );
  const data = await handle<{ profiles: Profile[]; total: number }>(res);
  return data.profiles;
}

export async function getProfile(slug: string): Promise<Profile> {
  const res = await fetch(`${API_V1}/profiles/${slug}`, { headers: headers() });
  return handle<Profile>(res);
}

// ── Signals ────────────────────────────────────────────────────────────

export type SignalSide = "LONG" | "SHORT";
export type SignalOutcome = "PENDING" | "TP1" | "TP2" | "TP3" | "SL" | "MANUAL" | "CANCELLED";

export interface Signal {
  id: string;
  profile_id: string;
  symbol: string;
  side: SignalSide;
  entry: number;
  sl: number | null;
  tp1: number | null;
  tp2: number | null;
  tp3: number | null;
  leverage: number | null;
  source: string;
  verdict: string | null;
  outcome: SignalOutcome;
  exit_price: number | null;
  exit_reason: string | null;
  pnl_usd: number | null;
  duration_h: number | null;
  multifactor_score: number | null;
  ml_score: number | null;
  regime: string | null;
  learning: string | null;
  opened_at: string;
  closed_at: string | null;
}

export interface SignalStats {
  total: number;
  open: number;
  closed: number;
  wins: number;
  losses: number;
  win_rate_pct: number;
  avg_win_usd: number;
  avg_loss_usd: number;
  total_pnl_usd: number;
  profit_factor: number | null;
}

export interface SignalListResponse {
  signals: Signal[];
  stats: SignalStats;
  total: number;
}

export async function listSignals(params: {
  profile_id: string;
  symbol?: string;
  side?: SignalSide;
  outcome?: SignalOutcome;
  from_date?: string;
  to_date?: string;
  limit?: number;
  offset?: number;
}): Promise<SignalListResponse> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) qs.set(k, String(v));
  });
  const res = await fetch(`${API_V1}/signals?${qs.toString()}`, {
    headers: headers(),
  });
  return handle<SignalListResponse>(res);
}

// ── Equity ─────────────────────────────────────────────────────────────

export interface EquityPoint {
  date: string;
  equity: number;
  daily_pnl_pct: number | null;
  dd_pct: number | null;
  outperformance_vs_hodl_pct: number | null;
  win_rate_pct: number | null;
  trade_count: number;
}

export interface EquitySummary {
  capital_initial: number;
  capital_current: number;
  total_pnl_usd: number;
  total_pnl_pct: number;
  max_dd_pct: number | null;
  trading_days: number;
  last_updated: string | null;
}

export async function getEquitySeries(profile_id: string): Promise<{
  points: EquityPoint[];
  summary: EquitySummary;
}> {
  const res = await fetch(`${API_V1}/equity?profile_id=${profile_id}`, {
    headers: headers(),
  });
  return handle<{ points: EquityPoint[]; summary: EquitySummary }>(res);
}

// ── Agents (streaming) ─────────────────────────────────────────────────

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
