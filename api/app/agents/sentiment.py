"""Sentiment agent — aggregated NLP score.

Combines pre-fetched sentiment snapshots from `sentiment_snapshots` (F&G,
Reddit VADER, News VADER, Funding contrarian → composite -100..+100) and
has the LLM interpret what the score means for short-term direction.

Input payload:
    {
        "fng": 48,
        "reddit_vader": 0.12,
        "news_vader": -0.05,
        "funding_btc": 0.0068,
        "composite": -8
    }

If `composite` isn't supplied, the agent doesn't try to compute it from
the components — that's the job of the worker that wrote the snapshot.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent


class SentimentAgent(BaseAgent):
    name = "sentiment"
    description = (
        "Aggregate sentiment score (F&G + Reddit VADER + News VADER + funding "
        "contrarian) and interpret for short-term BTC direction."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "fng": {"type": "integer", "minimum": 0, "maximum": 100},
            "reddit_vader": {"type": "number", "minimum": -1, "maximum": 1},
            "news_vader": {"type": "number", "minimum": -1, "maximum": 1},
            "funding_btc": {"type": "number"},
            "composite": {"type": "number", "minimum": -100, "maximum": 100},
        },
    }

    def system_prompt(self) -> str:
        return (
            "Sos el sentiment analyst del sistema Wally. Te paso un score "
            "agregado y los componentes. Tu trabajo: leer el sentimiento "
            "actual del mercado crypto en 2-3 párrafos cortos. Identificar "
            "extremos contrarian (F&G <20 o >80 son señales bullish/bearish "
            "respectivamente — contrarian sentiment). Funding alto positivo "
            "= longs sobre-cargados (riesgo squeeze short). Honest-first. "
            "Bajo 200 palabras."
        )

    def user_prompt(self, payload: dict[str, Any], precomputed: dict[str, Any]) -> str:
        components = {
            "F&G": payload.get("fng"),
            "Reddit VADER (-1..+1)": payload.get("reddit_vader"),
            "News VADER (-1..+1)": payload.get("news_vader"),
            "Funding BTC (% per 8h)": payload.get("funding_btc"),
        }
        return (
            f"Score sentimiento compuesto: **{payload.get('composite', 'n/a')}** "
            f"(-100 = capitulation, +100 = euphoria, 0 = neutral).\n\n"
            f"Componentes:\n```json\n{components}\n```\n\n"
            f"Devolveme la lectura actual del mercado + si hay extremo "
            f"contrarian que aprovechar."
        )
