"""Reproducible, angularly balanced placement of PVDF films on primary members.

This module contains only the geometric selection policy. It intentionally does
not imply bonded films are present in the continuum/beam FEM material model.
Missing ``piezo_count`` is historical v1.3 behavior (one film) to preserve
archived genotype reproducibility. New genomes explicitly specify 2 or 4.
"""
from __future__ import annotations
import itertools
import math
from functools import lru_cache
import numpy as np

VALID_COUNTS=(1,2,3,4,6,8)

def film_count(genome):
    v=int(genome.get('piezo_count',1))
    if v not in VALID_COUNTS:
        raise ValueError('PVDF film count must be one of 1,2,3,4,6,8')
    return v

@lru_cache(maxsize=4096)
def _cached_member_selection(key: tuple, n: int, phase: float):
    # Full audits repeat placement on the same geometry hundreds of times.
    ids=[row[0] for row in key]
    if n == 1:
        return (ids[0],)
    xy=np.asarray([(row[1],row[2]) for row in key],float)
    xy-=xy.mean(axis=0)
    ang=np.arctan2(xy[:,1],xy[:,0])
    target_gap=2*math.pi/n
    radial=max(float(np.linalg.norm(xy,axis=1).mean()),1e-7)
    best=None; best_score=float('inf')
    for subset in itertools.combinations(range(len(ids)),n):
        order=sorted(subset,key=lambda j: (ang[j]-phase)%(2*math.pi))
        a=np.sort(np.mod(ang[list(subset)]-phase,2*math.pi))
        gaps=np.diff(np.r_[a,a[0]+2*math.pi])
        circular=float(np.mean(((gaps-target_gap)/target_gap)**2))
        centroid=float(np.linalg.norm(xy[list(subset)].mean(axis=0))/radial)
        phase_mismatch=float(np.min(np.abs(np.angle(np.exp(1j*a)))))
        score=circular+1.5*centroid*centroid+0.0005*phase_mismatch
        if score < best_score:
            best_score=score; best=order
    return tuple(ids[j] for j in best)


def choose_film_members(paths, genome):
    """Return primary member indices; memoized by actual structural positions.

    A legacy genome lacking piezo_count retains its original single film.
    """
    candidates=[(int(i),round(float(points[0][0]),6),round(float(points[0][1]),6))
                for i,(points,_,tag) in enumerate(paths) if tag=='leg']
    n=film_count(genome)
    if len(candidates)<n:
        raise ValueError(f'{n} PVDF films requested, only {len(candidates)} primary beams')
    phase=round(float(genome.get('piezo_azimuth_rad',0.)),6)
    return list(_cached_member_selection(tuple(candidates),n,phase))

def layout_metrics(paths, genome, selected=None):
    selected=choose_film_members(paths,genome) if selected is None else selected
    pts=np.asarray([np.asarray(paths[k][0],float)[0,:2] for k in selected])
    all_leg=np.asarray([np.asarray(p[0],float)[0,:2] for p in paths if p[2]=='leg'])
    center=np.mean(all_leg,axis=0)
    imbalance=float(np.linalg.norm(np.mean(pts,axis=0)-center))
    radius=max(float(np.mean(np.linalg.norm(all_leg-center,axis=1))),1e-7)
    return dict(film_count=len(selected),strut_indices=[int(x) for x in selected],
                centroid_offset_mm=imbalance,normalized_imbalance=imbalance/radius,
                layout='single_legacy' if len(selected)==1 else f'balanced_{len(selected)}',
                legacy=('piezo_count' not in genome))
