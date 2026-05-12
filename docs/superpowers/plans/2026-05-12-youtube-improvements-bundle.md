# YouTube Improvements Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement six improvements distilled from four Alex Ruiz YouTube videos (per design `docs/superpowers/specs/2026-05-12-youtube-improvements-bundle-design.md`): docs update for retail-bingx, fib retracement-zones extension, dynamic min-R:R gate, three-months-positive challenge readiness, standalone Pullback detector, and Asian Range secondary strategy for fotmarkets.

**Architecture:** Each improvement is a small helper script (or extension of an existing one) plus a wire-in to one or more agents/slash commands. No new agents. No router changes (standalone-first). Tests use synthetic OHLCV fixtures; no live data dependence in unit tests.

**Tech Stack:** Python 3 stdlib + existing `.claude/scripts/.venv` deps (`requests`, `pandas`, `numpy`) + pytest from `shared/wally_core` for the shared test runner. Markdown for docs and slash commands.

---

## File Structure

| Path | Action | Feature |
|---|---|---|
| `.claude/profiles/retail-bingx/config.md` | Modify | G |
| `.claude/scripts/fib_extension.py` | Modify (add `retracement` mode) | C |
| `.claude/scripts/tests/test_fib_extension.py` | Modify (new tests) | C |
| `.claude/scripts/min_rr_gate.py` | Create | B |
| `.claude/scripts/tests/test_min_rr_gate.py` | Create | B |
| `.claude/agents/trade-validator.md` | Modify (FASE 0.9) | B |
| `.claude/agents/signal-validator.md` | Modify (Min-R:R block) | B |
| `.claude/scripts/challenge_readiness.py` | Create | F |
| `.claude/scripts/tests/test_challenge_readiness.py` | Create | F |
| `.claude/commands/challenge.md` | Modify (readiness banner) | F |
| `.claude/scripts/pullback_detector.py` | Create | A |
| `.claude/scripts/tests/test_pullback_detector.py` | Create | A |
| `.claude/commands/pullback.md` | Create | A |
| `.claude/scripts/asian_range.py` | Create | E |
| `.claude/scripts/tests/test_asian_range.py` | Create | E |
| `.claude/commands/asian-range.md` | Create | E |
| `.claude/profiles/fotmarkets/strategy_asian_range.md` | Create | E |
| `CLAUDE.md` | Modify (document bundle) | All |

**Implementation order (one commit per feature):** G → C → B → F → A → E → docs.

---

## Task 1 (Feature G): Document Operational Costs in retail-bingx

**Files:**
- Modify: `.claude/profiles/retail-bingx/config.md`

- [ ] **Step 1: Read the current config**

Run: `cat .claude/profiles/retail-bingx/config.md`

This loads the file into your context so you can pick the right anchor for the new section. Look for an existing heading near "capital", "leverage", or the bottom of the file. The new section goes at the end if no obvious anchor exists.

- [ ] **Step 2: Append the Cost Reality section**

Use the Edit tool to append the following block to `.claude/profiles/retail-bingx/config.md`. If a heading anchor exists near the end (e.g. "## Notes" or "## Filosofía"), insert before it. Otherwise append at end.

```markdown

## Cost Reality (added 2026-05-12)

Capital $0.93 + BingX taker fee 0.05% + leverage 10× makes real execution non-viable:

| Metric | Value |
|---|---|
| Capital | $0.93 |
| Size at 2% risk | $0.0186 margin |
| Notional at 10× | $0.186 |
| Taker fee/side | 0.05% |
| Round-trip cost | $0.0002 (0.02% of capital) |

Cost as % of capital is negligible *in absolute terms*, but:
- **Minimum tick size** on BTCUSDT.P (BingX) is $0.10, larger than the price move that
  $0.0002 fee implies — so any single tick of adverse slippage equals multiple round-trips.
- **Funding** at 0.01% per 8h on $0.186 notional = $0.0000186/cycle — tiny, but on a runner
  held overnight (regulation violation per CLAUDE.md anyway) it stacks.
- **Practical minimum** order size on BingX perp can exceed what a $0.93 account permits at
  10×, forcing oversize or no-fill.

**Operating rule:** `retail-bingx` is a **pedagogical / observation-only** profile. Use it
for replay analysis, signal validation rehearsal, and journal-entry practice — do not
execute real fills. Inherited from the three historical wins ($10 → $13.63) preserved in
`memory/trading_log.md`, the profile retains learning value without continued execution
exposure.
```

- [ ] **Step 3: Verify the file still parses cleanly**

Run: `head -100 .claude/profiles/retail-bingx/config.md && echo "---tail---" && tail -40 .claude/profiles/retail-bingx/config.md`

Expected: no broken markdown, the new section is at a sensible location.

- [ ] **Step 4: Commit**

```bash
git add .claude/profiles/retail-bingx/config.md
git commit -m "$(cat <<'EOF'
docs(retail-bingx): document round-trip cost reality ($0.93 = pedagogical)

Tick size and minimum order size on BingX perp make real execution non-viable
at $0.93 capital even though fees are proportionally tiny. Codify the profile
as observation-only.

Source: design doc 2026-05-12 YouTube bundle, feature G (V3 insight).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2 (Feature C): Fib Retracement Zones in fib_extension.py

**Files:**
- Modify: `.claude/scripts/fib_extension.py`
- Modify: `.claude/scripts/tests/test_fib_extension.py`

- [ ] **Step 1: Read the current fib_extension.py**

Run: `cat .claude/scripts/fib_extension.py`

Identify the current `main()` argparse and the `--mode` (if any) — the spec says `--mode retracement` should be an addition. The existing default behaviour (extension) must remain untouched.

- [ ] **Step 2: Read existing fib_extension tests**

Run: `cat .claude/scripts/tests/test_fib_extension.py`

You will be adding two new tests next to the existing pattern.

- [ ] **Step 3: Write the failing tests for retracement mode**

Use the Edit tool to add the following two tests to `.claude/scripts/tests/test_fib_extension.py` (append at end before any `__main__` block, or just append):

```python
def test_retracement_explicit_swing_levels():
    """Given an explicit swing high/low, all 5 retracement levels are correct."""
    from fib_extension import retracement_zones

    out = retracement_zones(swing_low=73500.0, swing_high=78285.0, direction="long")

    rng = 78285.0 - 73500.0
    assert abs(out["entry_zones"]["382"] - (78285.0 - rng * 0.382)) < 1e-6
    assert abs(out["entry_zones"]["500"] - (78285.0 - rng * 0.500)) < 1e-6
    assert abs(out["entry_zones"]["618"] - (78285.0 - rng * 0.618)) < 1e-6
    assert abs(out["sl_075"] - (78285.0 - rng * 0.75)) < 1e-6
    assert out["tp_swing"] == 78285.0
    assert out["direction"] == "long"


def test_retracement_direction_autodetect():
    """A bar series ending above the midpoint of the recent swing infers LONG bias."""
    from fib_extension import autodetect_direction

    # 10 synthetic closes forming a swing low at 100, swing high at 200, ending at 175 (above mid)
    closes = [100, 110, 130, 160, 190, 200, 195, 185, 178, 175]
    assert autodetect_direction(closes) == "long"

    # ending at 125 (below mid 150) → short
    closes_short = [200, 190, 170, 150, 130, 110, 100, 105, 115, 125]
    assert autodetect_direction(closes_short) == "short"
```

- [ ] **Step 4: Run the new tests, expect failure**

Run: `cd .claude/scripts && .venv/bin/python -m pytest tests/test_fib_extension.py -k "retracement" -v`

Expected: 2 failures with `ImportError` or `AttributeError` because `retracement_zones` and `autodetect_direction` do not exist yet.

- [ ] **Step 5: Implement retracement_zones in fib_extension.py**

Add the following two functions to `.claude/scripts/fib_extension.py`. Place them after the existing `classify_label` (or after the last top-level function before `main()`):

```python
RETRACEMENT_RATIOS = [0.382, 0.500, 0.618, 0.750]


