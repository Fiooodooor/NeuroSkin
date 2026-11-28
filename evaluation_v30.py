"""NeuroSkin 3 reproducible synthetic validation protocol.
Grouped held-out metrics do not establish physical sensor accuracy."""
from __future__ import annotations

import copy
from hashlib import sha256
from pathlib import Path
import math
from typing import Any
import numpy as np

from validation_contract import (
    load_protocol, digest, SCHEMA_VERSION, TestResult, Evidence,
    ValidationReport, runtime_versions,
)
from sensor_metrics import (
    NOISE_SIGMA, response_vector, decoder_holdout,
    finite_difference_jacobian, whitened_identifiability,
)
from electronics_budget import budget_for_response
from validation_design import shear_pairs
from scipy.stats import beta

ENGINE_SIGNATURE = 'neuroskin-v3-independent-shear-decoder-v1'


def solver_source_hash():
    """Hash actual numerical and validation source, not a manually typed release tag."""
    from provenance import numerical_source_hash
    return numerical_source_hash()



def _position_groups(family: str, genome: dict, grid=5):
    rad = min(3.0, float(genome.get('pad_radius', 3.0)) * .8)
    nx,ny=(grid,grid) if isinstance(grid,int) else grid
    if any(type(n) is not int or not 3<=n<=9 for n in (nx,ny)):
        raise ValueError('Synthetic validation grid must be 3..9 on each axis')
    positions = []
    for x in np.linspace(-rad,rad,nx):
        for y in np.linspace(-rad,rad,ny):
            if x*x + y*y <= rad*rad + 1e-10:
                positions.append((float(x), float(y)))
    return positions


def _respond(family, genome, fx, fy, fz, x, y, strain=0.0):
    from electromechanics import examine
    result = examine(family, genome, 'normal', force=[fx, fy, fz],
                     offset=(x, y), strain=strain)
    return response_vector(result), result


def _seed_from_genome(family: str, genome: dict, seed: int) -> int:
    # Python hash() is randomized per process, so avoid it for reproducibility.
    return int(sha256(digest({'family': family, 'genome': genome, 'seed': seed}).encode())
               .hexdigest()[:8], 16)


def simulate_load_dataset(family: str, genome: dict, protocol=None, *,
                          seed: int = 11239, dense: bool = False):
    """One fixed, protocol-derived set of loads, split by contact positions.

    We do not vary indenter and temperature here, because the current surrogate
    has no terms for these variables. Never manufacture a generalization result
    by varying only their labels.
    """
    protocol = protocol or load_protocol()
    positions = _position_groups(family, genome, grid=protocol.load_cases['contact_grid']['resolution'])
    forces = [float(f) for f in protocol.load_cases['normal_forces_N']]
    if not forces or len(forces)>16 or not np.isfinite(forces).all() or min(forces)<=0:
        raise ValueError('Require 1..16 positive finite normal loads')
    shears = shear_pairs(protocol.load_cases['shear_forces_N'],dense)
    if len(positions)*len(forces)*len(shears)>10000:raise ValueError('Synthetic design exceeds 10000 samples')
    from electromechanics import raw_mechanics,signals
    X, Y, groups, labels = [], [], [], []
    for idx, (x, y) in enumerate(positions):
        for fz in forces:
            for fx,fy in shears:
                # The static decoder deliberately excludes dynamic PVDF. Avoid
                # computing a transient film response that is never consumed.
                mechanics=raw_mechanics(family,genome,'normal',force=[fx,fy,-fz],offset=(x,y))
                v=response_vector({'electrical':signals(family,genome,mechanics)})
                X.append(v)
                Y.append([fx, fy, -fz, x, y])
                groups.append(idx)
                labels.append({'position': [x,y], 'normal_force_N': fz,
                               'shear_N': [fx,fy], 'source': 'synthetic_surrogate'})
    return np.asarray(X, float), np.asarray(Y, float), groups, labels, positions


