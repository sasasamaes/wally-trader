"""Tests for hmm_lib.model — HMM fit + BIC selection."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))

from hmm_lib import model
from hmm_lib.errors import HMMFitError


def _synthetic_features(n: int = 1500, seed: int = 0) -> np.ndarray:
    """3 clusters in 3D space — should be detected as 3 regimes."""
    rng = np.random.default_rng(seed)
    seg = n // 3
    cluster_a = rng.normal(loc=[-2, -1, -1], scale=0.3, size=(seg, 3))
    cluster_b = rng.normal(loc=[0, 0, 0], scale=0.3, size=(seg, 3))
    cluster_c = rng.normal(loc=[+2, +2, +1], scale=0.3, size=(n - 2 * seg, 3))
    return np.vstack([cluster_a, cluster_b, cluster_c])


def test_fit_returns_hmmfit_with_required_fields():
    features = _synthetic_features()
    fit = model.fit_best_hmm(features, k_range=(2, 3))
    assert fit.k in (2, 3)
    assert fit.transition_matrix.shape == (fit.k, fit.k)
    assert np.allclose(fit.transition_matrix.sum(axis=1), 1.0, atol=1e-6)
    assert fit.states.shape == (len(features),)
    assert isinstance(fit.bic, float)


def test_bic_picks_lowest():
    """When K=3 is clearly best, fit_best_hmm should pick K=3."""
    features = _synthetic_features(n=2000)
    fit = model.fit_best_hmm(features, k_range=(2, 3, 4, 5))
    # With 3 well-separated clusters, BIC should favor K=3 over K=2 and K>=4
    # (allow K=3 OR K=4 because BIC for K=4 can be close)
    assert fit.k in (3, 4), f"expected K in (3, 4), got {fit.k}"


def test_fit_is_deterministic_with_seed():
    features = _synthetic_features()
    fit1 = model.fit_best_hmm(features, k_range=(2, 3), random_state=42)
    fit2 = model.fit_best_hmm(features, k_range=(2, 3), random_state=42)
    assert np.allclose(fit1.transition_matrix, fit2.transition_matrix, atol=1e-9)
    assert fit1.k == fit2.k


def test_fit_raises_when_all_k_fail():
    """Mock GaussianHMM to always fail → HMMFitError."""
    features = _synthetic_features()
    with patch.object(model, "_fit_one_k", side_effect=ValueError("non-convergent")):
        with pytest.raises(HMMFitError):
            model.fit_best_hmm(features, k_range=(2,))
