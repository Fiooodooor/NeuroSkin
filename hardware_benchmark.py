"""NeuroSkin 1.7 CPU/CUDA comparison with explicit cold and warm phases.

The same small-strain HEX8 mesh, RHS and material are used. Both numerical
accuracy and run-time are reported. This is not a calibrated hardware benchmark
and does not automatically enable CUDA for the evolutionary workload.
"""
from __future__ import annotations
import argparse
import json
import random
import statistics
import time
from pathlib import Path
import numpy as np
from advanced import new_genome
from physical_fem import FEMConfig, HexElasticSolver, voxel_mesh
from hardware_profile import profile

CASES = {
    'normal': {'force': (0., 0., -0.1), 'offset': (0., 0.)},
    'offset': {'force': (0., 0., -0.1), 'offset': (1.0, 0.6)},
    'shear_x': {'force': (0.03, 0., -0.04), 'offset': (0., 0.)},
    'shear_y': {'force': (0., 0.03, -0.04), 'offset': (0., 0.)},
}


def compare_timings(cpu: dict, gpu: dict, rtol: float = 5e-3) -> dict:
    """Conservative speedup recommendation, *only* for the measured workload."""
    out = {'gpu_recommended_for_this_case': False,
           'relative_displacement_difference': None,
           'relative_full_field_difference': None,
           'speedup_cpu_over_gpu': None,
           'gpu_speedup_over_cpu_cold': None,
           'steady_state_speedup_gpu_over_cpu': None,
           'break_even_solves_estimate': None}
    if cpu.get('status') != 'ok' or gpu.get('status') != 'ok':
        return out
    cpu_u = np.asarray(cpu['_u'], dtype=float)
    gpu_u = np.asarray(gpu['_u'], dtype=float)
    error = float(np.linalg.norm(cpu_u - gpu_u) / max(np.linalg.norm(cpu_u), 1e-12))
    d0 = float(cpu['displacement_mm'])
    d1 = float(gpu['displacement_mm'])
    d_err = abs(d0 - d1) / max(abs(d0), 1e-12)
    cold_cpu = max(float(cpu['wall_seconds']), 1e-12)
    cold_gpu = max(float(gpu['wall_seconds']), 1e-12)
    warm_cpu = max(float(cpu['warm_solve_median_seconds']), 1e-12)
    warm_gpu = max(float(gpu['warm_solve_median_seconds']), 1e-12)
    out.update(relative_displacement_difference=d_err,
               relative_full_field_difference=error,
               speedup_cpu_over_gpu=cold_cpu / cold_gpu,
               gpu_speedup_over_cpu_cold=cold_cpu / cold_gpu,
               steady_state_speedup_gpu_over_cpu=warm_cpu / warm_gpu)
    saving = warm_cpu - warm_gpu
    if saving > 0:
        extra_start = max(0.0, float(gpu['setup_seconds']) - float(cpu['setup_seconds']))
        out['break_even_solves_estimate'] = int(np.ceil(extra_start / saving))
    # Never recommend CUDA merely because a tiny synthetic warm calculation
    # was faster; include compilation/setup and require consistent displacements.
    out['gpu_recommended_for_this_case'] = bool(
        np.isfinite(error) and error <= rtol and
        cold_gpu < cold_cpu / 1.15 and warm_gpu < warm_cpu / 1.15)
    return out


def _bench_one(mesh, young: float, device: str, load: dict, repeats: int, warmup: int) -> dict:
    """One factorization, one first solve, then explicit warmups and repetitions."""
    begin = time.perf_counter()
    try:
        solver = HexElasticSolver(mesh, young_MPa=young, compute_device=device)
        first = solver.solve(**load)
        first_wall = time.perf_counter() - begin
        for _ in range(warmup):
            solver.solve(**load)
        durations = []
        recent = first
        for _ in range(repeats):
            start = time.perf_counter()
            recent = solver.solve(**load)
            durations.append(time.perf_counter()-start)
        # cold means one setup + one solve, rather than including repeats
        return {'status': 'ok',
                'wall_seconds': round(first_wall, 6),
                'setup_seconds': round(solver.setup_s, 6),
                'solve_seconds': round(first['solve_s'], 6),
                'warm_solve_median_seconds': round(statistics.median(durations), 6),
                'warm_solve_min_seconds': round(min(durations), 6),
                'warm_solve_max_seconds': round(max(durations), 6),
                'warm_samples_seconds': [round(x, 6) for x in durations],
                'repeats': repeats, 'warmups': warmup,
                'displacement_mm': float(recent['mean_down_mm']),
                'residual': float(recent['free_residual_relative']),
                'force_balance': float(recent['force_equilibrium_relative']),
                'solver': solver.solver_mode,
                '_u': np.asarray(recent['displacement'],dtype=float)}
    except (RuntimeError, ValueError, OSError, MemoryError, ImportError) as exc:
        return {'status': 'unavailable', 'reason': f'{type(exc).__name__}: {exc}'}


def measure(family='quadrant', pitch=1.25, seed=42, force=0.1,
            repeats=5, warmup=1, case='normal'):
    if repeats < 1 or repeats > 100: raise ValueError('--repeats must be 1..100')
    if warmup < 0 or warmup > 20: raise ValueError('--warmup must be 0..20')
    if case not in CASES: raise ValueError(f'unknown load case {case}')
    if not 0 < force <= .5: raise ValueError('force must be in 0..0.5 N')
    g = new_genome(family, random.Random(seed))
    mesh = voxel_mesh(family, g, FEMConfig(pitch_mm=pitch, max_cells=6000))
    params = dict(CASES[case]); params['force'] = tuple(v * force / .1 for v in params['force'])
    cpu = _bench_one(mesh, g['material_E'], 'cpu', params, repeats, warmup)
    gpu = _bench_one(mesh, g['material_E'], 'gpu', params, repeats, warmup)
    comparison = compare_timings(cpu, gpu)
    for res in (cpu,gpu): res.pop('_u',None)
    return {'family': family, 'seed': seed, 'pitch_mm': pitch,
            'element_count': mesh.voxels, 'load_case': case, 'applied_force_N': params['force'],
            'hardware': profile(),
            'measurements': {'cpu': cpu, 'gpu': gpu, **comparison},
            'disclaimer': 'Same linear-elastic HEX8 mesh; cold setup and steady-state separate. GPU may be much slower for small problems. GPU CUDA CSR only <=6000 cells; 4x/8x FEM remains CPU matrix-free. No physical material validation.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='NeuroSkin cold/warm CPU vs CUDA FEM benchmark')
    parser.add_argument('--family', choices=['crown','chiral','quadrant'], default='quadrant')
    parser.add_argument('--pitch', type=float, default=1.25)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--force', type=float, default=0.1)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--warmup', type=int, default=1)
    parser.add_argument('--case', choices=sorted(CASES), default='normal')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    report = measure(args.family,args.pitch,args.seed,args.force,args.repeats,args.warmup,args.case)
    content = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(content, encoding='utf-8')
    print(content)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
