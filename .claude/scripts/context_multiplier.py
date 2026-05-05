#!/usr/bin/env python3
"""
context_multiplier.py — Calcula multiplicador contextual para ajuste adaptativo de TPs/SL.

Usado por:
- /punk-hunt → al construir setup en Phase 6 (TPs/SL adaptativos al entry)
- /punk-watch → al revisar trade activo (recalcular TPs según contexto cambiante)

Filosofía: "Ganar lo que da el mercado, no lo que yo quiero."
- Contexto débil (Asia early + ranging + low vol + smart money contrario) → TPs cortos
- Contexto fuerte (NY overlap + trending alineado + high vol + smart money alineado) → TPs amplios

Factores ortogonales que se multiplican entre sí (rango ~0.15 a ~3.5):
- hour_factor: 0.5 (Asia muerta) a 1.5 (NY/London overlap)
- regime_factor: 0.6 (ranging) a 1.4 (trending alineado)
- volatility_factor: 0.5 (low ATR) a 1.5 (high ATR)
- smart_money_factor: 0.7 (contrario) a 1.3 (alineado)

CLI:
    python3 context_multiplier.py --side SHORT --atr-pct 0.42 --regime TRENDING --ls-smart 0.95
"""

import argparse
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo


def hour_factor(now_cr=None):
    """Factor según hora CR (UTC-6).

    Mapeo basado en ventanas de mayor liquidez/volumen institucional en cripto:
    - 00:00-05:00: Asia muerta (0.5)
    - 05:00-08:00: London open transition (0.8)
    - 08:00-12:00: London/NY overlap (1.5) — mejor del día
    - 12:00-16:00: NY active (1.2)
    - 16:00-20:00: NY close (0.9)
    - 20:00-24:00: Asia early (0.6)
    """
    if now_cr is None:
        now_cr = datetime.now(ZoneInfo("America/Costa_Rica"))
    h = now_cr.hour
    if 0 <= h < 5:
        return 0.5
    if 5 <= h < 8:
        return 0.8
    if 8 <= h < 12:
        return 1.5
    if 12 <= h < 16:
        return 1.2
    if 16 <= h < 20:
        return 0.9
    return 0.6


def regime_factor(market_regime, side, regime_pct=0):
    """Factor según régimen y alineación con dirección del trade.

    market_regime: "RANGING" | "TRENDING_UP" | "TRENDING_DOWN" | "VOLATILE" | "TRENDING"
    side: "LONG" | "SHORT"
    regime_pct: opcional, % strength del régimen (0-100, del Neptune Range Filter)
    """
    r = market_regime.upper()
    s = side.upper()

    if r == "RANGING":
        return 0.7  # less margin for both sides

    if r == "VOLATILE":
        return 1.5  # más espacio (high vol favors wider TPs)

    # TRENDING_UP / TRENDING_DOWN / TRENDING
    if r in ("TRENDING_UP", "TRENDING"):
        if s == "LONG":
            base = 1.4  # con la tendencia
        else:  # SHORT contra-trend
            base = 0.7
    elif r == "TRENDING_DOWN":
        if s == "SHORT":
            base = 1.4
        else:  # LONG contra-trend
            base = 0.7
    else:
        base = 1.0

    # Si regime_pct alto (>70), amplifica el factor
    if regime_pct >= 70:
        return base * 1.1
    return base


def volatility_factor(atr_pct):
    """Factor según ATR % del precio actual (15m base).

    atr_pct: ATR(14) / precio × 100, valor típico 0.2-2.0%
    """
    if atr_pct < 0.3:
        return 0.5
    if atr_pct < 0.6:
        return 0.8
    if atr_pct < 1.0:
        return 1.0
    if atr_pct < 1.5:
        return 1.3
    return 1.5


def smart_money_factor(ls_ratio_smart, side):
    """Factor según L/S ratio Smart Money (top traders Binance) alineado con dirección.

    ls_ratio_smart > 1.0 = más longs que shorts en smart money
    ls_ratio_smart < 1.0 = más shorts que longs

    side: "LONG" | "SHORT"
    """
    s = side.upper()
    if s == "LONG":
        if ls_ratio_smart > 1.2:
            return 1.3
        if ls_ratio_smart > 1.0:
            return 1.1
        if ls_ratio_smart > 0.9:
            return 0.9
        return 0.7
    else:  # SHORT
        if ls_ratio_smart < 0.8:
            return 1.3
        if ls_ratio_smart < 1.0:
            return 1.1
        if ls_ratio_smart < 1.1:
            return 0.9
        return 0.7


