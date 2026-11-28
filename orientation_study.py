"""Relative upper/lower hybrid rotation study.

This is a screening study at a single frequency/force. A 45-degree phase shift
changes angular support placement; it does NOT reverse helix handedness.
All reported values are numerical predictions, not experimentally validated.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from typing import Iterable

ANGLES_DEG = (0.0, 22.5, 45.0, 67.5, 90.0)


def scan_rotations(family: str, genome: dict, *, angles_deg: Iterable[float] = ANGLES_DEG,
                   grid: int = 3, force_n: float = .1, fem_pitch: float | None = None) -> dict:
    from advanced import proxy
    from spatial_validation import spatial_pressure_test
    if genome.get('hybrid_id', 'none') in (None, '', 'none'):
        raise ValueError('Rotation study requires a two-stage hybrid genome')
    rows = []
    for angle in angles_deg:
        g = dict(genome)
        g['hybrid_phase'] = math.radians(float(angle))
        score, metrics, _ = proxy(family, g)
        try:
            space = spatial_pressure_test(family, g, grid_size=grid, force_n=force_n)
            row = {
                'angle_deg': float(angle),
                'phase_rad': float(g['hybrid_phase']),
                'proxy_score_0_100': float(score),
                'coverage_fraction': float(space['coverage_fraction']),
                'min_snr_assumed': float(space['min_snr_proxy']),
                'max_tilt_rad': float(space['max_tilt_rad']),
                'mean_point_quality': float(space['mean_point_quality']),
                'screen_pass': bool(space['status'] == 'PASS'),
                'failure_reasons': space['failure_reasons'],
                'min_strut_radius_mm': float(metrics.get('minimum_strut_radius_mm', 0.0)),
            }
            if fem_pitch is not None:
                from physical_fem import fem_sweep
                try:
                    fem = fem_sweep(family, g, pitch_mm=fem_pitch, backend='hex8', include_fields=False)
                    row['fem'] = {
                        'pitch_mm': fem_pitch,
                        'score': float(fem['fem_score']),
                        'feasible_linear': bool(fem['feasible_linear']),
                        'displacement_at_0p1N_mm': float(fem['load_cases']['press_center']['mean_down_mm']),
                        'inflated_features': int(fem['inflated_features']),
                    }
                except (ValueError, RuntimeError, MemoryError) as e:
                    row['fem'] = {'failed': True, 'error': str(e)}
        except (ValueError, RuntimeError) as e:
            row = {'angle_deg': float(angle), 'proxy_score_0_100': float(score),
                   'screen_pass': False, 'error': str(e)}
        rows.append(row)
    # Feasible first, then spatial quality, then proxy score. Identical protocol.
    eligible = [r for r in rows if 'error' not in r]
    sorted_rows = sorted(eligible, key=lambda r: (
        int(r['screen_pass']), r['coverage_fraction'], r['mean_point_quality'],
        r['min_snr_assumed'], -r['max_tilt_rad'], r['proxy_score_0_100']), reverse=True)
    winner = sorted_rows[0] if sorted_rows else None
    return {
        'hybrid_id': genome['hybrid_id'],
        'family': family,
        'tested_angles_deg': list(map(float, angles_deg)),
        'force_n': float(force_n),
        'grid': grid,
        'rows': rows,
        'best_screened_angle_deg': winner['angle_deg'] if winner else None,
        'recommended_only_as_screening_hypothesis': True,
        'physics': 'Six-DOF series-compliance proxy and synthetic capacitive response; optional coarse HEX8.',
        'warning': 'Rotation changes relative upper-stage azimuth, not helix handedness. 90° may be symmetry-equivalent to 0° for ideal fourfold cells; voxel and PVDF asymmetries may break this equivalence. The best proxy angle must be re-evaluated using identical high-resolution FEM and experimental load cases.',
    }


def main() -> None:
    ap = argparse.ArgumentParser(description='Screen a two-stage cell at several relative phase rotations')
    ap.add_argument('--hybrid-id', default='h01_serpentine_quadrant')
    ap.add_argument('--genome', type=Path, default=None)
    ap.add_argument('--grid', type=int, default=3, choices=(3, 5, 7))
    ap.add_argument('--force', type=float, default=.1)
    ap.add_argument('--fem-pitch', type=float, default=None)
    ap.add_argument('--out', type=Path, default=Path('hybrid_rotations.json'))
    args = ap.parse_args()
    from hybrid_library import BY_ID, genome_for
    if args.genome:
        genome = json.loads(args.genome.read_text(encoding='utf-8'))
        hybrid_id = genome.get('hybrid_id')
    else:
        hybrid_id = args.hybrid_id
        genome = genome_for(BY_ID[hybrid_id])
    if hybrid_id not in BY_ID:
        ap.error('Unknown hybrid_id in selected genotype')
    result = scan_rotations(BY_ID[hybrid_id].upper_family, genome,
                            grid=args.grid, force_n=args.force, fem_pitch=args.fem_pitch)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'best_screened_angle_deg': result['best_screened_angle_deg'],
                      'all_rows': [{k: r.get(k) for k in ('angle_deg','screen_pass','coverage_fraction','min_snr_assumed','max_tilt_rad')} for r in result['rows']]}, indent=2))

if __name__ == '__main__':
    main()