def retracement_zones(
    *, swing_low: float, swing_high: float, direction: str
) -> dict:
    """Compute fib retracement entry zones from a swing.

    For LONG bias: entries are progressive retracements down from swing_high.
    For SHORT bias: entries are progressive retracements up from swing_low.
    SL at 0.75 retracement; TP at the opposite swing extreme.
    """
    if swing_high <= swing_low:
        raise ValueError("swing_high must exceed swing_low")
    if direction not in ("long", "short"):
        raise ValueError("direction must be 'long' or 'short'")

    rng = swing_high - swing_low

    if direction == "long":
        anchor = swing_high
        sign = -1
        tp = swing_high
    else:
        anchor = swing_low
        sign = +1
        tp = swing_low

    entry_zones = {
        f"{int(round(r * 1000))}".zfill(3): round(anchor + sign * rng * r, 4)
        for r in (0.382, 0.500, 0.618)
    }
    sl = round(anchor + sign * rng * 0.75, 4)

    return {
        "direction": direction,
        "swing_high": round(swing_high, 4),
        "swing_low": round(swing_low, 4),
        "entry_zones": entry_zones,
        "sl_075": sl,
        "tp_swing": round(tp, 4),
    }


def autodetect_direction(closes: list[float]) -> str:
    """Direction from a closes series: LONG if last close > midpoint of (max, min)."""
    if not closes:
        raise ValueError("closes must not be empty")
    hi = max(closes)
    lo = min(closes)
    mid = (hi + lo) / 2
    return "long" if closes[-1] >= mid else "short"
```

- [ ] **Step 6: Run the new tests, expect pass**

Run: `cd .claude/scripts && .venv/bin/python -m pytest tests/test_fib_extension.py -k "retracement" -v`

Expected: 2 passed.

- [ ] **Step 7: Wire `--mode retracement` into the CLI**

Modify the `main()` function in `.claude/scripts/fib_extension.py`. Add `--mode` to argparse (default `extension`) and branch on it. The retracement branch needs to fetch recent closes and call `autodetect_direction` + compute swing high/low from those closes (use the last N=60 bars, configurable via existing `--bars` if it already exists, otherwise add `--bars 60` default).

Sketch (adapt to actual existing code):

```python
p.add_argument("--mode", choices=["extension", "retracement"], default="extension")
# ... existing args ...

args = p.parse_args()

if args.mode == "retracement":
    closes = _fetch_closes(args.symbol, args.tf, args.bars)  # reuse existing fetch path
    direction = autodetect_direction(closes)
    out = retracement_zones(
        swing_low=min(closes),
        swing_high=max(closes),
        direction=direction,
    )
    if args.json:
        print(json.dumps(out))
    else:
        print(f"{args.symbol} {args.tf} retracement {direction.upper()}")
        for level, price in out["entry_zones"].items():
            print(f"  fib {int(level)/1000:.3f}: {price}")
        print(f"  SL  fib 0.750: {out['sl_075']}")
        print(f"  TP  swing:    {out['tp_swing']}")
    sys.exit(0)

# ... existing extension flow continues unchanged ...
```

If `_fetch_closes` doesn't exist, look at how the existing extension mode pulls bars and reuse the same call.

- [ ] **Step 8: Manual smoke test of CLI**

Run: `cd .claude/scripts && .venv/bin/python fib_extension.py --symbol BTCUSDT --tf 1h --mode retracement --bars 60`

Expected: prints 5 levels and a direction label. If the fetch fails offline, do not block — proceed to step 9 (tests already pass on synthetic data).

- [ ] **Step 9: Run the full fib_extension test file**

Run: `cd .claude/scripts && .venv/bin/python -m pytest tests/test_fib_extension.py -v`

Expected: all tests pass (existing + 2 new).

- [ ] **Step 10: Commit**

```bash
git add .claude/scripts/fib_extension.py .claude/scripts/tests/test_fib_extension.py
git commit -m "$(cat <<'EOF'
feat(fib_extension): add retracement mode with entry zones

New --mode retracement returns fib 0.382/0.500/0.618 entry zones plus SL at
0.75 and TP at swing extreme. Direction auto-detects from closes mid-point.
Used by upcoming Pullback detector; standalone-callable for /punk-watch.

Source: design doc 2026-05-12 YouTube bundle, feature C (V1 insight).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3 (Feature B): Dynamic Min-R:R Gate

**Files:**
- Create: `.claude/scripts/min_rr_gate.py`
- Create: `.claude/scripts/tests/test_min_rr_gate.py`
- Modify: `.claude/agents/trade-validator.md`
- Modify: `.claude/agents/signal-validator.md`

- [ ] **Step 1: Write the failing tests**

Create `.claude/scripts/tests/test_min_rr_gate.py` with:

```python
"""Tests for min_rr_gate.py — dynamic min-R:R gate based on rolling WR."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from min_rr_gate import compute_min_rr, evaluate


def test_happy_path_high_wr_passes():
    """WR 0.55, setup R:R 1.5 → OK (min_rr = (1-0.55)/0.55 * 1.2 ≈ 0.98)."""
    out = evaluate(wr=0.55, setup_rr=1.5, sample_size=30)
    assert out["status"] == "OK"
    assert out["min_rr"] < 1.5
    assert "INSUFFICIENT_DATA" not in out.get("flags", [])


def test_warn_path_low_wr_demands_high_rr():
    """WR 0.40, setup R:R 1.2 → WARN (min_rr = 0.6/0.4 * 1.2 = 1.8)."""
    out = evaluate(wr=0.40, setup_rr=1.2, sample_size=30)
    assert out["status"] == "WARN"
    assert out["min_rr"] > 1.2


def test_insufficient_data_falls_back_to_15():
    """Fewer than 10 trades → fallback min_rr = 1.5 with INSUFFICIENT_DATA flag."""
    out = evaluate(wr=0.55, setup_rr=2.0, sample_size=5)
    assert out["status"] == "OK"
    assert out["min_rr"] == 1.5
    assert "INSUFFICIENT_DATA" in out["flags"]


def test_boundary_exact_min_rr_is_ok():
    """Setup R:R exactly equal to min_rr → OK (>=, not >)."""
    min_rr = compute_min_rr(wr=0.50)  # = 0.5/0.5 * 1.2 = 1.2
    out = evaluate(wr=0.50, setup_rr=min_rr, sample_size=20)
    assert out["status"] == "OK"


def test_wr_clamped_at_bounds():
    """WR clamped to [0.20, 0.80] to avoid pathological outputs."""
    high_wr = compute_min_rr(wr=0.95)  # clamped to 0.80 → 0.2/0.8 * 1.2 = 0.30
    low_wr = compute_min_rr(wr=0.05)   # clamped to 0.20 → 0.8/0.2 * 1.2 = 4.80
    assert 0.29 < high_wr < 0.31
    assert 4.79 < low_wr < 4.81
```

- [ ] **Step 2: Run tests, expect import failure**

Run: `cd .claude/scripts && .venv/bin/python -m pytest tests/test_min_rr_gate.py -v`

Expected: `ModuleNotFoundError: No module named 'min_rr_gate'`.

- [ ] **Step 3: Implement min_rr_gate.py**

Create `.claude/scripts/min_rr_gate.py`:

