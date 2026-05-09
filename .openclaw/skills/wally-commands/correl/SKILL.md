---
name: correl
description: Pairwise correlation between symbols (last 30d returns)
version: 1.0.0
metadata:
  openclaw:
    tags:
    - wally-trader
    - command
    - slash
    category: trading-command
    requires_toolsets:
    - terminal
    - subagents
---
<!-- generated from system/commands/correl.md by adapters/openclaw/transform.py -->
<!-- OpenClaw invokes via /correl -->


# /correl — Symbol correlation report

Compute Pearson correlation between specified symbols using daily returns.

## Usage

```
/correl                              # default symbols (BTC, ETH, SOL, DYDX, LDO, ALGO)
/correl BTCUSDT,ETHUSDT,SOLUSDT      # custom symbols
/correl --window 7d                   # custom lookback
```

## Implementation

```bash
shared/wally_core/.venv/bin/python -c "
from wally_core.portfolio import correlation_matrix
import sys, json
symbols_str = '$ARGUMENTS' if '$ARGUMENTS' else 'BTCUSDT,ETHUSDT,SOLUSDT,DYDXUSDT,LDOUSDT,ALGOUSDT'
symbols = [s.strip() for s in symbols_str.split(',') if s.strip()]
matrix = correlation_matrix(symbols, lookback_days=30)
# Print as table
print('Correlation matrix (30d returns):')
print(' ' * 12, end='')
for s in symbols:
    print(f'{s:>10s}', end='')
print()
for s1 in symbols:
    print(f'{s1:>12s}', end='')
    for s2 in symbols:
        print(f'{matrix.get((s1, s2), 0):>10.3f}', end='')
    print()
"
```
