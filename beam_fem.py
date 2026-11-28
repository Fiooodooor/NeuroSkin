"""3D geometrically curved Euler-Bernoulli space-frame FEM for thin NeuroSkin flexures.

A real mechanical finite-element system: 6 DOF/node (translation/rotation),
12x12 consistent 3D beam stiffness, exact assembled sparse equilibrium, constrained
base ends and rigid multi-point constraint at the contact-pad centre.

The linear (small rotation, small strain) *beam* approximation is very different
from nonlinear solid HEX8 and must NOT be represented as a refined 3D solid mesh.
Units: mm, N, MPa, radians. Fine axial pitch can be 0.15625 mm or smaller.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import ceil, pi, sqrt
import math
import time
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
from advanced import structural_struts, _profile_radius
from pvdf_array import choose_film_members
from pvdf_physics import charge_pc
from laminate_fem import film_interval, effective_film_properties


class BeamFEMError(ValueError):
    pass


def skew(r):
    x,y,z=map(float,r)
    return np.array([[0,-z,y],[z,0,-x],[-y,x,0]],float)


def local_frame(a,b):
    ex=np.asarray(b)-np.asarray(a)
    L=float(np.linalg.norm(ex))
    if L<1e-9:raise BeamFEMError('Zero-length member')
    ex=ex/L
    ref=np.array([0.,0.,1.]) if abs(ex[2])<.88 else np.array([0.,1.,0.])
    ey=np.cross(ref,ex);ey/=np.linalg.norm(ey)
    ez=np.cross(ex,ey)
    R=np.stack([ex,ey,ez])
    return R,L


def local_beam_stiffness(E,G,A,Iy,Iz,J,L):
    """Local x is beam axis. End DOFs [u_x,u_y,u_z,rx,ry,rz]."""
    K=np.zeros((12,12))
    def add2(i,j,k):
        K[i,i]+=k;K[j,j]+=k;K[i,j]-=k;K[j,i]-=k
    add2(0,6,E*A/L)
    add2(3,9,G*J/L)
    # Bending y, rotation z: classical Hermite beam.
    H=(E*Iz/L**3)*np.array([[12,6*L,-12,6*L],
                             [6*L,4*L*L,-6*L,2*L*L],
                             [-12,-6*L,12,-6*L],
                             [6*L,2*L*L,-6*L,4*L*L]])
    ids=[1,5,7,11]
    K[np.ix_(ids,ids)]+=H
    # Bending z, rotation y; physical ry = - dw/dx.
    ids=[2,4,8,10]
    T=np.diag([1,-1,1,-1])
    K[np.ix_(ids,ids)]+=T@((E*Iy/L**3)*np.array([
      [12,6*L,-12,6*L],[6*L,4*L*L,-6*L,2*L*L],
      [-12,-6*L,12,-6*L],[6*L,2*L*L,-6*L,4*L*L]]))@T
    return K


def sample_polyline(pts,pitch):
    pts=np.asarray(pts,dtype=float)
    d=np.linalg.norm(np.diff(pts,axis=0),axis=1)
    total=float(d.sum())
    if total<=0:raise BeamFEMError('Empty/zero-length centreline')
    nseg=max(2,int(ceil(total/pitch)))
    if nseg>1000:raise BeamFEMError('Too many segments for one member')
    arclength=np.r_[0.,np.cumsum(d)]
    s=np.linspace(0,total,nseg+1)
    coords=np.stack([np.interp(s,arclength,pts[:,k]) for k in range(3)],axis=1)
    return coords


@dataclass
class BeamPart:
    nodes: np.ndarray
    transforms: list
    global_ids: list
    radius: np.ndarray
    tag: str
    index: int
    displacement: np.ndarray | None = None
    stress: np.ndarray | None = None


class BeamFEM:
    def __init__(self,family,genome,pitch_mm=.15625,poisson=.35,max_nodes=12000):
        t0=time.monotonic()
        if family not in ('crown','chiral','quadrant'):raise ValueError('unknown family')
        if genome.get('hybrid_id','none') not in ('none',None,''):
            raise BeamFEMError('Beam FEM does not support coupled hybrid stage interfaces; use HEX8')
        if not .05<=pitch_mm<=2.5:raise ValueError('beam pitch must be in 0.05..2.5 mm')
        self.family=family;self.genome=dict(genome);self.pitch_mm=float(pitch_mm)
        self.E=float(genome.get('material_E',1.))
        if not .05<=self.E<=5000:raise BeamFEMError('Invalid Young modulus')
        self.G=self.E/(2*(1+poisson))
        self.padcentre=np.array([float(genome.get('pad_offset_x',0.)),float(genome.get('pad_offset_y',0.)),float(genome['height'])],float)
        self.pad_radius=float(genome.get('pad_radius',3.2))+.4
        self.parts=[];self.elements=[]
        self.laminate_segments=[]
        self.pvdf_member_indices=[]
        self.pvdf_properties=[]
        # Global unknown 0 is shared 6DOF rigid contact-pad reference.
        next_id=1
        rows=[];cols=[];values=[]
        paths=structural_struts(family,genome)
        if not paths:raise BeamFEMError('No load-bearing members')
        selected=choose_film_members(paths,genome)
        self.pvdf_member_indices=list(selected)
        material_by_member={}
        for idx in selected:
            path,radius,tag=paths[idx]
            _,_,lo,hi=film_interval(path,genome)
            props=effective_film_properties(genome,hi-lo,float(radius))
            material_by_member[idx]=(lo,hi,props)
            self.pvdf_properties.append(props)
        for path_idx,(path,radius,tag) in enumerate(paths):
            nodes=sample_polyline(path,self.pitch_mm)
            N=len(nodes)
            ids=[-1]+list(range(next_id,next_id+N-2))+[0]
            next_id+=N-2
            if next_id>max_nodes:raise BeamFEMError('Beam model exceeds max_nodes; increase pitch or node budget')
            Ts=[]
            for j in range(N):
                if j==N-1:
                    M=np.eye(6)
                    M[:3,3:]=-skew(nodes[j]-self.padcentre)
                else:M=np.eye(6)
                Ts.append(M)
            radii=np.array([_profile_radius(float(radius),i/(N-1),genome,tag) for i in range(N)])
            part=BeamPart(nodes,Ts,ids,radii,tag,path_idx)
            self.parts.append(part)
            sampled_arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(nodes,axis=0),axis=1))]
            for j in range(N-1):
                a,b=nodes[j:j+2]
                R,L=local_frame(a,b)
                r=float((radii[j]+radii[j+1])/2)
                A=pi_circle_area(r);I=pi*r**4/4;J=2*I
                film_EA=0.;props=None
                if path_idx in material_by_member:
                    lo,hi,props=material_by_member[path_idx]
                    middle=.5*(sampled_arc[j]+sampled_arc[j+1])
                    if lo<=middle<=hi:
                        film_EA=props['axial_EA_N']
                        eccentricity=r+props['adhesive_thickness_mm']+.5*props['film_thickness_mm']
                        A+=film_EA/self.E
                        # Isotropic bending approximation is a simplified composite beam,
                        # not a through-thickness laminate/shell neutral-axis model.
                        I+=film_EA*eccentricity**2/self.E
                        self.laminate_segments.append((path_idx,j,L,film_EA,props))
                kl=local_beam_stiffness(self.E,self.G,A,I,I,J,L)
                T6=np.zeros((6,6));T6[:3,:3]=R;T6[3:,3:]=R
                T12=np.zeros((12,12));T12[:6,:6]=T6;T12[6:,6:]=T6
                Kworld=T12.T@kl@T12
                ids2=(ids[j],ids[j+1]);mm=(Ts[j],Ts[j+1])
                for i1 in range(2):
                    if ids2[i1]<0:continue
                    row_ids=np.arange(ids2[i1]*6,ids2[i1]*6+6)
                    for i2 in range(2):
                        if ids2[i2]<0:continue
                        col_ids=np.arange(ids2[i2]*6,ids2[i2]*6+6)
                        block=mm[i1].T@Kworld[i1*6:(i1+1)*6,i2*6:(i2+1)*6]@mm[i2]
                        rows.extend(np.broadcast_to(row_ids[:,None],(6,6)).ravel())
                        cols.extend(np.broadcast_to(col_ids[None,:],(6,6)).ravel())
                        values.extend(block.ravel())
                self.elements.append((path_idx,j,kl,T12,Kworld))
        self.n_nodes=next_id;self.n_elements=len(self.elements)
        K=coo_matrix((np.asarray(values),(rows,cols)),shape=(6*next_id,6*next_id)).tocsc()
        K.sum_duplicates()
        self.K=K
        try:self.lu=splu(K)
        except RuntimeError as exc:
            import numpy as _np
            kdiag=_np.asarray(K.diagonal()); bad=_np.flatnonzero(kdiag<1.e-12)
            raise BeamFEMError(f'Singular frame: bad diagonal {bad[:10]} min={kdiag.min()} nodes={next_id}') from exc
        self.setup_s=time.monotonic()-t0

    def _endpoint_dofs(self,part,j,U):
        id=part.global_ids[j]
        return np.zeros(6) if id<0 else part.transforms[j]@U[6*id:6*id+6]

    def solve(self,force=(0,0,-.1),offset=(0.,0.),torque_z_Nmm=0.,include_fields=False):
        F=np.asarray(force,dtype=float)
        off=np.asarray(offset,dtype=float)
        if F.shape!=(3,) or off.shape!=(2,) or not np.isfinite(F).all() or not np.isfinite(off).all():
            raise BeamFEMError('Invalid load')
        if np.linalg.norm(off)>self.pad_radius+.01:
            raise BeamFEMError('Contact location is outside pad; no real contact possible')
        t0=time.monotonic()
        f=np.zeros(6*self.n_nodes);f[:3]=F
        f[3:6]=np.cross(np.array([off[0],off[1],0]),F)
        f[5]+=float(torque_z_Nmm)
        U=self.lu.solve(f)
        self._last_U=U
        residual=float(np.linalg.norm(self.K@U-f)/max(1e-12,np.linalg.norm(f)))
        if residual>1e-5:raise BeamFEMError(f'Beam force equilibrium failed: residual={residual:.3g}')
        reaction=np.zeros(6)
        maxstress=0.;maxstrain=0.;stress_perpart={}
        for part in self.parts:
            D=np.stack([self._endpoint_dofs(part,j,U) for j in range(len(part.nodes))])
            part.displacement=D
            part.stress=np.zeros(len(part.nodes))
        for partidx,j,kl,T12,Kworld in self.elements:
            part=self.parts[partidx]
            pa,pb=part.nodes[j:j+2]
            R,L=local_frame(pa,pb)
            wa,wb=part.displacement[j:j+2]
            local=T12@np.r_[wa,wb]
            p_local=kl@local
            if j==0:
                reaction+=np.r_[p_local[:3]@R,p_local[3:6]@R] + np.r_[np.zeros(3),np.cross(pa-self.padcentre,p_local[:3]@R)]
            r=float((part.radius[j]+part.radius[j+1])/2)
            A=pi_circle_area(r);I=pi*r**4/4;J=2*I
            axial=max(abs(p_local[0]),abs(p_local[6]))/A
            bending=max(np.linalg.norm(p_local[[4,5]]),np.linalg.norm(p_local[[10,11]]))*r/I
            tors=max(abs(p_local[3]),abs(p_local[9]))*r/J
            stress=sqrt((axial+bending)**2+3*tors**2)
            maxstress=max(maxstress,stress);maxstrain=max(maxstrain,(axial+bending)/self.E)
            part.stress[j]=max(part.stress[j],stress);part.stress[j+1]=max(part.stress[j+1],stress)
        # Base moment computed about pad center, so counterpart of external generalized load.
        reaction_force_balance=float(np.linalg.norm(reaction[:3]+F)/max(np.linalg.norm(F),1e-12))
        moment_balance=float(np.linalg.norm(reaction[3:]+f[3:6])/max(np.linalg.norm(f[3:6]),np.linalg.norm(F)*self.pad_radius,1e-12))
        laminate_energy=0.;per_member={}
        # Recovery of effective PVDF strain from the solved beam displacements.
        for member_id,element_id,L,ea,props in self.laminate_segments:
            part=self.parts[member_id]
            Apos,Bpos=part.nodes[element_id:element_id+2]
            tangent=(Bpos-Apos)/L
            ua=self._endpoint_dofs(part,element_id,U)[:3]
            ub=self._endpoint_dofs(part,element_id+1,U)[:3]
            axial=float(np.dot(ub-ua,tangent)/L)
            film_force=float(ea*axial)
            en=.5*ea*L*axial*axial
            laminate_energy+=en
            x=per_member.setdefault(member_id,{'sum_strain_L':0.,'length_mm':0.,'max_abs_effective_strain':0.,'energy_Nmm':0.,'film_force_N':0.})
            x['sum_strain_L']+=axial*L;x['length_mm']+=L
            x['max_abs_effective_strain']=max(x['max_abs_effective_strain'],abs(axial));x['energy_Nmm']+=en;x['film_force_N']+=film_force*L
        film_response=[]
        for i,member_id in enumerate(self.pvdf_member_indices):
            props=self.pvdf_properties[i];x=per_member.get(member_id,{})
            length=x.get('length_mm',0.)
            avg=x.get('sum_strain_L',0.)/max(length,1.e-12)
            charge=charge_pc(props,props['shear_lag_transfer']*avg) if length>0 else 0.0
            film_response.append({'film_index':i,'member_index':member_id,'effective_strain':float(avg),
               'max_abs_effective_film_strain':float(x.get('max_abs_effective_strain',0.)),
               'estimated_charge_pC':float(charge),'charge_amp_V_assumed':float(charge/props['piezo_feedback_pf']),
               'shear_lag_transfer':props['shear_lag_transfer'],'mechanical_energy_Nmm':float(x.get('energy_Nmm',0.))})
        d=U[:6]
        contact_displacement=d[:3]+np.cross(d[3:6],np.r_[off,0.])
        motion_max=max(float(np.linalg.norm(part.displacement[:,:3],axis=1).max()) for part in self.parts)
        result=dict(
            load_force_N=F.tolist(),offset_mm=off.tolist(),torque_z_Nmm=float(torque_z_Nmm),
            backend='linear_euler_bernoulli_space_frame',beam_pitch_mm=self.pitch_mm,
            nodes=self.n_nodes,elements=self.n_elements,
            top_dofs=d.tolist(),loaded_nodes=1,
            contact_patch_mode='rigid_pad_master',
            contact_patch_radius_used_mm=self.pad_radius,
            mean_contact_displacement_mm=contact_displacement.tolist(),
            mean_down_mm=float(-contact_displacement[2]),
            max_displacement_mm=motion_max,
            max_von_mises_MPa=maxstress,
            max_abs_principal_strain=maxstrain,
            max_principal_strain=maxstrain,
            force_reaction_N=reaction[:3].tolist(),moment_reaction_Nmm=reaction[3:6].tolist(),
            force_equilibrium_relative=reaction_force_balance,
            moment_equilibrium_relative=moment_balance,
            free_residual_relative=residual,
            energy_Nmm=float(.5*U@self.K@U),solve_s=time.monotonic()-t0,
            pvdf_stiffness_included=bool(self.laminate_segments),
            pvdf_adhesive_model='composite_beam_shear_lag_simplified',
            laminate_energy_Nmm=float(laminate_energy),
            pvdf_laminate_response={'film_count':len(self.pvdf_member_indices),'per_film':film_response,
                'total_laminate_energy_Nmm':float(laminate_energy),
                'film_mass_g':float(sum(k['film_mass_g'] for k in self.pvdf_properties)),
                'adhesive_mass_g':float(sum(k['adhesive_mass_g'] for k in self.pvdf_properties))},
            model_assumptions='linear 3D Euler-Bernoulli beam elements with effective PVDF axial/bending reinforcement and compliant adhesive shear-transfer; rigid pad, no resolved shell/peel/large deformation')
        if include_fields:
            result['fields']=self.surface_fields(U)
        return result

    def surface_fields(self,U=None,radial_sections=10):
        if U is None:U=np.zeros(6*self.n_nodes)
        nodes=[];disp=[];stress=[];faces=[]
        for part in self.parts:
            start=len(nodes)
            N=len(part.nodes)
            for j,point in enumerate(part.nodes):
                if j==0:tangent=part.nodes[1]-point
                elif j==N-1:tangent=point-part.nodes[j-1]
                else:tangent=part.nodes[j+1]-part.nodes[j-1]
                tangent=tangent/np.linalg.norm(tangent)
                ref=np.array([0,0,1.]) if abs(tangent[2])<.88 else np.array([0,1.,0])
                e1=np.cross(ref,tangent);e1/=np.linalg.norm(e1)
                e2=np.cross(tangent,e1)
                d=self._endpoint_dofs(part,j,U)
                for k in range(radial_sections):
                    a=2*pi*k/radial_sections
                    radial=part.radius[j]*(e1*math.cos(a)+e2*math.sin(a))
                    nodes.append(point+radial)
                    disp.append(d[:3]+np.cross(d[3:6],radial))
                    stress.append(float(part.stress[j]) if part.stress is not None else 0.)
            for j in range(N-1):
                a=start+j*radial_sections
                b=start+(j+1)*radial_sections
                for k in range(radial_sections):
                    kn=(k+1)%radial_sections
                    faces.append((a+k,a+kn,b+kn))
                    faces.append((a+k,b+kn,b+k))
        # Top rigid contact pad: circular rim and a center fan at two heights.
        start=len(nodes)
        rad=self.pad_radius
        h=self.padcentre[2]
        top=U[:6]
        for z in (h-.25,h+.25):
            for k in range(32):
                a=2*pi*k/32
                relative=np.array([rad*math.cos(a),rad*math.sin(a),z-h])
                nodes.append(self.padcentre+relative)
                disp.append(top[:3]+np.cross(top[3:6],relative))
                stress.append(0.)
        for k in range(32):
            n=(k+1)%32
            faces.extend([(start+k,start+n,start+32+n),(start+k,start+32+n,start+32+k)])
        for ring in (0,1):
            centerid=len(nodes)
            rel=np.array([0,0,(-.25 if ring==0 else .25)])
            nodes.append(self.padcentre+rel)
            disp.append(top[:3]+np.cross(top[3:6],rel));stress.append(0.)
            for k in range(32):
                a=start+ring*32+k;b=start+ring*32+(k+1)%32
                faces.append((centerid,a,b) if ring==1 else (centerid,b,a))
        return dict(vertices_mm=np.round(np.asarray(nodes),5).tolist(),
                    faces=faces, displacement_mm=np.round(np.asarray(disp),8).tolist(),
                    stress_vm_MPa=np.round(np.asarray(stress),6).tolist(),
                    principal_strain=np.round(np.asarray(stress)/self.E,7).tolist(),
                    note='Beam-FEM surface reconstruction. Node motion includes section rotations, stresses are 1D beam-theory estimates, not 3D solid stresses.')


def pi_circle_area(radius):return pi*radius*radius


def beam_sweep(family,g,pitch_mm=.25,include_fields=False,inspector_case='press_center',
               inspector_force_N=.1,inspector_offset=(0.,0.)):
    fem=BeamFEM(family,g,pitch_mm)
    cases={
      'press_center':dict(force=(0.,0.,-.1)),
      'press_x_minus':dict(force=(0.,0.,-.1),offset=(-1.4,0.)),
      'press_x_plus':dict(force=(0.,0.,-.1),offset=(1.4,0.)),
      'press_y_minus':dict(force=(0.,0.,-.1),offset=(0.,-1.4)),
      'press_y_plus':dict(force=(0.,0.,-.1),offset=(0.,1.4)),
      'shear_x':dict(force=(.03,0.,-.04)),
      'shear_y':dict(force=(0.,.03,-.04)),
      'torsion_z':dict(force=(0.,0.,-.04),torque_z_Nmm=.02)}
    results={name:fem.solve(**kwargs,include_fields=(include_fields and name=='press_center')) for name,kwargs in cases.items()}
    baseline=results['press_center']
    extrema=max(v['max_abs_principal_strain'] for v in results.values())
    central=baseline['mean_down_mm']
    pressure_valid=bool(central>1e-6 and baseline['energy_Nmm']>0 and all(results[k]['mean_down_mm']>1e-7 for k in list(cases)[:5]))
    epsilon0=.0088541878128; area=7.;gap=.45;epsr=2.8
    c0=epsilon0*epsr*area/gap
    signals={}
    for name,v in results.items():
        dz=np.clip(v['mean_down_mm'],-gap*.7,gap*.8)
        signals[name]=float(c0*(gap/(gap-dz)-1))
    spread=max(results[k]['mean_down_mm'] for k in list(cases)[:5])-min(results[k]['mean_down_mm'] for k in list(cases)[:5])
    sensitivity=float(np.clip(math.log1p(abs(signals['press_center'])/.0003)/math.log1p(200.),0.,1.))
    uniformity=float(math.exp(-max(0.,spread)/max(abs(central),.002)))
    guard=float(math.exp(-max(0,extrema-.07)*14))
    volume=sum(float(np.sum(np.linalg.norm(np.diff(p.nodes,axis=0),axis=1)*pi*((p.radius[:-1]+p.radius[1:])/2)**2)) for p in fem.parts)
    mass_guard=float(math.exp(-max(0.,volume-480)/450))
    score=round(float(100*(.35*sensitivity+.3*uniformity+.2*guard+.15*mass_guard)),4)
    max_motion=max(v['max_displacement_mm'] for v in results.values())
    relative_motion=max_motion/max(float(g['height']),1e-8)
    feasible=bool(pressure_valid and extrema<.08 and relative_motion<.15 and all(v['moment_equilibrium_relative']<1e-5 and v['force_equilibrium_relative']<1e-5 for v in results.values()))
    if not feasible:score=min(score,14.99)
    reports={k:{kk:(round(float(vv),7) if isinstance(vv,(float,np.floating)) else vv) for kk,vv in v.items() if kk!='fields'} for k,v in results.items()}
    report=dict(fem_backend='actual_3d_beam_frame_EB',mesh_pitch_mm=pitch_mm,elements=fem.n_elements,nodes=fem.n_nodes,volume_mm3=round(volume,2),
        inflated_features=0,max_motion_over_height=relative_motion,beam_linear_valid=feasible,mesh_warning='Beam FE uses physical member radii; axial pitch is NOT 3D voxel pitch. Linear small-strain assumption.',
        elastic_E_MPa=fem.E,poisson=.35,setup_time_s=round(fem.setup_s,4),load_cases=reports,
        capacitance_delta_pF_assumed=signals,max_abs_principal_strain=extrema,pressure_uniformity=uniformity,pressure_valid=pressure_valid,
        force_equilibrium_max=max(v['force_equilibrium_relative'] for v in results.values()),
        moment_equilibrium_max=max(v['moment_equilibrium_relative'] for v in results.values()),
        fem_score=score,feasible_linear=feasible,
        pvdf_stiffness_included=all(v.get('pvdf_stiffness_included',False) for v in results.values()),
        pvdf_adhesive_model='composite_beam_shear_lag_simplified',
        pvdf_film_count=len(fem.pvdf_member_indices),
        pvdf_total_laminate_energy_Nmm=baseline.get('laminate_energy_Nmm',0.),
        pvdf_fraction_of_total_energy=baseline.get('laminate_energy_Nmm',0.)/max(baseline['energy_Nmm'],1e-14),
        pvdf_max_abs_effective_strain=max((v['max_abs_effective_film_strain'] for r in results.values() for v in r['pvdf_laminate_response']['per_film']),default=0.),
        notes=['Real linear space-frame beam FEM with 6 degrees of freedom per node','No voxel inflation; physical member radius included',
             'Not solid 3-D FEM, contact/hyperelasticity excluded; PVDF/adhesive represented via 1D composite effective stiffness, not resolved bonded shell','Electrical response remains a separate parallel-plate estimate'])
    if include_fields:
        if inspector_case not in ('press_center','press_offset','shear_x','shear_y','torsion_z'):
            raise ValueError('Unsupported FEM inspection case')
        fn=float(inspector_force_N)
        if not 0.<fn<=.5:raise ValueError('Invalid inspection force')
        off=tuple(map(float,inspector_offset))
        opts={'press_center':dict(force=(0.,0.,-fn)),
              'press_offset':dict(force=(0.,0.,-fn),offset=off),
              'shear_x':dict(force=(fn*.3,0.,-fn*.4)),
              'shear_y':dict(force=(0.,fn*.3,-fn*.4)),
              'torsion_z':dict(force=(0.,0.,-fn*.4),torque_z_Nmm=.02*(fn/.1))}[inspector_case]
        inspection=(results['press_center'] if inspector_case=='press_center' and abs(fn-.1)<1e-12 else fem.solve(include_fields=True,**opts))
        if 'fields' not in inspection:
            inspection=dict(inspection,fields=fem.surface_fields(fem._last_U))
        report['fields']=inspection['fields']
        report['inspection_case']=inspector_case
        report['inspection_metrics']={k:v for k,v in inspection.items() if k!='fields'}
    return report