def time_target_factor(target_hold_minutes=60):
    """Factor para ajustar TPs al tiempo objetivo de hold del usuario.

    Filosofía bitunix: 1 trade cada ~1h, capturar lo que da el mercado en ventana corta.
    Si target_hold = 60 min → TPs deben ser alcanzables en ~4 velas de 15m.

    target_hold_minutes:
    - 30 min → factor 0.5 (TPs muy cortos, scalp puro)
    - 60 min → factor 1.0 (target nominal 1h)
    - 120 min → factor 1.5 (TPs amplios, swing intraday)
    - 240 min+ → factor 2.0 (TPs amplios, hold overnight)
    """
    if target_hold_minutes <= 30:
        return 0.5
    if target_hold_minutes <= 60:
        return 1.0
    if target_hold_minutes <= 120:
        return 1.5
    return 2.0


def calc_context_multiplier(
    side,
    atr_pct,
    market_regime,
    ls_ratio_smart=1.0,
    regime_pct=0,
    target_hold_minutes=60,
    now_cr=None,
):
    """Calcula multiplicador combinado (con time target).

    Rango típico: 0.10 (todo malo + scalp) a 5.0 (todo perfecto + swing).

    Returns: dict con multiplicador final + breakdown de factores
    """
    f_hour = hour_factor(now_cr)
    f_regime = regime_factor(market_regime, side, regime_pct)
    f_vol = volatility_factor(atr_pct)
    f_sm = smart_money_factor(ls_ratio_smart, side)
    f_time = time_target_factor(target_hold_minutes)
    multiplier = f_hour * f_regime * f_vol * f_sm * f_time
    return {
        "multiplier": round(multiplier, 3),
        "target_hold_minutes": target_hold_minutes,
        "factors": {
            "hour": round(f_hour, 2),
            "regime": round(f_regime, 2),
            "volatility": round(f_vol, 2),
            "smart_money": round(f_sm, 2),
            "time_target": round(f_time, 2),
        },
        "interpretation": _interpret(multiplier),
    }


def _interpret(m):
    if m < 0.3:
        return "DÉBIL — TPs muy cortos, salida rápida recomendada"
    if m < 0.6:
        return "BAJO — TPs cortos, contexto poco favorable"
    if m < 1.0:
        return "MODERADO — TPs balanceados, contexto mixto"
    if m < 1.5:
        return "BUENO — TPs amplios, contexto favorable"
    return "EXCELENTE — TPs muy amplios, dejar correr"


def sl_atr_multiplier(atr_pct):
    """Multiplier para SL basado en volatilidad actual de la moneda.

    Filosofía: monedas muy volátiles necesitan SL más amplio para no salirse por
    mechas falsas. Monedas low-vol pueden usar SL apretado.

    atr_pct: ATR(14) / precio × 100

    Returns: multiplicador para aplicar a ATR absoluto
    - < 0.3% (low vol majors quietos): SL 1.0×ATR
    - 0.3-0.6% (normal): SL 1.3×ATR
    - 0.6-1.0% (active): SL 1.6×ATR
    - 1.0-1.5% (high vol): SL 2.2×ATR
    - > 1.5% (very volatile, típico memecoins): SL 3.0×ATR
    """
    if atr_pct < 0.3:
        return 1.0
    if atr_pct < 0.6:
        return 1.3
    if atr_pct < 1.0:
        return 1.6
    if atr_pct < 1.5:
        return 2.2
    return 3.0


def calc_adaptive_levels(entry, side, atr, context_mult, atr_pct=None, sl_atr_mult=None, base_tp_atr_mult=3.0):
    """Calcula SL/TP1/TP2/TP3 adaptativos basado en ATR + context_multiplier + volatility.

    SL: adaptativo por volatility (sl_atr_multiplier basado en atr_pct).
        Si user pasa sl_atr_mult explícito, usa ese (override estructural).
    TPs: base 3×ATR escalado por context_multiplier × {0.5, 1.0, 2.0}

    Resultado:
    - SL: amplio si moneda volátil, apretado si quieta
    - TPs: cortos en contexto débil, largos en contexto fuerte

    Para usar SL dinámico, pasar atr_pct (no sl_atr_mult).
    """
    if sl_atr_mult is None:
        if atr_pct is None:
            sl_atr_mult = 1.5  # fallback legacy
        else:
            sl_atr_mult = sl_atr_multiplier(atr_pct)

    sl_distance = sl_atr_mult * atr
    base_tp = base_tp_atr_mult * atr

    tp1_distance = base_tp * context_mult * 0.5
    tp2_distance = base_tp * context_mult * 1.0
    tp3_distance = base_tp * context_mult * 2.0

    if side.upper() == "LONG":
        levels = {
            "sl": round(entry - sl_distance, 4),
            "tp1": round(entry + tp1_distance, 4),
            "tp2": round(entry + tp2_distance, 4),
            "tp3": round(entry + tp3_distance, 4),
        }
    else:
        levels = {
            "sl": round(entry + sl_distance, 4),
            "tp1": round(entry - tp1_distance, 4),
            "tp2": round(entry - tp2_distance, 4),
            "tp3": round(entry - tp3_distance, 4),
        }

    levels["distances_pct"] = {
        "sl": round(sl_distance / entry * 100, 3),
        "tp1": round(tp1_distance / entry * 100, 3),
        "tp2": round(tp2_distance / entry * 100, 3),
        "tp3": round(tp3_distance / entry * 100, 3),
    }
    levels["rr"] = {
        "tp1": round(tp1_distance / sl_distance, 2),
        "tp2": round(tp2_distance / sl_distance, 2),
        "tp3": round(tp3_distance / sl_distance, 2),
    }
    levels["sl_atr_mult_used"] = sl_atr_mult
    levels["sl_volatility_label"] = _sl_volatility_label(sl_atr_mult)
    return levels


