"""No-fade pattern detector — flag pumps idiosyncratic donde el fade-the-pump NO funciona.

Lección 2026-05-11 (SAGA -$103): SAGA pumpeó +38.72% 24h con:
- Funding LOW (+0.005%/8h, NO retail FOMO)
- Vol 24h $232M (5-10x normal $20-50M)
- Sin BTC drag (BTC -0.08% mientras SAGA +38%)
- OI subiendo +17% en 4h

Esto es CATALYST-DRIVEN MOVE (news/listing/whale), NO retail squeeze.
El fade-the-pump SHORT NO funciona — necesita catalyst exhaustion para
revertir, no técnica.

Heurística: si todos los siguientes:
1. Price 24h chg ≥ +25% (pump material)
2. Funding rate ≤ +0.01% per 8h (no retail euphoria)
3. Vol 24h ≥ 4x avg 7d (real money flow)
4. BTC 24h chg dentro de ±1% (decoupled del macro)

→ NO_FADE_PATTERN = NO recomendar SHORT counter-trend.

Usage:
    python3 .claude/scripts/no_fade_pattern.py --symbol SAGAUSDT
    python3 .claude/scripts/no_fade_pattern.py --symbol BTCUSDT --json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Literal


BINANCE_FAPI = "https://fapi.binance.com"
THRESH_PUMP_24H_PCT = 25.0
THRESH_FUNDING_PCT_8H = 0.01  # 0.01% per 8h
THRESH_VOL_RATIO = 4.0
THRESH_BTC_DECOUPLED = 1.0


@dataclass
class FadePatternResult:
    symbol: str
    pump_24h_pct: float
    funding_pct_8h: float
    vol_24h_usd: float
    vol_avg_7d_usd: float
    vol_ratio: float
    btc_24h_pct: float
    is_decoupled_from_btc: bool
    no_fade_pattern: bool
    flags: list[str]
    recommendation: Literal["FADE_OK", "FADE_RISKY", "NO_FADE"]
    reason: str


def _fetch_json(url: str, timeout: float = 10.0) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "wally-trader/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _get_24h(symbol: str) -> dict:
    return _fetch_json(f"{BINANCE_FAPI}/fapi/v1/ticker/24hr?symbol={symbol}")  # type: ignore[return-value]


def _get_funding(symbol: str) -> float:
    """Returns funding rate as percent per 8h."""
    data = _fetch_json(f"{BINANCE_FAPI}/fapi/v1/premiumIndex?symbol={symbol}")
    return float(data["lastFundingRate"]) * 100  # type: ignore[index]


def _get_vol_avg_7d(symbol: str) -> float:
    """Average daily quote volume over last 7 days, in USD."""
    klines = _fetch_json(
        f"{BINANCE_FAPI}/fapi/v1/klines?symbol={symbol}&interval=1d&limit=8"
    )
    # Skip the most recent (incomplete) day for average
    completed = klines[:-1]  # type: ignore[index]
    if not completed:
        return 0.0
    quote_vols = [float(k[7]) for k in completed]
    return sum(quote_vols) / len(quote_vols)


def evaluate(symbol: str) -> FadePatternResult:
    flags: list[str] = []

    try:
        ticker = _get_24h(symbol)
        pump = float(ticker["lastPrice"]) and float(ticker["priceChangePercent"])
        vol_24h = float(ticker["quoteVolume"])
    except (urllib.error.URLError, KeyError, ValueError) as exc:
        flags.append(f"ticker_error: {exc}")
        pump, vol_24h = 0.0, 0.0

    try:
        funding = _get_funding(symbol)
    except (urllib.error.URLError, KeyError, ValueError) as exc:
        flags.append(f"funding_error: {exc}")
        funding = 0.0

    try:
        vol_avg = _get_vol_avg_7d(symbol)
    except (urllib.error.URLError, KeyError, ValueError) as exc:
        flags.append(f"vol_avg_error: {exc}")
        vol_avg = 0.0

    try:
        btc = _get_24h("BTCUSDT")
        btc_pct = float(btc["priceChangePercent"])
    except (urllib.error.URLError, KeyError, ValueError) as exc:
        flags.append(f"btc_error: {exc}")
        btc_pct = 0.0

    vol_ratio = vol_24h / vol_avg if vol_avg > 0 else 0.0
    decoupled = abs(btc_pct) < THRESH_BTC_DECOUPLED

    # Pattern checks
    is_pump = pump >= THRESH_PUMP_24H_PCT
    is_low_funding = funding <= THRESH_FUNDING_PCT_8H
    is_high_vol = vol_ratio >= THRESH_VOL_RATIO

    if is_pump:
        flags.append(f"pump_24h_{pump:.1f}%")
    if is_low_funding:
        flags.append(f"funding_low_{funding:.4f}%/8h")
    if is_high_vol:
        flags.append(f"vol_ratio_{vol_ratio:.1f}x")
    if decoupled:
        flags.append(f"decoupled_from_btc_{btc_pct:+.2f}%")

    # Decision
    no_fade = is_pump and is_low_funding and is_high_vol and decoupled

    if no_fade:
        reco: Literal["FADE_OK", "FADE_RISKY", "NO_FADE"] = "NO_FADE"
        reason = (
            f"NO_FADE_PATTERN detected: idiosyncratic catalyst-driven pump "
            f"({pump:+.1f}% 24h, funding {funding:.4f}%/8h, vol {vol_ratio:.1f}x avg, "
            f"BTC {btc_pct:+.2f}% decoupled). Counter-trend SHORT NO recomendado — "
            f"esperá catalyst exhaustion técnico antes de fade. Reference: SAGA 2026-05-11."
        )
    elif is_pump and (is_low_funding or is_high_vol):
        reco = "FADE_RISKY"
        reason = (
            f"FADE_RISKY: pump material ({pump:+.1f}%) pero algunos indicadores "
            f"sugieren catalyst, no FOMO. Si fade, HALF size + SL hard tight."
        )
    else:
        reco = "FADE_OK"
        reason = (
            f"Pattern compatible con fade-the-pump tradicional. "
            f"Pump {pump:+.1f}%, funding {funding:.4f}%/8h."
        )

    return FadePatternResult(
        symbol=symbol,
        pump_24h_pct=round(pump, 2),
        funding_pct_8h=round(funding, 4),
        vol_24h_usd=round(vol_24h, 2),
        vol_avg_7d_usd=round(vol_avg, 2),
        vol_ratio=round(vol_ratio, 2),
        btc_24h_pct=round(btc_pct, 2),
        is_decoupled_from_btc=decoupled,
        no_fade_pattern=no_fade,
        flags=flags,
        recommendation=reco,
        reason=reason,
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbol", required=True, help="Binance perpetual symbol e.g. SAGAUSDT")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    result = evaluate(args.symbol)

    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        emoji = {"FADE_OK": "🟢", "FADE_RISKY": "🟡", "NO_FADE": "🔴"}[result.recommendation]
        print(f"{emoji} {result.symbol} → {result.recommendation}")
        print(f"   pump_24h: {result.pump_24h_pct:+.2f}%")
        print(f"   funding (8h): {result.funding_pct_8h:.4f}%")
        print(f"   vol_24h: ${result.vol_24h_usd/1e6:.2f}M (avg 7d: ${result.vol_avg_7d_usd/1e6:.2f}M)")
        print(f"   vol_ratio: {result.vol_ratio:.2f}x")
        print(f"   BTC 24h: {result.btc_24h_pct:+.2f}% ({'DECOUPLED' if result.is_decoupled_from_btc else 'tracking'})")
        print(f"   flags: {result.flags}")
        print(f"   {result.reason}")

    # Exit codes:
    # 0 = FADE_OK, 1 = FADE_RISKY, 2 = NO_FADE (block recommended)
    return {"FADE_OK": 0, "FADE_RISKY": 1, "NO_FADE": 2}[result.recommendation]


if __name__ == "__main__":
    sys.exit(main())
