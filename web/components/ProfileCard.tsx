"use client";

import Link from "next/link";
import { ArrowRight, TrendingDown, TrendingUp } from "lucide-react";
import type { Profile } from "@/lib/api";
import { cn, formatPct, formatUsd } from "@/lib/utils";

/**
 * Compact summary tile for one profile.
 *
 * Used on the dashboard grid. Surface the numbers a trader checks first:
 * current capital, today's PnL%, win rate, total trades.
 */
export function ProfileCard({ profile }: { profile: Profile }) {
  const m = profile.metrics;
  const pnl = m?.total_pnl_usd ?? 0;
  const pnlPct = m
    ? m.capital_initial > 0
      ? ((m.capital_current - m.capital_initial) / m.capital_initial) * 100
      : 0
    : 0;
  const isUp = pnl >= 0;

  return (
    <Link
      href={`/profiles/${profile.slug}`}
      className="group block rounded-lg border border-border bg-card p-5 transition hover:border-foreground/30"
    >
      <header className="mb-4 flex items-start justify-between">
        <div>
          <h3 className="text-lg font-medium">{profile.name}</h3>
          <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            {profile.kind}
          </p>
        </div>
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs",
            isUp
              ? "bg-bull/10 text-bull"
              : "bg-bear/10 text-bear",
          )}
        >
          {isUp ? (
            <TrendingUp className="h-3 w-3" />
          ) : (
            <TrendingDown className="h-3 w-3" />
          )}
          {formatPct(pnlPct, { sign: true })}
        </span>
      </header>

      <div className="space-y-2">
        <div className="flex items-baseline justify-between">
          <span className="text-xs text-muted-foreground">Capital</span>
          <span className="font-mono text-lg font-semibold">
            {formatUsd(m?.capital_current ?? profile.capital_current)}
          </span>
        </div>
        <div className="flex items-baseline justify-between">
          <span className="text-xs text-muted-foreground">Total PnL</span>
          <span
            className={cn(
              "font-mono text-sm",
              isUp ? "text-bull" : "text-bear",
            )}
          >
            {formatUsd(pnl, { sign: true })}
          </span>
        </div>
      </div>

      {m && (
        <div className="mt-4 grid grid-cols-3 gap-2 border-t border-border pt-3 text-xs">
          <Stat label="WR" value={`${m.win_rate_pct.toFixed(1)}%`} />
          <Stat
            label="PF"
            value={
              m.profit_factor === null
                ? "—"
                : m.profit_factor === Infinity
                  ? "∞"
                  : m.profit_factor.toFixed(2)
            }
          />
          <Stat label="Trades" value={String(m.closed_trade_count)} />
        </div>
      )}

      <div className="mt-4 flex items-center gap-1 text-xs text-muted-foreground transition group-hover:text-foreground">
        View details <ArrowRight className="h-3 w-3" />
      </div>
    </Link>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-muted-foreground">{label}</div>
      <div className="font-mono text-sm">{value}</div>
    </div>
  );
}
