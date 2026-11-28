"""Deterministic independent-holdout metrics for uncalibrated sensor surrogates.

The grouped partition is by *contact position*, so adjacent samples from the
same contact cannot leak between training and testing. Noise is assumed; nothing
is presented as measured or as true prediction accuracy in hardware.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

NOISE_SIGMA = np.array([0.001] * 4 + [0.0003] * 2 + [0.002], dtype=float)
FEATURE_SCALES = np.array([0.1, 0.1, 0.1, 3.0, 3.0], dtype=float)


def response_vector(response: dict) -> np.ndarray:
    e = response['electrical']
    out = np.asarray(list(e['pressure_delta_pF']) + list(e['lateral_delta_pF']) +
                     [e['hall_torsion_delta_mT']], dtype=float)
    if out.shape != (7,) or not np.isfinite(out).all():
        raise ValueError('Seven finite electrical channels required')
    return out


def grouped_position_split(groups, seed: int = 3322):
    """Split entire contact positions, never individual samples. No overlap."""
    keys = sorted(set(groups))
    if len(keys) < 5:
        raise ValueError('At least five independently positioned contacts required')
    rng = np.random.default_rng(seed)
    rng.shuffle(keys)
    n = len(keys)
    n_train = max(1, int(n * .6))
    n_val = max(1, int(n * .2))
    if n_train + n_val >= n:
        raise ValueError('Not enough contact groups for held-out test')
    domains = [set(keys[:n_train]), set(keys[n_train:n_train+n_val]),
               set(keys[n_train+n_val:])]
    result = []
    for d in domains:
        indices = np.array([i for i, g in enumerate(groups) if g in d], dtype=int)
        result.append(indices)
    return tuple(result)


def _ridge(X_train: np.ndarray, Y_train: np.ndarray, X_test: np.ndarray, alpha: float = 1.0):
    mu = X_train.mean(0)
    sd = np.maximum(X_train.std(0), 1e-8)
    A = np.column_stack((np.ones(len(X_train)), (X_train - mu) / sd))
    B = np.column_stack((np.ones(len(X_test)), (X_test - mu) / sd))
    regularizer = np.diag([0.] + [alpha] * X_train.shape[1])
    beta = np.linalg.solve(A.T @ A + regularizer, A.T @ Y_train)
    return B @ beta


def decoder_holdout(X, Y, position_groups, *, seed: int = 3322, assumed_noise=NOISE_SIGMA, add_synthetic_noise: bool = True):
    X = np.asarray(X, float)
    Y = np.asarray(Y, float)
    if X.ndim != 2 or X.shape[1] != 7 or Y.shape != (len(X), 5):
        raise ValueError('X must be [n,7], Y must be [n,5] for Fx,Fy,Fz,x,y')
    if not np.isfinite(X).all() or not np.isfinite(Y).all():
        raise ValueError('Nonfinite sensor dataset')
    train, val, test = grouped_position_split(position_groups, seed)
    noise = np.asarray(assumed_noise, dtype=float)
    if noise.shape != (7,) or (noise <= 0).any():
        raise ValueError('Positive 7-channel noise standard deviations required')
    # Synthetic additive Gaussian noise is generated from a fixed PRNG seed;
    # measurements with known covariance should replace it in future hardware loops.
    rng = np.random.default_rng(seed + 13)
    X_noisy = X + rng.normal(size=X.shape) * noise if add_synthetic_noise else X.copy()
    pred_val = _ridge(X_noisy[train], Y[train], X_noisy[val])
    pred_test = _ridge(X_noisy[train], Y[train], X_noisy[test])
    err = pred_test - Y[test]
    zero = np.zeros(7)
    no_contact = rng.normal(size=(20, 7)) * noise + zero
    pred_zero = _ridge(X_noisy[train], Y[train], no_contact)
    fp_rate = float(np.mean(np.linalg.norm(pred_zero[:, :3], axis=1) > 0.025))
    rmse = np.sqrt(np.mean(err[:, :3] ** 2, axis=0))
    loc_error = np.linalg.norm(err[:, 3:5], axis=1)
    val_error = float(np.sqrt(np.mean((pred_val - Y[val]) ** 2)))
    # Test-set baseline error quantiles reflect synthetic perturbations only.
    force_norm_error = np.linalg.norm(err[:, :3], axis=1)
    return {
        'train_count': len(train), 'validation_count': len(val), 'test_count': len(test),
        'split_policy': 'disjoint_contact_positions',
        'split_seed': seed,
        'training': 'ridge_with_train_only_scaling_and_assumed_gaussian_channel_noise',
        'source': 'synthetic_surrogate' if add_synthetic_noise else 'user_supplied_dataset_with_no_added_noise',
        'force_rmse_N': [float(x) for x in rmse],
        'force_rmse_norm_N': float(np.sqrt(np.mean(force_norm_error ** 2))),
        'force_error_p95_N': float(np.quantile(force_norm_error, .95)),
        'position_mae_mm': float(np.mean(loc_error)),
        'position_p95_mm': float(np.quantile(loc_error, .95)),
        'validation_rmse_mixed_units': val_error,
        'no_contact_false_positive_rate_assumed': fp_rate,
        'assumed_noise_std_channels': noise.tolist(),
        'independent_test_groups': len(set(np.asarray(position_groups)[test])),
        'notes': 'Held-out positions are synthetic, NOT independent mechanical or experimental ground truth. Flat/sphere/edge indenters are not modeled.',
    }


def whitened_identifiability(jacobian, noise_std=NOISE_SIGMA, scales=FEATURE_SCALES):
    J = np.asarray(jacobian, dtype=float)
    sigma = np.asarray(noise_std, float)
    scales = np.asarray(scales, float)
    if J.shape != (7, 5) or sigma.shape != (7,) or scales.shape != (5,) or (sigma <= 0).any():
        raise ValueError('Expected J[7,5], seven positive noise sigma, five variable scales')
    if not np.isfinite(J).all():
        raise ValueError('Nonfinite Jacobian')
    whitened = J * scales[None, :] / sigma[:, None]
    values = np.linalg.svd(whitened, compute_uv=False)
    rank = int(np.sum(values > max(float(values[0]), 1e-12) * 1e-6))
    return {
        'rank_5_unknowns': rank,
        'singular_values': [float(v) for v in values],
        'condition_number': float(values[0] / max(float(values[-1]), 1e-15)),
        'min_singular_value': float(values[-1]),
        'covariance_origin': 'assumed_independent_noise_per_channel',
        'is_hardware_identifiable': False,
    }


def finite_difference_jacobian(response_function, *, reference=(.015, -.01, -.1, .6, -.4),
                               steps=(.003, .003, .003, .15, .15)):
    p = np.asarray(reference, float)
    steps = np.asarray(steps, float)
    J = np.zeros((7, 5), float)
    for i, h in enumerate(steps):
        plus = p.copy()
        minus = p.copy()
        plus[i] += h
        minus[i] -= h
        J[:, i] = (response_function(plus) - response_function(minus)) / (2 * h)
    return J


def pareto_front(items: list[dict], columns: dict[str, str]):
    """Dominance on explicit objectives: 'min' or 'max', no magic weighted sum."""
    for direction in columns.values():
        if direction not in ('min', 'max'):
            raise ValueError('Objective direction must be min/max')
    result = []
    for i, current in enumerate(items):
        dominated = False
        for j, other in enumerate(items):
            if i == j:
                continue
            better_equal = []
            strictly_better = []
            for k, direction in columns.items():
                a = float(current[k])
                b = float(other[k])
                better_equal.append(b <= a if direction == 'min' else b >= a)
                strictly_better.append(b < a if direction == 'min' else b > a)
            if all(better_equal) and any(strictly_better):
                dominated = True
                break
        if not dominated:
            result.append(current)
    return result
