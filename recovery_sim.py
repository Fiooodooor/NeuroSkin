"""Explicitly assumption-based unloading/recovery screen for NeuroSkin.

The loaded displacement is calculated by the existing mechanical surrogate or
linear FEM; a one-mode standard linear solid *creep-compliance approximation*
models the delayed recovery of that displacement. Not a nonlinear viscoelastic
FEM, and not a prediction of permanent set, damage, or cyclic life.

J(t) = 1/E_inf - (1/E_inf - 1/E0)*exp(-t/tau).
For force F applied at 0 and removed at t_hold, Boltzmann superposition gives
u(t>=t_hold) = F*(J(t)-J(t-t_hold)). The post-unload residual tends to zero.
"""
from __future__ import annotations
import math
import numpy as np

DEFAULT_TAU_S=0.8
DEFAULT_RELAXED_RATIO=0.55  # E_inf / E0, assumed, not fitted
ASSUMED_SAFE_STRAIN=0.08


def recovery_curve(loaded_deflection_mm:float, strain_est:float, hold_s:float=1.0,
                   tau_s:float=DEFAULT_TAU_S,relaxed_ratio:float=DEFAULT_RELAXED_RATIO):
    if not (0<tau_s and 0<relaxed_ratio<=1 and hold_s>0):
        raise ValueError('Invalid relaxation parameters')
    u0=abs(float(loaded_deflection_mm));eps=abs(float(strain_est))
    if not (math.isfinite(u0) and math.isfinite(eps)):
        raise ValueError('Nonfinite displacement/strain')
    # Normalize E0 = 1, E_inf = relaxed_ratio. This is a temporal compliance
    # surrogate, not a claim that elastic constitutive moduli equal 1 MPa.
    def J(t):return 1/relaxed_ratio-(1/relaxed_ratio-1)*math.exp(-max(t,0)/tau_s)
    peak=u0*J(hold_s)
    delays=(0.,.1,.25,.5,1.,2.,5.,10.)
    residuals=[u0*(J(hold_s+t)-J(t)) for t in delays]
    residual_fraction=float(residuals[6]/max(peak,1e-12))
    # Strain guard does NOT prove plasticity or fatigue: it says we cannot
    # assume fully reversible behavior when the assumed safe range is exceeded.
    strain_screen=bool(eps<=ASSUMED_SAFE_STRAIN)
    recovered_5s=bool(residual_fraction<.05 and strain_screen)
    score=float(np.clip(100*(1-residual_fraction)*math.exp(-max(0,eps/ASSUMED_SAFE_STRAIN-1)*1.5),0,100))
    return {'model':'linear_SLS_creep_superposition_assumed',
            'hold_s':hold_s,'tau_s_assumed':tau_s,'relaxed_to_initial_modulus_ratio_assumed':relaxed_ratio,
            'loaded_deflection_mm_input':u0,'peak_creep_deflection_mm_estimate':peak,
            'strain_estimate':eps,'strain_screen_passed':strain_screen,
            'times_after_release_s':list(delays),'residual_mm_after_release':list(map(float,residuals)),
            'residual_fraction_after_5s':residual_fraction,'recovery_5s_passed_assumed':recovered_5s,
            'recovery_score_0_100_assumed':score,
            'fully_recovered_at_infinite_time_in_model':True,
            'warning':'No permanent set, debonding, fatigue or hysteresis modeled; calibrate tau, moduli and strain range using real load/unload tests.'}


def recovery_for_candidate(family:str, genome:dict, fem_max_strain:float|None=None,
                           fem_displacement_mm:float|None=None):
    from advanced import curve_stiffness,structural_struts
    from engine import solve_force
    if fem_displacement_mm is None:
        K=curve_stiffness(family,genome,E=float(genome.get('material_E',1.0)))
        u=solve_force(K,[0,0,-.1])
        disp=float(abs(u[2]))
    else:
        disp=float(abs(fem_displacement_mm))
    paths=structural_struts(family,genome)
    minimum_arc=min(float(np.linalg.norm(np.diff(a,axis=0),axis=1).sum()) for a,_,_ in paths if len(a)>1)
    # Simple conservative kinematic strain screen when FEM is unavailable.
    eps=float(abs(fem_max_strain)) if fem_max_strain is not None else disp/max(minimum_arc,.1)
    return recovery_curve(disp,eps)