```python
#!/usr/bin/env python3
"""min_rr_gate.py — Dynamic minimum-R:R gate based on rolling WR.

Formula: min_rr = ((1 - wr) / wr) * 1.2
- wr is clamped to [0.20, 0.80] to avoid pathological outputs.
- sample_size < 10 trades → fallback min_rr = 1.5 with INSUFFICIENT_DATA flag.

Usage:
    python3 min_rr_gate.py --wr 0.55 --setup-rr 1.5 --sample-size 30
    python3 min_rr_gate.py --profile retail --setup-rr 1.5

Exit codes: 0=OK 2=WARN.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

WR_CLAMP_MIN = 0.20
WR_CLAMP_MAX = 0.80
RR_BUFFER = 1.2
MIN_SAMPLE = 10
FALLBACK_MIN_RR = 1.5

SCRIPTS_DIR = Path(__file__).resolve().parent


def compute_min_rr(*, wr: float) -> float:
    """Dynamic min-R:R from WR. WR is decimal (0-1)."""
    wr_clamped = max(WR_CLAMP_MIN, min(WR_CLAMP_MAX, wr))
    return round((1.0 - wr_clamped) / wr_clamped * RR_BUFFER, 4)


def evaluate(*, wr: float, setup_rr: float, sample_size: int) -> dict:
    flags: list[str] = []
    if sample_size < MIN_SAMPLE:
        min_rr = FALLBACK_MIN_RR
        flags.append("INSUFFICIENT_DATA")
    else:
        min_rr = compute_min_rr(wr=wr)

    status = "OK" if setup_rr >= min_rr else "WARN"
    return {
        "wr": round(wr, 4),
        "sample_size": sample_size,
        "min_rr": min_rr,
        "setup_rr": round(setup_rr, 4),
        "status": status,
        "flags": flags,
    }


def fetch_wr_for_profile(profile: str) -> tuple[float, int]:
    """Call journal_metrics.py on the profile log and return (wr_decimal, n_trades)."""
    log_path = Path(f".claude/profiles/{profile}/memory/trading_log.md")
    if not log_path.exists():
        return (0.0, 0)
    res = subprocess.run(
        [
            str(SCRIPTS_DIR / ".venv" / "bin" / "python"),
            str(SCRIPTS_DIR / "journal_metrics.py"),
            "--log",
            str(log_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        return (0.0, 0)
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return (0.0, 0)
    wr_pct = float(data.get("win_rate_pct", 0.0))
    n = int(data.get("total_trades", data.get("n_trades", 0)))
    return (wr_pct / 100.0, n)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--wr", type=float, help="rolling WR (0.0-1.0)")
    p.add_argument("--sample-size", type=int, help="number of trades in WR window")
    p.add_argument("--profile", type=str, help="profile name (auto-loads WR from log)")
    p.add_argument("--setup-rr", type=float, required=True, help="proposed setup R:R")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.profile:
        wr, sample = fetch_wr_for_profile(args.profile)
    elif args.wr is not None and args.sample_size is not None:
        wr, sample = args.wr, args.sample_size
    else:
        print("ERROR: must pass --profile OR (--wr AND --sample-size)", file=sys.stderr)
        return 3

    out = evaluate(wr=wr, setup_rr=args.setup_rr, sample_size=sample)
    if args.json:
        print(json.dumps(out))
    else:
        print(f"WR={wr:.2%} (n={sample}) → min_rr={out['min_rr']:.2f}")
        print(f"setup_rr={args.setup_rr:.2f} → {out['status']}")
        if out["flags"]:
            print(f"flags: {', '.join(out['flags'])}")
    return 0 if out["status"] == "OK" else 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests, expect pass**

Run: `cd .claude/scripts && .venv/bin/python -m pytest tests/test_min_rr_gate.py -v`

Expected: 5 passed.

- [ ] **Step 5: Wire into trade-validator agent**

Read `.claude/agents/trade-validator.md`. Locate FASE 0.7 (volume_divergence) or FASE 0.8 (whatever the highest existing pre-filter phase is). Add a new FASE 0.9 block immediately after. Use the Edit tool to insert this section in the right place:

```markdown
### FASE 0.9 — Min-R:R gate (dinámico por WR del profile)

Después de macro_gate y session_quality, antes de los 4 filtros técnicos. Calcula el
R:R mínimo adaptativo según el WR de los últimos 30 días del profile activo.

Ejecutar:
```bash
.claude/scripts/.venv/bin/python .claude/scripts/min_rr_gate.py \
  --profile <profile> --setup-rr <ratio_proyectado> --json
```

Reglas:
- `status=OK` → continuar a los 4 filtros.
- `status=WARN` → reportar al operador ("R:R 1.2 < mínimo dinámico 1.8 para WR 40%")
  y degradar a NO-GO suave (no BLOCK absoluto, pero recomienda esperar mejor setup).
- `INSUFFICIENT_DATA` flag → tratar como OK (fallback 1.5) y anotar para que el operador
  sepa que no hay suficiente historial.

Fuente: design doc 2026-05-12 YouTube bundle, feature B.
```

- [ ] **Step 6: Wire into signal-validator agent**

Read `.claude/agents/signal-validator.md`. The signal-validator already has multi-phase pipeline. Add a comparable "Min-R:R" block after macro_gate / volume_divergence checks:

```markdown
### Filtro Min-R:R (adaptativo por WR profile)

Para señales externas (Discord/Telegram/Twitter), validar el R:R contra el mínimo dinámico
del profile receptor (típicamente bitunix). Llamada idéntica a trade-validator FASE 0.9:

```bash
.claude/scripts/.venv/bin/python .claude/scripts/min_rr_gate.py \
  --profile bitunix --setup-rr <ratio_de_la_señal> --json
```

`status=WARN` → degrada el score de la señal en -10 puntos y añade flag `LOW_RR` al
reporte. No bloquea — el operador decide.

Fuente: design doc 2026-05-12 YouTube bundle, feature B.
```

- [ ] **Step 7: Verify ruff is clean on new file**

Run: `cd .claude/scripts && .venv/bin/python -m ruff check min_rr_gate.py tests/test_min_rr_gate.py || true`

If ruff isn't installed in the venv, skip. Otherwise fix any reported issues before committing.

- [ ] **Step 8: Commit**

```bash
git add .claude/scripts/min_rr_gate.py \
        .claude/scripts/tests/test_min_rr_gate.py \
        .claude/agents/trade-validator.md \
        .claude/agents/signal-validator.md
git commit -m "$(cat <<'EOF'
feat(min_rr_gate): dynamic R:R floor from rolling 30d WR

New min_rr_gate.py: min_rr = ((1-wr)/wr) * 1.2 with WR clamped [0.20, 0.80] and
fallback 1.5 when sample <10. Wired into trade-validator FASE 0.9 and into
signal-validator as a soft -10 score penalty. WARN-only — never blocks.

Source: design doc 2026-05-12 YouTube bundle, feature B (V1 insight).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4 (Feature F): Three-Months-Positive Challenge Readiness

**Files:**
- Create: `.claude/scripts/challenge_readiness.py`
- Create: `.claude/scripts/tests/test_challenge_readiness.py`
- Modify: `.claude/commands/challenge.md`

- [ ] **Step 1: Write the failing tests**

Create `.claude/scripts/tests/test_challenge_readiness.py`:

```python
"""Tests for challenge_readiness.py."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from challenge_readiness import classify


def test_ready_three_consecutive_positive():
    """Three consecutive positive months → READY."""
    monthly_pnl = {"2026-02": 50.0, "2026-03": 30.0, "2026-04": 80.0}
    assert classify(monthly_pnl, today="2026-05-01")["status"] == "READY"


def test_borderline_one_positive_two_flat():
    """One positive, two flat (or one negative) in last 3 → BORDERLINE."""
    monthly_pnl = {"2026-02": -10.0, "2026-03": 5.0, "2026-04": 40.0}
    assert classify(monthly_pnl, today="2026-05-01")["status"] == "BORDERLINE"


def test_not_ready_last_month_negative():
    """Last month negative → NOT_READY regardless of earlier months."""
    monthly_pnl = {"2026-02": 50.0, "2026-03": 80.0, "2026-04": -30.0}
    assert classify(monthly_pnl, today="2026-05-01")["status"] == "NOT_READY"


def test_not_ready_no_track_record():
    """Empty input → NOT_READY with NO_DATA flag."""
    out = classify({}, today="2026-05-01")
    assert out["status"] == "NOT_READY"
    assert "NO_DATA" in out["flags"]


def test_only_last_3_months_count():
    """A profitable Jan 2025 doesn't help when 2026 has 3 negative."""
    monthly_pnl = {
        "2025-01": 500.0,
        "2026-02": -10.0,
        "2026-03": -20.0,
        "2026-04": -5.0,
    }
    assert classify(monthly_pnl, today="2026-05-01")["status"] == "NOT_READY"
```

- [ ] **Step 2: Run tests, expect import failure**

Run: `cd .claude/scripts && .venv/bin/python -m pytest tests/test_challenge_readiness.py -v`

Expected: `ModuleNotFoundError: No module named 'challenge_readiness'`.

- [ ] **Step 3: Implement challenge_readiness.py**

Create `.claude/scripts/challenge_readiness.py`:

