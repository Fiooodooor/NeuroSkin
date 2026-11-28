"""Resultant-preserving boundary wrench summaries for FEM visualization only."""
import numpy as np


def summarize(positions, forces, couples=None, bins=4):
    """Spatially aggregate vectors in XY bins; preserve force and moment about origin.

    Each group's force is plotted at its geometric centroid. An accompanying
    free couple accounts for the exact difference in moment (including pure
    beam support moments). Never infer internal stress trajectories from this.
    """
    p=np.asarray(positions,float);f=np.asarray(forces,float)
    c=np.zeros_like(f) if couples is None else np.asarray(couples,float)
    if p.ndim!=2 or p.shape[1]!=3 or not len(p) or f.shape!=p.shape or c.shape!=p.shape:
        raise ValueError('Invalid boundary vector arrays')
    if not all(np.isfinite(a).all() for a in (p,f,c)) or type(bins) is not int or not 1<=bins<=8:
        raise ValueError('Invalid boundary vector values or bin count')
    lo=p[:,:2].min(axis=0);span=np.ptp(p[:,:2],axis=0)
    xy=np.minimum(bins-1,np.floor((p[:,:2]-lo)/np.maximum(span,1e-12)*bins).astype(int))
    ids=xy[:,0]*bins+xy[:,1]
    result=[]
    for i in np.unique(ids):
        mask=ids==i;pos=p[mask].mean(axis=0);force=f[mask].sum(axis=0)
        couple=(np.cross(p[mask]-pos,f[mask])+c[mask]).sum(axis=0)
        result.append({'position_mm':pos.tolist(),'force_N':force.tolist(),'couple_Nmm':couple.tolist(),'node_count':int(mask.sum())})
    return {'groups':result,'force_N':f.sum(axis=0).tolist(),
            'moment_about_origin_Nmm':(np.cross(p,f)+c).sum(axis=0).tolist(),
            'node_count':len(p)}


def boundary_wrenches(load_positions,load_forces,reaction_positions,reaction_forces,load_couples=None,reaction_couples=None,source='HEX8 nodal vectors'):
    load=summarize(load_positions,load_forces,load_couples)
    reaction=summarize(reaction_positions,reaction_forces,reaction_couples)
    return {'source':source,'applied':load,'reaction':reaction,
            'force_balance_N':(np.asarray(load['force_N'])+reaction['force_N']).tolist(),
            'moment_balance_Nmm':(np.asarray(load['moment_about_origin_Nmm'])+reaction['moment_about_origin_Nmm']).tolist(),
            'note':'Reference-coordinate boundary resultants, not internal stress trajectories. Free couples are retained numerically; force arrows alone do not depict all moments.'}
