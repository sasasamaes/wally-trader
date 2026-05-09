"""Self-learning layer — auto-improvement from trade outcomes.

L1: recommendation_log   — log every system recommendation + user action + outcome
L2: pattern_miner        — mine winning/losing patterns from CSV history
L3: adaptive_weights     — re-weight composite score components from outcomes
L4: strategy_refresh     — auto-refresh regime_mapping.json from live trades
L5: post_mortem          — auto post-mortem on losing trades
L6: drift_response       — auto-tighten filters when calibration drift sustained
L7: online_ml_retrain    — retrain XGBoost when 25+ new closed trades
L8: override_tracker     — track user overrides + outcome correlation
"""
from .recommendation_log import log_recommendation, update_user_action, update_outcome, calibration_report
from .pattern_miner import mine_patterns, pattern_to_recommendation
from .adaptive_weights import fit_adaptive_weights, update_composite_weights, ab_test_weights
from .strategy_refresh import refresh_strategy_mapping
from .post_mortem import auto_postmortem, aggregate_postmortems
from .drift_response import check_drift_streak, apply_tightening, relax_when_resolved
from .online_ml_retrain import should_retrain, retrain_and_validate
from .override_tracker import log_override, override_calibration

__all__ = [
    "log_recommendation",
    "update_user_action",
    "update_outcome",
    "calibration_report",
    "mine_patterns",
    "pattern_to_recommendation",
    "fit_adaptive_weights",
    "update_composite_weights",
    "ab_test_weights",
    "refresh_strategy_mapping",
    "auto_postmortem",
    "aggregate_postmortems",
    "check_drift_streak",
    "apply_tightening",
    "relax_when_resolved",
    "should_retrain",
    "retrain_and_validate",
    "log_override",
    "override_calibration",
]