```python
#!/usr/bin/env python3
"""challenge_readiness.py — Are you ready to buy another funded challenge?

Per Alex Ruiz V3 rule: wait until 3 consecutive positive months on your current
profile before paying for a new $99-$199 challenge.

Status:
- READY      : last 3 months all positive
- BORDERLINE : 1-2 positive in last 3 (or all flat)
- NOT_READY  : last month negative OR no track record

Usage:
    python3 challenge_readiness.py --profile retail
    python3 challenge_readiness.py --profile retail --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def _previous_n_months(today: date, n: int) -> list[str]:
    """Return ['2026-02', '2026-03', '2026-04'] for today=2026-05-15, n=3."""
    out = []
    y, m = today.year, today.month
    for _ in range(n):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
        out.append(f"{y:04d}-{m:02d}")
    return list(reversed(out))


def classify(monthly_pnl: dict[str, float], today: str | date) -> dict:
    """monthly_pnl is {"YYYY-MM": float_usd}. today is ISO date or date object."""
    if isinstance(today, str):
        today_d = datetime.strptime(today, "%Y-%m-%d").date()
    else:
        today_d = today

    flags: list[str] = []
    if not monthly_pnl:
        return {
            "status": "NOT_READY",
            "months_checked": [],
            "months_positive": 0,
            "flags": ["NO_DATA"],
        }

    last3 = _previous_n_months(today_d, 3)
    values = [monthly_pnl.get(m) for m in last3]
    positives = sum(1 for v in values if v is not None and v > 0)
    last_month = values[-1]

    if last_month is None or last_month <= 0:
        status = "NOT_READY"
    elif positives == 3:
        status = "READY"
    else:
        status = "BORDERLINE"

    if any(v is None for v in values):
        flags.append("PARTIAL_DATA")

    return {
        "status": status,
        "months_checked": last3,
        "monthly_pnl_usd": {m: monthly_pnl.get(m) for m in last3},
        "months_positive": positives,
        "flags": flags,
    }


def _parse_monthly_from_log(log_path: Path) -> dict[str, float]:
    """Sum PnL$ rows from a trading_log.md markdown table grouped by YYYY-MM."""
    if not log_path.exists():
        return {}
    text = log_path.read_text()
    monthly: dict[str, float] = {}
    row_re = re.compile(
        r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|.*?\|\s*([+\-]?\$?\d+\.?\d*)\s*\|",
        re.MULTILINE,
    )
    for match in row_re.finditer(text):
        date_str, pnl_str = match.group(1), match.group(2)
        pnl_clean = pnl_str.replace("$", "").replace("+", "")
        try:
            pnl = float(pnl_clean)
        except ValueError:
            continue
        ym = date_str[:7]
        monthly[ym] = monthly.get(ym, 0.0) + pnl
    return monthly


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--profile", required=True)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    log_path = Path(f".claude/profiles/{args.profile}/memory/trading_log.md")
    monthly = _parse_monthly_from_log(log_path)
    today = date.today().isoformat()
    out = classify(monthly, today=today)
    out["profile"] = args.profile

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Profile: {args.profile}")
        print(f"Status:  {out['status']}")
        print(f"Months checked: {out['months_checked']}")
        for m, v in out["monthly_pnl_usd"].items():
            v_str = f"${v:+.2f}" if v is not None else "—"
            print(f"  {m}: {v_str}")
        if out["flags"]:
            print(f"flags: {', '.join(out['flags'])}")

    return 0 if out["status"] == "READY" else (2 if out["status"] == "BORDERLINE" else 1)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests, expect pass**

Run: `cd .claude/scripts && .venv/bin/python -m pytest tests/test_challenge_readiness.py -v`

Expected: 5 passed.

- [ ] **Step 5: Modify /challenge slash command**

Read `.claude/commands/challenge.md`. Add a new section at the end (or where the FTMO dashboard is rendered) that calls the readiness helper. Use the Edit tool:

```markdown

## Readiness for next challenge

Antes de pagar otro challenge ($99-$199), confirma 3 meses positivos en el profile activo:

```bash
.claude/scripts/.venv/bin/python .claude/scripts/challenge_readiness.py \
  --profile $WALLY_PROFILE --json
```

Lectura del status:
- **READY** ✅ → puedes comprar el siguiente challenge con base sólida
- **BORDERLINE** ⚠️ → 1-2 meses positivos, espera al menos 1 mes más de track récord
- **NOT_READY** ❌ → mes pasado negativo o sin histórico, NO compres ahora

Fuente: design doc 2026-05-12 YouTube bundle, feature F (V3 scaling rule).
```

- [ ] **Step 6: Manual smoke test**

Run: `cd /Users/josecampos/Documents/wally-trader && .claude/scripts/.venv/bin/python .claude/scripts/challenge_readiness.py --profile fundingpips || echo "exit $?"`

Expected: prints status (likely NOT_READY since most profiles have no 3-month track), exits 0/1/2 according to status. The non-zero exit is intentional for NOT_READY.

- [ ] **Step 7: Commit**

```bash
git add .claude/scripts/challenge_readiness.py \
        .claude/scripts/tests/test_challenge_readiness.py \
        .claude/commands/challenge.md
git commit -m "$(cat <<'EOF'
feat(challenge): three-months-positive readiness gate

challenge_readiness.py reads the active profile's trading_log.md, groups
PnL by month, and classifies READY/BORDERLINE/NOT_READY based on Alex
Ruiz's scaling rule (V3). Wired into /challenge as a soft advisory banner.

Source: design doc 2026-05-12 YouTube bundle, feature F.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5 (Feature A): Pullback Detector

**Files:**
- Create: `.claude/scripts/pullback_detector.py`
- Create: `.claude/scripts/tests/test_pullback_detector.py`
- Create: `.claude/commands/pullback.md`

- [ ] **Step 1: Write the failing tests with synthetic fixtures**

Create `.claude/scripts/tests/test_pullback_detector.py`:

```python
"""Tests for pullback_detector.py — impulse → pullback → continuation pattern."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pullback_detector import (
    detect_impulse,
    detect_pullback,
    detect_continuation,
    evaluate_setup,
)


def _bar(o, h, l, c, v=1000):
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def test_impulse_detected_on_5_green_with_above_avg_atr():
    """Five green candles with ATR > rolling mean → impulse identified."""
    chop = [_bar(100, 101, 99, 100) for _ in range(20)]
    impulse = [
        _bar(100, 103, 100, 102),
        _bar(102, 106, 101, 105),
        _bar(105, 110, 104, 109),
        _bar(109, 114, 108, 113),
        _bar(113, 118, 112, 117),
    ]
    bars = chop + impulse
    result = detect_impulse(bars, min_streak=3)
    assert result is not None
    assert result["color"] == "green"
    assert result["start_idx"] == 20
    assert result["end_idx"] == 24


def test_pullback_into_fib_zone_detected():
    """After impulse, 3 red candles retracing into 0.5 fib → pullback identified."""
    impulse_end_price = 117.0
    impulse_start_price = 100.0
    bars = [_bar(117, 117, 113, 113), _bar(113, 113, 109, 109), _bar(109, 109, 108, 108.5)]
    fib_50 = impulse_end_price - (impulse_end_price - impulse_start_price) * 0.5
    pb = detect_pullback(
        bars, impulse_high=impulse_end_price, impulse_low=impulse_start_price
    )
    assert pb is not None
    assert pb["end_price"] <= fib_50 + 1


def test_continuation_after_valid_pullback():
    """First impulse-color candle after pullback closes back inside zone → signal."""
    bars = [_bar(108.5, 112, 108, 111.5)]  # green close
    cont = detect_continuation(bars, impulse_color="green")
    assert cont is not None
    assert cont["confirmed"] is True


def test_no_signal_in_chop_low_adx():
    """ADX < 25 → evaluate_setup returns None."""
    bars = [_bar(100 + i % 2, 101, 99, 100 + (i + 1) % 2) for i in range(60)]
    out = evaluate_setup(bars, adx_proxy=15.0)
    assert out is None or out["signal"] is None


def test_no_signal_when_pullback_breaks_fib_786():
    """Pullback beyond 0.786 → invalidation, no signal."""
    impulse_high = 117.0
    impulse_low = 100.0
    bars = [_bar(117, 117, 103, 103)]  # retraces all the way past 0.786 (≈103.7)
    pb = detect_pullback(bars, impulse_high=impulse_high, impulse_low=impulse_low)
    assert pb is None


def test_evaluate_full_happy_path():
    """Full impulse + pullback + continuation in TREND_LEVE → signal with confidence."""
    chop = [_bar(100, 101, 99, 100) for _ in range(20)]
    impulse = [
        _bar(100, 103, 100, 102),
        _bar(102, 106, 101, 105),
        _bar(105, 110, 104, 109),
        _bar(109, 114, 108, 113),
        _bar(113, 118, 112, 117),
    ]
    pullback = [
        _bar(117, 117, 113, 113),
        _bar(113, 113, 109, 109),
        _bar(109, 109, 108, 108.5),
    ]
    continuation = [_bar(108.5, 112, 108, 111.5)]
    bars = chop + impulse + pullback + continuation
    out = evaluate_setup(bars, adx_proxy=30.0)
    assert out is not None and out["signal"] is not None
    assert out["signal"]["direction"] == "long"
    assert out["signal"]["confidence"] >= 60
```

