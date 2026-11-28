import concurrent.futures as cf
import multiprocessing
import random
import threading
import time
from dataclasses import replace
import numpy as np
import pytest
from audit_scheduler import plan_audits, run_audit_batch, process_capacity


def _spawn_probe(job):
    value, delay, workers = job
    import os
    time.sleep(delay)
    return value, workers, os.getpid()


def test_z840_fine_mesh_uses_three_audits_and_eight_load_cases():
    plan=plan_audits(3,40,True,'hex8',.3125,104*1024)
    assert (plan.processes,plan.case_workers)==(3,8)
    assert not plan.memory_limited
    assert plan.processes*plan.case_workers<=40
    assert plan.reserved_ram_mb_estimate<=104*1024*.5
    assert plan_audits(3,40,True,'hex8',.3125,8000).processes==1
    assert plan_audits(3,40,True,'auto',.3125,None).case_workers==1
    assert plan_audits(3,40,True,'auto',.3125,None).processes==1
    assert plan_audits(3,2,True,'hex8',.3125,104*1024).case_workers==1
    assert plan_audits(0,40,True,'hex8',.3125,8000).processes==0
    assert plan_audits(3,40,False,'hex8',.3125,104*1024).case_workers==1


def test_windows_process_cap(monkeypatch):
    monkeypatch.setattr('audit_scheduler.sys.platform','win32')
    assert process_capacity(88,256)==61
    assert process_capacity(40,24)==24


def test_parallel_batch_spawn_order_and_progress():
    plan=plan_audits(3,3,False,'hex8',.3125,32000)
    progress=[]
    with cf.ProcessPoolExecutor(max_workers=3,mp_context=multiprocessing.get_context('spawn')) as pool:
        out=run_audit_batch(pool,_spawn_probe,[(0,.6),(1,.5),(2,.4)],plan,
                            check_stop=lambda:None,progress=lambda i,d:progress.append((i,d)))
    assert [x[0] for x in out]==[0,1,2]
    assert len({x[2] for x in out})>=2
    assert (3,0) in progress and progress[-1]==(0,3)


def test_no_new_submission_after_cancel():
    stop=threading.Event(); calls=[]
    def job(args):
        calls.append(args[0]);stop.set();return args
    def check():
        if stop.is_set():raise RuntimeError('stop')
    with cf.ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(RuntimeError,match='stop'):
            run_audit_batch(pool,job,[(1,),(2,),(3,)],plan_audits(3,1,False,'beam',1.,32000),
                            check_stop=check,progress=lambda *args:None)
    assert calls==[1]


def test_shared_matrixfree_thread_safety_and_numerical_equivalence():
    from physical_fem import FEMConfig, HexElasticSolver,voxel_mesh
    from advanced import new_genome
    g=new_genome('quadrant',random.Random(42));g['hybrid_id']='none'
    mesh=voxel_mesh('quadrant',g,FEMConfig(pitch_mm=1.25),build_surface=False)
    solver=HexElasticSolver(mesh,g['material_E'],matrixfree_threshold=1,cg_maxiter=3000,cg_rtol=1e-7)
    if not solver.matrixfree.accelerated:pytest.skip('Numba unavailable')
    solver.matrixfree.warmup()
    params=[dict(force=(0,0,-.1),offset=(x,y)) for x,y in [(0,0),(.7,0),(0,.7),(-.7,0)]]
    serial=[solver.solve(**p) for p in params]
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        parallel=list(pool.map(lambda p:solver.solve(**p),params))
    for a,b in zip(serial,parallel):
        np.testing.assert_allclose(a['displacement'],b['displacement'],rtol=1e-10,atol=1e-12)
        assert a['cg_iterations']==b['cg_iterations']
        assert b['force_equilibrium_relative']<1e-4


@pytest.mark.parametrize('force_matrixfree',[False,True])
def test_fem_sweep_preserves_load_protocol_and_score(monkeypatch,force_matrixfree):
    import physical_fem as pf
    from hybrid_library import ranked,genome_for
    spec=ranked()[0];g=genome_for(spec)
    cfg=pf.FEMConfig
    if force_matrixfree:
        monkeypatch.setattr(pf,'FEMConfig',lambda **kw:cfg(matrixfree_threshold=1,cg_rtol=1e-7,**kw))
    a=pf.fem_sweep(spec.upper_family,g,pitch_mm=1.25,backend='hex8',case_workers=1)
    b=pf.fem_sweep(spec.upper_family,g,pitch_mm=1.25,backend='hex8',case_workers=4)
    assert list(a['load_cases'])==list(b['load_cases']) and len(b['load_cases'])==8
    assert b['load_case_workers']==4
    assert a['feasible_linear']==b['feasible_linear']
    assert a['fem_score']==pytest.approx(b['fem_score'],abs=1e-7)
    for k in a['load_cases']:
        for f in ('energy_Nmm','mean_down_mm','max_von_mises_MPa','cg_iterations'):
            assert a['load_cases'][k][f]==pytest.approx(b['load_cases'][k][f],abs=1e-8)
