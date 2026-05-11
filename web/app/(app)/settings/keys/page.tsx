"use client";

/**
 * Settings → Keys
 *
 * Where the user adds, views, and deletes their BYOK LLM keys.
 * Plaintext keys NEVER leave the form — once submitted, the API encrypts
 * them. The list view shows only `last4` + label.
 */

import { useEffect, useState } from "react";
import { Trash2, Plus, Loader2, ShieldCheck } from "lucide-react";
import {
  addLLMKey,
  deleteLLMKey,
  listLLMKeys,
  type LLMKey,
  type LLMProvider,
} from "@/lib/api";

const PROVIDERS: { id: LLMProvider; label: string; hint: string }[] = [
  { id: "anthropic", label: "Anthropic", hint: "sk-ant-…" },
  { id: "openai", label: "OpenAI", hint: "sk-…" },
  { id: "google", label: "Google Gemini", hint: "AIza…" },
  { id: "ollama", label: "Ollama (URL)", hint: "http://localhost:11434" },
];

export default function KeysPage() {
  const [keys, setKeys] = useState<LLMKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [provider, setProvider] = useState<LLMProvider>("anthropic");
  const [apiKey, setApiKey] = useState("");
  const [label, setLabel] = useState("");

  async function refresh() {
    setLoading(true);
    try {
      setKeys(await listLLMKeys());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load keys");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await addLLMKey({ provider, api_key: apiKey, label: label || undefined });
      setApiKey("");
      setLabel("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save key");
    } finally {
      setSubmitting(false);
    }
  }

  async function onDelete(id: string) {
    if (!confirm("Delete this key? Existing agents using it will fail until you re-add it.")) {
      return;
    }
    try {
      await deleteLLMKey(id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete key");
    }
  }

  return (
    <main className="container mx-auto max-w-3xl px-4 py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight">API Keys</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Bring Your Own Key. Each key is encrypted with AES-256-GCM before it
          touches the database. We never log plaintext keys, and we never see
          them after you submit.
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Add key form */}
      <form
        onSubmit={onSubmit}
        className="mb-12 rounded-lg border border-border bg-card p-6"
      >
        <h2 className="mb-4 text-lg font-medium">Add a new key</h2>
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Provider
            </label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value as LLMProvider)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              {PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              API key {provider === "ollama" && "(base URL)"}
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={
                PROVIDERS.find((p) => p.id === provider)?.hint ?? ""
              }
              className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm"
              autoComplete="off"
              required
              minLength={8}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Label (optional)
            </label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="My personal key"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              maxLength={80}
            />
          </div>
          <button
            type="submit"
            disabled={submitting || apiKey.length < 8}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-40"
          >
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            Save key
          </button>
        </div>
      </form>

      {/* Key list */}
      <section>
        <h2 className="mb-4 text-lg font-medium">Your keys</h2>
        {loading ? (
          <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Loading…
          </div>
        ) : keys.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No keys yet. Add one above to start using agents.
          </p>
        ) : (
          <ul className="space-y-2">
            {keys.map((k) => (
              <li
                key={k.id}
                className="flex items-center justify-between rounded-md border border-border bg-card px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <ShieldCheck className="h-4 w-4 text-bull" />
                  <div>
                    <div className="font-medium capitalize">
                      {k.provider}
                      {k.label && (
                        <span className="ml-2 text-xs text-muted-foreground">
                          ({k.label})
                        </span>
                      )}
                    </div>
                    <div className="font-mono text-xs text-muted-foreground">
                      ····{k.last4}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => void onDelete(k.id)}
                  className="text-muted-foreground transition hover:text-destructive"
                  aria-label="Delete key"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
