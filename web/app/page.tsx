import type { Route } from "next";
import Link from "next/link";
import { ArrowRight, Bot, Lock, ChartCandlestick } from "lucide-react";

// Optional catch-all routes (`[[...slug]]`) match the parent path at runtime
// but Next.js typedRoutes doesn't expose the bare parent in its generated
// union type. Casting `as Route` is the documented escape hatch.
const SIGN_IN = "/sign-in" as Route;
const SIGN_UP = "/sign-up" as Route;

export default function LandingPage() {
  return (
    <main className="container mx-auto flex min-h-screen max-w-5xl flex-col px-4 py-16">
      <header className="flex items-center justify-between">
        <Link href="/" className="font-mono text-xl font-semibold tracking-tight">
          wally<span className="text-muted-foreground">.trader</span>
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link href={SIGN_IN} className="text-muted-foreground hover:text-foreground">
            Sign in
          </Link>
          <Link
            href={SIGN_UP}
            className="inline-flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-primary-foreground transition hover:opacity-90"
          >
            Get started <ArrowRight className="h-3 w-3" />
          </Link>
        </nav>
      </header>

      <section className="mt-32 flex flex-col items-start gap-6">
        <h1 className="text-balance text-5xl font-semibold tracking-tight md:text-6xl">
          Your best trader friend.
          <br />
          <span className="text-muted-foreground">Who never sleeps.</span>
        </h1>
        <p className="max-w-2xl text-pretty text-lg text-muted-foreground">
          Wally Trader is a multi-agent trading copilot. Bring your own LLM
          key (Anthropic, OpenAI, Gemini, or local Ollama), connect a
          read-only broker, and get real-time regime detection, signal
          validation, and trade journaling — all under one polished dashboard.
        </p>
        <div className="flex gap-3">
          <Link
            href={SIGN_UP}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition hover:opacity-90"
          >
            Start free trial <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="#features"
            className="inline-flex items-center gap-2 rounded-md border border-border bg-secondary px-5 py-2.5 text-sm font-medium transition hover:bg-secondary/80"
          >
            Learn more
          </Link>
        </div>
      </section>

      <section id="features" className="mt-32 grid gap-8 md:grid-cols-3">
        <FeatureCard
          icon={Bot}
          title="BYOK AI"
          body="Use your own Anthropic, OpenAI, Gemini, or Ollama key. You pay the model; we never see your tokens."
        />
        <FeatureCard
          icon={ChartCandlestick}
          title="Live dashboards"
          body="Equity curve, signal log with WR/PF, regime monitor, macro calendar. Updates in real time."
        />
        <FeatureCard
          icon={Lock}
          title="Read-only brokers"
          body="Connect Bitunix, Binance, MT5 — but read-only. We never execute trades. Your money stays under your control."
        />
      </section>

      <footer className="mt-32 flex items-center justify-between border-t border-border pt-8 text-xs text-muted-foreground">
        <span>© {new Date().getFullYear()} Wally Trader</span>
        <span>Educational tool. Not financial advice.</span>
      </footer>
    </main>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  body,
}: {
  icon: React.ElementType;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <Icon className="h-6 w-6 text-foreground" />
      <h3 className="mt-4 text-lg font-medium">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
    </div>
  );
}
