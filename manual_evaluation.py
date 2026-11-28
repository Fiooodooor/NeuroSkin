"""Budgeted process parallelism for the manual audit; no changes to physics.

A single heavy-job admission owns this whole DAG. Spawn workers for independent
Python-heavy surrogate stages; keep the FEM in the server process, with bounded
case concurrency, so a large mesh/factorization never crosses process boundaries.
"""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, asdict
from multiprocessing import get_context
from time import monotonic
from threading import Lock


@dataclass(frozen=True)
class ManualPlan:
    cpu_budget: int
    surrogate_processes: int
    fem_case_workers: int
    available_ram_mb: int | None
    reserved_ram_mb_estimate: int
    device: str


def plan_manual(cores, ram_mb, fem_enabled, backend, pitch, device, hybrid):
    if type(cores) is not int or cores<1 or device not in ('cpu','gpu'):
        raise ValueError('Invalid manual CPU/device budget')
    # One local execution thread, plus independent process workers.
    tasks=2+int(hybrid) if fem_enabled else 1+int(hybrid)
    solid=fem_enabled and backend!='beam'
    base=6144 if solid and pitch<.4 else 4096 if solid else 512
    reserve=1024
    budget=0 if ram_mb is None else max(0,int(ram_mb*.5))
    processes=max(0,min(tasks,cores-1,(budget-base)//reserve))
    cpu_left=cores-processes
    cases=1
    if solid and device=='cpu' and ram_mb is not None:
        cases=max(1,min(8,cpu_left,1+(budget-base-processes*reserve)//256))
    return ManualPlan(cores,processes,cases,ram_mb,base+processes*reserve+(cases-1)*256,device)


def surrogate_stage(name,family,genome,options):
    # Explicitly import only numerical modules; no server or controller in a worker.
    if name=='audit':
        from full_evaluation import audit_candidate
        return audit_candidate(family,genome,options['objective'],options['audit_grid'])
    if name=='validation':
        from evaluation_v30 import safe_evaluate_protocol
        return safe_evaluate_protocol(family,genome,candidate_id=options['candidate_id'],seed=3322,monte_carlo_samples=8)
    if name=='orientation':
        from orientation_study import scan_rotations
        return scan_rotations(family,genome,grid=3,force_n=options['inspector_force'])
    raise ValueError('Unknown surrogate stage')


def attach_fem_evidence(report,fem):
    """Only these fields in evaluate_protocol depend on the independent FEM."""
    if report['evidence']['solver']=='surrogate_failed':
        return report
    ok=bool(fem and not fem.get('failed') and fem.get('feasible_linear'))
    convergence=bool(fem and fem.get('mesh_convergence_verified') is True)
    for t in report['tests']:
        if t['id']=='continuum_fem':
            t['status']='pass' if ok and convergence else 'fail' if fem and not ok else 'not_run'
        elif t['id']=='mesh_convergence':
            t['status']='pass' if convergence else 'not_run'
    report['evidence']['mesh_convergence_verified']=convergence
    report['metrics']['fem_available_but_unconverged']=bool(fem and ok and not convergence)
    return report


def run_manual(family,genome,options,plan,solve_fem,progress,*,executor_factory=None):
    """Run independent stages, join deterministically, drain on exceptions.

    Progress reports submitted tasks, not claimed per-core utilization. Runtime
    and worker budgets are diagnostic metadata, not qualification evidence.
    """
    names=['audit','validation']+(['orientation'] if options['hybrid'] else [])
    if options['fem_enabled']:names.append('fem')
    stages={n:{'state':'pending'} for n in names}
    lock=Lock()
    def state(name,status,elapsed=None):
        with lock:
            stages[name]={'state':status}
            if elapsed is not None:stages[name]['elapsed_s']=round(elapsed,3)
            progress({'plan':asdict(plan),'stages':{k:dict(v) for k,v in stages.items()}})
    def local(name,fn):
        t=monotonic();state(name,'running')
        try:
            v=fn()
        except BaseException:
            state(name,'failed',monotonic()-t);raise
        state(name,'completed',monotonic()-t);return v
    out={}
    if plan.surrogate_processes==0:
        for name in ['audit','fem','validation','orientation']:
            if name in names:
                out[name]=local(name,solve_fem if name=='fem' else lambda n=name:surrogate_stage(n,family,genome,options))
    else:
        factory=executor_factory or (lambda count:ProcessPoolExecutor(max_workers=count,mp_context=get_context('spawn')))
        remote=[n for n in names if n!='fem']
        local_name='fem' if 'fem' in names else remote.pop(0)
        with factory(plan.surrogate_processes) as pool:
            futures={}
            for name in remote:
                t=monotonic();state(name,'submitted')
                f=pool.submit(surrogate_stage,name,family,genome,options)
                futures[name]=f
                def done(fut,n=name,start=t):
                    state(n,'failed' if fut.cancelled() or fut.exception() is not None else 'completed',monotonic()-start)
                f.add_done_callback(done)
            try:
                out[local_name]=local(local_name,solve_fem if local_name=='fem' else lambda:surrogate_stage(local_name,family,genome,options))
                for name,f in futures.items():out[name]=f.result()
            finally:
                for f in futures.values():f.cancel()
    out['telemetry']={'plan':asdict(plan),'stages':stages}
    return out
