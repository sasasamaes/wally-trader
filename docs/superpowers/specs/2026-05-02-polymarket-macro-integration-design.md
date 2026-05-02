# Polymarket Macro Sentiment Integration — Design

**Date:** 2026-05-02
**Status:** Approved (pending implementation plan)
**Owner:** Francisco Campos
**Goals:**
- (B) Use Polymarket macro market probabilities as an external sentiment signal that informs BTC trading bias.
- (D) Build a research pipeline to validate that the signal has measurable edge before relying on it.

## 1. Context

The Wally Trader system uses several external sentiment inputs (F&G index, OKX funding, Reddit VADER, news RSS, Binance L/S ratios). It does not currently consume **prediction-market data**. Polymarket aggregates capital-weighted opinions on macro events (Fed policy, recession, tariffs, regulation) — events that historically drive BTC price action via DXY, risk-on/off rotation, and policy expectations.

The integration is purely **read-only**. We are not trading on Polymarket. We are using its prices as a leading indicator for our own BTC entries.

## 2. Scope

### In scope (V1)
- Read-only data ingestion from Polymarket Gamma API (with CLOB fallback).
- Auto-discovery of relevant macro markets by tag and volume threshold.
- Hourly intra-day polling, persisted as append-only JSONL snapshots.
- Composite macro→BTC bias score in range −100…+100.
- Skill `polymarket-macro` (auto-invokable by agents) + manual `/polymarket` command.
- Research pipeline with 4 hypothesis tests, exposed via `/polymarket-research`.
- Outcome capture for resolved markets (Brier-score calibration).

### Out of scope (V1, YAGNI)
- Trading on Polymarket (no wallet, no API key, no execution path).
- Multi-asset bias output (only BTC in V1; ETH/forex deferred).
- Multi-outcome (non-binary) markets.
- Polymarket subgraph integration for retrospective backtest from the start (interface stub only).
- Push notifications when markets move >X (deferred until value is proven).
- TradingView alerts with Polymarket data.

## 3. Architecture

### Component layout
```
.claude/scripts/polymarket/
├── client.py           # HTTP client (httpx) for Gamma + CLOB fallback. No business logic.
├── discovery.py        # Selects markets to track. Filters by tags + volume threshold.
├── poller.py           # Hourly job. Loads tracked_markets, calls client, appends snapshots.
├── analyzer.py         # Stateless. Reads snapshots.jsonl, returns deltas + composite score.
├── config.py           # Static config: tags whitelist, market→weight mapping, thresholds.
├── research/
│   ├── __init__.py
│   ├── hypotheses.py   # H1–H4, each a pure function over snapshots + BTC OHLCV.
│   ├── data_loader.py  # Joins snapshots.jsonl with BTC OHLCV from scripts/ml_system/data/.
│   └── report.py       # Renders markdown research report.
└── data/
    ├── snapshots.jsonl       # Append-only history, ~50 KB/month.
    ├── tracked_markets.json  # Active whitelist, regenerated daily by discovery.py.
    ├── resolutions.jsonl     # Outcome captures for resolved markets.
    └── README.md

.claude/skills/polymarket-macro/SKILL.md          # Auto-invokable skill (agents read it).
.claude/commands/polymarket.md                    # /polymarket command (manual).
.claude/commands/polymarket-research.md           # /polymarket-research command (manual).
.claude/launchd/com.wally.polymarket-poller.plist     # Hourly poller agent.
.claude/launchd/com.wally.polymarket-discovery.plist  # Daily 04:00 CR discovery agent.

tests/polymarket/
├── test_client.py
├── test_discovery.py
├── test_analyzer.py
├── test_research.py
└── fixtures/
    ├── gamma_response_sample.json
    └── snapshots_sample.jsonl
```

### Boundary rules
- `client.py` knows only HTTP. It does not decide which markets to fetch.
- `discovery.py` knows only filtering rules. It does not call `client.py` directly except through a thin adapter.
- `analyzer.py` is stateless. It reads JSONL and emits a structured result. No HTTP, no globals.
- `poller.py` and `discovery.py` are the only modules that write to disk.
- `research/` is read-only over `data/snapshots.jsonl` and BTC OHLCV.

## 4. Data flow