- [ ] **Step 2: Run tests, expect import failure**

Run: `cd .claude/scripts && .venv/bin/python -m pytest tests/test_pullback_detector.py -v`

Expected: `ModuleNotFoundError: No module named 'pullback_detector'`.

- [ ] **Step 3: Implement pullback_detector.py**

Create `.claude/scripts/pullback_detector.py`:

```python
#!/usr/bin/env python3
"""pullback_detector.py — Impulse → pullback → continuation pattern detector.

Pattern (LONG variant — SHORT is mirror):
1. Impulse: 3+ consecutive green candles with ATR > rolling-mean ATR.
2. Pullback: subsequent retrace to 0.382-0.618 fib of the impulse, invalidated
   beyond 0.786.
3. Continuation: first green-close candle after the pullback closes within zone.

Gates:
- ADX (or adx_proxy from caller) ≥ 25 — no signal in chop.

Outputs entry price, SL (fib 0.75), 3 TPs derived from impulse magnitude.

Usage:
    python3 pullback_detector.py --symbol BTCUSDT --tf 15m
    python3 pullback_detector.py --file /tmp/bars.json --adx 30
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import urllib.request
from pathlib import Path

ATR_WINDOW = 14
IMPULSE_MIN_STREAK = 3
FIB_INVALIDATION = 0.786
ADX_FLOOR = 25.0


def _color(bar: dict) -> str:
    return "green" if bar["close"] >= bar["open"] else "red"


def _true_range(prev: dict, cur: dict) -> float:
    return max(
        cur["high"] - cur["low"],
        abs(cur["high"] - prev["close"]),
        abs(cur["low"] - prev["close"]),
    )


def _atr_series(bars: list[dict], window: int = ATR_WINDOW) -> list[float]:
    trs = [bars[0]["high"] - bars[0]["low"]]
    for i in range(1, len(bars)):
        trs.append(_true_range(bars[i - 1], bars[i]))
    out: list[float] = []
    for i in range(len(trs)):
        start = max(0, i - window + 1)
        out.append(sum(trs[start : i + 1]) / (i - start + 1))
    return out


def detect_impulse(bars: list[dict], min_streak: int = IMPULSE_MIN_STREAK) -> dict | None:
    """Find the most recent N-streak of same-color candles with ATR > mean ATR."""
    if len(bars) < min_streak + ATR_WINDOW:
        return None
    atrs = _atr_series(bars)
    mean_atr = statistics.mean(atrs)
    # walk backwards looking for a clean streak
    i = len(bars) - 1
    while i >= min_streak - 1:
        streak_color = _color(bars[i])
        streak_start = i
        while streak_start > 0 and _color(bars[streak_start - 1]) == streak_color:
            streak_start -= 1
        streak_len = i - streak_start + 1
        if streak_len >= min_streak:
            slice_atrs = atrs[streak_start : i + 1]
            if statistics.mean(slice_atrs) > mean_atr:
                return {
                    "color": streak_color,
                    "start_idx": streak_start,
                    "end_idx": i,
                    "high": max(b["high"] for b in bars[streak_start : i + 1]),
                    "low": min(b["low"] for b in bars[streak_start : i + 1]),
                }
        i = streak_start - 1
    return None


def detect_pullback(bars: list[dict], *, impulse_high: float, impulse_low: float) -> dict | None:
    """Retrace into fib 0.382-0.618 zone, invalidated past 0.786."""
    if not bars:
        return None
    rng = impulse_high - impulse_low
    if rng <= 0:
        return None
    fib_382 = impulse_high - rng * 0.382
    fib_618 = impulse_high - rng * 0.618
    fib_786 = impulse_high - rng * FIB_INVALIDATION
    lowest = min(b["low"] for b in bars)
    end_close = bars[-1]["close"]
    if lowest < fib_786:
        return None
    if not (fib_618 - 1e-9 <= end_close <= fib_382 + 1e-9):
        # tolerate slight bleed using lowest as alternative
        if not (fib_618 - 1e-9 <= lowest <= fib_382 + 1e-9):
            return None
    return {
        "end_price": end_close,
        "fib_382": fib_382,
        "fib_618": fib_618,
        "fib_786": fib_786,
    }


def detect_continuation(bars: list[dict], *, impulse_color: str) -> dict | None:
    """First same-color-as-impulse close after pullback."""
    if not bars:
        return None
    last = bars[-1]
    if _color(last) == impulse_color:
        return {"confirmed": True, "close": last["close"]}
    return None


def evaluate_setup(bars: list[dict], *, adx_proxy: float) -> dict | None:
    """Full pipeline. Returns dict with signal=None if no setup, or full signal."""
    if adx_proxy < ADX_FLOOR:
        return {"signal": None, "reason": f"ADX {adx_proxy:.1f} < {ADX_FLOOR}"}

    impulse = detect_impulse(bars)
    if impulse is None:
        return {"signal": None, "reason": "no impulse"}

    after_impulse = bars[impulse["end_idx"] + 1 :]
    if len(after_impulse) < 2:
        return {"signal": None, "reason": "not enough bars after impulse"}

    # Use all but the last bar as the pullback span; last bar is continuation candidate.
    pb = detect_pullback(
        after_impulse[:-1],
        impulse_high=impulse["high"],
        impulse_low=impulse["low"],
    )
    if pb is None:
        return {"signal": None, "reason": "no valid pullback"}

    cont = detect_continuation(after_impulse[-1:], impulse_color=impulse["color"])
    if cont is None:
        return {"signal": None, "reason": "no continuation yet"}

    direction = "long" if impulse["color"] == "green" else "short"
    rng = impulse["high"] - impulse["low"]
    entry = cont["close"]
    if direction == "long":
        sl = impulse["high"] - rng * 0.75
        tps = [entry + rng * k for k in (1.0, 1.618, 2.618)]
    else:
        sl = impulse["low"] + rng * 0.75
        tps = [entry - rng * k for k in (1.0, 1.618, 2.618)]

    # naive confidence: ADX above 25 → 30 base; impulse strength → up to 30; pullback depth → 40
    pullback_depth = (impulse["high"] - pb["end_price"]) / rng if direction == "long" else (
        pb["end_price"] - impulse["low"]
    ) / rng
    adx_score = min(30, (adx_proxy - 25) * 2 + 10)
    impulse_score = min(30, 5 + (impulse["end_idx"] - impulse["start_idx"]) * 5)
    pullback_score = 40 * (1 - abs(pullback_depth - 0.5) * 2)
    confidence = max(0, min(100, round(adx_score + impulse_score + pullback_score)))

    return {
        "signal": {
            "direction": direction,
            "entry": round(entry, 4),
            "sl": round(sl, 4),
            "tps": [round(t, 4) for t in tps],
            "confidence": confidence,
            "impulse": impulse,
            "pullback": pb,
        }
    }


def _fetch_bars_binance(symbol: str, tf: str, limit: int = 200) -> list[dict]:
    tf_map = {"15m": "15m", "1h": "1h", "4h": "4h"}
    url = (
        f"https://api.binance.com/api/v3/klines?symbol={symbol}"
        f"&interval={tf_map.get(tf, tf)}&limit={limit}"
    )
    with urllib.request.urlopen(url, timeout=10) as r:
        raw = json.loads(r.read())
    return [
        {
            "open": float(b[1]),
            "high": float(b[2]),
            "low": float(b[3]),
            "close": float(b[4]),
            "volume": float(b[5]),
        }
        for b in raw
    ]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--tf", default="15m")
    p.add_argument("--limit", type=int, default=200)
    p.add_argument("--file", type=str, help="bars JSON (list of OHLCV dicts)")
    p.add_argument("--adx", type=float, default=None, help="ADX proxy if known")
    p.add_argument("--json", action="store_true")
    p.add_argument("--quick", action="store_true")
    args = p.parse_args()

    if args.file:
        bars = json.loads(Path(args.file).read_text())
    else:
        bars = _fetch_bars_binance(args.symbol, args.tf, args.limit)

    if args.adx is None:
        # try calling adx_calc if available; otherwise default 30 (assume TREND_LEVE)
        try:
            import subprocess
            res = subprocess.run(
                [
                    str(Path(__file__).resolve().parent / ".venv" / "bin" / "python"),
                    str(Path(__file__).resolve().parent / "adx_calc.py"),
                    "--file", args.file or "/dev/stdin",
                    "--json",
                ],
                input=json.dumps(bars) if not args.file else None,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if res.returncode == 0:
                args.adx = json.loads(res.stdout).get("adx", 30.0)
            else:
                args.adx = 30.0
        except Exception:
            args.adx = 30.0

    out = evaluate_setup(bars, adx_proxy=args.adx)
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    elif args.quick:
        sig = out.get("signal") if out else None
        if sig:
            print(f"PULLBACK {sig['direction'].upper()} conf={sig['confidence']} entry={sig['entry']} sl={sig['sl']}")
        else:
            print(f"NO_SIGNAL — {out.get('reason', 'unknown') if out else 'no data'}")
    else:
        print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests, expect pass**

Run: `cd .claude/scripts && .venv/bin/python -m pytest tests/test_pullback_detector.py -v`

Expected: all tests pass.

- [ ] **Step 5: Create the /pullback slash command**

Create `.claude/commands/pullback.md`:

```markdown
---
description: Detect impulse → pullback → continuation pattern for the active profile's default symbol (standalone, not wired to punk-smart yet)
---