def _sl_volatility_label(sl_mult):
    if sl_mult <= 1.0:
        return "TIGHT (low-vol asset, salida rápida)"
    if sl_mult <= 1.3:
        return "NORMAL (volatility típica)"
    if sl_mult <= 1.6:
        return "MODERADO (active asset)"
    if sl_mult <= 2.2:
        return "AMPLIO (high-vol, espacio para mechas)"
    return "MUY AMPLIO (memecoin/altcoin volátil)"


def detect_significant_change(old_levels, new_levels, threshold_pct=15.0):
    """Detecta si los nuevos TPs difieren >threshold_pct del original.

    Retorna lista de TPs que cambiaron significativamente.
    """
    significant = []
    for tp_key in ["tp1", "tp2", "tp3"]:
        old_d = old_levels.get("distances_pct", {}).get(tp_key)
        new_d = new_levels.get("distances_pct", {}).get(tp_key)
        if old_d is None or new_d is None:
            continue
        if old_d == 0:
            continue
        change_pct = abs(new_d - old_d) / old_d * 100
        if change_pct >= threshold_pct:
            significant.append({
                "level": tp_key,
                "old_distance_pct": old_d,
                "new_distance_pct": new_d,
                "change_pct": round(change_pct, 1),
                "direction": "EXTEND" if new_d > old_d else "REDUCE",
            })
    return significant


def main():
    p = argparse.ArgumentParser(description="Context multiplier para TPs adaptativos")
    p.add_argument("--side", required=True, choices=["LONG", "SHORT"])
    p.add_argument("--atr-pct", type=float, required=True, help="ATR(14) / precio × 100")
    p.add_argument("--regime", required=True,
                   choices=["RANGING", "TRENDING", "TRENDING_UP", "TRENDING_DOWN", "VOLATILE"])
    p.add_argument("--ls-smart", type=float, default=1.0, help="L/S ratio Smart Money (Binance top traders)")
    p.add_argument("--regime-pct", type=float, default=0, help="Range Filter strength % del Neptune")
    p.add_argument("--target-hold", type=int, default=60, help="Tiempo objetivo de hold en minutos (default 60 = 1h)")
    p.add_argument("--entry", type=float, help="Entry price (opcional, para calcular niveles)")
    p.add_argument("--atr", type=float, help="ATR absoluto (opcional, para calcular niveles)")
    p.add_argument("--json", action="store_true", help="Output JSON en vez de texto")
    args = p.parse_args()

    result = calc_context_multiplier(
        side=args.side,
        atr_pct=args.atr_pct,
        market_regime=args.regime,
        ls_ratio_smart=args.ls_smart,
        regime_pct=args.regime_pct,
        target_hold_minutes=args.target_hold,
    )

    if args.entry and args.atr:
        levels = calc_adaptive_levels(
            entry=args.entry,
            side=args.side,
            atr=args.atr,
            context_mult=result["multiplier"],
            atr_pct=args.atr_pct,
        )
        result["levels"] = levels

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        m = result["multiplier"]
        f = result["factors"]
        print(f"Context Multiplier: {m} ({result['interpretation']})")
        print(f"  hour={f['hour']} | regime={f['regime']} | vol={f['volatility']} | smart_money={f['smart_money']}")
        if "levels" in result:
            l = result["levels"]
            print(f"\nNiveles adaptativos para {args.side} @ {args.entry}:")
            print(f"  SL:  {l['sl']} ({l['distances_pct']['sl']}%)")
            print(f"  TP1: {l['tp1']} ({l['distances_pct']['tp1']}%) — R:R {l['rr']['tp1']}")
            print(f"  TP2: {l['tp2']} ({l['distances_pct']['tp2']}%) — R:R {l['rr']['tp2']}")
            print(f"  TP3: {l['tp3']} ({l['distances_pct']['tp3']}%) — R:R {l['rr']['tp3']}")


if __name__ == "__main__":
    main()
