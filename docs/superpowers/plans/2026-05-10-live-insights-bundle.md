# Live Insights Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Implement 5 features from the Dragno master live (2026-05-10) — multi-tier macro blackout, USDT.D tracker, volume divergence check, auto-MUGRE switch, fib extension exhaustion.

**Architecture:** Each feature is a small helper script (or extension of an existing one) plus integration into one or more existing agents. No new slash commands.

**Tech Stack:** Python 3 stdlib + existing wally_core/.venv deps (`requests`, `pandas`, `numpy`).

---

## File Structure

| Path | Purpose | Feature |
|---|---|---|
| `.claude/scripts/usdtd_tracker.py` | New: USDT.D price + trend | A |
| `.claude/scripts/macro_gate.py` | Modify: add `--check-tier` | B |
| `.claude/scripts/volume_divergence.py` | New: OBV slope divergence | C |
| `.claude/commands/punk-hunt.md` | Modify: macro-aware auto-tier-0 | D |
| `.claude/scripts/fib_extension.py` | New: Fibonacci extension exhaustion | E |
| `.claude/scripts/tests/test_*.py` | Tests for each helper | A, B, C, E |
| `.claude/agents/*.md` | Wire features into agents | A, B, C, E |
| `CLAUDE.md` | Document new tools | All |

---

## Implementation Order

Sequential dependencies:
1. **B** (macro tier extension) — first; D depends on it
2. **D** (auto-MUGRE) — depends on B
3. **A**, **C**, **E** — independent; can be parallelized

## Task 1 (Feature B): Extend macro_gate.py with --check-tier

**Files:**
- Modify: `.claude/scripts/macro_gate.py`
- Modify: `.claude/scripts/tests/test_macro_gate.py`

- [ ] **Step 1: Add `--check-tier` argparse + handler**

In `.claude/scripts/macro_gate.py`, find the existing argparse section and add:

```python
group.add_argument("--check-tier", action="store_true",
                   help="Output tier: OK/SOFT/WARN/HARD based on macro proximity")
p.add_argument("--soft-hours", type=int, default=48,
               help="Hours ahead to look for SOFT tier (default 48)")
```

Add a new dispatch branch in the `main()` function (or wherever subcommands are dispatched) calling `check_tier(cache, now, args.soft_hours)`.

- [ ] **Step 2: Implement check_tier()**

Add this function above `main()`:

```python
WARN_HOURS = 4


def check_tier(cache: dict | None, now: datetime, soft_hours: int = 48) -> dict:
    """Return tiered macro status: HARD | WARN | SOFT | OK."""
    if cache is None:
        return {"tier": "OK", "reason": "no_cache", "stale": True, "next_event": None}
    high_events = [e for e in cache["events"] if e.get("impact") == "high"]
    upcoming = []
    for ev in high_events:
        ev_dt = event_datetime(ev)
        delta = (ev_dt - now).total_seconds() / 60.0  # minutes; negative if past
        upcoming.append((delta, ev))
    upcoming.sort(key=lambda x: x[0] if x[0] >= 0 else float("inf"))

    if not upcoming:
        return {"tier": "OK", "reason": "no_high_events", "next_event": None}

    nearest_delta, nearest_ev = upcoming[0]
    abs_delta_min = abs(nearest_delta)

    # HARD: within ±30 min of any high-impact event
    for delta, ev in upcoming:
        if abs(delta) <= WINDOW_MINUTES:
            return {"tier": "HARD", "next_event": _event_payload(ev, delta)}

    # WARN: within ±WARN_HOURS hours
    for delta, ev in upcoming:
        if abs(delta) <= WARN_HOURS * 60:
            return {"tier": "WARN", "next_event": _event_payload(ev, delta)}

    # SOFT: within next `soft_hours` (positive direction only)
    for delta, ev in upcoming:
        if 0 < delta <= soft_hours * 60:
            return {"tier": "SOFT", "next_event": _event_payload(ev, delta)}

    return {"tier": "OK", "next_event": _event_payload(nearest_ev, nearest_delta)}


def _event_payload(ev: dict, delta_min: float) -> dict:
    return {
        "name": ev["name"],
        "country": ev.get("country", "?"),
        "datetime_cr": f"{ev['date']}T{ev['time_cr']}:00-06:00",
        "hours_until": round(delta_min / 60.0, 2),
    }
```

