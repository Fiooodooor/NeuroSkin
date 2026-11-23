"""Embedded PVDF-film / adhesive shear-transfer reinforcement for NeuroSkin.

Small-strain mechanically coupled approximation, not a layered shell model.
Uses a positive-semidefinite 1D membrane stiffness distributed onto nearby HEX8
substrate nodes.  The adhesive is a finite shear-lag transmission compliance in
series with the film. No piezoelectric voltage/field feedback is solved.

Units: mm, N, MPa (N/mm^2), pC, g.  The stiffness is assembled directly
into the SAME structural equilibrium equation as the elastomer HEX8 solid.

The distinction is important: (1) geometry/stiffness of PVDF DO affect
mechanical displacement, stress and selection; (2) this is not a calibrated
3D shell+adhesive multiphysics model and must be labelled as such.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.spatial import cKDTree
from pvdf_array import choose_film_members

DEFAULT_E_PVDF_MPA=2500.0  # typical films 2--4 GPa, material-dependent
DEFAULT_ADHESIVE_G_MPA=1.0 # assumption; must be measured for bonded laminate
DEFAULT_ADHESIVE_THICKNESS_MM=0.06
D31_PC_N=-23.0 # assumed nominal dynamic coefficient, not a calibrated electrode


def material_parameters(genome: dict) -> dict:
    def param(k, default, low, high):
        v=float(genome.get(k,default))
        if not (math.isfinite(v) and low <= v <= high):
            raise ValueError(f'Unphysical laminate parameter {k}={v}; allowed {low}..{high}')
        return v
    return {
        'pvdf_E_MPa':param('piezo_E_MPa',DEFAULT_E_PVDF_MPA,100.,10000.),
        'film_thickness_mm':param('piezo_thickness_um',28.,10.,250.)/1000.,
        'film_width_mm':param('piezo_width_mm',2.5,.2,10.),
        'film_span_mm':param('piezo_span_mm',4.,.3,20.),
        'adhesive_G_MPa':param('piezo_adhesive_G_MPa',DEFAULT_ADHESIVE_G_MPA,.001,100.),
        'adhesive_thickness_mm':param('piezo_adhesive_thickness_um',60.,5.,500.)/1000.,
        'bond_fraction':param('piezo_bond_fraction',.95,.1,1.),
        'film_position':param('piezo_position',.5,.04,.96),
        'piezo_feedback_pf':param('piezo_feedback_pf',100.,1.,10000.),
    }


def effective_film_properties(genome: dict, span_mm:float, member_radius_mm:float) -> dict:
    """Finite shear transfer approximation for a thin film bonded to a soft beam.

    Equivalent axial film stiffness k=eta*E_f*A/L. Two adhesive shear springs
    are treated in series with the film; eta=1/(1+2 E_f t_f t_a/(G_a c L^2)).
    This formula is a cheap shear-lag screen, not a distributed bond solution.
    """
    p=material_parameters(genome)
    L=max(float(span_mm),.2)
    w=min(p['film_width_mm'],max(.22,1.45*float(member_radius_mm)))
    E=p['pvdf_E_MPa']; thickness=p['film_thickness_mm']; t_a=p['adhesive_thickness_mm']; G=p['adhesive_G_MPa']
    eta=1./(1.+2.*E*thickness*t_a/(G*p['bond_fraction']*L**2))
    A=w*thickness
    return {**p,'effective_width_mm':w,'effective_span_mm':L,'shear_lag_transfer':eta,
            'axial_EA_N':eta*E*A, 'axial_stiffness_N_mm':eta*E*A/L,
            'film_volume_mm3':A*L,'adhesive_volume_mm3':w*L*t_a*p['bond_fraction'],
            'film_mass_g':A*L*.00178,
            'adhesive_mass_g':w*L*t_a*p['bond_fraction']*.0011}


def film_interval(points: np.ndarray, genome:dict):
    path=np.asarray(points,dtype=float)
    seg=np.linalg.norm(np.diff(path,axis=0),axis=1)
    total=float(seg.sum())
    if total < .2:raise ValueError('Degenerate PVDF support path')
    arclen=np.r_[0., np.cumsum(seg)]
    material=material_parameters(genome)
    mid=material['film_position']*total
    span=max(.35,min(material['film_span_mm'],.82*total))
    low=max(.07*total,mid-span/2.)
    high=min(.93*total,mid+span/2.)
    if high-low<.2:high=min(.96*total,low+.2)
    return path,arclen,float(low),float(high)


def film_stations(points:np.ndarray, genome:dict, member_radius_mm:float, pitch_mm:float):
    path,arc,low,high=film_interval(points,genome)
    material=material_parameters(genome)
    n=max(3,min(17,1+int(math.ceil((high-low)/max(.45,2.*pitch_mm)))))
    ss=np.linspace(low,high,n)
    pos=np.column_stack([np.interp(ss,arc,path[:,k]) for k in range(3)])
    dirs=np.gradient(pos,axis=0)
    surface=[]
    for pt,d in zip(pos,dirs):
        t=d/max(np.linalg.norm(d),1e-12)
        radial=np.array([pt[0],pt[1],0.],float)
        radial-=radial.dot(t)*t
        if np.linalg.norm(radial)<1e-8:
            radial=np.cross(t,np.array([0.,0.,1.]))
        radial/=max(np.linalg.norm(radial),1e-12)
        surface.append(pt+radial*(member_radius_mm+material['adhesive_thickness_mm']+material['film_thickness_mm']*.5))
    return np.asarray(surface), float(high-low)


@dataclass
class FilmEdge:
    indices:np.ndarray
    vector:np.ndarray
    stiffness_N_mm:float
    length_mm:float
    film_index:int
    member_index:int


@dataclass
class LaminateReinforcement:
    stiffness:csr_matrix
    edges:list[FilmEdge]
    properties:list[dict]
    film_count:int
    member_indices:list[int]
    mapped_sites:int
    def energy_Nmm(self,flat_displacement) -> float:
        u=np.asarray(flat_displacement,float)
        return .5*float(u @ (self.stiffness@u))
    def response(self,flat_displacement) -> dict:
        u=np.asarray(flat_displacement,float)
        per=[]
        for fi,p in enumerate(self.properties):
            edges=[e for e in self.edges if e.film_index==fi]
            strains=np.asarray([float(np.dot(e.vector,u[e.indices]))/e.length_mm for e in edges],float)
            # These strains are effective substrate strains filtered through bond compliance.
            avg=float(np.average(strains,weights=np.asarray([e.length_mm for e in edges])))
            maximum=float(np.max(np.abs(strains)))
            ffilm=p['pvdf_E_MPa']*p['effective_width_mm']*p['film_thickness_mm']*p['shear_lag_transfer']*avg
            charge=D31_PC_N*ffilm
            energy=float(sum(.5*e.stiffness_N_mm*np.dot(e.vector,u[e.indices])**2 for e in edges))
            per.append({'film_index':fi,'member_index':self.member_indices[fi],
                        'effective_strain':avg,'max_abs_effective_strain':maximum,
                        'effective_film_force_N':float(ffilm),'estimated_charge_pC':float(charge),
                        'charge_amp_V_assumed':float(charge/p['piezo_feedback_pf']),
                        'mechanical_energy_Nmm':energy,
                        'shear_lag_transfer':p['shear_lag_transfer']})
        return {'film_count':self.film_count,'per_film':per,
                'max_abs_effective_film_strain':max((p['max_abs_effective_strain'] for p in per),default=0.),
                'total_laminate_energy_Nmm':self.energy_Nmm(u),
                'total_estimated_charge_pC':float(sum(p['estimated_charge_pC'] for p in per)),
                'film_mass_g':float(sum(p['film_mass_g'] for p in self.properties)),
                'adhesive_mass_g':float(sum(p['adhesive_mass_g'] for p in self.properties))}


def embed_laminate(mesh, family:str, genome:dict) -> LaminateReinforcement:
    """Assemble energy-equivalent film membrane stiffness into actual HEX8 DOFs.

    4-nearest-node displacement interpolation follows the *surface* of each
    selected supporting beam. Actual mapped nodal positions define the axial
    direction, preserving infinitesimal rigid-body invariance and moment balance.
    It does not resolve through-thickness stresses, peel, debonding or full shells.
    """
    from advanced import structural_struts, _profile_radius
    paths=structural_struts(family,genome)
    chosen=choose_film_members(paths,genome)
    if not chosen:raise ValueError('No PVDF film members')
    tree=cKDTree(mesh.nodes)
    rows=[];cols=[];data=[];edges=[];properties=[];numsites=0
    ndof=3*len(mesh.nodes)
    for fi,index in enumerate(chosen):
        path,r,tag=paths[index]
        # The ribbon has a variable profile along its span; this average
        # also bounds its physically available width.
        radius=float(np.mean([_profile_radius(r,u,genome,tag) for u in (.3,.5,.7)]))
        positions,length=film_stations(path,genome,radius,mesh.pitch_mm)
        material=effective_film_properties(genome,length,radius)
        sites=[]
        for xyz in positions:
            dist,ids=tree.query(xyz,k=min(4,len(mesh.nodes)))
            ids=np.atleast_1d(ids).astype(np.int32)
            ds=np.atleast_1d(dist).astype(float)
            if ds.min()>max(2.6*mesh.pitch_mm,1.0):
                raise ValueError(f'Film {fi}: too far from HEX8 substrate ({ds.min():.3g} mm); refine geometry')
            if ds[0]<1e-7:weights=np.eye(1,len(ids),0).ravel()
            else:
                inv=1./np.maximum(ds,1e-6)**2
                weights=inv/inv.sum()
            coord=weights@mesh.nodes[ids]
            sites.append((ids,weights,coord))
            numsites+=1
        for (ids0,w0,x0),(ids1,w1,x1) in zip(sites[:-1],sites[1:]):
            delta=x1-x0
            L=float(np.linalg.norm(delta))
            if L<1e-5:continue
            tangent=delta/L
            accum={}
            for sign,ids,w in ((-1.,ids0,w0),(1.,ids1,w1)):
                for node,weight in zip(ids,w):
                    for axis in range(3):
                        key=3*int(node)+axis
                        accum[key]=accum.get(key,0.)+sign*float(weight)*float(tangent[axis])
            idx=np.asarray(sorted(accum),np.int32)
            val=np.asarray([accum[int(i)] for i in idx],float)
            kp=material['axial_EA_N']/L
            edges.append(FilmEdge(idx,val,kp,L,fi,int(index)))
            rr=np.repeat(idx,len(idx));cc=np.tile(idx,len(idx))
            rows.extend(rr.tolist());cols.extend(cc.tolist());data.extend((kp*np.outer(val,val)).ravel().tolist())
        properties.append(material)
    if not edges:raise ValueError('PVDF film has no valid mechanically coupled segments')
    stiffness=coo_matrix((data,(rows,cols)),shape=(ndof,ndof)).tocsr()
    stiffness.sum_duplicates()
    return LaminateReinforcement(stiffness,edges,properties,len(chosen),[int(i) for i in chosen],numsites)
