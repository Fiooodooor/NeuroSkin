"""Bounded, leakage-controlled synthetic experimental design and decoder fitting.

All models are numerical surrogates, not calibrated sensor performance.
"""
from itertools import product
import numpy as np


def shear_pairs(levels, dense=False):
    """Independent signed axis sweeps; dense mode is a Cartesian design."""
    v = np.asarray(levels, float)
    if v.ndim != 1 or not len(v) or not np.isfinite(v).all():
        raise ValueError('Finite shear levels required')
    values = sorted(set(v.tolist()) | {0.0})
    if len(values) > 9 or min(values) >= 0 or max(values) <= 0:
        raise ValueError('Require signed shear levels, at most nine including zero')
    if dense:
        return list(product(values, repeat=2))
    return [(0., 0.)] + [(x, 0.) for x in values if x] + [(0., y) for y in values if y]


def _features(x, mean, scale, centers, width):
    z = (x - mean) / scale
    if centers is None:
        return z
    d2 = np.maximum(0., (z*z).sum(1)[:,None] + (centers*centers).sum(1)[None,:] - 2*z@centers.T)
    return np.column_stack((z, np.exp(-d2 / (2*width**2))))


def fit_decoder(x, y, noise, spec):
    """Fit feature scaling, deterministic RBF centers and ridge weights on x only."""
    kind, alpha, width = spec
    mean = x.mean(0)
    scale = np.maximum(x.std(0), noise)
    centers = None
    if kind == 'rbf':
        z = (x-mean)/scale
        # Deterministic farthest-point centers, capped to avoid quadratic memory.
        first = int(np.argmin(np.sum(z*z,axis=1)))
        ids = [first]
        distance = np.sum((z-z[first])**2,axis=1)
        for _ in range(min(32,len(x))-1):
            i = int(np.argmax(distance))
            if distance[i] <= 1e-14:
                break
            ids.append(i)
            distance = np.minimum(distance,np.sum((z-z[i])**2,axis=1))
        centers = z[ids]
    a = _features(x,mean,scale,centers,width)
    am = a.mean(0)
    ym = y.mean(0)
    ac = a-am
    beta = np.linalg.solve(ac.T@ac + alpha*np.eye(a.shape[1]), ac.T@(y-ym))
    def predict(q):
        return (_features(q,mean,scale,centers,width)-am)@beta+ym
    return predict


def select_decoder(x, y, train, val, test, noise, target_scales, no_contact):
    """Tune only on validation groups, refit on train+validation, test once."""
    specs = [('ridge',a,1.) for a in (.01,.1,1.,10.)]
    specs += [('rbf',a,w) for a in (.1,1.) for w in (.75,2.,4.)]
    scores=[]
    for spec in specs:
        pred = fit_decoder(x[train],y[train],noise,spec)(x[val])
        loss = float(np.sqrt(np.mean(((pred-y[val])/target_scales)**2)))
        scores.append(loss)
    best = min(range(len(specs)),key=lambda i:(scores[i],i))
    spec = specs[best]
    validation_prediction = fit_decoder(x[train],y[train],noise,spec)(x[val])
    fit = np.concatenate((train,val))
    model = fit_decoder(x[fit],y[fit],noise,spec)
    return model(x[test]), model(no_contact), validation_prediction, {
        'family':spec[0], 'alpha':spec[1], 'rbf_width':spec[2] if spec[0]=='rbf' else None,
        'validation_normalized_rmse':scores[best], 'model_trials':len(specs),
        'final_fit_count':len(fit), 'selection_policy':'validation_only_then_refit_train_plus_validation',
        'target_scales_N_N_N_mm_mm':target_scales.tolist(),
    }
