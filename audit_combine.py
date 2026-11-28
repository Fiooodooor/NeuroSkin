"""One authoritative mechanical audit merger for GUI Evaluate All and Top-3.

The manual GUI force/offset controls affect inspection fields only. Rank and
feasibility must use the SAME standard load protocol for each candidate.
"""
from __future__ import annotations


def merge_fem_into_audit(audit: dict, fem: dict, family: str, genome: dict,
                         *, fem_backend: str = 'hex8', include_fields: bool = False) -> dict:
    from recovery_sim import recovery_for_candidate
    baseline = float(audit['audit_score_before_feasibility_band'])
    feasible = bool(audit['feasible'] and fem['feasible_linear'])
    audit['audited_surrogate_score'] = baseline
    audit['audited_surrogate_feasible'] = bool(audit['feasible'])
    audit['fem'] = fem if include_fields else dict(fem, fields=None)
    if fem.get('inflated_features',0):
        audit.setdefault('screening_failure_reasons', []).append('fem_geometry_inflated_members')
    if not fem['feasible_linear']:
        audit.setdefault('screening_failure_reasons', []).append('fem_linear_screen_failed')
    audit['audit_version'] = '2.2-standardized-multifidelity-mechanics'
    audit['audit_score'] = round(.4 * baseline + .6 * float(fem['fem_score']), 5)
    audit['validation_level'] = 'linear_continuum_FEM_plus_synthetic_electronics_unconverged'
    d = audit.setdefault('decision_basis', {})
    d.update({
        'fem_score': float(fem['fem_score']),
        'fem_feasible': bool(fem['feasible_linear']),
        'fem_pressure_valid': bool(fem.get('pressure_valid',False)),
        'pvdf_stiffness_included': bool(fem.get('pvdf_stiffness_included', False)),
        'pvdf_film_count': int(fem.get('pvdf_film_count',0)),
        'pvdf_adhesive_model': fem.get('pvdf_adhesive_model','none'),
        'pvdf_film_energy_fraction': float(fem.get('pvdf_fraction_of_total_energy',0.0)),
    })
    if fem.get('hybrid_stages'):
        h=fem['hybrid_stages']
        audit['hybrid_stages']=h
        d.update({
            'hybrid_architecture': h['architecture'],
            'hybrid_lower_compression_share': h['lower_compression_share'],
            'hybrid_mode_rank': h['stage_response_rank_max3'],
            'hybrid_stage_balance_score': h['balance_score_0_100'],
            'hybrid_stage_mode_separation_score': h.get('mode_separation_score_0_100'),
        })
    centered=(fem.get('load_cases') or {}).get('press_center') or {}
    if centered.get('mean_down_mm') is not None:
        unload = recovery_for_candidate(family,genome,
                        fem_max_strain=fem.get('max_abs_principal_strain'),
                        fem_displacement_mm=abs(centered['mean_down_mm']))
        audit['unloading_recovery'] = unload
        audit['audit_score'] = round(.93*audit['audit_score'] +
                    .07*unload['recovery_score_0_100_assumed'],5)
        d['fem_recovery_5s_residual_fraction_assumed'] = unload['residual_fraction_after_5s']
        feasible = feasible and bool(unload['strain_screen_passed'])
    shell=fem.get('laminate_shell')
    if isinstance(shell,dict) and not shell.get('failed'):
        audit['laminate_shell'] = shell
        audit['audit_score'] = round(.88*audit['audit_score']+.12*shell['shell_score'],5)
        feasible = feasible and bool(shell['feasible_shell_screen'])
        d.update({
            'laminate_shell_score': float(shell['shell_score']),
            'laminate_shell_feasible': bool(shell['feasible_shell_screen']),
            'laminate_shell_max_eq_stress_MPa': float(shell['max_eq_stress_MPa']),
            'laminate_shell_max_interfacial_shear_MPa': float(shell['max_interfacial_shear_MPa']),
            'laminate_shell_max_top_strain_abs': float(shell['max_top_fiber_strain_abs']),
        })
    if fem_backend == 'hex8' and (not isinstance(shell,dict) or shell.get('failed')):
        feasible = False
        audit.setdefault('screening_failure_reasons', []).append('laminate_shell_stage_missing_or_failed')
        d['laminate_shell_stage_status'] = 'failed'
    audit['feasible'] = bool(feasible)
    audit.setdefault('limitations', []).append(
         'FEM is linear; shell postprocessing is not a nonlinear contact or coupled piezoelectric field solve.')
    return audit


def mark_fem_failure(audit: dict, error: BaseException, *, fem_backend: str) -> dict:
    audit['audited_surrogate_score'] = float(audit['audit_score_before_feasibility_band'])
    audit['audited_surrogate_feasible'] = bool(audit['feasible'])
    audit['fem'] = {'failed':True,'error':f'{type(error).__name__}: {error}',
                    'fem_backend':fem_backend}
    audit['audit_score'] = 0.0
    audit['feasible'] = False
    audit['validation_level'] = 'fem_failed_not_validated'
    audit.setdefault('screening_failure_reasons', []).append('fem_solver_failed')
    return audit
