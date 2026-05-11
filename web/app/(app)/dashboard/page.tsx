/**
 * Authenticated dashboard placeholder.
 *
 * Phase 2 will fill this with the real profile grid + signal log +
 * equity curve. For now this is just a sanity check that the
 * (app) layout group works post-auth.
 */
export default function DashboardPage() {
  return (
    <main className="container mx-auto max-w-6xl px-4 py-12">
      <h1 className="text-3xl font-semibold tracking-tight">Dashboard</h1>
      <p className="mt-2 text-muted-foreground">
        Profiles, equity, and signals will land here in Phase 2.
      </p>
      <div className="mt-8 rounded-lg border border-dashed border-border p-12 text-center text-sm text-muted-foreground">
        Coming next:
        <ul className="mt-3 list-disc text-left pl-8">
          <li>Multi-profile grid with live capital / DD / WR</li>
          <li>Active trades panel (broker read-only sync)</li>
          <li>Signal log filterable by symbol/date/outcome</li>
          <li>Equity curve (Lightweight Charts)</li>
          <li>Regime monitor + macro calendar widget</li>
        </ul>
      </div>
    </main>
  );
}
