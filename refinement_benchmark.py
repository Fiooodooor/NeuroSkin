"""Reproducible initial-population screening benchmark (not a hardware validation).

Example:
  python refinement_benchmark.py --samples 32 --seed 2026 --out artifacts/refinement-benchmark.json
"""
from __future__ import annotations
import argparse, json, random, time
from pathlib import Path
import numpy as np
from advanced import new_genome
from spatial_validation import spatial_pressure_test
from optimization import evaluate


def benchmark(samples: int = 32, seed: int = 2026, grid: int = 3) -> dict:
    if not 1 <= samples <= 10000:
        raise ValueError('samples must be 1..10000')
    if grid not in (3, 5, 7):
        raise ValueError('grid must be 3, 5 or 7')
    rng=random.Random(seed)
    data={}
    started=time.monotonic()
    for family in ('quadrant','crown','chiral'):
        items=[]
        for _ in range(samples):
            genome=new_genome(family,rng)
            # The same fast geometry, electronics and spatial plausibility
            # model as the live evolutionary population.
            score,metrics,_=evaluate(family,genome,physical_gate=True,gate_grid=grid)
            gate=metrics.get('spatial_gate',{})
            items.append(dict(score=score,coverage=gate.get('coverage_fraction',0.),
                              mean_quality=gate.get('mean_point_quality',0.),
                              min_snr=gate.get('min_snr_proxy',0.),
                              max_tilt=gate.get('max_tilt_rad',0.),
                              passed=bool(metrics.get('spatial_feasible',False))))
        data[family]={
            'samples':len(items),
            'passed_fast_screen':sum(v['passed'] for v in items),
            'coverage_ge_80_percent':sum(v['coverage'] >= .8 for v in items),
            'assumed_min_snr_ge_3':sum(v['min_snr'] >= 3. for v in items),
            'mean_score':round(float(np.mean([v['score'] for v in items])),5),
            'mean_point_quality':round(float(np.mean([v['mean_quality'] for v in items])),5),
            'mean_min_snr':round(float(np.mean([v['min_snr'] for v in items])),5),
            'best_score':round(max(v['score'] for v in items),5),
        }
    return {
        'version':'1.9.1', 'seed':seed, 'grid':grid,
        'per_family_samples':samples, 'family_results':data,
        'elapsed_seconds':round(time.monotonic()-started,3),
        'disclaimer':'Surrogate/synthetic electrical noise and loads, NOT validated sensor performance.'
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--samples',type=int,default=32)
    ap.add_argument('--seed',type=int,default=2026)
    ap.add_argument('--grid',type=int,choices=(3,5,7),default=3)
    ap.add_argument('--out',default='artifacts/refinement-benchmark.json')
    args=ap.parse_args()
    result=benchmark(args.samples,args.seed,args.grid)
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
