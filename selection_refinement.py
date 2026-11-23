"""Screening and promotion policy for NeuroSkin v1.9.1.

The values are *engineering heuristics* on synthetic electrical data and
small-strain mechanics, NOT validated probabilities of performance. Feasibility
is enforced as a rank band only after every active audit stage is complete.
"""
from __future__ import annotations
import math

AUDIT_POLICY_VERSION = '1.9.1-spatial-operating-band-feasibility-first'
OPERATING_FORCES_N = ('0.1', '0.4')
LOW_FORCE_KEY = '0.025'
FEASIBLE_SCORE_FLOOR = 50.0
INFEASIBLE_SCORE_CEILING = 49.99
MIN_ACCEPTED_SNR = 3.0
MIN_COVERAGE = 0.80
MAX_ACCEPTED_TILT_RAD = 0.35


def spatial_operating_summary(spatial: dict) -> dict:
    """Distinguish 25mN diagnostic sensitivity from 100/400mN load band.

    Min SNR of one failing sample is still recorded (not silently discarded).
    A failed 25 mN diagnostic is reported, but does not automatically invalidate
    the stated 0.1--0.4 N operating band.
    """
    if any(k not in spatial for k in (LOW_FORCE_KEY, *OPERATING_FORCES_N)):
        raise ValueError('Spatial audit missing mandatory force levels')
    operating = [spatial[k] for k in OPERATING_FORCES_N]
    low = spatial[LOW_FORCE_KEY]
    worst_coverage = min(float(s['coverage_fraction']) for s in operating)
    lowest_snr = min(float(s['min_snr_proxy']) for s in operating)
    worst_tilt = max(float(s['max_tilt_rad']) for s in operating)
    quality = sum(float(s.get('mean_point_quality', s['coverage_fraction'])) for s in operating) / len(operating)
    reasons = set()
    for s in operating:
        reasons.update(s.get('failure_reasons', []))
    if worst_coverage < MIN_COVERAGE:
        reasons.add('operating_coverage_below_80_percent')
    if lowest_snr < MIN_ACCEPTED_SNR:
        reasons.add('operating_min_snr_below_3')
    if worst_tilt > MAX_ACCEPTED_TILT_RAD:
        reasons.add('operating_tilt_excess')
    return {
        'operating_force_N': [0.1, 0.4],
        'low_force_diagnostic_N': 0.025,
        'low_force_coverage': float(low['coverage_fraction']),
        'low_force_min_snr_assumed': float(low['min_snr_proxy']),
        'operating_worst_coverage': worst_coverage,
        'operating_min_snr_assumed': lowest_snr,
        'operating_max_tilt_rad': worst_tilt,
        'operating_mean_margin_quality': quality,
        'screen_feasible': bool(worst_coverage >= MIN_COVERAGE and lowest_snr >= MIN_ACCEPTED_SNR and worst_tilt <= MAX_ACCEPTED_TILT_RAD),
        'failing_conditions': sorted(reasons),
        'note': 'Synthetic 0.1--0.4N operating-band screen; 0.025N is a diagnostic, not an uncalibrated pass/fail requirement.'
    }


def enforce_score_band(audit: dict) -> dict:
    """Ensure a failing audit cannot outrank a feasible one due to score mixing.

    This intentionally invalidates raw numeric comparability with v1.9 and
    earlier experiments; provenance hash/version identify the new policy.
    """
    raw = float(audit['audit_score'])
    if not math.isfinite(raw):
        audit['feasible'] = False
        raw = 0.0
    audit['audit_score_before_feasibility_band'] = round(raw, 5)
    if audit['feasible']:
        bounded = max(FEASIBLE_SCORE_FLOOR, min(100., raw))
        audit['score_band'] = 'feasible'
    else:
        # Do NOT clamp every failed design to 49.99: that creates another
        # evolutionary plateau after FEM scores are blended. Compress its
        # raw 0..100 utility monotonically into the 0..49.99 failure band.
        bounded = INFEASIBLE_SCORE_CEILING * max(0.,min(100.,raw)) / 100.
        audit['score_band'] = 'failed_screen'
    audit['audit_score'] = round(bounded, 5)
    audit['audit_policy_version'] = AUDIT_POLICY_VERSION
    return audit


def guided_child(family: str, genome: dict, screening_metrics: dict, rng):
    """Make a bounded, geometry/electronics-relevant mutation based on failures.

    This is a *mutation proposal*, not a guaranteed improvement. It is evaluated
    by the same quick screen, FEM and audit as any other offspring.
    """
    from advanced import PARAM_EXTRA, jump, _snap_piezo_count
    from engine import LIMITS
    q = jump(family, genome, rng, 'local')
    gate = screening_metrics.get('spatial_gate', {})
    reasons = set(gate.get('failure_reasons', []))
    bounds = {**LIMITS[family], **PARAM_EXTRA[family]}

    def nudge(key, factor=None, delta=None, target=None):
        if key not in q or key not in bounds:
            return
        old = float(q[key]); lo, hi = bounds[key]
        new = old * factor if factor is not None else old + delta if delta is not None else old + .25 * (target - old)
        q[key] = round(float(min(hi, max(lo, new))), 5)

    # Real, bounded electrode design knobs rather than adjusting an imaginary
    # noise floor or unmeasured amplifier accuracy.
    if 'weak_pressure_signal' in reasons:
        nudge('electrode_area_mm2', factor=rng.uniform(1.04, 1.14))
        nudge('dielectric_gap_mm', factor=rng.uniform(.94, .985))
        nudge('mount_compliance_mm_N', factor=rng.uniform(1.015, 1.08))
    if 'excessive_tilt' in reasons or 'wrong_vertical_deflection' in reasons:
        nudge('pad_offset_x', target=0.0)
        nudge('pad_offset_y', target=0.0)
        if family == 'quadrant':
            nudge('asymmetry', target=0.0)
            nudge('bow', factor=rng.uniform(.92, .99))
        elif family == 'chiral':
            nudge('balance', target=0.0)
    if 'unilateral_contact_risk' in reasons:
        nudge('pad_offset_x', target=0.0)
        nudge('pad_offset_y', target=0.0)
        if family != 'quadrant':
            q['ribs'] = min(int(bounds['ribs'][1]), max(int(bounds['ribs'][0]), int(q['ribs']) + rng.choice([0, 1])))
    if 'capacitor_bottom_out_risk' in reasons:
        nudge('dielectric_gap_mm', factor=rng.uniform(1.05, 1.15))
        nudge('mount_compliance_mm_N', factor=rng.uniform(.92, .98))
    if family == 'quadrant' and int(q.get('piezo_count', 1)) == 3:
        if rng.random() < .8:
            q['piezo_count'] = 4
    # Prefer channels that can be differentiated digitally, but continue
    # evolving valid summed/differential configurations in the main search.
    if rng.random() < .4:
        q['piezo_wiring'] = 0
    return _snap_piezo_count(q, family)
