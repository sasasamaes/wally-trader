"""Regime detection agent.

Pure-logic ADX + DI classification comes from `wally_core.regime`. The
LLM layer adds plain-language interpretation + strategy recommendation
in the user's preferred language (Spanish technical mix per the project
convention).

Input payload:
    {
        "symbol": "BTCUSDT",
        "bars": [{"open":..., "high":..., "low":..., "close":..., "volume":...}, ...]
    }
"""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent


class RegimeAgent(BaseAgent):
    name = "regime"
    description = (
        "Detect current market regime (RANGE / TRENDING UP / TRENDING DOWN / "
        "VOLATILE) using ADX(14) + DI and recommend the strategy class."
    )
    input_schema = {
        "type": "object",
        "required": ["symbol", "bars"],
        "properties": {
            "symbol": {"type": "string", "description": "Ticker like BTCUSDT"},
            "bars": {
                "type": "array",
                "description": "OHLCV bars, at least 50 entries on the analysis timeframe.",
                "items": {"type": "object"},
            },
            "timeframe": {"type": "string", "default": "1H"},
        },
    }

    def system_prompt(self) -> str:
        return (
            "Sos un analista técnico de trading crypto. Tu trabajo es interpretar "
            "el regime de mercado actual a partir de métricas ya calculadas (ADX, "
            "DI+, DI-, ATR%, RSI) y recomendar la clase de estrategia adecuada. "
            "Sé directo, técnico, en español. Usá términos en inglés cuando sean "
            "estándar (SL, TP, leverage, range, trend). No inventes números — "
            "si una métrica no está, decilo. Output: 2-4 párrafos cortos + tabla "
            "de niveles si los hay."
        )

    async def precompute(self, payload: dict[str, Any]) -> dict[str, Any]:
        from wally_core.regime import compute_adx, label_regime  # type: ignore[import-not-found]

        bars = payload.get("bars", [])
        if not bars:
            return {"error": "No bars supplied. Pass `bars` with OHLCV data."}

        adx_result = compute_adx(bars, length=14)
        regime_label = label_regime(
            adx_result.get("adx", 0.0),
            adx_result.get("plus_di", 0.0),
            adx_result.get("minus_di", 0.0),
        )
        return {
            "adx_result": adx_result,
            "regime_label": regime_label,
            "timeframe": payload.get("timeframe", "1H"),
        }

    def user_prompt(self, payload: dict[str, Any], precomputed: dict[str, Any]) -> str:
        if "error" in precomputed:
            return precomputed["error"]
        adx = precomputed["adx_result"]
        regime = precomputed["regime_label"]
        symbol = payload.get("symbol", "UNKNOWN")
        return (
            f"Analizá el regime actual de {symbol} ({precomputed['timeframe']}).\n\n"
            f"Métricas calculadas:\n"
            f"- ADX(14): {adx.get('adx', 0):.2f}\n"
            f"- +DI: {adx.get('plus_di', 0):.2f}\n"
            f"- -DI: {adx.get('minus_di', 0):.2f}\n"
            f"- Regime label: {regime}\n\n"
            f"Devolveme:\n"
            f"1. Diagnóstico del regime (1-2 oraciones)\n"
            f"2. Estrategia recomendada (Mean Reversion / Donchian Breakout / "
            f"MA Crossover / Stand-aside)\n"
            f"3. Niveles técnicos clave si los podés inferir\n"
            f"4. Warning explícito si el regime es VOLATILE o ambiguo"
        )
