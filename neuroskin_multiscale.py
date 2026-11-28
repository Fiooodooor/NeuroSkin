"""T0 reference mechanics; mm, N, N mm; no hardware/FEM qualification."""
import numpy as np


def _matrix(k):
    k = np.asarray(k, dtype=float)
    if k.shape != (6, 6) or not np.isfinite(k).all():
        raise ValueError('expected finite 6x6 stiffness')
    if not np.allclose(k, k.T, rtol=1e-10, atol=1e-12):
        raise ValueError('stiffness must be symmetric')
    if np.min(np.linalg.eigvalsh(k)) <= 0:
        raise ValueError('stiffness must be positive definite')
    return k


def transport(r):
    """Twist map from origin to point r; wrench map is its transpose."""
    r = np.asarray(r, dtype=float)
    if r.shape != (3,) or not np.isfinite(r).all():
        raise ValueError('expected finite displacement vector')
    x, y, z = r
    t = np.eye(6)
    t[:3, 3:] = -np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return t


def stack_response(stiffnesses, offsets_mm, wrench):
    """1-3 series stages, each stiffness in global axes at its own upper port.

    Offsets run from each port to the common top reference point. Rigid,
    massless connections; small displacement; no contact or dynamics.
    """
    if not 1 <= len(stiffnesses) <= 3 or len(stiffnesses) != len(offsets_mm):
        raise ValueError('require 1-3 stages and one offset per stage')
    w = np.asarray(wrench, dtype=float)
    if w.shape != (6,) or not np.isfinite(w).all():
        raise ValueError('expected finite wrench')
    compliance = np.zeros((6, 6))
    energy = 0.
    stages = []
    for k, r in zip(stiffnesses, offsets_mm):
        k, t = _matrix(k), transport(r)
        wi = t.T @ w
        ui = np.linalg.solve(k, wi)
        compliance += t @ np.linalg.solve(k, t.T)
        energy += float(wi @ ui / 2)
        stages.append({'wrench': wi.tolist(), 'displacement': ui.tolist()})
    displacement = compliance @ w
    return {'stiffness': np.linalg.solve(compliance, np.eye(6)),
            'displacement': displacement, 'strain_energy_Nmm': energy,
            'energy_balance_error_Nmm': abs(energy - float(w @ displacement / 2)),
            'stages': stages}


def symmetry_error(k, order, length_mm, mirror=False):
    """Dimensionless stiffness residual, using axial-vector rotations for Dn."""
    k = _matrix(k)
    if order not in (1, 2, 3, 4, 6, 8) or not np.isfinite(length_mm) or length_mm <= 0:
        raise ValueError('invalid symmetry order or reference length')
    s = np.diag([1., 1., 1., 1/length_mm, 1/length_mm, 1/length_mm])
    k = s @ k @ s
    errors = []
    for i in range(order):
        angle = 2*np.pi*i/order
        c, v = np.cos(angle), np.sin(angle)
        r = np.array([[c,-v,0],[v,c,0],[0,0,1.]])
        for q in ([r, r @ np.diag([1.,-1.,1.])] if mirror else [r]):
            t = np.zeros((6,6))
            t[:3,:3], t[3:,3:] = q, np.linalg.det(q)*q
            errors.append(float(np.linalg.norm(t.T @ k @ t-k)/np.linalg.norm(k)))
    return max(errors)


def tile_response(vertical_stiffness, coupling_N_mm, loads_N):
    """Square tile with grounded taxels and nearest-neighbour membrane springs.

    Positive loads are compressive. Finite free membrane edges; no curvature,
    electrical coupling, or friction. Signed inputs are intentionally rejected.
    """
    k, f = np.asarray(vertical_stiffness,float), np.asarray(loads_N,float)
    if k.ndim != 2 or k.shape != f.shape or k.shape[0] != k.shape[1] or k.shape[0] not in (3,5,7,8):
        raise ValueError('expected matching 3x3, 5x5, 7x7 or 8x8 arrays')
    if not np.isfinite(k).all() or not np.isfinite(f).all() or np.any(k<=0) or np.any(f<0):
        raise ValueError('invalid stiffness or load')
    if not np.isfinite(coupling_N_mm) or coupling_N_mm < 0:
        raise ValueError('invalid membrane coupling')
    n = k.shape[0]
    a = np.diag(k.ravel())
    for y in range(n):
        for x in range(n):
            i = y*n+x
            for j in ([i+1] if x+1<n else []) + ([i+n] if y+1<n else []):
                a[i,i] += coupling_N_mm
                a[j,j] += coupling_N_mm
                a[i,j] -= coupling_N_mm
                a[j,i] -= coupling_N_mm
    u = np.linalg.solve(a,f.ravel()).reshape(k.shape)
    reactions = k*u
    return {'displacement_mm':u, 'reaction_N':reactions,
            'force_balance_error_N':abs(float(reactions.sum()-f.sum())),
            'strain_energy_Nmm':float(np.sum(f*u)/2), 'tier':'T0'}
