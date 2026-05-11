"""Signal validator agent.

Mirrors the CLI `/signal` command: takes an externally-sourced trade
signal (entry/SL/TP/leverage) and runs it through the project's filter
stack, returning GO / NO-GO with rationale.

Pure validation uses `wally_core.signals` + `wally_core.macro`; the LLM
adds context-aware reasoning over the validation output.

Input payload:
    {
        "symbol": "LDOUSDT",
        "side": "SHORT",
        "entry": 0.4356,
        "sl": 0.4500,
        "tps": [0.4248, 0.4150, 0.4020],
        "leverage": 20,
        "filters_4_count": 4,
        "regime": "TRENDING_DOWN",
        "multifactor_score": -65,
        "ml_score": 72,
        "chainlink_delta_pct": 0.3,
        "saturday": false,
        "macro_tier": "SOFT"
    }
"""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent


class SignalValidatorAgent(BaseAgent):
    name = "signal_validator"
    description = (
        "Validate an externally-sourced trading signal against the project's "
        "filter stack (4 technical filters + multifactor + ML + macro tier + "
        "regime). Output: GO/NO-GO with score 0-100 and recommended sizing."
    )
    input_schema = {
        "type": "object",
        "required": ["symbol", "side", "entry"],
        "properties": {
            "symbol": {"type": "string"},
            "side": {"type": "string", "enum": ["LONG", "SHORT"]},
            "entry": {"type": "number"},
            "sl": {"type": "number"},
            "tps": {"type": "array", "items": {"type": "number"}},
            "leverage": {"type": "integer"},
            "filters_4_count": {"type": "integer", "minimum": 0, "maximum": 4},
            "regime": {"type": "string"},
            "multifactor_score": {"type": "number"},
            "ml_score": {"type": "number"},
            "chainlink_delta_pct": {"type": "number"},
            "saturday": {"type": "boolean"},
            "macro_tier": {
                "type": "string",
                "enum": ["OK", "SOFT", "WARN", "HARD"],
                "default": "OK",
            },
        },
    }

    def system_prompt(self) -> str:
        return (
            "Sos el validador de señales del sistema Wally Trader. Aplicás 4 "
            "filtros técnicos + multifactor + ML + macro tier + regime check + "
            "Saturday Precision Protocol. Output requerido:\n\n"
            "1. **Veredicto en 1 línea:** GO_FULL / GO_HALF / NO_GO\n"
            "2. **Score 0-100** (suma ponderada de filtros)\n"
            "3. **Tabla** con cada filtro y su pass/fail\n"
            "4. **Sizing recomendado:** % capital (2% retail default, profile-aware)\n"
            "5. **Hard blocks:** macro HARD tier = NO_GO inmediato, sin importar lo demás\n"
            "6. **Disclaimer 20x** si leverage ≥ 15x\n\n"
            "Honest-first: si el setup es marginal pero la comunidad lo está "
            "ejecutando, decirlo explícito. Bajo 400 palabras."
        )

    def user_prompt(self, payload: dict[str, Any], precomputed: dict[str, Any]) -> str:
        return (
            f"Validá esta señal externa:\n\n"
            f"```json\n{payload}\n```\n\n"
            f"Aplicá el filter stack completo y devolvé el output según el "
            f"formato del system prompt. Si `macro_tier` es HARD, bloqueá la "
            f"señal sin importar los demás filtros. Si es WARN, sugerí HALF "
            f"size. Si es SOFT, INFO + considera tier-0 MUGRES."
        )