# /pullback

Detector standalone para el patrón **impulso → pullback → continuación** — útil cuando el
régimen es TREND_LEVE/FUERTE (ADX ≥ 25) y Mean Reversion no aplica.

## Uso

```
/pullback                        # asset default del profile, TF 15m
/pullback BTCUSDT 1h             # asset y TF custom
/pullback ETHUSDT 15m --adx 32   # con ADX conocido (skip auto-detect)
```

## Pipeline

1. Carga bars OHLCV del símbolo+TF (200 últimas por default)
2. Calcula ADX(14) — exige ≥ 25 (gate)
3. Detecta el impulso más reciente (3+ velas mismo color, ATR > μ)
4. Detecta pullback hacia fib 0.382–0.618 (invalida si pasa 0.786)
5. Confirma continuación con primera vela impulse-color post-pullback
6. Devuelve entry / SL / 3 TPs / confidence 0-100

## Ejecutar

```bash
.claude/scripts/.venv/bin/python .claude/scripts/pullback_detector.py \
  --symbol ${1:-BTCUSDT} --tf ${2:-15m} --quick
```

## Output

```
PULLBACK LONG conf=72 entry=108.50 sl=104.25
TPs: 125.00 / 144.50 / 175.30
```

Si `NO_SIGNAL` → razón explícita (no impulse / no pullback / no continuation yet).

## Estado: STANDALONE — no integrado a `/punk-smart` v2

Por decisión del 2026-05-12 (design doc), antes de wirearlo al router debe correr backtest
comparativo vs MA Crossover en TREND_LEVE.

## Fuente

Design doc 2026-05-12 YouTube bundle, feature A (V1 Alex Ruiz — patrón impulso-pullback-continuación).
```

- [ ] **Step 6: Smoke test the slash command's helper call**

Run: `cd /Users/josecampos/Documents/wally-trader && .claude/scripts/.venv/bin/python .claude/scripts/pullback_detector.py --symbol BTCUSDT --tf 15m --quick`

Expected: prints either a signal line or a NO_SIGNAL reason. Should not crash.

- [ ] **Step 7: Commit**

```bash
git add .claude/scripts/pullback_detector.py \
        .claude/scripts/tests/test_pullback_detector.py \
        .claude/commands/pullback.md
git commit -m "$(cat <<'EOF'
feat(pullback): standalone impulse-pullback-continuation detector

New pullback_detector.py + /pullback command. ADX≥25 gate, 3-step pipeline
(impulse → fib 0.382-0.618 retracement → continuation candle). Returns
entry/SL/3-TPs + confidence 0-100. NOT wired to punk-smart router yet
(per design decision Q1 — backtest first).

Source: design doc 2026-05-12 YouTube bundle, feature A (V1 insight).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6 (Feature E): Asian Range Strategy for fotmarkets

**Files:**
- Create: `.claude/scripts/asian_range.py`
- Create: `.claude/scripts/tests/test_asian_range.py`
- Create: `.claude/commands/asian-range.md`
- Create: `.claude/profiles/fotmarkets/strategy_asian_range.md`

- [ ] **Step 1: Write the failing tests with synthetic fixtures**

Create `.claude/scripts/tests/test_asian_range.py`:

```python
"""Tests for asian_range.py — Asian session range + grab/fakeout detector."""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from asian_range import (
    asian_session_high_low,
    detect_break_and_grab,
    evaluate_setup,
)


def _bar(ts_iso, o, h, l, c, v=1000):
    return {
        "ts": ts_iso,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
    }


def test_asian_high_low_computed_from_session_bars():
    """Bars between 23:00-08:00 UTC contribute; outside ignored."""
    bars = [
        _bar("2026-05-12T22:00:00+00:00", 1.10, 1.101, 1.099, 1.100),  # pre-Asian
        _bar("2026-05-12T23:00:00+00:00", 1.100, 1.102, 1.099, 1.101),
        _bar("2026-05-13T00:00:00+00:00", 1.101, 1.105, 1.098, 1.104),  # high here
        _bar("2026-05-13T04:00:00+00:00", 1.104, 1.107, 1.090, 1.092),  # low here (1.090)
        _bar("2026-05-13T07:00:00+00:00", 1.092, 1.095, 1.091, 1.094),
        _bar("2026-05-13T08:00:00+00:00", 1.094, 1.110, 1.094, 1.109),  # post-Asian
    ]
    out = asian_session_high_low(bars, anchor="2026-05-13T08:00:00+00:00")
    assert abs(out["high"] - 1.107) < 1e-9
    assert abs(out["low"] - 1.090) < 1e-9


def test_break_above_then_close_back_inside_is_grab():
    """Price breaks above Asian high then closes back inside within 4 bars → grab."""
    asian_high = 1.107
    asian_low = 1.090
    london_bars = [
        _bar("2026-05-13T08:00:00+00:00", 1.094, 1.112, 1.094, 1.110),  # break above
        _bar("2026-05-13T08:05:00+00:00", 1.110, 1.111, 1.103, 1.104),  # back inside
    ]
    grab = detect_break_and_grab(london_bars, asian_high=asian_high, asian_low=asian_low)
    assert grab is not None
    assert grab["side"] == "high"
    assert grab["direction"] == "short"


def test_break_below_then_close_back_inside_is_grab():
    asian_high = 1.107
    asian_low = 1.090
    london_bars = [
        _bar("2026-05-13T08:00:00+00:00", 1.094, 1.094, 1.085, 1.087),  # break below
        _bar("2026-05-13T08:05:00+00:00", 1.087, 1.099, 1.087, 1.095),  # back inside
    ]
    grab = detect_break_and_grab(london_bars, asian_high=asian_high, asian_low=asian_low)
    assert grab is not None
    assert grab["side"] == "low"
    assert grab["direction"] == "long"


def test_one_sided_trend_no_range_returns_no_signal():
    """Asian session that just trends one direction — no clear range, no grab logic."""
    bars = [_bar(f"2026-05-13T0{i}:00:00+00:00", 1.1 + i * 0.001, 1.1 + i * 0.001 + 0.002,
                  1.1 + i * 0.001 - 0.0005, 1.1 + i * 0.001 + 0.0015) for i in range(9)]
    out = evaluate_setup(bars, anchor="2026-05-13T08:30:00+00:00")
    # range exists but very narrow; grab requires a true break-then-reverse which won't happen
    assert out["signal"] is None or out["signal"].get("confidence", 0) < 30


def test_break_without_grab_no_signal():
    """Price breaks high and continues — no close back inside → no grab."""
    asian_high = 1.107
    asian_low = 1.090
    london_bars = [
        _bar("2026-05-13T08:00:00+00:00", 1.094, 1.115, 1.094, 1.113),
        _bar("2026-05-13T08:05:00+00:00", 1.113, 1.120, 1.110, 1.118),
        _bar("2026-05-13T08:10:00+00:00", 1.118, 1.125, 1.115, 1.122),
    ]
    grab = detect_break_and_grab(london_bars, asian_high=asian_high, asian_low=asian_low)
    assert grab is None


def test_grab_too_late_after_4_bars_no_signal():
    """Close back inside happens on bar 5 → no signal (window is 4 bars)."""
    asian_high = 1.107
    asian_low = 1.090
    london_bars = [
        _bar("2026-05-13T08:00:00+00:00", 1.094, 1.112, 1.094, 1.111),  # break
        _bar("2026-05-13T08:05:00+00:00", 1.111, 1.115, 1.110, 1.113),
        _bar("2026-05-13T08:10:00+00:00", 1.113, 1.114, 1.110, 1.112),
        _bar("2026-05-13T08:15:00+00:00", 1.112, 1.113, 1.110, 1.111),
        _bar("2026-05-13T08:20:00+00:00", 1.111, 1.112, 1.103, 1.104),  # too late
    ]
    grab = detect_break_and_grab(london_bars, asian_high=asian_high, asian_low=asian_low)
    assert grab is None
```