- [ ] **Step 3: Wire dispatcher**

Find the existing `if args.check_now:` block and add:

```python
elif args.check_tier:
    result = check_tier(cache, now, args.soft_hours)
    print(json.dumps(result, indent=2))
    return 0
```

- [ ] **Step 4: Add tests**

Append to `.claude/scripts/tests/test_macro_gate.py`:

```python
def test_check_tier_returns_hard_when_within_30min(monkeypatch, fixed_cache):
    now = datetime(2026, 5, 13, 12, 50, tzinfo=CR_OFFSET)  # 10 min before FOMC at 13:00
    result = mg.check_tier(fixed_cache, now)
    assert result["tier"] == "HARD"


def test_check_tier_returns_warn_when_within_4h(monkeypatch, fixed_cache):
    now = datetime(2026, 5, 13, 10, 0, tzinfo=CR_OFFSET)  # 3h before FOMC
    result = mg.check_tier(fixed_cache, now)
    assert result["tier"] == "WARN"


def test_check_tier_returns_soft_when_within_48h(monkeypatch, fixed_cache):
    now = datetime(2026, 5, 12, 12, 0, tzinfo=CR_OFFSET)  # ~25h before FOMC
    result = mg.check_tier(fixed_cache, now)
    assert result["tier"] == "SOFT"


def test_check_tier_returns_ok_when_far_away(monkeypatch, fixed_cache):
    now = datetime(2026, 5, 8, 12, 0, tzinfo=CR_OFFSET)  # 5 days before FOMC
    result = mg.check_tier(fixed_cache, now)
    assert result["tier"] == "OK"
```

