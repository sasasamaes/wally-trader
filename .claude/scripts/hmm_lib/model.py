"""HMM fit using hmmlearn.GaussianHMM with BIC-based K selection."""
import logging
import math
import warnings
from dataclasses import dataclass

import numpy as np
from hmmlearn import hmm

from hmm_lib.errors import HMMFitError

log = logging.getLogger(__name__)


@dataclass
class HMMFit:
    model: hmm.GaussianHMM
    k: int
    bic: float
    log_likelihood: float
    states: np.ndarray              # (N,) int per bar
    transition_matrix: np.ndarray   # (K, K)


def _params_count(k: int, n_features: int, covariance_type: str) -> int:
    """Free parameters in a GaussianHMM for BIC calculation."""
    # Initial probs: K - 1
    # Transitions: K * (K - 1)
    # Means: K * n_features
    # Covariances: full → K * n_features * (n_features + 1) / 2
    #              diag → K * n_features
    init = k - 1
    trans = k * (k - 1)
    means = k * n_features
    if covariance_type == "full":
        covs = k * n_features * (n_features + 1) // 2
    else:
        covs = k * n_features
    return init + trans + means + covs


def _fit_one_k(features: np.ndarray, k: int, *, random_state: int,
               covariance_type: str = "full", n_iter: int = 100) -> hmm.GaussianHMM:
    """Single fit attempt for given K. Raises ValueError on convergence/singularity failure."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        model = hmm.GaussianHMM(
            n_components=k,
            covariance_type=covariance_type,
            n_iter=n_iter,
            random_state=random_state,
            tol=1e-3,
        )
        model.fit(features)
    return model


def _try_fit_with_retries(features: np.ndarray, k: int, base_seed: int) -> hmm.GaussianHMM | None:
    """Try seeds; fall back to covariance_type='diag' on singularity."""
    for seed in (base_seed, base_seed + 1, base_seed + 2, base_seed + 3, base_seed + 4):
        try:
            return _fit_one_k(features, k, random_state=seed, covariance_type="full")
        except (ValueError, Warning) as exc:
            log.warning("K=%d full seed=%d failed: %s", k, seed, exc)
    for seed in (base_seed, base_seed + 1):
        try:
            return _fit_one_k(features, k, random_state=seed, covariance_type="diag")
        except (ValueError, Warning) as exc:
            log.warning("K=%d diag seed=%d failed: %s", k, seed, exc)
    return None


def fit_best_hmm(features: np.ndarray, *, k_range=(2, 3, 4, 5), random_state: int = 42) -> HMMFit:
    """Fit GaussianHMM for each K in k_range, pick lowest BIC."""
    n_obs, n_features = features.shape
    candidates: list[tuple[int, hmm.GaussianHMM, float, float]] = []
    for k in k_range:
        m = _try_fit_with_retries(features, k, random_state)
        if m is None:
            continue
        try:
            ll = m.score(features)
        except Exception as exc:
            log.warning("K=%d score failed: %s", k, exc)
            continue
        if not math.isfinite(ll):
            continue
        params = _params_count(k, n_features, m.covariance_type)
        bic = -2 * ll + params * math.log(n_obs)
        candidates.append((k, m, ll, bic))

    if not candidates:
        raise HMMFitError(f"all K in {k_range} failed to fit")

    # Lowest BIC wins
    k_best, model_best, ll_best, bic_best = min(candidates, key=lambda c: c[3])
    states = model_best.predict(features)
    return HMMFit(
        model=model_best,
        k=k_best,
        bic=bic_best,
        log_likelihood=ll_best,
        states=states,
        transition_matrix=model_best.transmat_,
    )
