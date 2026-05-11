"""Journal agent — daily session close.

Computes session metrics from a list of closed trades (WR, PF, avg win,
avg loss, Sharpe, max DD) using `wally_core.journal.compute_metrics`,
then has the LLM write a narrative wrap-up with lessons + setup for the
next session.

Input payload:
    {
        "date": "2026-05-11",
        "profile": "bitunix",
        "capital_pre": 177.98,
        "capital_post": 226.22,
        "trades": [
            {"symbol": "LDOUSDT", "side": "SHORT", "entry": 0.4356,
             "exit": 0.4133, "pnl_usd": 48.24, "hold_min": 88, ...}
        ]
    }
"""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent


class JournalAgent(BaseAgent):
    name = "journal"
    description = (
        "Close a trading session: compute WR/PF/Sharpe/DD from closed trades "
        "and write a narrative wrap-up with meta-lessons and setup for the "
        "next session."
    )
    requires_profile = True
    input_schema = {
        "type": "object",
        "required": ["date", "profile", "trades"],
        "properties": {
            "date": {"type": "string", "format": "date"},
            "profile": {"type": "string"},
            "capital_pre": {"type": "number"},
            "capital_post": {"type": "number"},
            "trades": {"type": "array", "items": {"type": "object"}},
        },
    }

    def system_prompt(self) -> str:
        return (
            "Sos el journal-keeper del sistema Wally. Cerrás la sesión de "
            "trading del día. Output requerido:\n\n"
            "1. **Tabla resumen** (capital pre/post, PnL, WR, calidad)\n"
            "2. **Métricas acumuladas** si hay datos de varios días\n"
            "3. **3-5 lecciones meta** del día (no del último trade — del "
            "sistema operando como un todo)\n"
            "4. **Setup para mañana** (catalysts macro, ventana óptima, "
            "playbook por escenario)\n"
            "5. **Disciplina mark** (5 estrellas)\n\n"
            "Tone: honest-first, celebratorio pero calibrado. Si WR=100% en "
            "<10 trades, recordá que es estadísticamente fragil. Bajo 700 "
            "palabras textuales (tablas no cuentan)."
        )

    async def precompute(self, payload: dict[str, Any]) -> dict[str, Any]:
        from wally_core.journal import compute_metrics  # type: ignore[import-not-found]

        try:
            metrics = compute_metrics(payload.get("trades", []))
            return {"metrics": metrics.model_dump() if hasattr(metrics, "model_dump") else metrics.__dict__}
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Journal metrics failed: {exc}"}

    def user_prompt(self, payload: dict[str, Any], precomputed: dict[str, Any]) -> str:
        if "error" in precomputed:
            return precomputed["error"]
        return (
            f"Cerrá el journal de {payload['date']} para profile "
            f"`{payload['profile']}`.\n\n"
            f"Capital pre: ${payload.get('capital_pre', 0):.2f}\n"
            f"Capital post: ${payload.get('capital_post', 0):.2f}\n"
            f"Trades del día: {len(payload.get('trades', []))}\n\n"
            f"Métricas calculadas:\n```json\n{precomputed['metrics']}\n```\n\n"
            f"Trades raw:\n```json\n{payload.get('trades', [])}\n```\n\n"
            f"Devolvé el output completo según el formato del system prompt."
        )
