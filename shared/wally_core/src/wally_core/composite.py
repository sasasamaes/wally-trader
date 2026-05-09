"""Composite signal score — combines all confluences into single 0-100 grade."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class SignalGrade(str, Enum):
    A_PLUS = "A+"  # 90-100
    A = "A"  # 80-89
    B = "B"  # 65-79
    C = "C"  # 50-64
    F = "F"  # <50


# Default weights (used when no adaptive weights file is found)
_DEFAULT_WEIGHTS = {
    "multifactor": 0.25,
    "regime_aligned": 0.20,
    "ml": 0.20,
    "sentiment": 0.15,
    "macro_clear": 0.10,
    "smart_router": 0.10,
}


def _load_adaptive_weights(
    profile: Optional[str] = None,
    profiles_dir: str = ".claude/profiles",
) -> Optional[dict]:
    """Load adaptive weights from profile learning directory.

    Returns None if profile is None, file missing, or load fails — caller uses defaults.
    """
    if not profile:
        return None
    path = Path(profiles_dir) / profile / "memory" / "learning" / "composite_weights.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        weights = data.get("weights") if isinstance(data, dict) else data
        if isinstance(weights, dict) and len(weights) >= 6:
            return weights
        return None
    except Exception:
        return None


@dataclass
class CompositeScoreResult:
    score: int  # 0-100
    grade: SignalGrade
    breakdown: dict  # each component score
    veto_reasons: list[str] = field(default_factory=list)  # hard rejections
    recommended_size_multiplier: float = 1.0  # 0.5x for B, 1.0x for A, 1.5x for A+


def composite_signal_score(
    *,
    multifactor_score: int,  # 0-100 from wally_core.multifactor
    regime_aligned: bool,  # does the side match what regime_mapping recommends?
    ml_score: Optional[int] = None,  # 0-100 from XGBoost, None if unavailable
    sentiment_score: int = 50,  # 0-100, 50 neutral
    macro_clear: bool = True,  # macro_gate_check returns no event in window
    smart_router_decision: str = "no_setup",  # approved/no_setup/vetoed/stand_aside
    profile: Optional[str] = None,  # if set, loads adaptive weights from L3
    profiles_dir: str = ".claude/profiles",
) -> CompositeScoreResult:
    """Weighted composite:
    - 25% multifactor (default, overridden by adaptive weights if available)
    - 20% regime alignment (binary 0 or 100)
    - 20% ml score (default 50 if unavailable)
    - 15% sentiment
    - 10% macro clear (binary 0 or 100)
    - 10% smart router (approved=100, no_setup=50, vetoed=20, stand_aside=0)

    Hard vetoes:
    - macro_clear=False → score capped at 50
    - smart_router='vetoed' → score capped at 40
    - smart_router='stand_aside' AND regime_aligned=False → score capped at 30

    Adaptive weights (L3): if profile is set and composite_weights.json exists,
    those weights override defaults. Falls back to defaults if missing or invalid.
    """
    # Load adaptive weights (L3 integration) — backward compat: None → use defaults
    adaptive = _load_adaptive_weights(profile, profiles_dir)
    weights = adaptive if adaptive is not None else _DEFAULT_WEIGHTS

    breakdown = {}
    veto_reasons = []

    # Components
    breakdown["multifactor"] = multifactor_score
    breakdown["regime_aligned"] = 100 if regime_aligned else 0
    breakdown["ml"] = ml_score if ml_score is not None else 50
    breakdown["sentiment"] = sentiment_score
    breakdown["macro_clear"] = 100 if macro_clear else 0

    sr_score = {
        "approved": 100,
        "no_setup": 50,
        "vetoed": 20,
        "stand_aside": 0,
    }.get(smart_router_decision, 50)
    breakdown["smart_router"] = sr_score

    # Weighted — use adaptive or default weights
    score = round(
        weights.get("multifactor", 0.25) * multifactor_score
        + weights.get("regime_aligned", 0.20) * breakdown["regime_aligned"]
        + weights.get("ml", 0.20) * breakdown["ml"]
        + weights.get("sentiment", 0.15) * sentiment_score
        + weights.get("macro_clear", 0.10) * breakdown["macro_clear"]
        + weights.get("smart_router", 0.10) * sr_score
    )

    # Apply hard caps
    if not macro_clear:
        veto_reasons.append("macro_event_in_window")
        score = min(score, 50)
    if smart_router_decision == "vetoed":
        veto_reasons.append("smart_router_vetoed")
        score = min(score, 40)
    if smart_router_decision == "stand_aside" and not regime_aligned:
        veto_reasons.append("stand_aside_and_counter_trend")
        score = min(score, 30)

    # Grade
    if score >= 90:
        grade = SignalGrade.A_PLUS
        size_mult = 1.5
    elif score >= 80:
        grade = SignalGrade.A
        size_mult = 1.0
    elif score >= 65:
        grade = SignalGrade.B
        size_mult = 0.5
    elif score >= 50:
        grade = SignalGrade.C
        size_mult = 0.25
    else:
        grade = SignalGrade.F
        size_mult = 0.0

    return CompositeScoreResult(
        score=score,
        grade=grade,
        breakdown=breakdown,
        veto_reasons=veto_reasons,
        recommended_size_multiplier=size_mult,
    )
