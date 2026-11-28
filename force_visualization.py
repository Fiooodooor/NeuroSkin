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


def substrate_sections(centers, stress, pitch_mm, z_bottom, z_top):
    """Approximate force on the upper side of horizontal HEX8 substrate cuts.

    Stress is element-center Voigt [xx, yy, zz, xy, yz, xz] in MPa;
    n = -e_z is the outward normal of the upper region. Each aligned voxel
    contributes pitch² * sigma @ n at its section centroid. This is center-
    stress quadrature, not a fully equilibrated section integration; separate
    embedded-film forces are excluded. Coordinates are undeformed.
    """
    p=np.asarray(centers,float);s=np.asarray(stress,float);h=float(pitch_mm)
    if p.ndim!=2 or p.shape[1]!=3 or not len(p) or s.shape!=(len(p),6):
        raise ValueError('Invalid HEX8 section data')
    if not np.isfinite(p).all() or not np.isfinite(s).all() or not np.isfinite([h,z_bottom,z_top]).all() or h<=0 or z_top<=z_bottom:
        raise ValueError('Invalid section geometry')
    # Quantize only the layer IDs; actual returned coordinates remain physical.
    origin=float(p[:,2].min())
    layer=np.rint((p[:,2]-origin)/h).astype(int)
    z=origin+layer*h
    if not np.allclose(z,p[:,2],rtol=0.,atol=max(1e-8,h*1e-6)):
        raise ValueError('Section sampling requires aligned voxel HEX8 layers')
    available=np.unique(layer[(z>z_bottom)&(z<z_top)])
    targets=[z_bottom+(z_top-z_bottom)*f for f in (1/3,2/3)]
    picked=[]
    for target in targets:
        if not len(available):break
        i=int(available[np.argmin(np.abs(origin+available*h-target))])
        if i not in picked:picked.append(i)
    sections=[]
    for i in picked:
        mask=layer==i
        # N = MPa * mm². No absolute value: keep signed shear and tension.
        forces=-s[mask][:,[5,4,2]]*h*h
        section=summarize(p[mask],forces)
        section.update(z_mm=float(origin+i*h),area_mm2=float(mask.sum()*h*h),element_count=int(mask.sum()))
        sections.append(section)
    return sections