def robust_screen(family: str, genome: dict, *, seed: int = 105, samples: int = 12):
    """Small calibrated-parameter *placeholder* for Monte Carlo uncertainty.

    Never treat these 1-sigma assumptions as empirical manufacturing tolerances.
    """
    if not (1 <= samples <= 128):
        raise ValueError('Monte-Carlo sample count must be between 1 and 128')
    rng = np.random.default_rng(seed)
    result = []
    failures=[]
    nominal, _ = _respond(family, genome, 0, 0, -.1, 0.0, 0.0)
    zero, _ = _respond(family, genome, 0, 0, 0., 0.0, 0.0)
    original_strength = np.linalg.norm((nominal-zero) / NOISE_SIGMA)
    variations = {
        'material_E': (.12, .35, 2.5),
        'dielectric_gap_mm': (.06, .20, .8),
        'piezo_bond_fraction': (.07, .50, 1.0),
        'piezo_adhesive_thickness_um': (.08, 20.0, 130.0),
    }
    # Draw every axis even for genomes without the corresponding parameter.
    # This preserves common random scenarios across all architectures.
    scenarios=rng.standard_normal((samples,len(variations)+1))
    for i,scenario in enumerate(scenarios):
        gp = copy.deepcopy(genome)
        for z,(key,(sigma,lo,hi)) in zip(scenario,variations.items()):
            if key in gp:
                gp[key]=float(np.clip(float(gp[key])*math.exp(z*sigma),lo,hi))
        noise_multiplier=math.exp(scenario[-1]*.15)
        try:
            v,_=_respond(family,gp,0,0,-.1,0.,0.)
            baseline,_=_respond(family,gp,0,0,0.,0.,0.)
            strength=float(np.linalg.norm((v-baseline)/(NOISE_SIGMA*noise_multiplier)))
            if not math.isfinite(strength):raise ValueError('nonfinite SNR')
            result.append(strength)
        except (ValueError,ArithmeticError,RuntimeError,np.linalg.LinAlgError) as exc:
            failures.append({'index':i,'reason':f'{type(exc).__name__}: {exc}'})
            result.append(0.)
    v=np.asarray(result)
    misses=int(np.sum(v<3.))
    upper=1. if misses==samples else float(beta.ppf(.95,misses+1,samples-misses))
    return {
        'source': 'synthetic_surrogate', 'samples': samples, 'seed': seed,
        'nominal_whitened_signal': float(original_strength),
        'scenario_hash':digest(scenarios.tolist()),'failed_trials':len(failures),'trial_failures':failures,
        'assumed_snr_below_3_upper95':upper,'interval_note':'One-sided exact binomial bound under assumed independent sampled scenarios; not a measured failure probability.',
        'assumed_snr_p10': float(np.quantile(v, .1)),
        'assumed_snr_p50': float(np.median(v)),
        'assumed_snr_p90': float(np.quantile(v, .9)),
        'assumed_snr_below_3_fraction': float(np.mean(v < 3.0)),
        'assumptions': {'material_E_relative_log_sigma': .12,
                        'gap_relative_log_sigma': .06,
                        'bond_relative_log_sigma': .07,'adhesive_thickness_relative_log_sigma':.08,
                        'distribution':'independent lognormal multipliers clipped to declared parameter bounds',
                        'noise_relative_log_sigma': .15},
        'unsupported_axes': ['temperature', 'actual_indenter_shape', 'bond_peel',
                             'electrode_parasitics', 'material_hysteresis'],
        'warning': 'Synthetic variation of model parameters, not measurement-derived tolerances',
    }


def validate_physical_genome(genome: dict):
    """Reject nonphysical parameters before numerical evaluation, not afterward."""
    if not isinstance(genome,dict):
        raise ValueError('Genome must be a mapping')
    required_positive = ('radius','height','thickness','material_E','dielectric_gap_mm',
                         'electrode_area_mm2','piezo_E_MPa','piezo_adhesive_G_MPa',
                         'piezo_adhesive_thickness_um')
    for key in required_positive:
        if key in genome:
            val=float(genome[key])
            if not math.isfinite(val) or val <= 0.0:
                raise ValueError(f'Nonphysical parameter {key}={val}')
    if 'piezo_bond_fraction' in genome:
        b=float(genome['piezo_bond_fraction'])
        if not math.isfinite(b) or not 0.0 < b <= 1.0:
            raise ValueError('Bonded-film fraction must be in (0,1]')