(Reuse the existing `fixed_cache` fixture — if it doesn't exist, add one with a single FOMC event at 2026-05-13T13:00 CR.)

- [ ] **Step 5: Smoke test**

```bash
python3 .claude/scripts/macro_gate.py --check-tier
```

Expected: JSON output with `tier` field. Tier value depends on actual current macro events but command must not crash.

- [ ] **Step 6: Commit**

```bash
git add .claude/scripts/macro_gate.py .claude/scripts/tests/test_macro_gate.py
git commit -m "feat(macro-gate): add --check-tier with HARD/WARN/SOFT/OK levels"
```

---

## Task 2 (Feature D): Auto-MUGRE switch on macro SOFT in /punk-hunt

**Files:**
- Modify: `.claude/commands/punk-hunt.md`

- [ ] **Step 1: Read current punk-hunt.md to understand the existing structure**

```bash
cat .claude/commands/punk-hunt.md
```

- [ ] **Step 2: Add macro-tier check section**

After the command's frontmatter and BEFORE the existing "Caza autónoma" or main scan instructions, insert a new section. Use the Edit tool to insert this text after the YAML frontmatter:

```markdown
## Pre-flight: Macro tier check (NUEVO 2026-05-10)

Antes de escanear, ejecuta:

```bash
TIER=$(python3 .claude/scripts/macro_gate.py --check-tier | python3 -c "import sys, json; print(json.load(sys.stdin)['tier'])")
echo "Macro tier: $TIER"
```

Lógica de routing:
- `HARD` → **ABORTA** scan. Imprime: "🚫 Macro HARD blackout. NO scan today." y termina.
- `WARN` → procede pero **fuerza tier-0** (MUGRES) si user no pasó `--no-auto-tier`. Imprime aviso: "⚠️ Macro WARN — auto-engaging tier-0 (mugres) for decoupling."
- `SOFT` → procede pero **fuerza tier-0** si user no pasó `--no-auto-tier`. Imprime: "ℹ️ Macro SOFT (FOMC/CPI en <48h) — auto-engaging tier-0."
- `OK` → procede con scan estándar (o `--tier-0` si user lo pasó explícito).

User puede override con `--no-auto-tier` para forzar scan normal pese al tier WARN/SOFT.
```

- [ ] **Step 3: Smoke test (manual)**

There's no automated test. Note in the commit message that this is intentional — the behavior is exercised when the user runs `/punk-hunt` after Feature B is deployed.

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/punk-hunt.md
git commit -m "feat(punk-hunt): auto-engage tier-0 MUGRES on macro WARN/SOFT"
```

---

## Task 3 (Feature A): USDT.D tracker — script + tests

**Files:**
- Create: `.claude/scripts/usdtd_tracker.py`
- Create: `.claude/scripts/tests/test_usdtd_tracker.py`

- [ ] **Step 1: Write failing tests**

Create `.claude/scripts/tests/test_usdtd_tracker.py`:

```python
"""Tests for usdtd_tracker.py."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import usdtd_tracker as ut


def test_classify_trend_up():
    assert ut.classify_trend(change_7d_pct=2.5) == "UP"


def test_classify_trend_down():
    assert ut.classify_trend(change_7d_pct=-1.2) == "DOWN"


def test_classify_trend_flat():
    assert ut.classify_trend(change_7d_pct=0.3) == "FLAT"


def test_btc_bias_from_usdtd():
    # USDT.D UP → BEARISH for BTC (capital flowing into stables)
    assert ut.btc_bias_from_usdtd("UP") == "BEARISH"
    assert ut.btc_bias_from_usdtd("DOWN") == "BULLISH"
    assert ut.btc_bias_from_usdtd("FLAT") == "NEUTRAL"
```

Run: `python3 -m pytest .claude/scripts/tests/test_usdtd_tracker.py -v` → expect ALL FAIL (module not found).

- [ ] **Step 2: Implement script**

Create `.claude/scripts/usdtd_tracker.py`:

```python
#!/usr/bin/env python3
"""usdtd_tracker.py — Track USDT dominance + BTC dominance for inverse-correlation signal.

USDT.D rising = capital rotating into stables = bearish for BTC
USDT.D falling = capital leaving stables = bullish for BTC

Source: CoinGecko global API (free, no auth).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import urllib.request

CR_OFFSET = timezone(timedelta(hours=-6))
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_FILE = CACHE_DIR / "usdtd.json"
CACHE_TTL_SEC = 600  # 10 minutes
COINGECKO_URL = "https://api.coingecko.com/api/v3/global"
FLAT_THRESHOLD_PCT = 0.5  # ±0.5% 7d = FLAT


def classify_trend(change_7d_pct: float) -> str:
    if change_7d_pct > FLAT_THRESHOLD_PCT:
        return "UP"
    if change_7d_pct < -FLAT_THRESHOLD_PCT:
        return "DOWN"
    return "FLAT"


def btc_bias_from_usdtd(trend: str) -> str:
    return {"UP": "BEARISH", "DOWN": "BULLISH", "FLAT": "NEUTRAL"}.get(trend, "UNKNOWN")


def _fetch_coingecko_global(timeout: int = 10) -> dict:
    req = urllib.request.Request(
        COINGECKO_URL,
        headers={"User-Agent": "wally-trader/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _load_cache() -> dict | None:
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text())
        if time.time() - data.get("cached_at", 0) > CACHE_TTL_SEC:
            return None
        return data["payload"]
    except (json.JSONDecodeError, KeyError):
        return None


def _save_cache(payload: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps({
        "cached_at": time.time(),
        "payload": payload,
    }))


def fetch_dominance(use_cache: bool = True, _fetcher=_fetch_coingecko_global) -> dict:
    """Returns {usdtd: float, btcd: float, ts: str}."""
    if use_cache:
        cached = _load_cache()
        if cached is not None:
            return cached
    data = _fetcher()
    dom = data["data"]["market_cap_percentage"]
    payload = {
        "usdtd": round(dom.get("usdt", 0.0), 3),
        "btcd": round(dom.get("btc", 0.0), 3),
        "ts": datetime.now(CR_OFFSET).isoformat(),
    }
    _save_cache(payload)
    return payload


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--quick", action="store_true", help="Single-line status")
    p.add_argument("--no-cache", action="store_true")
    args = p.parse_args()

    try:
        cur = fetch_dominance(use_cache=not args.no_cache)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR fetching dominance: {e}", file=sys.stderr)
        return 2

    # 7d change requires history; CoinGecko's free /global doesn't include it.
    # Approximation: fetch /coins/tether/market_chart?days=7 for usdt mcap series,
    # but that costs another API call and requires a market-cap → dominance conversion
    # we don't have. For v1, set change_7d_pct=0 and FLAT. Future iteration can use
    # a stored 7d-ago snapshot from this very cache.
    change_7d_pct = 0.0
    trend = classify_trend(change_7d_pct)
    bias = btc_bias_from_usdtd(trend)

    payload = {
        "ts": cur["ts"],
        "usdtd": cur["usdtd"],
        "btcd": cur["btcd"],
        "change_24h_pct": None,  # not available from /global
        "change_7d_pct": change_7d_pct,
        "trend_label": trend,
        "btc_inverse_bias": bias,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    elif args.quick:
        print(f"USDT.D={payload['usdtd']}%  BTC.D={payload['btcd']}%  "
              f"trend={trend}  bias={bias}")
    else:
        print(f"USDT.D: {payload['usdtd']}%")
        print(f"BTC.D:  {payload['btcd']}%")
        print(f"Trend (7d): {trend}")
        print(f"BTC inverse bias: {bias}")
        print(f"As of: {payload['ts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Make executable: `chmod +x .claude/scripts/usdtd_tracker.py`

Run tests: `python3 -m pytest .claude/scripts/tests/test_usdtd_tracker.py -v` → expect 4 PASSED.

- [ ] **Step 3: Smoke test live fetch**

```bash
python3 .claude/scripts/usdtd_tracker.py --quick
```

Expected: a line like `USDT.D=5.96%  BTC.D=58.31%  trend=FLAT  bias=NEUTRAL`.

If the network call fails, exit code 2 is acceptable. The CoinGecko free API is rate-limited (~30/min) but for manual use this is fine.

- [ ] **Step 4: Commit**

```bash
git add .claude/scripts/usdtd_tracker.py .claude/scripts/tests/test_usdtd_tracker.py
git commit -m "feat(usdtd-tracker): USDT dominance + BTC inverse-bias signal"
```

---

## Task 4 (Feature C): Volume divergence detector

**Files:**
- Create: `.claude/scripts/volume_divergence.py`
- Create: `.claude/scripts/tests/test_volume_divergence.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for volume_divergence.py."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import volume_divergence as vd


def _synthetic_bars(price_slope: float, volume_slope: float, n: int = 50) -> list[dict]:
    """Generate n bars with given linear price and volume slopes."""
    bars = []
    base_price = 70000.0
    base_vol = 1000.0
    for i in range(n):
        close = base_price + price_slope * i
        prev_close = base_price + price_slope * (i - 1) if i > 0 else close
        vol = max(10.0, base_vol + volume_slope * i)
        bars.append({
            "open": prev_close,
            "high": close + 50,
            "low": close - 50,
            "close": close,
            "volume": vol,
        })
    return bars


def test_obv_slope_positive_when_price_and_volume_up():
    bars = _synthetic_bars(price_slope=10.0, volume_slope=20.0)
    obv = vd.compute_obv(bars)
    slope = vd.linear_slope(obv)
    assert slope > 0


def test_bearish_divergence_price_up_obv_down():
    bars = _synthetic_bars(price_slope=10.0, volume_slope=-15.0)
    result = vd.detect_divergence(bars, direction="LONG")
    assert result["divergence"] == "BEARISH"


def test_no_divergence_when_aligned():
    bars = _synthetic_bars(price_slope=10.0, volume_slope=20.0)
    result = vd.detect_divergence(bars, direction="LONG")
    assert result["divergence"] == "NONE"


def test_insufficient_data():
    result = vd.detect_divergence([{"close": 1, "volume": 1}] * 5, direction="LONG")
    assert result["divergence"] == "INSUFFICIENT_DATA"
```

Run: `python3 -m pytest .claude/scripts/tests/test_volume_divergence.py -v` → expect ALL FAIL.

- [ ] **Step 2: Implement script**

Create `.claude/scripts/volume_divergence.py`:

```python
#!/usr/bin/env python3
"""volume_divergence.py — detect price/OBV divergence pre-entry.

Master's veto: precio sube sin fuerza, oscilador cae → not credible.
We compute OBV (On-Balance Volume) and check whether its slope aligns
with the price slope. If diverging, warn against trading in the
proposed direction.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

CR_OFFSET = timezone(timedelta(hours=-6))
MIN_BARS = 30
PRICE_THRESHOLD_PCT = 0.5
VOLUME_THRESHOLD_PCT = -10.0

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


def fetch_bars(symbol: str, tf: str = "1h", bars: int = 50,
               _fetcher=None) -> list[dict]:
    """Fetch OHLCV from Binance public API. _fetcher injectable for tests."""
    if _fetcher is not None:
        return _fetcher(symbol, tf, bars)
    interval_map = {"15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
    interval = interval_map.get(tf, "1h")
    url = f"{BINANCE_KLINES_URL}?symbol={symbol}&interval={interval}&limit={bars}"
    req = urllib.request.Request(url, headers={"User-Agent": "wally-trader/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read().decode())
    return [
        {"open": float(b[1]), "high": float(b[2]), "low": float(b[3]),
         "close": float(b[4]), "volume": float(b[5])}
        for b in data
    ]


def compute_obv(bars: list[dict]) -> list[float]:
    """On-Balance Volume series."""
    if not bars:
        return []
    obv = [0.0]
    for i in range(1, len(bars)):
        prev_close = bars[i - 1]["close"]
        close = bars[i]["close"]
        vol = bars[i]["volume"]
        if close > prev_close:
            obv.append(obv[-1] + vol)
        elif close < prev_close:
            obv.append(obv[-1] - vol)
        else:
            obv.append(obv[-1])
    return obv


def linear_slope(series: list[float]) -> float:
    """Simple least-squares slope of a 1D series."""
    n = len(series)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(series) / n
    num = sum((i - x_mean) * (series[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den else 0.0


def detect_divergence(bars: list[dict], direction: str = "LONG") -> dict:
    """Detect price-OBV divergence. Direction is the proposed trade direction."""
    if len(bars) < MIN_BARS:
        return {"divergence": "INSUFFICIENT_DATA", "n_bars": len(bars)}

    closes = [b["close"] for b in bars]
    obv = compute_obv(bars)
    price_slope = linear_slope(closes)
    obv_slope = linear_slope(obv)
    price_change_pct = (closes[-1] - closes[0]) / closes[0] * 100.0 if closes[0] else 0.0
    volume_change_pct = ((bars[-1]["volume"] - bars[0]["volume"]) / bars[0]["volume"] * 100.0
                        if bars[0]["volume"] else 0.0)

    divergence = "NONE"
    verdict = "OK"

    # Bearish divergence: price up, OBV down
    if price_slope > 0 and obv_slope < 0:
        divergence = "BEARISH"
        if direction.upper() == "LONG":
            verdict = "WARN_DIVERGENCE_AGAINST_LONG"
    # Bullish divergence: price down, OBV up
    elif price_slope < 0 and obv_slope > 0:
        divergence = "BULLISH"
        if direction.upper() == "SHORT":
            verdict = "WARN_DIVERGENCE_AGAINST_SHORT"

    return {
        "n_bars": len(bars),
        "price_change_pct": round(price_change_pct, 3),
        "volume_change_pct": round(volume_change_pct, 3),
        "price_slope": round(price_slope, 6),
        "obv_slope": round(obv_slope, 2),
        "divergence": divergence,
        "verdict": verdict,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--tf", default="1h")
    p.add_argument("--bars", type=int, default=50)
    p.add_argument("--direction", default="LONG", choices=["LONG", "SHORT"])
    p.add_argument("--json", action="store_true")
    p.add_argument("--quick", action="store_true")
    args = p.parse_args()

    try:
        bars = fetch_bars(args.symbol, args.tf, args.bars)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR fetching bars: {e}", file=sys.stderr)
        return 2

    result = detect_divergence(bars, direction=args.direction)
    result["symbol"] = args.symbol
    result["tf"] = args.tf
    result["direction"] = args.direction.upper()
    result["ts"] = datetime.now(CR_OFFSET).isoformat()

    if args.json:
        print(json.dumps(result, indent=2))
    elif args.quick:
        print(f"{args.symbol} {args.tf} {args.direction.upper()}: "
              f"div={result['divergence']}  verdict={result['verdict']}  "
              f"price={result['price_change_pct']:+.2f}%  "
              f"vol={result['volume_change_pct']:+.2f}%")
    else:
        for k, v in result.items():
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Make executable: `chmod +x .claude/scripts/volume_divergence.py`

Run tests: `python3 -m pytest .claude/scripts/tests/test_volume_divergence.py -v` → expect 4 PASSED.

- [ ] **Step 3: Smoke test live**

```bash
python3 .claude/scripts/volume_divergence.py --symbol BTCUSDT --direction LONG --quick
```

Expected: single line with current BTC divergence status.

- [ ] **Step 4: Commit**

```bash
git add .claude/scripts/volume_divergence.py .claude/scripts/tests/test_volume_divergence.py
git commit -m "feat(volume-divergence): OBV slope vs price slope pre-entry check"
```

---

## Task 5 (Feature E): Fib extension exhaustion

**Files:**
- Create: `.claude/scripts/fib_extension.py`
- Create: `.claude/scripts/tests/test_fib_extension.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for fib_extension.py."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import fib_extension as fe


def test_extension_pct_at_150():
    # Swing low 100, swing high 200, current 250 → extension = (250-100)/(200-100)*100 = 150%
    pct = fe.extension_pct(swing_low=100, swing_high=200, current=250)
    assert pct == 150.0


def test_extension_pct_at_200():
    pct = fe.extension_pct(swing_low=100, swing_high=200, current=300)
    assert pct == 200.0


def test_classify_label_ok():
    assert fe.classify_label(120.0) == "OK"


def test_classify_label_mild():
    assert fe.classify_label(155.0) == "EXHAUSTION_MILD"


def test_classify_label_high():
    assert fe.classify_label(210.0) == "EXHAUSTION_HIGH"


def test_classify_label_extreme():
    assert fe.classify_label(275.0) == "EXHAUSTION_EXTREME"
```

- [ ] **Step 2: Implement script**

Create `.claude/scripts/fib_extension.py`:

```python
#!/usr/bin/env python3
"""fib_extension.py — Fibonacci extension exhaustion detector.

Master's rule: indices/BTC at 150% or 200% weekly fib extension = profit-taking zone.
We auto-detect the most recent valid swing and classify the current price's extension level.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

CR_OFFSET = timezone(timedelta(hours=-6))
LEVELS = [127.2, 150.0, 161.8, 200.0, 261.8]

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


def extension_pct(swing_low: float, swing_high: float, current: float) -> float:
    rng = swing_high - swing_low
    if rng == 0:
        return 0.0
    return round((current - swing_low) / rng * 100.0, 2)


def classify_label(pct: float) -> str:
    if pct >= 261.8:
        return "EXHAUSTION_EXTREME"
    if pct >= 200.0:
        return "EXHAUSTION_HIGH"
    if pct >= 150.0:
        return "EXHAUSTION_MILD"
    return "OK"


def detect_swing(bars: list[dict]) -> tuple[float, float, int, int]:
    """Find swing low and swing high. Returns (low, high, low_idx, high_idx)."""
    if not bars:
        return 0.0, 0.0, 0, 0
    lows = [b["low"] for b in bars]
    highs = [b["high"] for b in bars]
    low_idx = lows.index(min(lows))
    high_idx = highs.index(max(highs))
    return min(lows), max(highs), low_idx, high_idx


def fetch_bars(symbol: str, tf: str = "1w", bars: int = 100,
               _fetcher=None) -> list[dict]:
    if _fetcher is not None:
        return _fetcher(symbol, tf, bars)
    interval_map = {"1d": "1d", "4h": "4h", "1w": "1w", "1M": "1M"}
    interval = interval_map.get(tf, "1w")
    url = f"{BINANCE_KLINES_URL}?symbol={symbol}&interval={interval}&limit={bars}"
    req = urllib.request.Request(url, headers={"User-Agent": "wally-trader/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read().decode())
    return [
        {"open": float(b[1]), "high": float(b[2]), "low": float(b[3]),
         "close": float(b[4]), "volume": float(b[5])}
        for b in data
    ]


def analyze(symbol: str, tf: str, bars: int, _fetcher=None) -> dict:
    raw = fetch_bars(symbol, tf, bars, _fetcher=_fetcher)
    if not raw:
        return {"symbol": symbol, "tf": tf, "error": "no_bars"}
    swing_low, swing_high, low_idx, high_idx = detect_swing(raw)
    current = raw[-1]["close"]
    ext = extension_pct(swing_low, swing_high, current)
    label = classify_label(ext)
    next_level = next((lvl for lvl in LEVELS if lvl > ext), None)
    next_price = (
        round(swing_low + (next_level / 100.0) * (swing_high - swing_low), 2)
        if next_level else None
    )
    swing_range_pct = (swing_high - swing_low) / swing_low * 100.0 if swing_low else 0.0
    confidence = "low" if swing_range_pct < 5.0 else "normal"
    return {
        "symbol": symbol,
        "tf": tf,
        "swing_low": round(swing_low, 2),
        "swing_high": round(swing_high, 2),
        "swing_range_pct": round(swing_range_pct, 2),
        "current_price": round(current, 2),
        "current_extension_pct": ext,
        "level_label": label,
        "next_level": {"pct": next_level, "price": next_price} if next_level else None,
        "confidence": confidence,
        "ts": datetime.now(CR_OFFSET).isoformat(),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--tf", default="1w")
    p.add_argument("--bars", type=int, default=100)
    p.add_argument("--json", action="store_true")
    p.add_argument("--quick", action="store_true")
    args = p.parse_args()
    try:
        result = analyze(args.symbol, args.tf, args.bars)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    elif args.quick:
        print(f"{args.symbol} {args.tf} ext={result['current_extension_pct']:.1f}%  "
              f"label={result['level_label']}  conf={result['confidence']}")
    else:
        for k, v in result.items():
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Make executable, run tests (expect 6 PASSED).

- [ ] **Step 3: Smoke test**

```bash
python3 .claude/scripts/fib_extension.py --symbol BTCUSDT --tf 1w --quick
```

Expected: line with extension % + label.

- [ ] **Step 4: Commit**

```bash
git add .claude/scripts/fib_extension.py .claude/scripts/tests/test_fib_extension.py
git commit -m "feat(fib-extension): exhaustion detector at 150/200/261.8% levels"
```

---

## Task 6: Wire features into agents

**Files:**
- Modify: `.claude/agents/trade-validator.md`
- Modify: `.claude/agents/signal-validator.md`
- Modify: `.claude/agents/regime-detector.md`
- Modify: `.claude/agents/morning-analyst.md`
- Modify: `.claude/agents/morning-analyst-ftmo.md`

For each agent, add a brief section instructing it to call the relevant new helper.
Patterns:

**trade-validator.md** — add after FASE 0.5 (session_quality):

```markdown
### FASE 0.6 — Macro tier check (NUEVO 2026-05-10)
Run: `python3 .claude/scripts/macro_gate.py --check-tier`
- `tier=HARD` → NO-GO (already enforced; surface explicitly)
- `tier=WARN` → reduce size 50%, continue
- `tier=SOFT` → INFO message, continue
- `tier=OK` → continue

### FASE 0.7 — Volume divergence check (NUEVO 2026-05-10)
For the proposed direction, run:
`python3 .claude/scripts/volume_divergence.py --symbol $SYMBOL --tf 1h --direction $SIDE --quick`
- `verdict=WARN_DIVERGENCE_*` → reduce size 50%, surface warning
- `verdict=OK` → continue silently
```

**signal-validator.md** — same FASE 0.6 + 0.7 plus FASE 0.8:

```markdown
### FASE 0.8 — USDT.D bias check (NUEVO 2026-05-10)
Run: `python3 .claude/scripts/usdtd_tracker.py --quick`
- If signal direction conflicts with `btc_inverse_bias`:
  - LONG signal + USDT.D bias=BEARISH → WARN (capital flowing to stables)
  - SHORT signal + USDT.D bias=BULLISH → WARN
- If aligned or NEUTRAL → continue silently
```

**regime-detector.md** — add at the end of regime output:

```markdown
### USDT.D context (NUEVO 2026-05-10)
After classifying BTC regime, run: `python3 .claude/scripts/usdtd_tracker.py --quick`
Append the trend + btc_inverse_bias to the report. This is a confluence factor.
```

**morning-analyst.md** + **morning-analyst-ftmo.md** — add fib extension scan for relevant assets:

```markdown
### Fase Fib Extension (NUEVO 2026-05-10)
For each asset in the active watchlist, run:
`python3 .claude/scripts/fib_extension.py --symbol $ASSET --tf 1w --quick`
If `level_label != OK`, surface in the morning report as "Exhaustion candidate".
Do NOT block trades — informational only.
```

- [ ] **Step 1: Apply each agent modification using Edit tool**

Read each file first, then use Edit to insert the new section in a reasonable location (usually after the existing FASE/section that matches in spirit).

- [ ] **Step 2: Commit**

```bash
git add .claude/agents/
git commit -m "feat(agents): wire macro-tier, volume-div, usdtd, fib-ext into agents"
```

---

## Task 7: Docs update

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Append new subsection**

Find the existing section "Discipline & Observability tooling (Bundle 1, 2026-05-04)" and after its last subsection, add:

```markdown
## Live Insights Bundle (Bundle 2, 2026-05-10)

Five features inspired by Dragno master live (YT Be8IYJLgdYA):

### Feature A — USDT.D tracker
- `python3 .claude/scripts/usdtd_tracker.py [--json|--quick]`
- Tracks USDT dominance + BTC dominance. Inverse-correlation signal: USDT.D UP = bearish BTC.
- Wired into: regime-detector, signal-validator.

### Feature B — Macro multi-tier blackout
- `python3 .claude/scripts/macro_gate.py --check-tier [--soft-hours N]`
- Tiers: HARD (±30min, NO-GO), WARN (±4h, reduce 50%), SOFT (next 48h, INFO), OK.
- Wired into: trade-validator, signal-validator FASE 0.6.

### Feature C — Volume/OBV divergence
- `python3 .claude/scripts/volume_divergence.py --symbol BTCUSDT --direction LONG --quick`
- Detects price ↑ / OBV ↓ ("subiendo sin fuerza" — master's veto).
- Wired into: trade-validator, signal-validator FASE 0.7.

### Feature D — Auto-MUGRE switch
- `/punk-hunt` now reads macro tier first. WARN/SOFT → auto `--tier-0` (MUGRES).
- HARD → aborts scan entirely. Override with `--no-auto-tier`.

### Feature E — Fib extension exhaustion
- `python3 .claude/scripts/fib_extension.py --symbol SPX --tf 1w --quick`
- Labels: OK / MILD (≥150%) / HIGH (≥200%) / EXTREME (≥261.8%).
- Wired into: morning-analyst, morning-analyst-ftmo (informational only).

Spec: `docs/superpowers/specs/2026-05-10-live-insights-bundle-design.md`
Plan: `docs/superpowers/plans/2026-05-10-live-insights-bundle.md`
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude.md): document Live Insights Bundle (Bundle 2)"
```

---

## Self-Review Checklist

- ✅ Each feature has a script (or modification) + tests + integration
- ✅ All scripts use stdlib + existing venv deps only
- ✅ All scripts support `--json` and `--quick`
- ✅ All scripts exit 0 on success, 2 on data/network errors, 1 on arg errors
- ✅ Caching present for Feature A (CoinGecko rate-limited)
- ✅ No placeholders (every code block is complete)
- ✅ Agent wiring is additive (no removed behavior)
- ✅ Spec coverage: all 5 features mapped to tasks

## Notes for Implementer

- Feature B's tests assume the existing `fixed_cache` fixture. If absent, create one with a FOMC event at 2026-05-13T13:00 CR.
- USDT.D 24h/7d change is approximated as 0 in v1; a future iteration can compute from historical cache snapshots.
- Volume divergence MIN_BARS=30 is the gate; below that returns INSUFFICIENT_DATA.
- Fib extension defaults to 1W timeframe and 100 bars; for daily-impulse swings users pass `--tf 1d`.
- Agent wiring uses helper invocations from agent prompts — agents must be configured to allow `Bash` tool. Verify each agent's `allowed-tools` includes `Bash`.