- [ ] **Step 2: Run tests, expect import failure**

Run: `cd .claude/scripts && .venv/bin/python -m pytest tests/test_asian_range.py -v`

Expected: `ModuleNotFoundError: No module named 'asian_range'`.

- [ ] **Step 3: Implement asian_range.py**

Create `.claude/scripts/asian_range.py`:

```python
#!/usr/bin/env python3
"""asian_range.py — Asian session range + grab/fakeout detector.

Asian session bars: UTC 23:00-08:00 (CR 17:00-02:00). At London open, price often sweeps
one side of the Asian range then closes back inside within a few bars — a classic ICT
liquidity grab. Entry = market on grab confirmation, SL = beyond sweep + small buffer,
TP = opposite range bound.

Usage:
    python3 asian_range.py --symbol EURUSD --check-grab
    python3 asian_range.py --file /tmp/bars5m.json --check-grab --json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ASIAN_START_HOUR_UTC = 23
ASIAN_END_HOUR_UTC = 8
GRAB_WINDOW_BARS = 4
SL_BUFFER_PIPS = 0.0002  # 2 pips for EURUSD; override via --buffer


def _parse_ts(ts_iso: str) -> datetime:
    return datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))


def _in_asian_session(ts: datetime) -> bool:
    h = ts.astimezone(timezone.utc).hour
    if ASIAN_START_HOUR_UTC > ASIAN_END_HOUR_UTC:
        return h >= ASIAN_START_HOUR_UTC or h < ASIAN_END_HOUR_UTC
    return ASIAN_START_HOUR_UTC <= h < ASIAN_END_HOUR_UTC


def asian_session_high_low(bars: list[dict], *, anchor: str) -> dict:
    """Compute high/low of the Asian session ending at the bar before `anchor`."""
    anchor_dt = _parse_ts(anchor)
    asian_bars = [b for b in bars if _in_asian_session(_parse_ts(b["ts"])) and _parse_ts(b["ts"]) < anchor_dt]
    if not asian_bars:
        return {"high": None, "low": None, "n_bars": 0}
    return {
        "high": max(b["high"] for b in asian_bars),
        "low": min(b["low"] for b in asian_bars),
        "n_bars": len(asian_bars),
    }


def detect_break_and_grab(
    london_bars: list[dict],
    *,
    asian_high: float,
    asian_low: float,
    window: int = GRAB_WINDOW_BARS,
) -> dict | None:
    """Find a break of asian_high or asian_low followed by a close back inside within window."""
    if not london_bars or asian_high is None or asian_low is None:
        return None
    break_idx = None
    side = None
    for i, b in enumerate(london_bars[:window]):
        if b["high"] > asian_high and b["close"] > asian_high:
            break_idx, side = i, "high"
            break
        if b["low"] < asian_low and b["close"] < asian_low:
            break_idx, side = i, "low"
            break
    if break_idx is None:
        return None
    # search next (window - break_idx) bars for close back inside
    for j in range(break_idx + 1, min(window, len(london_bars))):
        b = london_bars[j]
        if side == "high" and b["close"] < asian_high:
            return {
                "side": "high",
                "direction": "short",
                "break_bar_idx": break_idx,
                "grab_bar_idx": j,
                "sweep_extreme": max(x["high"] for x in london_bars[break_idx : j + 1]),
            }
        if side == "low" and b["close"] > asian_low:
            return {
                "side": "low",
                "direction": "long",
                "break_bar_idx": break_idx,
                "grab_bar_idx": j,
                "sweep_extreme": min(x["low"] for x in london_bars[break_idx : j + 1]),
            }
    return None


def evaluate_setup(bars: list[dict], *, anchor: str | None = None) -> dict:
    """Full pipeline: compute Asian H/L, look for grab in bars after anchor."""
    if anchor is None:
        # use the latest bar's timestamp at hour 08:00 UTC as anchor
        anchor = bars[-1]["ts"]
    anchor_dt = _parse_ts(anchor)
    asian = asian_session_high_low(bars, anchor=anchor)
    london_bars = [b for b in bars if _parse_ts(b["ts"]) >= anchor_dt]
    grab = detect_break_and_grab(london_bars, asian_high=asian["high"], asian_low=asian["low"])
    if grab is None:
        return {"signal": None, "asian": asian, "reason": "no grab"}

    if grab["direction"] == "long":
        entry = london_bars[grab["grab_bar_idx"]]["close"]
        sl = grab["sweep_extreme"] - SL_BUFFER_PIPS
        tp = asian["high"]
    else:
        entry = london_bars[grab["grab_bar_idx"]]["close"]
        sl = grab["sweep_extreme"] + SL_BUFFER_PIPS
        tp = asian["low"]

    risk = abs(entry - sl)
    reward = abs(tp - entry)
    rr = round(reward / risk, 3) if risk > 0 else 0.0
    confidence = 50 + min(40, int(rr * 10))

    return {
        "signal": {
            "direction": grab["direction"],
            "entry": round(entry, 5),
            "sl": round(sl, 5),
            "tp": round(tp, 5),
            "rr": rr,
            "confidence": confidence,
            "asian_range": {"high": asian["high"], "low": asian["low"]},
            "grab": grab,
        }
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="EURUSD")
    p.add_argument("--file", help="bars JSON")
    p.add_argument("--anchor", help="ISO UTC timestamp of London open candle")
    p.add_argument("--check-grab", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--quick", action="store_true")
    args = p.parse_args()

    if not args.file:
        print("ERROR: --file required (live forex fetch out of scope here)", file=sys.stderr)
        return 3
    bars = json.loads(Path(args.file).read_text())
    out = evaluate_setup(bars, anchor=args.anchor)

    if args.json:
        print(json.dumps(out, indent=2, default=str))
    elif args.quick:
        sig = out.get("signal")
        if sig:
            print(f"ASIAN_GRAB {sig['direction'].upper()} conf={sig['confidence']} entry={sig['entry']} sl={sig['sl']} tp={sig['tp']} rr={sig['rr']}")
        else:
            print(f"NO_SIGNAL — {out.get('reason', 'unknown')}")
    else:
        print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests, expect pass**

Run: `cd .claude/scripts && .venv/bin/python -m pytest tests/test_asian_range.py -v`

Expected: 6 passed.

- [ ] **Step 5: Create /asian-range slash command**

Create `.claude/commands/asian-range.md`:

```markdown
---
description: Asian session range + London-open grab/fakeout detector (fotmarkets EURUSD 5m)
---

# /asian-range

Detector standalone para el patrón **Asian range + London grab** — ICT liquidity grab
post-Asian session. Aplicable principalmente a EURUSD y GBPUSD durante la ventana de
Londres (CR 02:00-08:00, ideal CR 07:00-09:00 para fotmarkets).

## Uso

```
/asian-range                       # EURUSD default, requiere --file con bars 5m
/asian-range EURUSD --file <path>  # explícito
```

## Pipeline

1. Computa Asian session high/low (UTC 23:00-08:00 ≈ CR 17:00-02:00)
2. Espera London open candle (anchor = UTC 08:00 o el bar siguiente)
3. Detecta break: una vela cierra fuera del rango asiático (high o low)
4. Detecta grab: cierre de vuelta dentro del rango en ≤ 4 velas → reversal
5. Entry = market en confirmación grab; SL = más allá del sweep + 2 pips; TP = lado
   opuesto del rango asiático

## Ejecutar

```bash
.claude/scripts/.venv/bin/python .claude/scripts/asian_range.py \
  --file ${1:-/tmp/bars5m.json} --check-grab --quick
```

## Estado: SECONDARY — no reemplaza Fotmarkets-Micro

Por decisión del 2026-05-12 (design doc Q2), Asian Range es estrategia secundaria
informativa. La principal del profile fotmarkets sigue siendo Fotmarkets-Micro 5m
(scalping reversal post-pullback).

## Fuente

