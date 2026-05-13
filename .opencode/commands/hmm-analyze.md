# /hmm-analyze

Run an HMM regime analysis on a single asset × strategy combination. Strictly diagnostic — never modifies live state.

## Usage

```
/hmm-analyze <SYMBOL> <STRATEGY> [--html] [--suggest-mapping] [--force-refresh] [--seed N]
```

## Arguments

- `SYMBOL` — Binance Futures symbol (e.g., `ETHUSDT`). Case-insensitive.
- `STRATEGY` — one of: `A_VWAP`, `B_TrendPullback`, `C_BBSqueeze`, `D_MACDMomentum`, `E_RangeBounce`.

## Flags

- `--html` — also emit interactive plotly HTML report (requires plotly installed).
- `--suggest-mapping` — print a DRY-RUN diff for `regime_mapping.json` (never writes the file).
- `--force-refresh` — bypass the 1h OHLCV cache.
- `--seed N` — change HMM random seed (default 42) for reproducibility experiments.

## Output

Markdown report saved to `docs/hmm_analysis/<SYMBOL>_<STRATEGY>_<YYYY-MM-DD>.md` with 7 sections (Summary, Regime Distribution, Transition Matrix, Backtest per Regime, Recommendations, Caveats). Optional HTML alongside.

## Steps Claude executes

1. Verify profile (no profile guard — tool works for any profile, diagnostic only).
2. Run `.claude/scripts/.venv/bin/python .claude/scripts/hmm_analyze.py --symbol <SYMBOL> --strategy <STRATEGY> [...]`.
3. Print the produced markdown report path.
4. If `--suggest-mapping`, print the dry-run diff to the user along with a reminder that the file is unchanged.

## Reglas

- NUNCA modifica `regime_mapping.json`.
- NUNCA toca paths live (`/punk-smart`, `/signal`, `/validate`).
- Si la red está caída y la cache es stale → reporta error con exit code 3.
- Si el símbolo no está listado en Binance Futures → exit code 2.

## Ejemplo

```
/hmm-analyze ETHUSDT A_VWAP --suggest-mapping
```

Output esperado:
- Markdown en `docs/hmm_analysis/ETHUSDT_A_VWAP_2026-05-13.md`
- Diff DRY-RUN impreso a stdout
