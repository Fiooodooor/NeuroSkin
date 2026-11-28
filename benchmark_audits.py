"""Run the same finalist protocol under several CPU budgets; no speedup claims.

Example: python benchmark_audits.py --cores 1,16,24,32,40 --pitch .3125
Each configuration starts a fresh pool; reported wall time includes startup/JIT.
Run several repetitions on an otherwise idle workstation to compare medians.
"""
import argparse
import concurrent.futures as cf
import json
import multiprocessing
import os
import time
from audit_scheduler import available_ram_mb, plan_audits, run_audit_batch
from advanced import audit_job, evolution_worker_initializer
from hybrid_library import ranked, genome_for


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cores',default='1,16,24,32,40')
    p.add_argument('--pitch',type=float,default=.3125)
    p.add_argument('--grid',type=int,choices=(3,5,7),default=5)
    p.add_argument('--repeats',type=int,default=1)
    args=p.parse_args()
    if args.repeats<1 or args.repeats>20:p.error('repeats must be 1..20')
    if not .12<=args.pitch<=2.:p.error('pitch must be .12..2 mm')
    available=len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else (os.cpu_count() or 1)
    budgets=[int(x) for x in args.cores.split(',')]
    if any(n<1 or n>available for n in budgets):p.error(f'cores must be within 1..{available}')
    specs=ranked()[:3]
    jobs=[(s.upper_family,genome_for(s),'balanced',args.grid,True,args.pitch,'hex8') for s in specs]
    reference=None
    for n in budgets:
        for repeat in range(args.repeats):
            plan=plan_audits(len(jobs),n,True,'hex8',args.pitch,available_ram_mb())
            start=time.perf_counter()
            if n==1:
                results=run_audit_batch(None,audit_job,jobs,plan,check_stop=lambda:None,progress=lambda *a:None)
            else:
                with cf.ProcessPoolExecutor(max_workers=plan.processes,mp_context=multiprocessing.get_context('spawn'),initializer=evolution_worker_initializer) as pool:
                    results=run_audit_batch(pool,audit_job,jobs,plan,check_stop=lambda:None,progress=lambda *a:None)
            summary=[{'id':s.id,'score':r['audit_score'],'feasible':r['feasible'],
                      'fem_failed':bool(r.get('fem',{}).get('failed')),
                      'fem_error':r.get('fem',{}).get('error'),
                      'actual_case_workers':r.get('fem',{}).get('load_case_workers',1)} for s,r in zip(specs,results)]
            comparison=[(r['score'],r['feasible'],r['fem_failed']) for r in summary]
            if reference is None:reference=comparison
            match=all(abs(a[0]-b[0])<1e-5 and a[1:]==b[1:] for a,b in zip(reference,comparison))
            print(json.dumps({'cpu_budget':n,'repeat':repeat+1,'wall_s':round(time.perf_counter()-start,3),
                              'plan':plan.as_dict(),'same_as_first_scores_and_flags':match,'results':summary}),flush=True)
            if not match:raise SystemExit('Numerical/audit mismatch; investigate before interpreting speedup')


if __name__=='__main__':
    main()
