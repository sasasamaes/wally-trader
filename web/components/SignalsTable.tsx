"use client";

/**
 * SignalsTable — filterable signal log with WR/PF header.
 *
 * Phase 2 uses simple state-based filters (no TanStack Table yet — overkill
 * for this row count). Phase 3 can swap in TanStack Table when we add
 * column-level sorting + virtualization for thousands of rows.
 */

import { useMemo, useState } from "react";
import { ArrowUpRight, ArrowDownRight, MinusCircle } from "lucide-react";
import type { Signal, SignalOutcome, SignalSide, SignalStats } from "@/lib/api";
import { cn, formatPct, formatUsd } from "@/lib/utils";

interface Props {
  signals: Signal[];
  stats: SignalStats;
}

const OUTCOME_BADGE: Record<SignalOutcome, string> = {
  PENDING: "bg-muted text-muted-foreground",
  TP1: "bg-bull/10 text-bull",
  TP2: "bg-bull/15 text-bull",
  TP3: "bg-bull/20 text-bull",
  SL: "bg-bear/15 text-bear",
  MANUAL: "bg-secondary text-foreground",
  CANCELLED: "bg-muted text-muted-foreground",
};

export function SignalsTable({ signals, stats }: Props) {
  const [side, setSide] = useState<SignalSide | "ALL">("ALL");
  const [outcome, setOutcome] = useState<SignalOutcome | "ALL">("ALL");
  const [symbol, setSymbol] = useState<string>("");

  const filtered = useMemo(() => {
    return signals.filter((s) => {
      if (side !== "ALL" && s.side !== side) return false;
      if (outcome !== "ALL" && s.outcome !== outcome) return false;
      if (symbol && !s.symbol.toLowerCase().includes(symbol.toLowerCase())) {
        return false;
      }
      return true;
    });
  }, [signals, side, outcome, symbol]);

  return (
    <div className="rounded-lg border border-border bg-card">
      {/* Stats header */}
      <header className="grid grid-cols-2 gap-2 border-b border-border p-4 sm:grid-cols-5">
        <Stat label="Trades" value={String(stats.closed)} />
        <Stat label="WR" value={`${stats.win_rate_pct.toFixed(1)}%`} />
        <Stat
          label="PF"
          value={
            stats.profit_factor === null
              ? "—"
              : stats.profit_factor === Infinity
                ? "∞"
                : stats.profit_factor.toFixed(2)
          }
        />
        <Stat label="Avg win" value={formatUsd(stats.avg_win_usd)} />
        <Stat
          label="Total PnL"
          value={formatUsd(stats.total_pnl_usd, { sign: true })}
          accent={stats.total_pnl_usd >= 0 ? "bull" : "bear"}
        />
      </header>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 border-b border-border p-3 text-xs">
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Search symbol…"
          className="rounded-md border border-input bg-background px-3 py-1.5 font-mono"
        />
        <select
          value={side}
          onChange={(e) => setSide(e.target.value as SignalSide | "ALL")}
          className="rounded-md border border-input bg-background px-2 py-1.5"
        >
          <option value="ALL">All sides</option>
          <option value="LONG">Long</option>
          <option value="SHORT">Short</option>
        </select>
        <select
          value={outcome}
          onChange={(e) => setOutcome(e.target.value as SignalOutcome | "ALL")}
          className="rounded-md border border-input bg-background px-2 py-1.5"
        >
          <option value="ALL">All outcomes</option>
          <option value="PENDING">Pending</option>
          <option value="TP1">TP1</option>
          <option value="TP2">TP2</option>
          <option value="TP3">TP3</option>
          <option value="SL">SL</option>
          <option value="MANUAL">Manual</option>
        </select>
        <span className="ml-auto self-center text-muted-foreground">
          {filtered.length} / {signals.length}
        </span>
      </div>

      {/* Rows */}
      <div className="max-h-[60vh] overflow-y-auto">
        {filtered.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted-foreground">
            No signals match the current filters.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-card text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2 text-left">Symbol</th>
                <th className="px-3 py-2 text-left">Side</th>
                <th className="px-3 py-2 text-right">Entry</th>
                <th className="px-3 py-2 text-right">Exit</th>
                <th className="px-3 py-2 text-right">Lev</th>
                <th className="px-3 py-2 text-right">PnL</th>
                <th className="px-3 py-2">Outcome</th>
                <th className="px-3 py-2 text-right">Hold</th>
                <th className="px-3 py-2 text-left">Date</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr
                  key={s.id}
                  className="border-t border-border/60 transition hover:bg-secondary/40"
                >
                  <td className="px-4 py-2 font-mono">{s.symbol}</td>
                  <td className="px-3 py-2">
                    <SideBadge side={s.side} />
                  </td>
                  <td className="px-3 py-2 text-right font-mono">{s.entry}</td>
                  <td className="px-3 py-2 text-right font-mono text-muted-foreground">
                    {s.exit_price ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {s.leverage ? `${s.leverage}x` : "—"}
                  </td>
                  <td
                    className={cn(
                      "px-3 py-2 text-right font-mono",
                      s.pnl_usd && s.pnl_usd > 0 && "text-bull",
                      s.pnl_usd && s.pnl_usd < 0 && "text-bear",
                    )}
                  >
                    {s.pnl_usd === null
                      ? "—"
                      : formatUsd(s.pnl_usd, { sign: true })}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-medium",
                        OUTCOME_BADGE[s.outcome],
                      )}
                    >
                      {s.outcome}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right text-xs text-muted-foreground">
                    {s.duration_h !== null
                      ? `${s.duration_h.toFixed(1)}h`
                      : "—"}
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">
                    {new Date(s.opened_at).toISOString().slice(0, 10)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "bull" | "bear";
}) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div
        className={cn(
          "font-mono text-base font-semibold",
          accent === "bull" && "text-bull",
          accent === "bear" && "text-bear",
        )}
      >
        {value}
      </div>
    </div>
  );
}

function SideBadge({ side }: { side: SignalSide }) {
  if (side === "LONG") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-bull/10 px-2 py-0.5 text-xs font-medium text-bull">
        <ArrowUpRight className="h-3 w-3" />
        Long
      </span>
    );
  }
  if (side === "SHORT") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-bear/10 px-2 py-0.5 text-xs font-medium text-bear">
        <ArrowDownRight className="h-3 w-3" />
        Short
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
      <MinusCircle className="h-3 w-3" />
      {side}
    </span>
  );
}