def evaluate_protocol(family: str, genome: dict, *, candidate_id: str = 'adhoc',
                      seed: int = 11239, protocol=None, monte_carlo_samples: int = 8,
                      dense: bool = False, fem: dict | None = None):
    validate_physical_genome(genome)
    protocol = protocol or load_protocol()
    protocol_hash = digest(protocol.model_dump(mode='json'))
    genome_hash = digest({'family': family, 'genome': genome})
    X, Y, groups, labels, positions = simulate_load_dataset(
        family, genome, protocol, seed=seed, dense=dense)
    fractions=tuple(float(protocol.dataset_splits[k+'_fraction']) for k in ('train','validation','test'))
    metrics = decoder_holdout(X, Y, groups, seed=seed,fractions=fractions)
    from electromechanics import examine
    ref = np.asarray([.015, -.01, -.1, .6, -.4], dtype=float)
    J = finite_difference_jacobian(lambda args: _respond(
        family, genome, args[0], args[1], args[2], args[3], args[4])[0])
    info = whitened_identifiability(J)
    from full_evaluation import manufacturability
    geometry = manufacturability(family, genome)
    from recovery_sim import recovery_for_candidate
    recovery = recovery_for_candidate(family, genome)
    robustness = robust_screen(family, genome, seed=seed + 1, samples=monte_carlo_samples)
    contact_vec, contact_result = _respond(family, genome, 0.0, 0.0, -0.1, 0.0, 0.0)
    budget = budget_for_response(contact_result)
    zero_vec, _ = _respond(family, genome, 0.0, 0.0, 0.0, 0.0, 0.0)
    contact_snr = float(np.linalg.norm((contact_vec-zero_vec) / NOISE_SIGMA))
    # Do not silently interpret an unconverged FEM as independent proof.
    fem_is_ok = bool(fem and not fem.get('failed') and fem.get('feasible_linear'))
    convergence = bool(fem and fem.get('mesh_convergence_verified') is True)
    tests = [
        TestResult(id='contact_load', status='pass' if contact_snr >= 3.0 else 'fail',
                   source='synthetic_surrogate', metric=contact_snr, limit=3.0,
                   reason='Whitened vector amplitude under assumed per-channel RMS noise'),
        TestResult(id='no_contact', status='pass' if np.isfinite(zero_vec).all() and np.linalg.norm(zero_vec) < .001 else 'fail',
                   source='synthetic_surrogate', metric=float(np.linalg.norm(zero_vec)), limit=.001,
                   reason='No contact should produce an approximately zero incremental signal'),
        TestResult(id='independent_holdout',
                   status='pass' if metrics['force_rmse_norm_N'] <= .08 and metrics['position_mae_mm'] <= 2.5 else 'fail',
                   source='synthetic_surrogate', metric=float(metrics['force_rmse_norm_N']), limit=.08,
                   reason='Contact-position-disjoint holdout; assumed acceptance targets: norm force RMSE<=0.08N, position MAE<=2.5mm'),
        TestResult(id='sensor_covariance', status='pass', source='synthetic_surrogate',
                   metric=float(np.min(NOISE_SIGMA)), reason='Positive declared assumed independent-channel covariance, NOT measured noise'),
        TestResult(id='observability',status='pass' if info['rank_5_unknowns']==5 else 'fail',
                   source='synthetic_surrogate',metric=float(info['rank_5_unknowns']),limit=5.,reason='Five locally observable force/position unknowns required in static readout'),
        TestResult(id='robustness_completion',status='pass' if robustness['failed_trials']==0 else 'fail',
                   source='synthetic_surrogate',metric=float(robustness['failed_trials']),limit=0.,reason='Failed numerical trials are not silently dropped'),
        TestResult(id='geometry_screen', status='pass' if geometry['passed'] else 'fail',
                   source='synthetic_surrogate', metric=float(geometry['minimum_member_diameter_mm']),
                   reason='Heuristic slenderness and manufacturing warnings'),
        TestResult(id='continuum_fem', status='pass' if fem_is_ok and convergence else
                   ('fail' if fem and not fem_is_ok else 'not_run'), source='linear_fem',
                   reason='Requires independent mesh-convergence evidence; a single HEX8 mesh does not qualify as converged'),
        TestResult(id='mesh_convergence', status='pass' if convergence else 'not_run', source='linear_fem',
                   reason='Mesh-refinement tolerance not yet verified by same-protocol study'),
        TestResult(id='nonlinear_contact', status='unsupported', source='nonlinear_fem',
                   reason='Nonlinear diagnostic solver exists; no independently qualified candidate nonlinear result in this report'),
        TestResult(id='hardware_test', status='not_run', source='hardware_measurement',
                   reason='Optional T3: no physically measured calibration data supplied; does not block software release or evolution'),
        TestResult(id='indenter_variation', status='unsupported', source='synthetic_surrogate',
                   reason='Indenter geometry is not included in the surrogate'),
        TestResult(id='temperature_variation', status='unsupported', source='synthetic_surrogate',
                   reason='Temperature does not enter the current constitutive or circuit equations'),
    ]
    necessary = {t.id: t for t in tests}
    complete = all(necessary[k].status == 'pass' for k in (
        'contact_load','no_contact','independent_holdout','sensor_covariance','geometry_screen','observability','robustness_completion'))
    evidence = Evidence(
        solver='six_dof_composite_surrogate',
        solver_hash=solver_source_hash(),
        material_hash=digest({'material_E': genome.get('material_E'),
                              'pvdf_E': genome.get('piezo_E_MPa'),
                              'bond': genome.get('piezo_adhesive_G_MPa')}),
        seed=int(seed), noise_provenance='assumed',
        evaluation_settings_hash=digest({'dense':bool(dense),'monte_carlo_samples':monte_carlo_samples,'model':ENGINE_SIGNATURE}),
        mesh_convergence_verified=convergence,
        environment_versions=runtime_versions(),
    )
    report = ValidationReport(
        candidate_id=str(candidate_id), family=family, protocol_hash=protocol_hash,
        genome_hash=genome_hash, evidence=evidence,
        tier='T0', source='synthetic_surrogate', tests=tests,
        pass_current_tier=complete, eligible_for_same_tier_promotion=complete,
        metrics={'decoder_holdout': metrics, 'observability': info,
                 'robustness_monte_carlo': robustness, 'readout_budget': budget,
                 'normal_snr_assumed': contact_snr,
                 'zero_force_response_norm': float(np.linalg.norm(zero_vec)),
                 'geometry': geometry, 'recovery_assumed': recovery,
                 'spatial_positions': len(positions),
                 'cases': len(X),'shear_pairs_N':shear_pairs(protocol.load_cases['shear_forces_N'],dense),
                 'readout_basis':'seven static capacitance/Hall proxy channels; PVDF excluded',
                 'force_levels_N': protocol.load_cases['normal_forces_N'],
                 'excluded_from_prediction': ['indenter shape', 'ambient temperature'],
                 'fem_available_but_unconverged': bool(fem and fem_is_ok and not convergence)},
        warnings=[
            'T0: Synthetic readouts and assumed noise, not measured sensor accuracy.',
            'A single FEM run does not establish mesh convergence.',
            'No nonlinear contact, no calibrated viscoelasticity or measured hysteresis.',
            'No unmodeled load/temperature/indenter case is silently scored as passed.',
        ],
    )
    return report.model_dump(mode='json')


