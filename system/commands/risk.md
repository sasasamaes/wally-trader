---
description: Calcula position sizing según el profile activo
allowed-tools: Agent
---

Calcula position sizing según el profile activo.

Pasos que ejecuta Claude:

1. Lee profile: `PROFILE=$(bash .claude/scripts/profile.sh get)`

2. SI profile == "retail":
   - Usa regla clásica 2% del capital actual (desde profiles/retail/config.md)
   - Despacha al agente `risk-manager` con parámetros retail
   - Fórmula: `risk_usd = capital * 0.02; size = risk_usd / (sl_distance / entry) / leverage`

3. SI profile == "ftmo":
   - Carga config desde `.claude/profiles/ftmo/config.md` (risk_per_trade_pct, leverage)
   - Lee equity actual via `python3 .claude/scripts/guardian.py --profile ftmo --action status`
   - Lee pip_value del asset desde `.claude/profiles/ftmo/memory/mt5_symbols.md`
   - Si pip_value es "PENDING" → ERROR: "Pip value de <asset> no validado. Pega screenshot MT5 Specification."
   - Fórmula:
     ```
     risk_usd = equity * (risk_per_trade_pct / 100)  # 0.5% por default
     sl_pips = abs(entry - sl)
     lots = risk_usd / (sl_pips * pip_value_per_lot)
     lots = round(lots, 2)
     ```
   - Simula worst-case en guardian:
     `python3 guardian.py --profile ftmo --action check-entry --asset <X> --entry <E> --sl <SL> --loss-if-sl <risk_usd>`
   - Si guardian retorna BLOCK_SIZE → aplica size_adjustment factor
   - Si BLOCK_HARD → NO-GO total

4. Output:
   - Lots (FTMO) o BTC size + margin (retail)
   - Capital a arriesgar ($X)
   - Leverage
   - Guardian veredicto (solo FTMO)

5. Siempre incluye disclaimer: "Leverage con dinero real puede liquidar capital. Tu decides."

Contexto del trade:
$ARGUMENTS
