"""Multifactor scoring agent.

Wraps `wally_core.multifactor.composite_score` (Momentum + Volatility +
Trend Quality + Volume → -100 to +100). The LLM explains the breakdown
in plain language and points out which factor is dragging vs supporting.

Input payload:
    {
        "symbol": "BTCUSDT",
        "bars": [...]
    }
"""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent


class MultifactorAgent(BaseAgent):
    name = "multifactor"
    description = (
        "Compute the multifactor score (Momentum + Volatility + Trend Quality "
        "+ Volume) for a symbol on a timeframe. Returns -100 to +100 with "
        "narrative explaining which factor is the strongest signal."
    )
    input_schema = {
        "type": "object",
        "required": ["symbol", "bars"],
        "properties": {
            "symbol": {"type": "string"},
            "bars": {"type": "array", "items": {"type": "object"}},
        },
    }

    def system_prompt(self) -> str:
        return (
            "Sos el analista multifactor del sistema Wally. Te paso un score "
            "compuesto ya calculado (Momentum, Volatility, Trend Quality, "
            "Volume → -100 a +100). Tu trabajo: explicar el score en español "
            "técnico, identificar qué factor manda, y traducir a una decisión "
            "operativa concreta (LONG/SHORT/STAND-ASIDE). Bajo 200 palabras."
        )

    async def precompute(self, payload: dict[str, Any]) -> dict[str, Any]:
        from wally_core.multifactor import composite_score  # type: ignore[import-not-found]

        try:
            score = composite_score(payload["symbol"], payload.get("bars", []))
            return {"score": score}
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Multifactor calc failed: {exc}"}

    def user_prompt(self, payload: dict[str, Any], precomputed: dict[str, Any]) -> str:
        if "error" in precomputed:
            return precomputed["error"]
        return (
            f"Multifactor score para {payload['symbol']}: "
            f"**{precomputed['score']}** (-100 = strong bearish, "
            f"+100 = strong bullish, 0 = neutral).\n\n"
            f"Devolveme:\n"
            f"1. Lectura direccional (LONG bias / SHORT bias / NEUTRAL)\n"
            f"2. Confianza (low/med/high)\n"
            f"3. Si entrar ahora o esperar mejor confluence\n"
            f"4. Próximo trigger a observar"
        )
