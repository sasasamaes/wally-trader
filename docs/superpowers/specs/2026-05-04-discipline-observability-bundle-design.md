# Spec: Discipline & Observability Bundle

**Date:** 2026-05-04
**Status:** Approved (sections 1-4 confirmed in brainstorming session)
**Author:** brainstorming session with user
**Bundle scope:** features #3, #7, #8 from the post-Polymarket roadmap

## Context

After merging the Polymarket macro sentiment integration to `main`, we identified 5 candidate next features. Two are strategy/data work (Donchian Breakout for BTC, NAS100/SPX500 backtest expansion); three are discipline/observability tooling that share an implementation pattern: a Python helper script + launchd job + slash command (or wire-in to existing skill).

The user chose option B from the decomposition discussion: **bundle the three observability features into one spec** and treat the strategy/data work as a separate spec later. This document covers the bundle.

## Goals

1. **Defensive trading discipline (#7).** Prevent the system from authorizing entries during the ±30 min window around high-impact macro events (FOMC, CPI, NFP, ECB/BoE/BoJ rate decisions). Backtest 2026-04-30 showed -10pp WR on macro-event days versus baseline; eliminating those trades is pure defense.
2. **Bitunix signal logging (#3).** Capture every external signal we validate via `/signal` plus its decision and (later) outcome into `signals_received.md` and `.csv` automatically, so we can compare `hit_rate_filtered` vs `hit_rate_blind` once we accumulate 30+ entries (per `docs/backtest_findings_2026-04-30.md` Group E).
3. **Cross-profile observability (#8).** Replace the manual `/review` weekly with an automated digest that summarizes all profiles + previews next week's macro events, delivered every Sunday 18:00 CR.

## Non-Goals (Out of Scope)

- Bundle 2 features: Donchian BTC strategy (#1), NAS100/SPX500 data expansion (#2). Separate spec later.
- Auto-capture of Bitunix signals from Discord (too much infra; out of scope).
- `/journal bitunix` enhancement that calculates `hit_rate_filtered` vs `hit_rate_blind`. The schema and infrastructure to enable this calculation is part of #3, but the calculation itself is a future iteration once we have ≥30 logged signals.
- Auto-fill of "hypothetical outcome" for SKIP signals (would require a separate launchd job that reads price 24h after signal time). Future iteration.
- Notion delivery for weekly digest (Notion MCP not configured per current statusline).
- Backtesting whether the ±30 min macro window is the optimal length. We use the industry default; tuning is a future iteration once we have 30+ days of data showing how often we got blocked vs how often the block was warranted.

## Decisions Made During Brainstorming

| Question | Decision | Rationale |
|---|---|---|
| Where does macro gate enforce? | `morning-analyst` (warn) + `/validate` + `/signal` (hard block) | Catches both day-level planning and intraday entries near events |
| Macro data source | TradingEconomics primary + Forex Factory fallback | Robust against single-source outage |
| Which events block | USA tier-1 (FOMC, CPI, NFP, PCE, PPI, GDP, Powell, Retail Sales) + ECB/BoE/BoJ rate decisions | Covers BTC and the multi-asset universe FTMO/FundingPips trade |
| Time window | ±30 min | Industry default; matches skill `macro-events-calendar` |
| Macro cache refresh | Daily via launchd, CR 04:00 (before morning) | Cheap, well before any session activity |
| Bitunix capture method | Auto-log on `/signal` + `/log-outcome` companion command | Splits creation moment (signal) from completion moment (trade close) |
| Weekly digest scope | Cross-profile compact + next-week macro lookahead | Actionable forward-looking section, not just retrospective |
| Digest schedule + delivery | Sunday 18:00 CR + macOS notification | Pasive but visible; user already uses `osascript` notif elsewhere |

## Architecture

### Feature 1: Macro Events Gate (#7)

**Components:**

| File | Purpose |
|---|---|
| `.claude/scripts/macro_calendar.py` | Fetcher. TradingEconomics primary, Forex Factory fallback. Atomic write to cache. |
| `.claude/scripts/macro_gate.py` | CLI helper. Subcommands: `--check-now`, `--check-day YYYY-MM-DD`, `--next-events --days N`. Pure read of cache. |
| `.claude/launchd/com.wally.macro-calendar.plist` | Daily refresh CR 04:00. |
| `.claude/cache/macro_events.json` | Cache schema: `{fetched_at, source, events: [{date, time_cr, country, name, impact}]}`. |

**Event whitelist:**
- USA tier-1: FOMC Meeting, FOMC Minutes, CPI, Core CPI, NFP, PCE, Core PCE, PPI, GDP (advance/preliminary/final), Powell speeches, Retail Sales.
- Europe/UK/Japan: ECB Rate Decision + Lagarde press, BoE Rate Decision, BoJ Rate Decision.
- Filter logic: feed must report `impact == "high"` AND event name fuzzy-matches whitelist. The whitelist guards against TE/FF mislabeling random events as high-impact.

**Wire-in points:**
- `morning-analyst` and `morning-analyst-ftmo` (system/agents/): at start of analysis, call `bash macro_gate.py --check-day today`. If event found, prepend `🔴 MACRO ALERT: <event> <time CR>` to output. Does NOT block the morning workflow itself — informational + recommends specific time windows to avoid.
- `trade-validator` agent: in FASE 1 (before evaluating the 4 filters), call `bash macro_gate.py --check-now`. If `blocked=true` → return immediately with `NO-GO: macro event window — <event_name> at <time_cr>, in <delta_minutes> min`. Skip filter evaluation entirely.
- `signal-validator` agent: same gate as trade-validator, same response format.

**Source fallback logic:**
1. Try TE: `GET api.tradingeconomics.com/calendar?c=guest:guest&country=united%20states,euro%20area,united%20kingdom,japan&importance=3` (importance=3 means high). 10s timeout.
2. On 429 / 5xx / timeout / parse error → try Forex Factory HTML scrape (`forexfactory.com/calendar`). Selectors depend on current FF DOM and are confirmed during implementation; the parser must extract: date, time (TZ converted to CR), event name, country, impact level. Implementation should snapshot the FF page once, save as test fixture, and write the parser against the snapshot.
3. On both failing → keep existing cache, log error to `.claude/cache/macro_calendar_errors.log`, exit code 1. Cache TTL warning (`stale=true`) kicks in if `fetched_at < now - 24h`.

**Error handling at consumer side:**
- `macro_gate.py` reads cache. If cache file missing → `{blocked: false, reason: "no_cache", stale: true}` to stderr + exit 0 (don't break the consumer).
- If cache stale >24h → `stale: true` flag in JSON output. trade-validator policy: stale >24h → warn user but don't block (avoid DoS via broken feed).
- If cache stale <24h → trust it. Macro events don't move minute-to-minute.

### Feature 2: Bitunix Log Capture (#3)

**Components:**

| File | Purpose |
|---|---|
| `.claude/scripts/bitunix_log.py` | CLI with subcommands: `append-signal --stdin`, `append-outcome SYMBOL OUTCOME EXIT_PRICE [--pnl USD] [--id N]`. |
| `system/commands/log-outcome.md` | Slash command definition. Plus mirrors in `.opencode/commands/log-outcome.md` and `.hermes/skills/wally-commands/log-outcome/SKILL.md` (per multi-CLI portability pattern). |
| Modification to `system/commands/signal.md` (and mirrors) | At end of validation, if `WALLY_PROFILE=bitunix`, pipe report through `bitunix_log.py append-signal --stdin`. |

**Flow `/signal SYMBOL SIDE entry=X sl=Y tp=Z` → automatic logging:**
1. `/signal` skill executes its existing 8-step validation pipeline and produces a markdown report.
2. After producing the report, if `WALLY_PROFILE=bitunix`, the skill pipes its full output to `bitunix_log.py append-signal --stdin`.
3. The script parses the report using regex/sectioning anchored on stable headers (`**Pipeline validación (8 steps):**`, `**Validation Score:**`, `**Decisión:**`, etc.). Extracts the 24 fields specified in the existing `signals_received.csv` schema.
4. Writes a new entry block to `signals_received.md` (using the template already present in the file) and appends a row to `signals_received.csv`.
5. If parse fails → log to `.claude/cache/bitunix_log_errors.log` with the unparsed report attached, write `WARNING: bitunix_log parse failed, see cache/bitunix_log_errors.log` to stderr, exit non-zero. Do NOT fail the `/signal` skill itself — the warning is enough signal.

**Flow `/log-outcome BTCUSDT TP1 67500`:**
1. Read `signals_received.md`, find the most recent entry of `BTCUSDT` where `executed=yes` AND outcome fields are blank.
2. If found → fill `Outcome`, `Exit price`, `PnL` (compute from entry+exit+leverage if not provided), `Time to outcome`, prompt interactively only for fields that can't be inferred (e.g. "Held 4-pilar al exit? Y/N").
3. Update the corresponding row in `.csv`.
4. If no open entry found → error: `No open signal for BTCUSDT. Last entry was 2026-05-02, already closed.` Exit 1.
5. If multiple open entries (rare, e.g. staggered copy-trades) → list them with index and prompt for `--id N`.

**Profile gating:**
- `bitunix_log.py append-signal` checks `WALLY_PROFILE` env. If not `bitunix` → silent no-op exit 0. The log is intentionally bitunix-only.
- `/log-outcome` slash command on a non-bitunix profile prints `Solo aplica a profile bitunix.` and exits.

### Feature 3: Weekly Digest (#8)

**Components:**

| File | Purpose |
|---|---|
| `.claude/scripts/weekly_digest.py` | Generator. Reads each profile, calls macro lookahead, writes markdown, fires notification. |
| `.claude/launchd/com.wally.weekly-digest.plist` | Sunday 18:00 CR. |
| `memory/weekly_digests/` | Output directory. Files named `YYYY-Wnn.md` (ISO week format). |

**CLI:**
- `bash .claude/scripts/weekly_digest.py` (default: `--week current`).
- `bash .claude/scripts/weekly_digest.py --week 2026-W17` (regenerate past).
- `bash .claude/scripts/weekly_digest.py --week current --no-notif` (suppress notification, useful for testing).

**Output structure** (~150-250 lines):

```markdown
# Weekly Digest — Week 18 (2026-04-27 → 2026-05-03)

## Cross-profile summary

| Profile | Capital | PnL semana | PnL mes | Trades | WR | Status |
|---|---|---|---|---|---|---|
| retail | $18.09 (≈₡8,241) | +$2.50 (+16%) | +$3.10 | 4 | 75% | active |
| ... |

## Profile más activo: <name> (<N> trades)
[mini-review: top win, top loss, hora más rentable, lección clave]

## 🔴 Macro week ahead (next 7 days)
| Día | Hora CR | Evento | Impact |
|---|---|---|---|
| ... |

NO TRADE windows: <list>

## Highlights y disciplina
- ✅/⚠️ items: 2 SLs consecutivos check, ventana operativa check, filtros 4/4 check.

## Próxima semana — sugerencias
- [auto-generated bullets based on patterns + macro]
```

**Data sources per profile:**
- `memory/trading_log.md` (each profile) — each profile has its own log format. The script uses a **per-profile parser registry** keyed by profile name. Initial parsers cover only profiles with active trading history at spec time: `retail`, `retail-bingx`, `ftmo`, `bitunix`. Profiles without a registered parser (or with no `trading_log.md` at all) appear in the table with `not started` or `parser pending` and do NOT crash the digest.
- Adding a new profile to the digest in the future requires writing one parser function in `weekly_digest.py` plus a fixture in `tests/fixtures/digest/profiles/<name>/`.
- `config.md` (each profile) — extract `Capital actual:` line via regex `r'Capital actual.*?\$([\d,.]+)'`. If line missing, capital shows `—`.
- For `retail` only: also call `bash .claude/scripts/fx_rate.sh` to compute CRC equivalent. Show as footer note: `Tipo cambio del día: 1 USD = ₡XXX`.
- Capital deltas: read previous week's digest at `memory/weekly_digests/YYYY-W<n-1>.md` if exists; if not, delta shows `—`.

**Macro lookahead section:**
- Calls `bash .claude/scripts/macro_gate.py --next-events --days 7`.
- If cache unavailable / stale → render `(macro cache unavailable — refresh: bash .claude/scripts/macro_calendar.py)` instead of the table. Digest does not fail.

**Notification:**
- After writing file: `osascript -e 'display notification "📊 Weekly digest ready: N trades, $X PnL, M macro events next week" with title "Wally Trader" subtitle "Week NN"'`.
- If `osascript` not available (e.g., headless run) → log `notification skipped (no osascript)` to stderr and continue.

**Idempotency:**
- Multiple runs in same week overwrite `YYYY-Wnn.md`. No append, no duplicate.
- Header includes `Generated: <ISO timestamp>` so the diff is obvious.

## Testing Strategy

### Unit tests

**`tests/test_macro_calendar.py`** (~6-8 tests):
- Fixture `fixtures/macro/te_response.json` (anonymized real TE response).
- Fixture `fixtures/macro/ff_response.html` (anonymized FF HTML snippet).
- Test: TE parse → expected events list.
- Test: TE 429 → falls through to FF.
- Test: both fail → keeps existing cache, exit 1, error log written.
- Test: whitelist filter excludes random "PMI" events tagged high-impact.
- Test: atomic write (tmp + rename, not partial file on crash).

**`tests/test_macro_gate.py`** (~5-7 tests):
- Fixture `fixtures/macro/cache_today_event.json` with one event "today 06:30 CR".
- Test: monkeypatch `now()` to 06:18 CR → `--check-now` blocks (delta=12 min < 30).
- Test: monkeypatch to 05:59 CR → does NOT block (delta=31 min > 30).
- Test: monkeypatch to 07:30 CR → does NOT block (post-window).
- Test: cache `fetched_at` >24h ago → output flag `stale: true`.
- Test: cache missing → exit 0, output `blocked: false, reason: no_cache`.
- Test: `--next-events --days 7` returns sorted list within window.

**`tests/test_bitunix_log.py`** (~6-8 tests):
- Fixture `fixtures/bitunix/signal_report_canonical.md` (canonical `/signal` output).
- Test: `append-signal --stdin` parses 24 fields correctly, appends to MD + CSV.
- Test: malformed report → does NOT write, error log populated, non-zero exit.
- Test: `WALLY_PROFILE != bitunix` → no-op exit 0.
- Test: `append-outcome` finds open entry by symbol, fills outcome fields.
- Test: `append-outcome` with two open entries → requires `--id`.
- Test: `append-outcome` with no open entry → error message, exit 1.
- Test: PnL auto-computation (long/short, with leverage).

**`tests/test_weekly_digest.py`** (~5-7 tests):
- Fixture mini-repo with 2-3 profile dirs containing dummy `trading_log.md` + `config.md`.
- Test: generates valid markdown, table rows match dummy data.
- Test: profile with no `trading_log.md` → row shows `not started`, no crash.
- Test: macro cache missing → digest renders fallback message, no crash.
- Test: idempotency — running twice for same `--week` produces identical content (modulo `Generated:` timestamp line).
- Test: `--no-notif` flag suppresses osascript call.

### Integration verification (manual, post-implementation)

- Run `bash .claude/scripts/macro_calendar.py` once in dev → verify cache populates with plausible events for current week.
- Run `bash .claude/scripts/macro_gate.py --check-now` → verify exit 0 and output structure.
- In a `bitunix` profile session, run `/signal BTCUSDT LONG entry=X sl=Y tp=Z` (with dummy values) → verify entry appears in `signals_received.md` and `.csv`.
- Run `bash .claude/scripts/weekly_digest.py --week current` → visually inspect output and macOS notification.

### Sanity tests

Add to `.claude/scripts/test_pdf_helpers.py` (which runs hourly via `preprompt_check.sh`):
- `macro_gate.py --check-now` exits 0 even with empty cache (defensive).
- `weekly_digest.py --week current --no-notif --dry-run` returns a non-empty markdown string (smoke test).

### Coverage target

- Helpers in `.claude/scripts/` (the four new ones): ≥80% line coverage. Critical because they are in the defensive trading path.
- Slash command definitions are markdown files; only smoke-tested by invoking them.

### Out of scope for tests

- launchd plist files. Verification is manual: `launchctl load <plist>` and observe trigger in `launchctl list | grep wally`.
- Production rate-limit behavior of TradingEconomics. We test against fixtures only.
- Forex Factory HTML structure stability. If FF changes their markup, the parser breaks; we accept that risk because FF is the fallback path used only when TE fails.

## File Manifest

### New files
- `.claude/scripts/macro_calendar.py`
- `.claude/scripts/macro_gate.py`
- `.claude/scripts/bitunix_log.py`
- `.claude/scripts/weekly_digest.py`
- `.claude/launchd/com.wally.macro-calendar.plist`
- `.claude/launchd/com.wally.weekly-digest.plist`
- `system/commands/log-outcome.md`
- `.opencode/commands/log-outcome.md`
- `.hermes/skills/wally-commands/log-outcome/SKILL.md`
- `.claude/scripts/tests/test_macro_calendar.py`
- `.claude/scripts/tests/test_macro_gate.py`
- `.claude/scripts/tests/test_bitunix_log.py`
- `.claude/scripts/tests/test_weekly_digest.py`
- `.claude/scripts/tests/fixtures/macro/te_response.json`
- `.claude/scripts/tests/fixtures/macro/ff_response.html`
- `.claude/scripts/tests/fixtures/macro/cache_today_event.json`
- `.claude/scripts/tests/fixtures/bitunix/signal_report_canonical.md`
- `.claude/scripts/tests/fixtures/bitunix/profiles/` (mini-repo for weekly digest tests)
- `memory/weekly_digests/` (directory; first file created on first run)

### Modified files
- `system/commands/signal.md` (and `.opencode/commands/signal.md`, `.hermes/skills/wally-commands/signal/SKILL.md`): append step "if profile bitunix, pipe to bitunix_log".
- `system/agents/morning-analyst.md` (and mirrors): add macro gate check at start.
- `system/agents/morning-analyst-ftmo.md` (and mirrors): same.
- `system/agents/trade-validator.md` (and mirrors): add macro gate as FASE 1 prerequisite.
- `system/agents/signal-validator.md` (and mirrors): add macro gate as prerequisite.
- `.claude/scripts/test_pdf_helpers.py`: append 2 sanity tests.
- `.claude/scripts/requirements-helpers.txt`: add `requests` if not present (likely already), `beautifulsoup4` for FF scraping.
- `CLAUDE.md`: add brief reference to new commands and macro gate behavior.

### New launchd jobs
- `com.wally.macro-calendar` — daily 04:00 CR.
- `com.wally.weekly-digest` — Sunday 18:00 CR.

### New slash commands
- `/log-outcome <symbol> <outcome> <exit_price> [--pnl <usd>] [--id <n>]`

## Dependencies Between Features

- **#8 reads #7 cache** (soft dependency). Weekly digest works without macro cache, just renders a fallback message.
- **#3 hooks into existing `/signal` skill** (modification, not new). Risk: if `/signal` output format changes later, parser must be updated. Mitigated by the `bitunix_log_errors.log` warning path.
- **All three are otherwise independent.** Implementation order can be parallel; recommended sequential for testability is #7 → #3 → #8 (because #8 references #7's CLI).

## Open Questions / Risks

| Risk | Mitigation |
|---|---|
| TradingEconomics guest tier rate-limit | 24h cache; we hit the API once/day. Far below any plausible limit. |
| Forex Factory HTML markup changes | Only used as fallback. If both fail, system falls back to "stale cache" mode with warning. Tests are against fixed fixtures, so we'd notice in production not in CI. |
| `/signal` skill output format drift | Parser uses anchored regex on stable section headers. If skill is rewritten, parser tests will fail in CI before merge. |
| macOS notification permissions | First run will prompt user for permission once. Documented in spec acceptance steps. |
| User forgets to run `/log-outcome` | Acceptable: `/journal bitunix` (future) flags entries with no outcome older than N days. Not in this spec. |
| Cache file conflicts in multi-terminal session | Atomic writes (tmp file + rename) for both `macro_events.json` and the digest output prevent partial reads. |

## Acceptance Criteria

1. **AC1 — Macro gate blocks correctly.** With a cache containing an event at "today 13:00 CR" and clock at 12:45, running `bash .claude/scripts/macro_gate.py --check-now` returns `{blocked: true, ...}`. With clock at 12:29 (31 min before), returns `{blocked: false, ...}`.
2. **AC2 — Macro fetcher hybrid works.** `bash .claude/scripts/macro_calendar.py` populates `.claude/cache/macro_events.json` with at least 5 events for the current week. Cache JSON includes `source: "tradingeconomics"` or `source: "forexfactory"`.
3. **AC3 — Trade-validator integrates.** When invoked during a macro window, the trade-validator returns `NO-GO: macro event window` without evaluating the 4 filters.
4. **AC4 — Bitunix auto-log.** In a `bitunix` profile session, running `/signal BTCUSDT LONG entry=67000 sl=66500 tp=68000` adds one structured entry to `.claude/profiles/bitunix/memory/signals_received.md` and one row to `.csv` with all 24 schema fields populated.
5. **AC5 — `/log-outcome` closes entries.** After AC4, running `/log-outcome BTCUSDT TP1 68000` updates the markdown entry's outcome section and the CSV row.
6. **AC6 — Weekly digest generates.** Running `bash .claude/scripts/weekly_digest.py --week current --no-notif` writes `memory/weekly_digests/YYYY-Wnn.md` with cross-profile table, macro lookahead section, and disciplina checks.
7. **AC7 — launchd jobs trigger.** `launchctl load ~/Library/LaunchAgents/com.wally.macro-calendar.plist` (or whatever installation path the project uses) and `com.wally.weekly-digest.plist` succeed and appear in `launchctl list`. Manually invoking each `launchctl start <label>` produces expected output.

## Success Metrics (post-deployment)

- 0 trades executed during a macro ±30 min window in the next 30 days (verifiable via cross-referencing trading_log timestamps with macro cache history).
- ≥10 Bitunix signals logged with completed outcomes in the next 30 days.
- 4 weekly digests generated (4 Sundays) with no errors logged in `.claude/cache/macro_calendar_errors.log` or `bitunix_log_errors.log`.
- macOS notification confirmed firing on first Sunday post-install.

## Implementation Order Recommendation

Sequential, but tasks within each feature can parallelize. The writing-plans skill will produce a detailed plan; this is the suggested sequence:

1. **#7 Macro Gate** first. It is consumed by #8, has the highest defensive value, and unblocks the rest.
2. **#3 Bitunix Log** second. Independent from #7, low coupling. Can be done in parallel by another worker if available.
3. **#8 Weekly Digest** last. Consumes #7 cache and reads cross-profile data that is now stable.