Design doc 2026-05-12 YouTube bundle, feature E (V3 Alex Ruiz — strategy if I had $100).
```

- [ ] **Step 6: Create the fotmarkets secondary-strategy doc**

Create `.claude/profiles/fotmarkets/strategy_asian_range.md`:

```markdown
# Fotmarkets — Asian Range (Secondary Strategy)

> Estado: **secondary** (informativa). Primary strategy del profile sigue siendo
> Fotmarkets-Micro 5m (ver `strategy.md`).

## Tesis

Durante la sesión asiática (UTC 23:00-08:00 ≈ CR 17:00-02:00), pares forex mayores
(EURUSD, GBPUSD) se mueven en rango estrecho. Los stops del retail se acumulan justo
fuera de ese rango. La apertura de Londres frecuentemente *barre* uno de los extremos
y luego revierte — patrón ICT clásico de liquidity grab.

## Reglas

| Parámetro | Valor |
|---|---|
| Asset | EURUSD (primary), GBPUSD (secondary) |
| TF | 5m |
| Sesión Asia | UTC 23:00 – 08:00 (CR 17:00 – 02:00) |
| Sesión Londres | UTC 08:00 – 13:00 (CR 02:00 – 07:00); ventana fotmarkets CR 07:00-11:00 = London/NY overlap |
| Entry | Market en confirmación de grab (cierre de vuelta dentro del rango en ≤ 4 velas tras break) |
| SL | Sweep extreme + 2 pips buffer |
| TP | Lado opuesto del rango asiático |
| R:R mínimo | 1.5:1 (gate dinámico de `/min_rr_gate` decide caso por caso) |
| Risk | Mismo que primary (fase-aware: 10% / 5% / 2%) |
| Frecuencia | 0-1 setup/día (no siempre hay grab limpio) |
| Macro gate | OBLIGATORIO — si `macro_gate --check-tier` retorna HARD/WARN, no operar |

## Conflicto con Fotmarkets-Micro

Si en la misma vela aparece setup primary (Micro) y secondary (Asian Range) en
direcciones distintas → prioridad **primary**. No abrir ambas.

Si son misma dirección → entrar **una sola posición** con la mejor R:R proyectada.

## Estado pendiente de validación

No backtested aún en data histórica fotmarkets. Tratar como sandbox manual hasta acumular
≥ 10 trades con outcome registrado en `memory/trading_log.md`.

## Fuente

- Design doc: `docs/superpowers/specs/2026-05-12-youtube-improvements-bundle-design.md`
- Plan: `docs/superpowers/plans/2026-05-12-youtube-improvements-bundle.md` (Task 6)
- Origen del concepto: V3 Alex Ruiz — "Esta es la estrategia que seguiría si solo tuviera $100"
```

- [ ] **Step 7: Commit**

```bash
git add .claude/scripts/asian_range.py \
        .claude/scripts/tests/test_asian_range.py \
        .claude/commands/asian-range.md \
        .claude/profiles/fotmarkets/strategy_asian_range.md
git commit -m "$(cat <<'EOF'
feat(asian_range): secondary EURUSD 5m strategy for fotmarkets

asian_range.py detects Asian session high/low (UTC 23:00-08:00) + grab-and-reverse
within 4 bars of London open. Returns entry/SL/TP/R:R/confidence. NEW /asian-range
slash command + fotmarkets strategy_asian_range.md (secondary, does not replace
Fotmarkets-Micro).

Source: design doc 2026-05-12 YouTube bundle, feature E (V3 insight).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Wrap-Up — Document the Bundle in CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Append the bundle section to CLAUDE.md**

Read `CLAUDE.md` and locate the last "Bundle" section (currently "Live Insights Bundle (Bundle 2, 2026-05-10)"). Append after it a new section:

```markdown

## YouTube Improvements Bundle (Bundle 3, 2026-05-12)

Six improvements distilled from four Alex Ruiz videos (es):

### Feature B — Dynamic Min-R:R Gate
- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/min_rr_gate.py --profile <name> --setup-rr <ratio>`
- Formula: `min_rr = ((1-wr)/wr) * 1.2` with WR clamped [0.20, 0.80], fallback 1.5 when <10 trades.
- Wired into `trade-validator` FASE 0.9 and `signal-validator` (LOW_RR score penalty).

### Feature C — Fib Retracement Zones (extension of fib_extension.py)
- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/fib_extension.py --mode retracement --symbol BTCUSDT --tf 1h`
- Output: 0.382 / 0.500 / 0.618 entry zones + SL at 0.75 + TP at swing extreme.
- Used internally by pullback_detector.py.

### Feature F — Three-Months-Positive Challenge Gate
- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/challenge_readiness.py --profile <name>`
- Returns READY / BORDERLINE / NOT_READY based on last 3 months of PnL parsed from the profile log.
- Wired into `/challenge` as a soft advisory banner before any "buy next challenge" decision.

### Feature G — retail-bingx Cost Reality (documentation only)
- `.claude/profiles/retail-bingx/config.md` updated to mark the profile as observation-only ($0.93 capital + tick size makes real execution non-viable despite tiny fees).

### Feature A — Pullback Detector (standalone, no router wire-in yet)
- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/pullback_detector.py --symbol BTCUSDT --tf 15m`
- Slash: `/pullback [SYMBOL] [TF]`
- Pipeline: ADX≥25 gate → impulse (3+ same-color, ATR>μ) → fib 0.382-0.618 retrace → continuation candle.
- Output: entry / SL (fib 0.75) / 3 TPs (Fibonacci extensions) / confidence 0-100.
- **Standalone-first** by design — backtest vs MA Crossover required before wiring into `regime_mapping.json`.

### Feature E — Asian Range Secondary Strategy (fotmarkets)
- CLI: `.claude/scripts/.venv/bin/python .claude/scripts/asian_range.py --file <bars5m.json> --check-grab`
- Slash: `/asian-range [SYMBOL] --file <path>`
- Pipeline: compute Asian session H/L (UTC 23:00-08:00) → detect break-and-reverse within 4 bars of London open.
- **Secondary only** — Fotmarkets-Micro 5m remains primary. See `.claude/profiles/fotmarkets/strategy_asian_range.md`.

### Out of scope (intentional)
- HMM regime detector — Alex's own V2 conclusion walked back HMM-for-param-tuning; existing `regime_mapping.json` + ADX cover the use case.
- 3h IA course (V4) — chapters 1:21, 1:36, 1:53, 2:06, 2:30 identified as worth manual viewing, but no programmatic distillation.

### Tests
- 22+ new tests across `test_min_rr_gate.py`, `test_fib_extension.py` (new tests), `test_challenge_readiness.py`, `test_pullback_detector.py`, `test_asian_range.py`. All synthetic fixtures, no live-data dependence.

### Spec & plan
- Design: `docs/superpowers/specs/2026-05-12-youtube-improvements-bundle-design.md`
- Plan: `docs/superpowers/plans/2026-05-12-youtube-improvements-bundle.md`
```

- [ ] **Step 2: Verify the doc still reads cleanly**

Run: `tail -80 CLAUDE.md`

Expected: the new bundle section appears at the bottom of CLAUDE.md, formatted consistently with previous bundles.

- [ ] **Step 3: Final test pass across all new tests**

Run:
```bash
cd .claude/scripts && .venv/bin/python -m pytest \
  tests/test_fib_extension.py \
  tests/test_min_rr_gate.py \
  tests/test_challenge_readiness.py \
  tests/test_pullback_detector.py \
  tests/test_asian_range.py -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
docs(CLAUDE): document YouTube Improvements Bundle (2026-05-12)

Adds Bundle 3 section summarizing the six features (B/C/F/G/A/E) + out-of-scope
items + spec/plan paths.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes

**Spec coverage check:** every numbered Feature in the spec maps to one Task:
- B → Task 3 ✓
- C → Task 2 ✓
- F → Task 4 ✓
- G → Task 1 ✓
- A → Task 5 ✓
- E → Task 6 ✓
- Wrap-up doc → Task 7 ✓

**Type consistency:** function names match between tasks (`retracement_zones`, `autodetect_direction`, `detect_impulse`, `detect_pullback`, `detect_continuation`, `evaluate_setup` for pullback; `asian_session_high_low`, `detect_break_and_grab`, `evaluate_setup` for asian_range).

**No router wire-in for A/E:** confirmed standalone-first per design Q1/Q2.

**No placeholder text:** every step contains the actual code or doc body to apply.
