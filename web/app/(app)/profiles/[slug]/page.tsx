"use client";

import { useEffect, useState } from "react";
import { use as usePromise } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, RefreshCw, TrendingDown, TrendingUp } from "lucide-react";
import {
  getEquitySeries,
  getProfile,
  listSignals,
  type EquityPoint,
  type EquitySummary,
  type Profile,
  type Signal,
  type SignalStats,
} from "@/lib/api";
import { EquityCurve } from "@/components/charts/EquityCurve";
import { SignalsTable } from "@/components/SignalsTable";
import { cn, formatPct, formatUsd } from "@/lib/utils";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export default function ProfileDetailPage({ params }: PageProps) {
  const { slug } = usePromise(params);

  const [profile, setProfile] = useState<Profile | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [stats, setStats] = useState<SignalStats | null>(null);
  const [points, setPoints] = useState<EquityPoint[]>([]);
  const [summary, setSummary] = useState<EquitySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      const [p, sigData, eqData] = await Promise.all([
        getProfile(slug),
        // We need profile.id for signals/equity — fetch profile first
        // (handled by the Promise.all + a second-pass useEffect below)
        Promise.resolve(null),
        Promise.resolve(null),
      ]);
      setProfile(p);
      const [sig, eq] = await Promise.all([
        listSignals({ profile_id: p.id, limit: 500 }),
        getEquitySeries(p.id),
      ]);
      setSignals(sig.signals);
      setStats(sig.stats);
      setPoints(eq.points);
      setSummary(eq.summary);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load profile");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  if (loading) {
    return (
      <main className="container mx-auto flex max-w-6xl items-center justify-center px-4 py-24">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </main>
    );
  }

  if (error || !profile || !stats || !summary) {
    return (
      <main className="container mx-auto max-w-6xl px-4 py-12">
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error ?? "Profile not found"}
        </div>
        <Link
          href="/dashboard"
          className="mt-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3 w-3" />
          Back to dashboard
        </Link>
      </main>
    );
  }

  const isUp = summary.total_pnl_usd >= 0;

  return (
    <main className="container mx-auto max-w-6xl px-4 py-8">
      {/* Breadcrumb + actions */}
      <div className="mb-6 flex items-center justify-between">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3 w-3" />
          Dashboard
        </Link>
        <button
          onClick={() => void refresh()}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground transition hover:text-foreground"
        >
          <RefreshCw className="h-3 w-3" />
          Refresh
        </button>
      </div>

      {/* Header */}
      <header className="mb-8">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">
              {profile.name}
            </h1>
            <p className="mt-1 font-mono text-xs uppercase tracking-wider text-muted-foreground">
              {profile.kind} • {profile.currency}
            </p>
          </div>
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm",
              isUp ? "bg-bull/10 text-bull" : "bg-bear/10 text-bear",
            )}
          >
            {isUp ? (
              <TrendingUp className="h-4 w-4" />
            ) : (
              <TrendingDown className="h-4 w-4" />
            )}
            {formatPct(summary.total_pnl_pct, { sign: true })}
          </span>
        </div>
      </header>

      {/* Summary tiles */}
      <section className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Tile label="Capital" value={formatUsd(summary.capital_current)} mono />
        <Tile
          label="Total PnL"
          value={formatUsd(summary.total_pnl_usd, { sign: true })}
          accent={isUp ? "bull" : "bear"}
          mono
        />
        <Tile
          label="Max DD"
          value={
            summary.max_dd_pct === null
              ? "—"
              : `-${summary.max_dd_pct.toFixed(2)}%`
          }
          accent={summary.max_dd_pct !== null ? "bear" : undefined}
          mono
        />
        <Tile label="Trading days" value={String(summary.trading_days)} mono />
      </section>

      {/* Equity curve */}
      <section className="mb-8 rounded-lg border border-border bg-card p-4">
        <h2 className="mb-3 text-sm font-medium text-muted-foreground">
          Equity curve
        </h2>
        <EquityCurve points={points} height={300} />
      </section>

      {/* Signals table */}
      <section>
        <h2 className="mb-3 text-sm font-medium text-muted-foreground">
          Signal log
        </h2>
        <SignalsTable signals={signals} stats={stats} />
      </section>
    </main>
  );
}

function Tile({
  label,
  value,
  accent,
  mono,
}: {
  label: string;
  value: string;
  accent?: "bull" | "bear";
  mono?: boolean;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div
        className={cn(
          "mt-1 text-xl font-semibold",
          mono && "font-mono",
          accent === "bull" && "text-bull",
          accent === "bear" && "text-bear",
        )}
      >
        {value}
      </div>
    </div>
  );
}
