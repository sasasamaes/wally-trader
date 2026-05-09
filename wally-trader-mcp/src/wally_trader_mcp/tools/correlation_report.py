"""Correlation report MCP tool."""
from wally_core.portfolio import correlation_matrix


def correlation_report(symbols_csv: str, lookback_days: int = 30) -> dict:
    """Compute correlation matrix for comma-separated symbols.

    symbols_csv: 'BTCUSDT,ETHUSDT,...'
    """
    symbols = [s.strip() for s in symbols_csv.split(",") if s.strip()]
    matrix = correlation_matrix(symbols, lookback_days=lookback_days)

    # Convert to nested dict for JSON
    out = {}
    for (s1, s2), v in matrix.items():
        if s1 not in out:
            out[s1] = {}
        out[s1][s2] = v

    return {
        "symbols": symbols,
        "lookback_days": lookback_days,
        "matrix": out,
    }