def failed_validation_report(family: str, genome: dict, *, candidate_id: str,
                             seed: int, reason: str, protocol=None, dense=False, monte_carlo_samples=8) -> dict:
    """Fail-closed result for known numerical/geometry failures.

    Does not silently omit a failed test or claim a validated tier.
    """
    protocol=protocol or load_protocol()
    tests=[TestResult(id=k,status='fail',source='synthetic_surrogate',
                      reason='Incomplete numerical evaluation: '+reason) for k in
           ('contact_load','no_contact','independent_holdout','sensor_covariance','geometry_screen','observability','robustness_completion')]
    tests.extend((TestResult(id='continuum_fem',status='not_run',source='linear_fem'),
                  TestResult(id='nonlinear_contact',status='unsupported',source='nonlinear_fem'),
                  TestResult(id='hardware_test',status='not_run',source='hardware_measurement')))
    evidence=Evidence(solver='surrogate_failed',
                      solver_hash=solver_source_hash(),
                      material_hash=digest({'material_E':genome.get('material_E')}),
                      seed=seed,noise_provenance='assumed',evaluation_settings_hash=digest({'dense':bool(dense),'monte_carlo_samples':monte_carlo_samples,'model':ENGINE_SIGNATURE}),environment_versions=runtime_versions())
    return ValidationReport(candidate_id=str(candidate_id),family=family,
           protocol_hash=digest(protocol.model_dump(mode='json')),
           genome_hash=digest({'family':family,'genome':genome}),
           evidence=evidence,tier='T0',source='synthetic_surrogate',tests=tests,
           metrics={'failure':reason},pass_current_tier=False,
           eligible_for_same_tier_promotion=False,
           warnings=['Validation failed: candidate is not eligible for promotion.']).model_dump(mode='json')


def safe_evaluate_protocol(family: str, genome: dict, *, candidate_id: str,
                           seed: int = 3322, **options) -> dict:
    try:
        return evaluate_protocol(family,genome,candidate_id=candidate_id,seed=seed,**options)
    except (ValueError, ArithmeticError, RuntimeError, OverflowError) as exc:
        return failed_validation_report(family,genome,candidate_id=candidate_id,seed=seed,
                     reason=f'{type(exc).__name__}: {exc}',protocol=options.get('protocol'),dense=options.get('dense',False),monte_carlo_samples=options.get('monte_carlo_samples',8))
