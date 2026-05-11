"use client";

/**
 * Agents chat — streaming SSE-backed conversation with the 6 core agents.
 *
 * Each "send" opens a new run. Streaming text appears incrementally; usage
 * (tokens + cost) shows below the message when the stream ends.
 */

import { useEffect, useRef, useState } from "react";
import { Loader2, Send, Bot, DollarSign } from "lucide-react";
import { listAgents, runAgent, type AgentMeta, type LLMProvider } from "@/lib/api";

const DEFAULT_MODELS: Record<LLMProvider, string> = {
  anthropic: "claude-sonnet-4-6",
  openai: "gpt-4o-mini",
  google: "gemini-2.0-flash",
  ollama: "llama3.1",
};

interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    cost_usd: number;
    model: string;
  };
  error?: string;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentMeta[]>([]);
  const [agentName, setAgentName] = useState<string>("regime");
  const [provider, setProvider] = useState<LLMProvider>("anthropic");
  const [model, setModel] = useState<string>(DEFAULT_MODELS["anthropic"]);
  const [input, setInput] = useState<string>("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [running, setRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    void listAgents().then(setAgents).catch(() => setAgents([]));
  }, []);

  useEffect(() => {
    setModel(DEFAULT_MODELS[provider]);
  }, [provider]);

  async function send() {
    if (!input.trim() || running) return;
    const payloadText = input.trim();

    // Most agents expect structured input. For Phase 1 we treat the textarea
    // as a freeform JSON or natural-language hint placed under `input.prompt`.
    // The agent's `precompute()` can ignore what it doesn't need.
    let payload: Record<string, unknown>;
    try {
      payload = JSON.parse(payloadText);
    } catch {
      payload = { prompt: payloadText };
    }

    const userTurn: ChatTurn = { role: "user", content: payloadText };
    const assistantTurn: ChatTurn = { role: "assistant", content: "" };
    setTurns((prev) => [...prev, userTurn, assistantTurn]);
    setInput("");
    setRunning(true);

    const ac = new AbortController();
    abortRef.current = ac;

    try {
      for await (const ev of runAgent(
        agentName,
        { provider, model, input: payload },
        ac.signal,
      )) {
        setTurns((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (!last || last.role !== "assistant") return next;
          if (ev.type === "text") {
            last.content += ev.delta;
          } else if (ev.type === "usage") {
            last.usage = {
              prompt_tokens: ev.prompt_tokens,
              completion_tokens: ev.completion_tokens,
              cost_usd: ev.cost_usd,
              model: ev.model,
            };
          } else if (ev.type === "error") {
            last.error = ev.error;
          }
          return next;
        });
        if (ev.type === "done") break;
      }
    } catch (e) {
      setTurns((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last && last.role === "assistant") {
          last.error = e instanceof Error ? e.message : "Request failed";
        }
        return next;
      });
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }

  function cancel() {
    abortRef.current?.abort();
  }

  return (
    <main className="container mx-auto flex h-screen max-w-4xl flex-col px-4 py-6">
      {/* Header */}
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Agents</h1>
        <div className="flex items-center gap-2 text-xs">
          <select
            value={agentName}
            onChange={(e) => setAgentName(e.target.value)}
            className="rounded-md border border-input bg-background px-2 py-1.5"
          >
            {agents.map((a) => (
              <option key={a.name} value={a.name}>
                /{a.name}
              </option>
            ))}
          </select>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value as LLMProvider)}
            className="rounded-md border border-input bg-background px-2 py-1.5"
          >
            <option value="anthropic">Anthropic</option>
            <option value="openai">OpenAI</option>
            <option value="google">Google</option>
            <option value="ollama">Ollama</option>
          </select>
          <input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-44 rounded-md border border-input bg-background px-2 py-1.5 font-mono"
          />
        </div>
      </header>

      {/* Description of active agent */}
      <div className="mb-4 rounded-md border border-border bg-card/50 px-4 py-3 text-xs text-muted-foreground">
        {agents.find((a) => a.name === agentName)?.description ??
          "Select an agent above."}
      </div>

      {/* Conversation */}
      <div className="flex-1 space-y-4 overflow-y-auto rounded-md border border-border bg-card/30 p-4">
        {turns.length === 0 && (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Send a message to start. Free-form text or JSON input payload.
          </div>
        )}
        {turns.map((t, i) => (
          <div
            key={i}
            className={`flex gap-3 ${
              t.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {t.role === "assistant" && (
              <Bot className="mt-1 h-5 w-5 flex-shrink-0 text-muted-foreground" />
            )}
            <div
              className={`max-w-[80%] space-y-2 rounded-md px-4 py-2.5 text-sm ${
                t.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary"
              }`}
            >
              <pre className="whitespace-pre-wrap break-words font-sans">
                {t.content || (running && t.role === "assistant" ? "…" : "")}
              </pre>
              {t.usage && (
                <div className="flex items-center gap-3 border-t border-border/50 pt-2 text-xs text-muted-foreground">
                  <DollarSign className="h-3 w-3" />
                  <span>{t.usage.model}</span>
                  <span>{t.usage.prompt_tokens + t.usage.completion_tokens} tokens</span>
                  <span>${t.usage.cost_usd.toFixed(6)}</span>
                </div>
              )}
              {t.error && (
                <div className="border-t border-destructive/30 pt-2 text-xs text-destructive">
                  {t.error}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="mt-4 flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              void send();
            }
          }}
          placeholder="Message or JSON payload. Cmd/Ctrl+Enter to send."
          className="flex-1 rounded-md border border-input bg-background px-3 py-2 font-mono text-sm"
          rows={3}
          disabled={running}
        />
        {running ? (
          <button
            onClick={cancel}
            className="inline-flex items-center gap-2 rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground transition"
          >
            <Loader2 className="h-4 w-4 animate-spin" />
            Cancel
          </button>
        ) : (
          <button
            onClick={() => void send()}
            disabled={!input.trim()}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
            Send
          </button>
        )}
      </div>
    </main>
  );
}
