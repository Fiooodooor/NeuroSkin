"""packaging, processor-group planning and fair CPU/GPU benchmark checks."""
from __future__ import annotations
import random
from pathlib import Path
from unittest.mock import patch
import numpy as np
from hardware_profile import _cpu, profile
from hardware_benchmark import compare_timings, measure
from advanced import new_genome
from physical_fem import FEMConfig, HexElasticSolver, voxel_mesh

ROOT = Path(__file__).resolve().parents[1]


def test_single_install_manifest():
    files=sorted(p.name for p in ROOT.glob('requirements*.txt'))
    assert files == ['requirements.txt']
    req=(ROOT/'requirements.txt').read_text()
    for line in ('fastapi','uvicorn','numpy','trimesh','pydantic','scipy','psutil',
                 'numba','cupy-cuda12x[ctk]','gmsh','scikit-fem','meshio','pyvista'):
        assert line in req
    assert 'cupy-cuda13x' not in '\n'.join(x for x in req.splitlines() if x and not x.lstrip().startswith('#'))


def test_windows_44_of_88_logical_workers_conservative():
    class FakeProc:
        def cpu_affinity(self):return list(range(44))
    def fake_count(logical=True):return 88 if logical else 44
    with patch('psutil.cpu_count',side_effect=fake_count),patch('psutil.Process',return_value=FakeProc()):
        info=_cpu()
    assert info['logical_host']==88
    assert info['physical_host']==44
    assert info['process_available_logical']==44
    assert info['threads_per_physical_core_estimate']==2
    assert info['process_available_physical_estimate']==22
    assert info['affinity_subset_of_host']
    with patch('hardware_profile._cpu',return_value=info), \
         patch('hardware_profile._memory_mb',return_value=(131072,100000)), \
         patch('hardware_profile.discover_gpu',return_value={'available':False}):
        plan=profile()['recommended']
    assert plan['evolution_cores']==20
    assert plan['heavy_fem_concurrency']>=1


def test_gpu_consistency_cannot_hide_bad_solution():
    cpu=dict(status='ok',_u=np.array([[1.,2.,3.]]),wall_seconds=.01,
             setup_seconds=.009,warm_solve_median_seconds=.001,displacement_mm=.1)
    gpu=dict(status='ok',_u=np.array([[1.,2.,30.]]),wall_seconds=.005,
             setup_seconds=.002,warm_solve_median_seconds=.0005,displacement_mm=.1)
    out=compare_timings(cpu,gpu)
    assert out['relative_displacement_difference']==0
    assert out['relative_full_field_difference']>1
    assert not out['gpu_recommended_for_this_case']


def test_setup_cost_in_break_even_and_no_unjustified_gpu_claim():
    cpu=dict(status='ok',_u=np.array([1.,2.]),wall_seconds=.02,
             setup_seconds=.01,warm_solve_median_seconds=.01,displacement_mm=.1)
    gpu=dict(status='ok',_u=np.array([1.,2.]),wall_seconds=20.,
             setup_seconds=19.,warm_solve_median_seconds=.001,displacement_mm=.1)
    out=compare_timings(cpu,gpu)
    assert not out['gpu_recommended_for_this_case']
    assert out['break_even_solves_estimate']>1000
    assert out['steady_state_speedup_gpu_over_cpu']>1


def test_unavailable_gpu_does_not_affect_cpu_benchmark():
    from hardware_benchmark import _bench_one
    def cpu_only(mesh,young,device,load,repeats,warmup):
        if device=='gpu':return {'status':'unavailable','reason':'GPU not accessible'}
        return _bench_one(mesh,young,device,load,repeats,warmup)
    with patch('hardware_benchmark._bench_one',side_effect=cpu_only):
        report=measure('quadrant',1.25,42,.1,repeats=2,warmup=0)
    assert report['measurements']['cpu']['status']=='ok'
    assert report['measurements']['gpu']['status']=='unavailable'
    assert not report['measurements']['gpu_recommended_for_this_case']
    assert report['measurements']['cpu']['repeats']==2


def test_existing_cpu_fem_unchanged():
    genome=new_genome('quadrant',random.Random(17))
    mesh=voxel_mesh('quadrant',genome,FEMConfig(pitch_mm=1.25))
    result=HexElasticSolver(mesh,genome['material_E']).solve(force=(0,0,-.1))
    assert result['compute_device']=='cpu'
    assert 0<result['mean_down_mm']<10
    assert result['force_equilibrium_relative']<1e-4