### Discovery (1×/day, CR 04:00 via launchd)
1. `GET /markets?active=true&closed=false&tag=politics|economics|fed|crypto&limit=200`
2. Filter: `volume_24h ≥ $500k AND end_date > now + 7d`.
3. Rank by `abs(probability_yes − 0.5)` descending → markets closer to 50/50 carry more informational content.
4. Take top 12. Write to `tracked_markets.json` (atomic write: temp file + rename).
5. If discovery returns 0 markets, do NOT overwrite the previous file. Log warn.

### Polling (hourly via launchd)
1. Load `tracked_markets.json`.
2. For each market, call `client.get_market(condition_id)`.
3. Extract: `prob_yes`, `volume_24h`, `last_trade_price`, `timestamp`.
4. Append one line per market to `snapshots.jsonl`:
   ```json
   {"ts":"2026-05-02T13:00:00Z","id":"0x...","slug":"fed-cut-may-2026","prob":0.62,"vol_24h":2400000,"last_trade":0.62}
   ```
   Field `last_trade` is the most recent CLOB trade price; on a thin orderbook it can diverge from `prob_yes` (which is the midpoint of best bid/ask). Both are persisted so analyzer can prefer the more reliable signal per market.
5. On error: retry 2× with backoff (1s, 2s); on second failure fall back to CLOB; on CLOB failure log warn and skip the cycle. Never write a partial or empty snapshot.

### Analysis (on-demand, called by skill / command)
1. Read tail of `snapshots.jsonl` for last 7 days.
2. For each tracked market, compute:
   - `prob_now`
   - `delta_1h`, `delta_24h`, `delta_7d` (in percentage points)
   - `flag_moving`: `abs(delta_24h) > 0.10`
3. Compute composite score (see §5).
4. Return structured result.

## 5. Composite score

The composite measures deviation from a coin-flip baseline, so a market sitting at exactly 50% contributes zero regardless of its weight sign.

```
weighted_sum  = Σ ((prob_yes[m] − 0.5) * weight[m])   for m in markets with mapped weight
total_weight  = Σ |weight[m]|                          for the same set
composite     = (weighted_sum / total_weight) * 200    if total_weight else null
                  # ×200 because (p−0.5) ranges over [−0.5, +0.5], scaling to [−100, +100]

bucket = {
  composite >  +40 → STRONG-BULL,
  +15..+40         → MILD-BULL,
  -15..+15         → NEUTRAL,
  -40..-15         → MILD-BEAR,
  composite <  -40 → STRONG-BEAR,
}
```

Worked example with the initial weights and probabilities `{fed-cut: 0.62, recession: 0.28, tariffs: 0.41, stablecoin-pass: 0.10, debt-ceiling: 0.18, etf: 0.55}`:
- `weighted_sum = (0.12)(+0.30) + (−0.22)(−0.25) + (−0.09)(−0.20) + (−0.40)(+0.20) + (−0.32)(−0.15) + (0.05)(+0.10)`
- `= 0.036 + 0.055 + 0.018 − 0.080 + 0.048 + 0.005 = +0.082`
- `total_weight = 0.30+0.25+0.20+0.20+0.15+0.10 = 1.20`
- `composite = (0.082 / 1.20) × 200 = +13.7` → **MILD-BULL**

### Initial market→weight mapping (in `config.py`)

Patterns are evaluated as **case-insensitive substrings of the market slug** (not regex, not glob). The first pattern that matches wins; ordering in the config dict matters. A market matching no pattern is tracked but excluded from the composite.

| Pattern (substring of slug) | Weight |
|---|---|
| `fed-cut`, `fed-rate-cut` | +0.30 |
| `us-recession`, `recession-2026` | −0.25 |
| `trump-tariffs`, `tariff-trigger` | −0.20 |
| `stablecoin-pass`, `crypto-regulation-pass` | +0.20 |
| `debt-ceiling-crisis` | −0.15 |
| `btc-etf-net-inflows` | +0.10 |

Markets discovered but not matching any pattern are tracked but excluded from the composite. Weights are revised after each `/polymarket-research` cycle based on observed information coefficients.

## 6. Skill and command output

### Skill `polymarket-macro` (consumed by agents like morning-analyst, signal-validator)

Returns markdown structured for LLM parsing:

```markdown
## Polymarket Macro Sentiment — 2026-05-02 13:00 CR

**Composite BTC bias:** +12 (range -100..+100, neutral 0)
**Status:** FRESH (last poll 18min ago) | tracked 11 markets | regime MILD-BULL

### Markets relevantes ahora (ordenados por |delta_24h|)
| Market | Prob now | Δ24h | Δ7d | Vol 24h | Contribution |
|---|---|---|---|---|---|
| Fed cut May 2026 FOMC | 62% | +8pp | +14pp | $2.4M | +0.19 (BULL) |
| US recession 2026 | 28% | -5pp | -3pp | $890k | +0.18 (BULL) |
| ...

**Contribution column** = `(prob_yes − 0.5) × weight` for that market — the live impact of this market on the composite, signed so positive = bullish for BTC. Raw weights live in §5; a market at exactly 50% contributes zero.

### Catalysts próximos 7d
- FOMC May 6-7 → market "Fed cut May" resuelve esa semana

### Flags
- ⚠️ Fed-cut +14pp en 7d → DXY pressure bajista, sesgo LONG BTC favorecido
- ✅ Recession odds bajando → risk-on alineado
```

### Command `/polymarket` (manual, prepended quick summary)

```
🟢 PM Macro Bias: +12 (MILD-BULL) | 11 markets | last poll 18min ago
⚠️ Fed-cut +14pp en 7d → DXY bajista esperado
✅ Recession odds -3pp → risk-on
[full table below]
```

Optional args:
- `/polymarket` — full report
- `/polymarket fed` — filter by tag
- `/polymarket movers` — only `|delta_24h| > 5pp`
- `/polymarket history <slug>` — 7-day ASCII timeline of one market

## 7. Hard rules for the signal

1. The Polymarket bias **never converts a NO-GO technical setup into a GO**. It is a 5th filter (parallel to ML score), not a gate.
2. An extreme PM bias (`|composite| > 40`) that contradicts the 4 mandatory technical filters can **reduce position size by 25%**. It cannot increase size.
3. If `STATUS: STALE` (no fresh snapshot in last 2h), the skill returns "PM macro no disponible esta sesión" and agents must ignore the signal.
4. The signal is **profile-agnostic**. It applies equally to every profile that trades BTC or macro-correlated assets. There is no per-profile duplication.

## 8. Research pipeline

### Hypotheses

| ID | Question | Success metric |
|---|---|---|
| H1 | Does composite predict BTC return at +4h / +24h? | `corr(composite_t, BTC_return_{t+Δ}) ≠ 0`, p<0.05 |
| H2 | Does a >5pp 24h spike on a single market predict BTC volatility? | `E[\|BTC_return_{t+24h}\|]` post-spike > baseline |
| H3 | Is the edge concentrated **before** event resolution? | Correlation strongest in window `[t−2d, t−0]`; weak post-event |
| H4 | Per-market information coefficient (which markets carry edge, which are noise) | IC + Sharpe attribution per market |

### Command

```
/polymarket-research                 # all 4 hypotheses with current data
/polymarket-research H1              # single hypothesis
/polymarket-research H4 --min-snapshots 200
```

Output: `docs/polymarket_research/YYYY-MM-DD-report.md`. The report includes sample sizes per hypothesis and an explicit caveat when N<200.

### Cadence

- **Not automated.** The research report is run by the user every 30–60 days, or whenever a market resolves.
- After each report the user (with assistant) updates `config.py` weights based on observed IC, dropping markets whose IC sits in [-0.05, +0.05] across two consecutive reports.

### Realism caveat

30–60 days does not yield statistical significance. The first report is **directional only**. The system's value compounds at ~6 months, when ICs begin to stabilize. The accumulated `snapshots.jsonl` is a private dataset whose value exceeds the code's.

## 9. Resolutions and calibration

When a market closes, `discovery.py` detects the transition (`closed=true`) and records the outcome in `resolutions.jsonl`:

```json
{"slug":"fed-cut-may-2026","resolved_ts":"...","outcome":"YES","final_prob_pre_resolution":0.62}
```

Calibration metric: Brier score over all resolved markets. If Polymarket is systematically miscalibrated on a class of markets (e.g., consistently over-priced tail risk), that is itself an exploitable signal — fed back into the weight mapping.

## 10. Error handling

