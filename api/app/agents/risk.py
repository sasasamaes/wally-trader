"""Risk sizing agent.

Combines `wally_core.risk.calculate_position_size` (which already returns
a dict with size, margin, liq price, warnings) with LLM-generated
narrative explaining the math in plain Spanish.

Input payload:
    {
        "capital_usd": 200,
        "entry": 0.4356,
        "sl": 0.4500,
        "side": "SHORT",
        "leverage": 20,
        "profile": "bitunix"
    }
"""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent


class RiskAgent(BaseAgent):
    name = "risk"
    description = (
        "Calculate position size, margin, and liquidation price for a "
        "prospective trade. Includes profile-specific risk caps (2% retail, "
        "0.5% FTMO, etc.) and dynamic adjustments based on ATR volatility."
    )
    input_schema = {
        "type": "object",
        "required": ["capital_usd", "entry", "sl", "side"],
        "properties": {
            "capital_usd": {"type": "number"},
            "entry": {"type": "number"},
            "sl": {"type": "number"},
            "side": {"type": "string", "enum": ["LONG", "SHORT"]},
            "leverage": {"type": "integer", "default": 10},
            "profile": {"type": "string", "default": "retail"},
            "mode": {"type": "string", "enum": ["flat", "var"], "default": "flat"},
        },
    }

    def system_prompt(self) -> str:
        return (
            "Sos un risk manager para trading crypto. Te paso un cálculo de "
            "position size ya hecho — tu trabajo es **explicar** la decisión "
            "en español técnico, marcar warnings explícitos si hay leverage "
            "alto + SL ajustado (riesgo de liquidación), y sugerir ajustes "
            "si la matemática no cuadra. Bajo 250 palabras. Tabla resumen "
            "+ 2-3 bullet points + disclaimer al final."
        )

    async def precompute(self, payload: dict[str, Any]) -> dict[str, Any]:
        from wally_core.risk import calculate_position_size  # type: ignore[import-not-found]

        try:
            result = calculate_position_size(
                capital_usd=payload["capital_usd"],
                entry=payload["entry"],
                sl=payload["sl"],
                side=payload.get("side", "LONG"),
                leverage=payload.get("leverage", 10),
                profile=payload.get("profile", "retail"),
                mode=payload.get("mode", "flat"),
            )
            return {"calculation": result}
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Risk calc failed: {exc}"}

    def user_prompt(self, payload: dict[str, Any], precomputed: dict[str, Any]) -> str:
        if "error" in precomputed:
            return precomputed["error"]
        calc = precomputed["calculation"]
        return (
            f"Explicá el siguiente cálculo de risk para profile "
            f"`{payload.get('profile', 'retail')}`:\n\n"
            f"Inputs:\n"
            f"- Capital: ${payload['capital_usd']:.2f}\n"
            f"- Entry: {payload['entry']}\n"
            f"- SL: {payload['sl']}\n"
            f"- Side: {payload['side']}\n"
            f"- Leverage: {payload.get('leverage', 10)}x\n\n"
            f"Resultado:\n```json\n{calc}\n```\n\n"
            f"Devolveme análisis ejecutable: tabla, warnings, sugerencias."
        )
