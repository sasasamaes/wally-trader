"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Loader2 } from "lucide-react";
import { listProfiles, type Profile } from "@/lib/api";
import { ProfileCard } from "@/components/ProfileCard";
import { formatUsd } from "@/lib/utils";

/**
 * Dashboard — grid of all the user's trading profiles.
 *
 * Refresh strategy: simple polling every 30s. Phase 3 will swap this for
 * WebSocket subscriptions per-profile so updates land instantly.
 */
export default function DashboardPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      const data = await listProfiles(true);
      setProfiles(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load profiles");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
    const id = setInterval(() => void refresh(), 30_000);
    return () => clearInterval(id);
  }, []);

  const totalCapital = profiles.reduce(
    (acc, p) => acc + (p.metrics?.capital_current ?? p.capital_current),
    0,
  );
  const totalPnl = profiles.reduce(
    (acc, p) => acc + (p.metrics?.total_pnl_usd ?? 0),
    0,
  );

  return (
    <main className="container mx-auto max-w-6xl px-4 py-12">
      <header className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {profiles.length} profile{profiles.length === 1 ? "" : "s"} •{" "}
            <span className="font-mono">{formatUsd(totalCapital)}</span> aggregate
            capital • {formatUsd(totalPnl, { sign: true })} lifetime
          </p>
        </div>
        <Link
          href="/profiles/new"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          New profile
        </Link>
      </header>

      {error && (
        <div className="mb-6 rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-24 text-sm text-muted-foreground">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Loading profiles…
        </div>
      ) : profiles.length === 0 ? (
        <EmptyState />
      ) : (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {profiles.map((p) => (
            <ProfileCard key={p.id} profile={p} />
          ))}
        </section>
      )}
    </main>
  );
}

function EmptyState() {
  return (
    <div className="rounded-lg border border-dashed border-border p-12 text-center">
      <h3 className="text-lg font-medium">No profiles yet</h3>
      <p className="mt-2 text-sm text-muted-foreground">
        Create your first profile to start tracking. Or migrate from your local CLI
        with{" "}
        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
          uv run python scripts/migrate_local_to_db.py
        </code>
      </p>
      <Link
        href="/profiles/new"
        className="mt-6 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
      >
        Create profile
      </Link>
    </div>
  );
}