| Scenario | Behavior |
|---|---|
| Gamma API 5xx / timeout | Retry 2× with backoff (1s, 2s) |
| Gamma definitively down | Fallback to CLOB endpoint |
| Both APIs down | Log warn, skip cycle. No partial write. |
| Discovery returns 0 markets, previous file exists | Keep previous `tracked_markets.json`. Log warn. |
| Discovery returns 0 markets, first run (no previous file) | Write empty `{"markets": [], "generated_at": "..."}`. Skill returns `STATUS: NO_MARKETS`. |
| `snapshots.jsonl` line malformed | Analyzer skips line, logs warn, continues |
| Last snapshot >2h old | Skill returns `STATUS: STALE`. Agents ignore. |
| Composite undefined (no mapped markets) | Returns `null`. Skill shows "PM no disponible". |
| BTC OHLCV missing | Research H1–H3 marked N/A; H4 still runs (no BTC join needed). |

## 11. Testing

- All HTTP is mocked. Tests do not call Polymarket API.
- `test_client.py` — fixture-driven parsing tests (Gamma response shape, CLOB fallback).
- `test_discovery.py` — synthetic market list, verifies tag filter + volume threshold + ranking.
- `test_analyzer.py` — synthetic JSONL, verifies deltas and composite math against hand-computed expected values.
- `test_research.py` — synthetic snapshot/OHLCV pairs where the answer to each hypothesis is known.
- Smoke test (manual, post-install):
  ```bash
  python3 .claude/scripts/polymarket/discovery.py --dry-run
  python3 .claude/scripts/polymarket/poller.py --once
  python3 .claude/scripts/polymarket/analyzer.py --json
  ```
- Integrated into existing pytest suite (referenced from CHANGELOG: "tier-1 hardening — pytest suite").

## 12. Operations

### launchd jobs
- `com.wally.polymarket-poller.plist` — runs `poller.py` every 3600s.
- `com.wally.polymarket-discovery.plist` — runs `discovery.py` daily at 04:00 CR (before the morning protocol at 06:00).
- Logs: `~/Library/Logs/wally-trader/polymarket-{poller,discovery}.log`, rotated 7 days.

### Secrets
None. The Gamma API and CLOB API are public read-only. No keys to manage.

### Install
```bash
mkdir -p .claude/scripts/polymarket/data
pip install httpx pytest-asyncio
python3 .claude/scripts/polymarket/discovery.py     # initial bootstrap
python3 .claude/scripts/polymarket/poller.py --once # first manual snapshot
launchctl load ~/Library/LaunchAgents/com.wally.polymarket-poller.plist
launchctl load ~/Library/LaunchAgents/com.wally.polymarket-discovery.plist
/polymarket   # verification
```

### Maintenance
- Steady-state: zero touch.
- Every 30–60 days: run `/polymarket-research`, update `config.py` weights.
- When a market resolves: discovery rotates automatically.
- If Polymarket changes API: only `client.py` is affected.

## 13. Defaults

- Poller cadence: **1h**.
- Discovery cadence: **1 day** at CR 04:00.
- Volume threshold: **$500k notional 24h**.
- Tags whitelist: `["politics", "economics", "fed", "crypto"]`.
- Top-N tracked markets: **12**.
- Snapshot retention: **indefinite** (text JSONL, ~50 KB/month).
- Research report cadence: **manual**, recommended every 30–60 days.

## 14. Acceptance criteria

The implementation is considered complete when:

1. `discovery.py --dry-run` prints ≥3 valid markets matching the filter rules.
2. `poller.py --once` writes at least one well-formed line to `snapshots.jsonl` for every tracked market.
3. `analyzer.py --json` returns a composite score and per-market deltas for the current snapshot.
4. `/polymarket` command renders the markdown report with FRESH status and at least 3 markets.
5. `/polymarket-research H4` runs end-to-end on synthetic test data and emits a markdown report with per-market IC.
6. All four pytest test files pass with mocked HTTP.
7. The skill `polymarket-macro` is invoked successfully by the `morning-analyst` agent during a dry-run morning, and its output appears in the morning report under a new "PM Macro" subsection (without breaking the existing 17 phases).
8. A `STATUS: STALE` simulation (touch snapshots back 3h) makes both skill and command return the stale message and agents do not crash.

## 15. References

- Polymarket Gamma API docs: `https://docs.polymarket.com/`
- CLOB endpoint: `https://clob.polymarket.com`
- Existing project conventions (CLAUDE.md): risk 2%, profile awareness, sentiment as 5th filter.
- ML system precedent (XGBoost score) — same hard-rule pattern: never converts NO-GO into GO.
