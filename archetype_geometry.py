"""Parametric, endpoint-preserving 3-D motif deformations for seed-library archetypes.

All designs are conceptual volumetric strut networks (NOT replicas of cited papers).
Primary path endpoints remain attached to the common mechanical mounting system.
Secondary ribs connect known primary-member points; thickness follows the same
profile in visualization, surrogate mechanics and FEM rasterization.
"""
from __future__ import annotations
import math
import numpy as np

WEB_IDS={'s_radial_ladder','s_spatial_trellis','s_tripod_triage',
         'r_gyroid_web','r_tpms_diamond','r_lc_origami','r_fish_scale'}

def apply(family: str, g: dict, original: list):
    ident=g.get('topology','')
    if not ident.startswith(('s_','r_')):
        return original
    varied=[]
    phase=float(g.get('phase',0.))
    wave=max(1,int(g.get('wave_count',2)))
    amp=min(1.0,max(.20,float(g.get('wave_amp',.5))))
    primaries=[j for j,(_,_,tag) in enumerate(original) if tag=='leg']
    for i,(path,r,tag) in enumerate(original):
        pts=np.asarray(path,float).copy()
        if tag!='leg':
            varied.append((pts,r,tag));continue
        origin=pts[0,:2]
        radial=origin/max(1e-9,np.linalg.norm(origin))
        tangent=np.array([-radial[1],radial[0]])
        sign=1 if (i%2==0) else -1
        n=len(pts)
        for j in range(1,n-1):
            u=j/(n-1);s=math.sin(math.pi*u)**2
            w=2*math.pi*wave*u+phase
            dr=0.;dt=0.;dz=0.
            if ident=='s_wave_pairs':
                dt=sign*.68*amp*s*math.sin(2*math.pi*1.5*u)
            elif ident=='s_double_saddle':
                dt=sign*.72*amp*s*math.sin(2*math.pi*u);dr=.28*amp*s*math.cos(2*math.pi*u)
            elif ident=='s_radial_ladder':
                dr=.35*amp*s
            elif ident=='s_opposed_helix':
                dt=sign*.84*amp*s*math.sin(math.pi*u/1.7)
            elif ident=='s_catenary':
                dr=.65*amp*s;dz=.10*amp*s*math.sin(math.pi*u)
            elif ident=='s_gradient_arch':
                dr=.48*amp*s*(1-.5*u)
            elif ident=='s_split_helix':
                dt=sign*.85*amp*s*(math.sin(2*math.pi*u)+.33*math.sin(4*math.pi*u))
            elif ident=='s_tripod_triage':
                dt=sign*.35*amp*s;dr=.25*amp*s*math.sin(2*math.pi*u)
            elif ident=='s_mirror_flex':
                dt=sign*.52*amp*s*math.sin(2*math.pi*u);dr=sign*.16*amp*s
            elif ident=='s_spatial_trellis':
                dt=.31*amp*s*math.sin(w);dr=.29*amp*s*math.cos(w)
            elif ident=='r_fish_scale':
                dt=sign*.50*amp*s*math.sin(w);dr=.25*amp*s*math.cos(2*w)
            elif ident=='r_kirigami_hinge':
                # smoothed approximations of fold-like strain isolators
                dt=sign*.56*amp*s*math.sin(3*math.pi*u);dr=.27*amp*s*math.sin(2*math.pi*u)
            elif ident=='r_buckled_pvdf':
                dr=.66*amp*s*math.sin(math.pi*u);dt=.31*amp*s*math.sin(2*math.pi*u)
            elif ident=='r_gyroid_web':
                dr=.46*amp*s*math.sin(w);dt=.46*amp*s*math.cos(w)
            elif ident=='r_orthogonal_piezo':
                dr=.12*amp*s;dt=sign*.54*amp*s*math.sin(2*math.pi*u)
            elif ident=='r_microporous':
                dr=.24*amp*s*math.sin(4*math.pi*u);dt=.19*amp*s*math.cos(4*math.pi*u)
            elif ident=='r_auxetic_kirigami':
                dr=-.46*amp*s*math.sin(2*math.pi*u);dt=sign*.38*amp*s*math.sin(3*math.pi*u)
            elif ident=='r_rigid_island':
                dt=sign*.19*amp*s*math.sin(2*math.pi*u)
            elif ident=='r_lc_origami':
                dr=.38*amp*s*math.sin(4*math.pi*u);dt=sign*.24*amp*s*math.cos(4*math.pi*u)
            elif ident=='r_tpms_diamond':
                dr=.37*amp*s*math.sin(3*math.pi*u+phase);dt=.37*amp*s*math.cos(3*math.pi*u+phase)
            pts[j,:2]+=radial*dr+tangent*dt
            pts[j,2]+=dz
        varied.append((pts,r,tag))
    # Real crossbars between neighboring primary paths, not floating cosmetic parts.
    # Only a small number of braces to bound mesh size and make physical connectivity explicit.
    if ident in WEB_IDS and len(primaries)>=4:
        for k in range(min(4,len(primaries))):
            a=varied[primaries[k]][0];b=varied[primaries[(k+1)%len(primaries)]][0]
            index=max(2,min(len(a)-3,round(len(a)*(.42 if k%2 else .58))))
            start=a[index];end=b[index]
            if np.linalg.norm(end-start)<.3:continue
            n=max(9,round(len(a)*.6))
            points=[]
            for j in range(n):
                u=j/(n-1);p=start*(1-u)+end*u
                p[2]+=.15*amp*math.sin(math.pi*u)
                points.append(p)
            r=min(float(varied[primaries[k]][1]),float(varied[primaries[(k+1)%len(primaries)]][1]))*.54
            varied.append((np.asarray(points),max(.23,r),'web'))
    return varied
