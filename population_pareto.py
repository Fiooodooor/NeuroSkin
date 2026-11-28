"""Feasible-first population ranking over common cheap T0 proxy objectives.

Rank/crowding are generation-local. Never compare them across generations,
never treat them as physical qualification, and never impute missing metrics.
"""
import math
import numpy as np

OBJECTIVES=('fitness_geometry','fitness_electrical','fitness_robustness','piezo_score')


def _finite(value, fallback=-1e30):
    try:
        v=float(value)
        return v if math.isfinite(v) else fallback
    except (ValueError,TypeError,OverflowError):
        return fallback


def constraint_class(candidate, physical_gate):
    m=candidate.get('metrics',{})
    if m.get('error') or _finite(candidate.get('fitness')) < 0 or any(_finite(m.get(k))==-1e30 for k in OBJECTIVES):
        return 2
    if (physical_gate and m.get('spatial_feasible') is not True) or candidate.get('known_audit_feasible') is False:
        return 1
    return 0


def _fronts(values):
    # Collapse duplicates so clones do not receive arbitrary boundary bonuses.
    unique,inverse=np.unique(values,axis=0,return_inverse=True)
    dominates=(unique[:,None,:]>=unique[None,:,:]).all(axis=2)&(unique[:,None,:]>unique[None,:,:]).any(axis=2)
    incoming=dominates.sum(axis=0).astype(int)
    ranks=np.full(len(unique),-1,dtype=int)
    crowd=np.zeros(len(unique))
    level=0
    while np.any(ranks<0):
        front=np.flatnonzero((incoming==0)&(ranks<0))
        if not len(front):raise RuntimeError('Non-dominated sorting failed')
        ranks[front]=level
        for k in range(unique.shape[1]):
            v=unique[front,k]
            distinct,inv=np.unique(v,return_inverse=True)
            if len(distinct)<2:continue
            gap=np.zeros(len(distinct));gap[0]=gap[-1]=1.
            if len(distinct)>2:gap[1:-1]=(distinct[2:]-distinct[:-2])/(distinct[-1]-distinct[0])
            crowd[front]+=gap[inv]
        incoming-=dominates[front].sum(axis=0)
        level+=1
    return ranks[inverse],crowd[inverse]


def rank_population(candidates, physical_gate):
    eligible=[]
    for c in candidates:
        cls=constraint_class(c,physical_gate)
        c['pareto']={'constraint_class':cls,'rank':None,'crowding':0.,'source':'T0_common_fast_screen'}
        if cls==0:eligible.append(c)
    if eligible:
        values=np.array([[float(c['metrics'][k]) for k in OBJECTIVES] for c in eligible])
        ranks,crowd=_fronts(values)
        for c,r,d in zip(eligible,ranks,crowd):
            c['pareto'].update(rank=int(r),crowding=float(d))
    return [c['id'] for c in eligible if c['pareto']['rank']==0]


def parent_key(candidate):
    p=candidate.get('pareto',{})
    cls=p.get('constraint_class',0)
    rank=p.get('rank')
    return (-cls,-rank if rank is not None else 0,_finite(p.get('crowding'),0.),_finite(candidate.get('selection')))


def archive_key(candidate):
    # Rank and crowding are relative to one population, not archive-wide.
    return (-candidate.get('pareto',{}).get('constraint_class',0),_finite(candidate.get('selection')))
