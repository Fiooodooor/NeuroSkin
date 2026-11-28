"""Benchmark the actual local Evaluate All API with a fixed seed/hybrid.

Start server.py separately, stop evolution and avoid other manual jobs.
Wall time includes request, worker startup, solver and JSON serialization.
A failed FEM or changed qualification is never counted as a speedup.
"""
import argparse
import json
import math
import statistics
import time
from urllib.request import Request, urlopen


def request(base,path,payload=None,timeout=1800):
    data=None if payload is None else json.dumps(payload).encode('utf-8')
    req=Request(base.rstrip('/')+path,data=data,headers={'Content-Type':'application/json'})
    with urlopen(req,timeout=timeout) as response:
        return json.load(response)


def numerical_signature(report):
    f=report.get('fem')
    if not f or f.get('failed'):
        raise ValueError('FEM failed or missing; no timing comparison')
    audit=report['audit']
    validation=report['validation_v30']
    cases=f['load_cases']
    if len(cases)!=8:
        raise ValueError('Expected eight standardized HEX8 load cases')
    return {
        'identity':(report['candidate_id'],report['family'],validation['protocol_hash'],
                    f['fem_backend'],f['fem_linear_solver'],f['mesh_pitch_mm'],f['nodes'],f['elements']),
        'flags':(audit['feasible'],validation['pass_current_tier'],f['feasible_linear'],
                 f['geometry_fidelity_pass'],f['pressure_valid']),
        'metrics':{'audit_score':float(audit['audit_score']),'fem_score':float(f['fem_score']),
                   **{name+'.'+key:float(v[key]) for name,v in cases.items()
                      for key in ('energy_Nmm','mean_down_mm','max_abs_principal_strain',
                                  'force_equilibrium_relative','moment_equilibrium_relative')}}
    }


def compare(a,b):
    if a['identity']!=b['identity'] or a['flags']!=b['flags'] or a['metrics'].keys()!=b['metrics'].keys():
        return False
    return all(math.isclose(v,b['metrics'][k],rel_tol=1e-5,abs_tol=1e-6) for k,v in a['metrics'].items())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',default='http://127.0.0.1:8765')
    p.add_argument('--selection',choices=('seed','hybrid'),default='seed')
    p.add_argument('--index',default='r_gyroid_web')
    p.add_argument('--cores',default='1,16,24,40')
    p.add_argument('--pitch',type=float,default=.3125)
    p.add_argument('--grid',type=int,choices=(3,5,7),default=5)
    p.add_argument('--repeats',type=int,default=1)
    p.add_argument('--timeout',type=float,default=1800)
    args=p.parse_args()
    budgets=[int(x) for x in args.cores.split(',')]
    capacity=request(args.url,'/api/compute/status')
    if not budgets or budgets[0]!=1 or any(n<1 or n>min(256,capacity['available_cpu']) for n in budgets):
        p.error('start with 1 worker and stay within available CPU budget')
    if not .12<=args.pitch<=2 or not 1<=args.repeats<=20 or args.timeout<=0:
        p.error('invalid pitch, repetitions or timeout')
    ref=None;times={}
    payload={'selection':args.selection,'index':args.index,'expected_candidate_id':args.selection+'-'+args.index,
             'audit_grid':args.grid,'fem_pitch_mm':args.pitch,'fem_backend':'hex8','fem_enabled':True,
             'fem_compute_device':'cpu','fem_include_previews':True,'objective':'balanced'}
    for budget in budgets:
        times.setdefault(budget,[])
        for rep in range(args.repeats):
            status=request(args.url,'/api/compute/status')
            if status.get('evolution_active') or status.get('manual_jobs'):
                raise SystemExit('Stop evolution and all other manual analyses before benchmarking')
            start=time.perf_counter()
            result=request(args.url,'/api/evaluate_all',{**payload,'compute_workers':budget},args.timeout)
            wall=time.perf_counter()-start
            sig=numerical_signature(result)
            if ref is None:ref=sig
            match=compare(ref,sig)
            fem=result['fem']
            print(json.dumps({'requested_workers':budget,'repeat':rep+1,'wall_s':round(wall,3),
                              'same_numerical_signature':match,'telemetry':result['compute_telemetry'],
                              'actual_case_workers':fem['load_case_workers'],
                              'actual_matvec_workers':fem.get('matrixfree_matvec_workers',0),
                              'solver':fem['fem_linear_solver'],'setup_s':fem['setup_time_s'],
                              'cases_s':fem['load_cases_wall_s'],'qualification_flags':sig['flags']}),flush=True)
            if not match:raise SystemExit('Numerical mismatch; investigate before interpreting speedup')
            times[budget].append(wall)
    baseline=statistics.median(times[1])
    print(json.dumps({'medians':[{'workers':n,'wall_s':round(statistics.median(v),3),
                                  'speedup_vs_1':round(baseline/statistics.median(v),3)}
                                 for n,v in times.items()]}),flush=True)


if __name__=='__main__':
    main()
