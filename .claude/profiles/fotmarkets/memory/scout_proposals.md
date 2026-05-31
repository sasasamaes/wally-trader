# Fot-Scout Proposals — fotmarkets

Log de propuestas generadas por `/fot-scout` (NO son trades ejecutados — eso vive en
`trading_log.md` vía `/journal`). Sirve para medir el hit-rate del scanner por origen y
trackear el camino $50 → $500. Lo appendea el agente `fot-scout-analyst`.

Schema por entrada:

```
## YYYY-MM-DD HH:MM CR — SYMBOL SIDE
- Regime: <RANGE_CHOP|TREND_LEVE|...> | Strategy: <mean_reversion|ma_cross|...> | Score: N/100
- Entry: X | SL: Y (P pips) | TP: Z (R:R R) | Lots: L | Risk: $U (P%)
- Status: GO | NO-GO | WAIT | TENTATIVE | OVERRIDE_LOCKED
- Gates: macro=.. session=.. vol_div=.. min_rr=..
- Razón: <una línea>
- Capital al momento: $C ($C/500 = N%)
```

---

<!-- Las propuestas se appendean debajo de esta línea -->
