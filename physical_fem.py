"""NeuroSkin 1.2: actual 3D, small-strain, isotropic linear-elastic HEX8 FEM.

Geometry comes from the SAME parametrized structural_struts() used by the viewer.
Every occupied voxel is an 8-node *solid* finite element (not a spring proxy).
Units throughout: mm, N, MPa=N/mm^2, N*mm. No large strains/contact/PVDF coupling.

The meshing step explicitly discloses minimum-thickness voxel inflation, so it is
NOT a substitute for a tetrahedral mesh convergence study. """
from __future__ import annotations
import dataclasses
import math
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any
import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
from matrixfree_fem import MatrixFreeElasticity
from reference_fem import ke_hex
from advanced import structural_struts, _profile_radius

CORNERS=np.asarray([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]], dtype=np.int32)
FACES=(
  ((0,3,2,1),(-1,0,0)), ((1,2,6,5),(1,0,0)),
  ((0,1,5,4),(0,-1,0)), ((3,7,6,2),(0,1,0)),
  ((0,4,7,3),(0,0,-1)), ((4,5,6,7),(0,0,1)),
)

class InvalidGeometry(ValueError):
    """Invalid geometry is never assigned a valid mechanical score."""

@dataclass(frozen=True)
class FEMConfig:
    pitch_mm: float=1.15
    young_MPa: float=1.0
    poisson: float=0.35
    min_feature_fraction: float=1.15
    max_cells: int=800_000
    max_memory_mb: int=3072
    matrixfree_threshold: int=18_000
    cg_maxiter: int=5000
    cg_rtol: float=5e-5
    cg_timeout_s: float=180.0
    def __post_init__(self):
        if not 0.12<=self.pitch_mm<=2.5: raise ValueError('pitch outside 0.12..2.5 mm')
        if not self.young_MPa>0 or not -0.99<self.poisson<0.48: raise ValueError('Invalid elastic constants')
        if not 0.5<=self.min_feature_fraction<=1.5: raise ValueError('Invalid voxel min feature')
        if not 50<=self.max_cells<=2_000_000: raise ValueError('Invalid cell limit')
        if not 128<=self.max_memory_mb<=65_536: raise ValueError('Invalid memory budget')
        if not 100<=self.cg_maxiter<=20_000 or not 1e-9<=self.cg_rtol<=0.005: raise ValueError('Invalid CG controls')
        if not 2<=self.cg_timeout_s<=3600:raise ValueError('Invalid CG timeout')

@dataclass
class SolidMesh:
    nodes: np.ndarray
    elements: np.ndarray
    surface_faces: np.ndarray
    bottom: np.ndarray
    top: np.ndarray
    voxels: int
    volume_mm3: float
    pitch_mm: float
    min_radius_mm: float
    inflated_features: int
    geometry_warning: str


def voxel_mesh(family: str, genome: dict, config: FEMConfig=FEMConfig(), *, build_surface: bool=True) -> SolidMesh:
    """Construct a connected hexahedral solid from curved struts, base and top plate.

    Rasterization uses actual beam centreline and radius. Sub-grid features are
    conservatively thickened in a clearly reported manner. This is a numerical
    resolution policy; results change with pitch and require mesh convergence.
    """
    if family not in ('crown','chiral','quadrant'):raise ValueError('unknown family')
    hybrid=genome.get('hybrid_id','none') not in ('none',None,'')
    if hybrid:
        from hybrid_geometry import mid_height,mid_radius
        mid_z=mid_height(genome)
        mid_r=mid_radius(genome)
        mid_t=float(genome.get('hybrid_plate_thickness',.65))
        if not .45<=mid_t<=1.:raise InvalidGeometry('Hybrid intermediate plate thickness outside allowed range')
    paths=structural_struts(family, genome)
    if not paths:raise InvalidGeometry('No structural paths')
    h=config.pitch_mm;H=float(genome['height']); pad=float(genome.get('pad_radius',3.2))+.4
    if h<.5 and config.max_cells<=4500:
        raise InvalidGeometry(f'Solid HEX8 at {h:g} mm requires a much larger element budget. Select space-frame beam FEM for fine flexures, or explicitly increase max_cells and use a high-memory solid solver.')
    if not 3<H<10 or not 1<pad<7:raise InvalidGeometry('Unphysical pad/height')
    rmin=min(float(_profile_radius(r,(i+.5)/(len(pts)-1),genome,tag))
             for pts,r,tag in paths for i in range(len(pts)-1))
    # Fixed envelope across a family. Grid coordinate is *cell lower corner*.
    half=max(10.3, float(genome['radius'])+2.3, pad+2.)
    x0=-math.ceil(half/h)*h; x1=-x0
    nx=int(round((x1-x0)/h)); nz=int(math.ceil((H+.7)/h))+1
    xx=x0+(np.arange(nx)+.5)*h
    zz=(np.arange(nz)+.5)*h
    X,Y=np.meshgrid(xx,xx,indexing='ij')
    xy=np.stack([X,Y],axis=-1)
    occupancy=np.zeros((nx,nx,nz),bool)
    cx=float(genome.get('pad_offset_x',0.));cy=float(genome.get('pad_offset_y',0.))
    inflated=0
    # Volumetric base: separate four feet for quadrant; shared disk otherwise.
    for k,z in enumerate(zz):
        if z <=.85:
            if family=='quadrant' and not hybrid:
                r=float(genome['radius'])*.77
                for sx in (-1,1):
                    for sy in (-1,1):
                        occupancy[:,:,k] |= (np.abs(X-sx*r)<=1.65)&(np.abs(Y-sy*r)<=1.65)
            else:
                occupancy[:,:,k] |= (X*X+Y*Y <=9.3**2)
        if hybrid and abs(z-mid_z)<=max(mid_t*.5, h*.55):
            occupancy[:,:,k] |= X*X+Y*Y<=mid_r**2
        if H-max(.65,h*.75) <= z <= H+max(.45,h*.45):
            occupancy[:,:,k] |= (X-cx)**2+(Y-cy)**2<=pad**2
    # Rasterize each curved segment only in a bounded local box, rather than
    # evaluating every segment over the entire XY plane and all Z slices.
    # This is essential for pitch <= 0.3125 mm.
    for pts,r,tag in paths:
        pts=np.asarray(pts,float)
        member_inflated=False
        for seg_idx,(a,b) in enumerate(zip(pts[:-1],pts[1:])):
            radius=float(_profile_radius(r,(seg_idx+.5)/(len(pts)-1),genome,tag))
            radius_resolved=max(radius,config.min_feature_fraction*h)
            if radius_resolved>radius+1e-8:member_inflated=True
            ab=b-a;length2=float(np.dot(ab,ab))
            if length2<1e-14:continue
            low=np.minimum(a,b)-radius_resolved-0.02*h
            high=np.maximum(a,b)+radius_resolved+0.02*h
            ix0=max(0,int(math.ceil((low[0]-x0)/h-.5)))
            iy0=max(0,int(math.ceil((low[1]-x0)/h-.5)))
            iz0=max(0,int(math.ceil(low[2]/h-.5)))
            ix1=min(nx,int(math.floor((high[0]-x0)/h-.5))+1)
            iy1=min(nx,int(math.floor((high[1]-x0)/h-.5))+1)
            iz1=min(nz,int(math.floor(high[2]/h-.5))+1)
            if ix0>=ix1 or iy0>=iy1 or iz0>=iz1:continue
            xv=xx[ix0:ix1,None,None]
            yv=xx[None,iy0:iy1,None]
            zv=zz[None,None,iz0:iz1]
            t=np.clip(((xv-a[0])*ab[0]+(yv-a[1])*ab[1]+(zv-a[2])*ab[2])/length2,0.0,1.0)
            d2=(xv-a[0]-t*ab[0])**2+(yv-a[1]-t*ab[1])**2+(zv-a[2]-t*ab[2])**2
            occupancy[ix0:ix1,iy0:iy1,iz0:iz1] |= d2<=radius_resolved**2
        if member_inflated:inflated+=1
    if not np.any(occupancy):raise InvalidGeometry('No occupied cells')
    # 6-neighbour connectivity is required for HEX8 face-connected solid.
    labels,ncomp=ndimage.label(occupancy,structure=ndimage.generate_binary_structure(3,1))
    if ncomp!=1:raise InvalidGeometry(f'{ncomp} disconnected solid components at pitch={h:g} mm')
    cells=np.argwhere(occupancy).astype(np.int32)
    # Budget is a conservative estimate for matrix-free vectors, FEM fields, and
    # temporary arrays; actual peak RSS depends on SciPy/Numba and OS allocator.
    estimated_mb=len(cells)*0.0045 + (nx*nx*nz)*1.0e-6
    if estimated_mb>config.max_memory_mb:
        raise InvalidGeometry(f'Estimated FEM working set {estimated_mb:.0f} MB exceeds {config.max_memory_mb} MB budget (pitch {h:g} mm); increase memory budget explicitly or use a coarser mesh')
    if len(cells)>config.max_cells:raise InvalidGeometry(f'{len(cells)} elements exceeds max_cells={config.max_cells}')
    coords,inv=np.unique((cells[:,None,:]+CORNERS[None,:,:]).reshape(-1,3),axis=0,return_inverse=True)
    elements=inv.reshape(-1,8).astype(np.int32)
    nodes=coords.astype(float)*h+np.array([x0,x0,0.])
    zmin=nodes[:,2].min();zmax=nodes[:,2].max()
    bottom=np.flatnonzero(np.isclose(nodes[:,2],zmin,atol=1e-5)).astype(np.int32)
    top=np.flatnonzero(np.isclose(nodes[:,2],zmax,atol=1e-5)).astype(np.int32)
    if len(bottom)<4 or len(top)<4:raise InvalidGeometry('Missing bottom support or top load patch')
    triangles=[]
    if build_surface:
        # FE boundary triangles can be expensive for fine meshes. The solid
        # FEM does not need them when running the automated Top-3 audit.
        for local_face, direction in FACES:
            dx,dy,dz=direction
            p=cells+np.array([dx,dy,dz])
            inside=(p[:,0]>=0)&(p[:,0]<nx)&(p[:,1]>=0)&(p[:,1]<nx)&(p[:,2]>=0)&(p[:,2]<nz)
            neighbour=np.zeros(len(cells),bool)
            idx=np.flatnonzero(inside)
            neighbour[idx]=occupancy[p[idx,0],p[idx,1],p[idx,2]]
            face_nodes=elements[~neighbour][:,local_face]
            for q in face_nodes:
                triangles.extend(((int(q[0]),int(q[1]),int(q[2])),(int(q[0]),int(q[2]),int(q[3]))))
    msg=(f'{inflated}/{len(paths)} flexures had radius below {config.min_feature_fraction*h:.2f} mm '
         'and were inflated by voxel resolution.' if inflated else 'All flexures meet sampling radius; voxel staircase still present.')
    return SolidMesh(nodes,elements,np.asarray(triangles,np.int32),bottom,top,
                     len(cells),len(cells)*h**3,h,rmin,inflated,msg)


def _B_at_center(h:float):
    B=np.zeros((6,24))
    for i,(x,y,z) in enumerate(CORNERS):
        gx=(2*int(x)-1)/(4*h);gy=(2*int(y)-1)/(4*h);gz=(2*int(z)-1)/(4*h)
        j=3*i
        B[0,j]=gx;B[1,j+1]=gy;B[2,j+2]=gz
        B[3,j]=gy;B[3,j+1]=gx
        B[4,j+1]=gz;B[4,j+2]=gy
        B[5,j]=gz;B[5,j+2]=gx
    return B

def _unique_preserve_order(seq):
    seen=set(); out=[]
    for x in seq:
        x=int(x)
        if x not in seen:
            seen.add(x); out.append(x)
    return np.asarray(out,dtype=np.int32)

def _contact_candidates(mesh: SolidMesh, top: np.ndarray, dest: np.ndarray, patch_radius_mm: float):
    xy=mesh.nodes[top,:2]
    rr=np.linalg.norm(xy-dest,axis=1)
    order=np.argsort(rr)
    tries=[]
    base=max(float(patch_radius_mm), 0.55*mesh.pitch_mm)
    for scale in (1.0, 1.35, 1.8, 2.4, 3.2):
        rad=base*scale
        sel=top[rr<=rad]
        if len(sel):
            tries.append((rad,_unique_preserve_order(sel)))
    # nearest-k fallback makes archived / coarse meshes usable instead of hard-failing
    for k in (4, 8, 12, 16):
        if len(order)>=k:
            tries.append((float(rr[order[min(k-1,len(order)-1)]]), _unique_preserve_order(top[order[:k]])))
    return tries

class HexElasticSolver:
    """Factorize global 3D stiffness once, reuse for independent load cases."""
    def __init__(self, mesh:SolidMesh, young_MPa:float=1., poisson:float=.35,
                 *, matrixfree_threshold: int=18_000, cg_maxiter: int=5000, cg_rtol:float=5e-5, cg_timeout_s:float=180., compute_device: str='cpu',
                 family:str|None=None, genome:dict|None=None, include_laminate:bool=True):
        t=time.monotonic();self.mesh=mesh
        n=len(mesh.nodes); self.edof=(3*mesh.elements[:,:,None]+np.arange(3)[None,None,:]).reshape(-1,24)
        klocal=ke_hex(young_MPa,poisson,mesh.pitch_mm)
        self.laminate=None
        if include_laminate and family is not None and genome is not None:
            from laminate_fem import embed_laminate
            try:self.laminate=embed_laminate(mesh,family,genome)
            except (ValueError,IndexError) as exc:raise InvalidGeometry(f'PVDF/adhesive laminate invalid: {exc}') from exc
        extra=self.laminate.stiffness if self.laminate is not None else None
        self.fixed=(3*mesh.bottom[:,None]+np.arange(3)[None,:]).reshape(-1)
        self.free=np.setdiff1d(np.arange(3*n),self.fixed)
        if compute_device not in ('cpu','gpu','auto'):
            raise ValueError('compute_device must be cpu, gpu or auto')
        # AUTO remains CPU until an explicit, successful hardware benchmark validates GPU speedup.
        # Pascal P1000 FP64 sparse solves are often slower than dual-Xeon CPU calculations.
        self.compute_device='cpu' if compute_device=='auto' else compute_device
        if self.compute_device=='gpu' and len(mesh.elements)>min(matrixfree_threshold,6_000):
            raise InvalidGeometry('GPU CUDA CSR path is limited to <= 6000 HEX8 elements; high-resolution HEX8 requires CPU matrix-free. Reduce mesh size or use --compute-device cpu.')
        self.solver_mode=('gpu_sparse_cg' if self.compute_device=='gpu' else
                          ('direct_sparse' if len(mesh.elements)<=matrixfree_threshold else 'matrix_free_cg'))
        self.factor=None;self.matrixfree=None;self.K=None;self.gpu=None
        self._factor_lock=threading.Lock()
        if self.solver_mode in ('direct_sparse','gpu_sparse_cg'):
            rr=np.broadcast_to(self.edof[:,:,None],(len(self.edof),24,24)).ravel()
            cc=np.broadcast_to(self.edof[:,None,:],(len(self.edof),24,24)).ravel()
            vals=np.tile(klocal.flatten(),len(self.edof))
            self.K=coo_matrix((vals,(rr,cc)),shape=(3*n,3*n)).tocsr()
            if extra is not None:self.K=(self.K+extra).tocsr()
            if self.solver_mode=='gpu_sparse_cg':
                from gpu_sparse_fem import GPUSparseCG, GPUUnavailable
                try:
                    self.gpu=GPUSparseCG(self.K[self.free,:][:,self.free],
                        rtol=min(cg_rtol,5e-6),maxiter=cg_maxiter,timeout_s=cg_timeout_s,
                        budget_mb=1024)
                except GPUUnavailable as exc:
                    raise InvalidGeometry(str(exc)) from exc
            else:
                try:self.factor=splu(self.K[self.free,:][:,self.free].tocsc())
                except RuntimeError as exc:raise InvalidGeometry('Singular FEM stiffness / disconnected support') from exc
        else:
            try:
                self.matrixfree=MatrixFreeElasticity(self.edof,klocal,self.free,3*n,
                       maxiter=cg_maxiter,rtol=cg_rtol,timeout_s=cg_timeout_s,extra_stiffness=extra)
            except RuntimeError as exc:raise InvalidGeometry(str(exc)) from exc
        lmb=young_MPa*poisson/((1+poisson)*(1-2*poisson))
        mu=young_MPa/(2*(1+poisson))
        D=np.zeros((6,6));D[:3,:3]=lmb;np.fill_diagonal(D[:3,:3],lmb+2*mu);D[3:,3:]=np.eye(3)*mu
        self.B=_B_at_center(mesh.pitch_mm);self.D=D
        self.setup_s=time.monotonic()-t

    def _multiply(self,x):
        return self.K@x if self.K is not None else self.matrixfree.multiply(x)

    def solve(self,force=(0,0,-.1),offset=(0.,0.),patch_radius_mm=3.1,torque_z_Nmm=0.):
        mesh=self.mesh;top=mesh.top
        xy=mesh.nodes[top,:2]
        # Contact offset is relative to top-pad centre, not global bounding box.
        padcentre=xy.mean(axis=0)
        dest=padcentre+np.asarray(offset,float)
        attempts=_contact_candidates(mesh, top, dest, patch_radius_mm)
        selected=None; used_radius=None; selection_mode='requested'
        for idx,(rad,candidate) in enumerate(attempts):
            if len(candidate)>=4:
                selected=candidate; used_radius=float(rad)
                selection_mode='requested' if idx==0 else ('expanded' if idx<5 else 'nearest_nodes')
                break
        if selected is None or len(selected)<4:
            nearest=len(attempts[-1][1]) if attempts else 0
            raise InvalidGeometry(f'Contact patch only has {nearest} nodes after adaptive expansion; refine or enlarge the patch')
        load=np.asarray(force,float)
        if not np.all(np.isfinite(load)) or not np.all(np.isfinite(offset)):raise ValueError('Non-finite load')
        f=np.zeros(3*len(mesh.nodes))
        for dim in range(3):f[3*selected+dim]+=load[dim]/len(selected)
        if torque_z_Nmm:
            lv=mesh.nodes[selected,:2]-mesh.nodes[selected,:2].mean(axis=0)
            m2=float(np.square(lv).sum())
            if m2<1e-10:raise InvalidGeometry('Patch has no torsion lever arm')
            f[3*selected]+= -torque_z_Nmm*lv[:,1]/m2
            f[3*selected+1]+=torque_z_Nmm*lv[:,0]/m2
        t=time.monotonic();u=np.zeros_like(f)
        try:
            if self.gpu is not None:
                u[self.free]=self.gpu.solve(f[self.free])
            elif self.factor is not None:
                # SuperLU factor is shared, but its solve is not assumed reentrant.
                with self._factor_lock:
                    u[self.free]=self.factor.solve(f[self.free])
            else:
                u[self.free]=self.matrixfree.solve(f)[self.free]
        except RuntimeError as exc:
            raise InvalidGeometry(str(exc)) from exc
        r=self._multiply(u)-f
        U=u.reshape(-1,3);R=r.reshape(-1,3)
        epsilon=np.einsum('ab,cb->ca',self.B,u[self.edof],optimize=True)
        sigma=epsilon@self.D.T
        von=np.sqrt(.5*((sigma[:,0]-sigma[:,1])**2+(sigma[:,1]-sigma[:,2])**2+(sigma[:,2]-sigma[:,0])**2)+3*(sigma[:,3]**2+sigma[:,4]**2+sigma[:,5]**2))
        st=np.zeros((len(epsilon),3,3));st[:,0,0]=epsilon[:,0];st[:,1,1]=epsilon[:,1];st[:,2,2]=epsilon[:,2];st[:,0,1]=st[:,1,0]=epsilon[:,3]*.5;st[:,1,2]=st[:,2,1]=epsilon[:,4]*.5;st[:,0,2]=st[:,2,0]=epsilon[:,5]*.5
        principal=np.linalg.eigvalsh(st)[:,-1]
        residual=float(np.linalg.norm(r[self.free])/max(np.linalg.norm(f),1e-12))
        reactions=R[mesh.bottom].sum(axis=0)
        force_balance=float(np.linalg.norm(reactions+load)/max(np.linalg.norm(load),abs(torque_z_Nmm)/max(patch_radius_mm,1.),1e-12))
        if residual>max(1e-5,5*(self.matrixfree.rtol if self.matrixfree else 0.0)) or force_balance>1e-4:raise InvalidGeometry(f'Failed force equilibrium residual={residual:.3g}, force_balance={force_balance:.3g}')
        # Reaction moments from real support reactions and applied nodal load.
        origin=np.array([0.,0.,0.]); mr=np.cross(mesh.nodes[mesh.bottom]-origin,R[mesh.bottom]).sum(axis=0)
        mf=np.cross(mesh.nodes-origin,f.reshape(-1,3)).sum(axis=0)
        # A centred vertical load has zero theoretical moment. Dividing roundoff
        # (~1e-14 Nmm) by the old 1e-10 Nmm floor fabricated a 1e-4 "relative"
        # imbalance and falsely rejected refined meshes. Normalize by the
        # actual characteristic force × length of the loaded structure instead.
        characteristic_length_mm=max(float(np.ptp(mesh.nodes,axis=0).max()),mesh.pitch_mm)
        reference_moment_Nmm=max(float(np.linalg.norm(mf)),abs(torque_z_Nmm),
                                  float(np.linalg.norm(load))*characteristic_length_mm,1e-10)
        moment_error=float(np.linalg.norm(mr+mf)/reference_moment_Nmm)
        energy=float(.5*u@self._multiply(u))
        laminate_energy=(self.laminate.energy_Nmm(u) if self.laminate else 0.)
        laminate_response=(self.laminate.response(u) if self.laminate else None)
        # Effective capacitance proxy uses displacement of actual FE top nodes;
        # it is NOT a coupled electrostatic solve.
        top_down=-float(U[selected,2].mean())
        return dict(load_force_N=load.tolist(),offset_mm=list(map(float,offset)),torque_z_Nmm=float(torque_z_Nmm),
            displacement=U,element_strain=epsilon,element_stress=sigma,von_mises_MPa=von,
            principal_strain=principal,loaded_nodes=int(len(selected)),contact_patch_radius_used_mm=float(used_radius),contact_patch_mode=selection_mode,
            mean_contact_displacement_mm=U[selected].mean(axis=0).tolist(),
            mean_down_mm=top_down,max_displacement_mm=float(np.linalg.norm(U,axis=1).max()),
            max_principal_strain=float(principal.max()),max_abs_principal_strain=float(np.max(np.abs(np.linalg.eigvalsh(st)))),
            max_von_mises_MPa=float(von.max()),energy_Nmm=energy,
            force_reaction_N=reactions.tolist(),moment_reaction_Nmm=mr.tolist(),
            pvdf_stiffness_included=bool(self.laminate is not None),
            pvdf_adhesive_model='embedded_membrane_shear_lag' if self.laminate else 'none',
            laminate_energy_Nmm=float(laminate_energy),
            substrate_energy_Nmm=float(energy-laminate_energy),
            pvdf_laminate_response=laminate_response,
            force_equilibrium_relative=force_balance,moment_equilibrium_relative=moment_error,
            free_residual_relative=residual,solver_mode=self.solver_mode,
            cg_iterations=(self.matrixfree.last_iterations if self.matrixfree else (self.gpu.iterations if self.gpu else 0)),compute_device=self.compute_device,solve_s=time.monotonic()-t)


def fem_sweep(family,g,pitch_mm=1.25,include_fields=False,backend='auto',
              inspector_case='press_center',inspector_force_N=.1,inspector_offset=(0.,0.),compute_device='cpu',case_workers=1):
    """Real FEM: small-pitch space-frame or coarser HEX8 solid with explicit backend labels."""
    if type(case_workers) is not int or not 1<=case_workers<=8:
        raise ValueError('case_workers must be an integer in 1..8')
    if backend not in ('auto','beam','hex8'):
        raise ValueError('backend must be auto, beam or hex8')
    if g.get('hybrid_id','none') not in ('none',None,'') and backend=='beam':
        raise InvalidGeometry('Two-stage hybrid requires a connected solid HEX8 mesh; the legacy beam FEM cannot represent the rigid middle plate')
    if backend=='beam' or (backend=='auto' and pitch_mm<.7 and g.get('hybrid_id','none') in ('none',None,'')):
        from beam_fem import beam_sweep
        return beam_sweep(family,g,pitch_mm=pitch_mm,include_fields=include_fields,inspector_case=inspector_case,
                          inspector_force_N=inspector_force_N,inspector_offset=inspector_offset)

    """Identical FEM load protocol for all shortlisted candidates.

    Return physical measurements, explicit validity flags, and optional FE fields.
    No global physics claims if the model is nonconvergent or too highly strained.
    """
    config=FEMConfig(pitch_mm=pitch_mm,young_MPa=float(g.get('material_E',1.0)))
    mesh=voxel_mesh(family,g,config,build_surface=include_fields)
    fem=HexElasticSolver(mesh,config.young_MPa,config.poisson,
            family=family,genome=g,
            matrixfree_threshold=config.matrixfree_threshold,cg_maxiter=config.cg_maxiter,cg_rtol=config.cg_rtol,cg_timeout_s=config.cg_timeout_s,compute_device=compute_device)
    cases={
       'press_center':dict(force=(0.,0.,-.1)),
       'press_x_minus':dict(force=(0.,0.,-.1),offset=(-1.4,0.)),
       'press_x_plus':dict(force=(0.,0.,-.1),offset=(1.4,0.)),
       'press_y_minus':dict(force=(0.,0.,-.1),offset=(0.,-1.4)),
       'press_y_plus':dict(force=(0.,0.,-.1),offset=(0.,1.4)),
       'shear_x':dict(force=(.03,0.,-.04)),
       'shear_y':dict(force=(0.,.03,-.04)),
       'torsion_z':dict(force=(0.,0.,-.04),torque_z_Nmm=.02)
    }
    # Shared read-only mesh and stiffness; do not clone large FEM objects.
    # GPU and unaccelerated Python matvec remain serial. Direct sparse solves
    # serialize only the SuperLU call; their field recovery can overlap.
    used_workers=case_workers if fem.gpu is None and (fem.matrixfree is None or fem.matrixfree.accelerated) else 1
    if used_workers>1:
        if fem.matrixfree is not None:fem.matrixfree.warmup()
        with ThreadPoolExecutor(max_workers=used_workers) as executor:
            solved=list(executor.map(lambda params:fem.solve(**params),cases.values()))
        results=dict(zip(cases,solved))
    else:
        results={name:fem.solve(**params) for name,params in cases.items()}
    baseline=results['press_center']
    hybrid_stages=None
    if g.get('hybrid_id','none') not in ('none',None,''):
        from hybrid_geometry import mid_height
        z_mid=mid_height(g)
        z=mesh.nodes[:,2]
        lower_idx=np.flatnonzero((z>=z_mid-max(.7,pitch_mm*1.2)) & (z<z_mid-max(.15,pitch_mm*.18)))
        upper_idx=np.flatnonzero((z>z_mid+max(.15,pitch_mm*.18)) & (z<=z_mid+max(.7,pitch_mm*1.2)))
        mid_idx=np.flatnonzero(np.abs(z-z_mid)<=max(.2,pitch_mm*.55))
        if not len(mid_idx) or not len(upper_idx) or not len(lower_idx):
            raise InvalidGeometry('Hybrid intermediate-plate displacement cannot be resolved; refine mesh')
        stage_by_case={}
        for label,res in results.items():
            u=res['displacement']
            # For a rigid middle plate, mean in-plane shift is a meaningful
            # mechanical observable, not a reconstructed force measurement.
            umid=np.mean(u[mid_idx],axis=0)
            utop=np.mean(u[mesh.top],axis=0)
            stage_by_case[label]={'lower_displacement_xyz_mm':umid.tolist(),
                                  'upper_displacement_xyz_mm':(utop-umid).tolist(),
                                  'total_displacement_xyz_mm':utop.tolist()}
        b=stage_by_case['press_center']
        uz_mid=float(b['lower_displacement_xyz_mm'][2])
        uz_upper=float(b['upper_displacement_xyz_mm'][2])
        uz_top=float(b['total_displacement_xyz_mm'][2])
        lower_frac=float(abs(uz_mid)/max(abs(uz_top),1e-9))
        upper_frac=float(abs(uz_upper)/max(abs(uz_top),1e-9))
        # The three force-direction cases excite two distinct stage outputs;
        # this is a mechanical response basis, NOT calibrated force inference.
        signatures=[]
        for name in ('press_center','shear_x','shear_y'):
            row=stage_by_case[name]
            signatures.append(row['upper_displacement_xyz_mm']+row['lower_displacement_xyz_mm'])
        signature=np.asarray(signatures,float)
        scales=np.maximum(np.linalg.norm(signature,axis=0),1e-8)
        normalized=signature/scales[None,:]
        sv=np.linalg.svd(normalized,compute_uv=False)
        rank=int(np.linalg.matrix_rank(normalized,tol=max(float(sv[0]),1.e-10)*1e-4))
        condition=float(sv[0]/max(float(sv[-1]),1e-12))
        hybrid_stages={
          'architecture':g['hybrid_id'],'interface_z_mm':float(z_mid),
          'lower_compression_mm':float(-uz_mid),
          'upper_compression_mm':float(-uz_upper),
          'total_compression_mm':float(-uz_top),
          'lower_compression_share':lower_frac,
          'upper_compression_share':upper_frac,
          'continuity_error_mm':float(abs(-uz_top + uz_mid + uz_upper)),
          'stage_response_rank_max3':rank,
          'stage_response_condition':condition,
          'stage_response_singular_values':sv.tolist(),
          'stage_displacements_by_load':stage_by_case,
          'midplane_sample_nodes':int(len(mid_idx)),
          'upper_sample_nodes':int(len(upper_idx)),
          'lower_sample_nodes':int(len(lower_idx)),
          'readout_channels':{'upper_dynamic':'PVDF (selected upper members)','lower_dynamic':'PVDF (selected lower members)',
                              'static':'two independently modeled capacitive electrodes (assumed)'},
          'source':'Connected HEX8 stage displacement samples and normalized 3-axis mechanical transfer; no sensor calibration'}
    inspection=None
    if include_fields:
        if inspector_case not in ('press_center','press_offset','shear_x','shear_y','torsion_z'):
            raise ValueError('Unsupported FEM inspection case')
        force_n=float(inspector_force_N)
        if not np.isfinite(force_n) or not 0.<force_n<=.5:raise ValueError('Invalid inspection force')
        offset_xy=tuple(map(float,inspector_offset))
        if len(offset_xy)!=2 or not np.isfinite(offset_xy).all():raise ValueError('Invalid inspection offset')
        # The standardized 8-case audit remains identical for everyone.
        # The user-controlled extra case reuses the same FEM factorization.
        custom={
          'press_center':dict(force=(0.,0.,-force_n)),
          'press_offset':dict(force=(0.,0.,-force_n),offset=offset_xy),
          'shear_x':dict(force=(force_n*.3,0.,-force_n*.4)),
          'shear_y':dict(force=(0.,force_n*.3,-force_n*.4)),
          'torsion_z':dict(force=(0.,0.,-force_n*.4),torque_z_Nmm=.02*(force_n/.1))
        }[inspector_case]
        inspection=(results['press_center'] if inspector_case=='press_center' and abs(force_n-.1)<1e-12 else fem.solve(**custom))
    shell_result=None
    shell_inspection_result=None
    if fem.laminate:
        from laminate_shell import resolve_laminate_shell
        try:
            # Champion scores MUST use the standardized 0.1N centered case;
            # user-selected inspection loads are visual only, not a back door
            # for changing the Top-3 full-audit result.
            shell_result=resolve_laminate_shell(mesh,family,g,baseline['displacement'])
            if inspection is not None:
                shell_inspection_result=(shell_result if inspection is baseline else
                    resolve_laminate_shell(mesh,family,g,inspection['displacement']))
        except (ValueError, RuntimeError) as exc:
            shell_result={'failed':True,'message':str(exc),'model':'reduced_ribbon_shell_postprocess'}
            shell_inspection_result=shell_result
    extrema=max(v['max_abs_principal_strain'] for v in results.values())
    central=baseline['mean_down_mm']
    # A credible press must push down, produce FEM energy, and have balanced reactions.
    pressure_valid=bool(central>1e-6 and baseline['energy_Nmm']>0 and all(results[k]['mean_down_mm']>1e-7 for k in list(cases)[:5]))
    # Synthetic electronic response proxy from actual FE deflection, not false claim of measured capacitance.
    epsilon0=8.8541878128e-3 # pF/mm
    # Keep the *assumed* FEM-based capacitance proxy consistent with the
    # evolutionary genotype. It still maps top displacement to an idealized
    # electrode gap, NOT actual resolved dielectric contact pressure.
    area_mm2=float(g.get('electrode_area_mm2',7.))
    gap_mm=float(g.get('dielectric_gap_mm',.45))
    eps_rel=float(g.get('dielectric_epsilon_r',2.8))
    c0=epsilon0*eps_rel*area_mm2/gap_mm
    signals={}
    for name,v in results.items():
        dz=np.clip(v['mean_down_mm'], -gap_mm*.7,gap_mm*.8)
        signals[name]=float(c0*(gap_mm/(gap_mm-dz)-1))
    spread=max(results[k]['mean_down_mm'] for k in list(cases)[:5])-min(results[k]['mean_down_mm'] for k in list(cases)[:5])
    rms=math.sqrt(float(np.mean([results[k]['mean_down_mm']**2 for k in list(cases)[:5]])))
    # Score is explicit engineering heuristic derived from FEM values, not prediction accuracy.
    sensitivity=float(np.clip(math.log1p(abs(signals['press_center'])/.0003)/math.log1p(200.),0.,1.))
    pressure_uniformity=float(math.exp(-max(0.,spread)/max(abs(central),.002)))
    strain_guard=float(math.exp(-max(0,extrema-.07)*14))
    volume_guard=float(math.exp(-max(0.,mesh.volume_mm3-480)/450))
    score=100*(.35*sensitivity+.3*pressure_uniformity+.2*strain_guard+.15*volume_guard)
    if fem.laminate:
        # Discourage high film strain/delamination risk: this is a conservative
        # design screen, not a measured PVDF fatigue limit.
        peak_film=max(x['max_abs_effective_strain']
                      for r in results.values() for x in r['pvdf_laminate_response']['per_film'])
        film_guard=math.exp(-max(0.,peak_film-.01)*25.)
        score*=film_guard
    else:peak_film=0.;film_guard=1.
    if hybrid_stages is not None:
        # Evaluate second-stage participation and normalized mechanical
        # excitation diversity without rewarding merely large absolute u.
        share=hybrid_stages['lower_compression_share']
        balance=float(math.exp(-(math.log(max(share,1e-5)/.20)/1.4)**2))
        rank_factor=hybrid_stages['stage_response_rank_max3']/3.
        condition_factor=1./(1.+max(0.,math.log10(max(1.,hybrid_stages['stage_response_condition']))-1.))
        modal=float(.65*rank_factor+.35*condition_factor)
        hybrid_stages['balance_score_0_100']=round(100.*balance,4)
        hybrid_stages['mode_separation_score_0_100']=round(100.*modal,4)
        score=.80*score+.12*(100.*balance)+.08*(100.*modal)
    valid=bool(pressure_valid and extrema<.12 and mesh.voxels>80 and mesh.inflated_features==0 and max(v['force_equilibrium_relative'] for v in results.values())<1e-4 and max(v['moment_equilibrium_relative'] for v in results.values())<1e-4)
    score=round(float(score),4)
    report={'fem_backend':'actual_hex8_linear_3d','fem_linear_solver':fem.solver_mode,'mesh_pitch_mm':pitch_mm,'elements':mesh.voxels,'nodes':len(mesh.nodes),'volume_mm3':round(mesh.volume_mm3,2),
            'inflated_features':mesh.inflated_features,'geometry_fidelity_pass':mesh.inflated_features==0,'mesh_warning':mesh.geometry_warning,'elastic_E_MPa':config.young_MPa,
            'poisson':config.poisson,'setup_time_s':round(fem.setup_s,4),'load_case_workers':used_workers,
            'load_cases':{k:{kk:(round(float(vv),7) if isinstance(vv,(float,np.floating)) else vv) for kk,vv in value.items() if kk not in ('displacement','element_strain','element_stress','von_mises_MPa','principal_strain')} for k,value in results.items()},
            'capacitance_delta_pF_assumed':signals,
            'fem_capacitor_assumption':{'electrode_area_mm2':area_mm2,'dielectric_gap_mm':gap_mm,
                  'dielectric_eps_r_assumed':eps_rel,
                  'note':'Top-pad FEM displacement is NOT resolved capacitor-dielectric compression; synthetic gap transfer only.'},
            'max_abs_principal_strain':extrema,
            'pressure_uniformity':pressure_uniformity,'pressure_valid':pressure_valid,
            'force_equilibrium_max':max(v['force_equilibrium_relative'] for v in results.values()),
            'moment_equilibrium_max':max(v['moment_equilibrium_relative'] for v in results.values()),
            'fem_score':score,'feasible_linear':valid,'pvdf_stiffness_included':bool(fem.laminate),
            'hybrid_stages':hybrid_stages,
            'pvdf_adhesive_model':'embedded_membrane_shear_lag' if fem.laminate else 'none',
            'pvdf_film_count':(fem.laminate.film_count if fem.laminate else 0),
            'pvdf_total_laminate_energy_Nmm':baseline.get('laminate_energy_Nmm',0.),
            'pvdf_max_abs_effective_strain':peak_film,'pvdf_film_strain_guard':film_guard,
            'pvdf_fraction_of_total_energy':float(baseline.get('laminate_energy_Nmm',0.)/max(baseline['energy_Nmm'],1.e-14)),
            'pvdf_mean_dynamic_charge_pC_assumed':float(sum(x['estimated_charge_pC'] for x in baseline['pvdf_laminate_response']['per_film']) if fem.laminate else 0.),
            'pvdf_mass_g_estimate':float(baseline['pvdf_laminate_response']['film_mass_g']) if fem.laminate else 0.,
            'adhesive_mass_g_estimate':float(baseline['pvdf_laminate_response']['adhesive_mass_g']) if fem.laminate else 0.,
            'laminate_shell':shell_result,
            'laminate_shell_inspection':shell_inspection_result if include_fields else None,
            'notes':['Real 3-D linear HEX8 displacement/strain/stress solve on voxelized struts',
                     'Voxel-inflated thin members; verify pitch convergence',
                     'Larger strains require hyperelasticity and contact',
                     'Electrical capacitance is a separate parallel-plate estimate using FEM displacement, not coupled field FEM',
                     'PVDF is mechanically embedded in the primary solve as an effective axial membrane with approximate adhesive shear-lag. A final reduced ribbon-shell post-process is also reported, but it is still not a fully coupled film+bond shell/solid multiphysics solve.']}
    if include_fields:
        report['fields']=_serialize_mesh_fields(mesh,inspection)
        report['inspection_case']=inspector_case
        report['inspection_metrics']={k:v for k,v in inspection.items() if k not in ('displacement','element_strain','element_stress','von_mises_MPa','principal_strain')}
    return report


def _serialize_mesh_fields(mesh:SolidMesh,result:dict):
    cell_sigma=np.asarray(result['von_mises_MPa'])
    cell_strain=np.asarray(result['principal_strain'])
    # Surface per-vertex averages of element fields, keeping fixed 1:1 FE node IDs.
    node_vm=np.zeros(len(mesh.nodes));node_strain=np.zeros(len(mesh.nodes));counts=np.zeros(len(mesh.nodes))
    for j in range(8):
        np.add.at(node_vm,mesh.elements[:,j],cell_sigma)
        np.add.at(node_strain,mesh.elements[:,j],cell_strain)
        np.add.at(counts,mesh.elements[:,j],1)
    node_vm/=np.maximum(counts,1);node_strain/=np.maximum(counts,1)
    # Large FE surface meshes can overwhelm browsers, even if the solver succeeds.
    # Preserve full nodal fields in VTK/NPZ exports; limit visualization payload.
    full_triangles=len(mesh.surface_faces)
    max_triangles=85_000
    surface=mesh.surface_faces
    if full_triangles>max_triangles:
        step=int(math.ceil(full_triangles/max_triangles))
        surface=surface[::step]
    used,inv=np.unique(surface.reshape(-1),return_inverse=True)
    return {'vertices_mm':np.round(mesh.nodes[used],5).tolist(),
            'faces':inv.reshape(-1,3).tolist(),
            'displacement_mm':np.round(np.asarray(result['displacement'])[used],7).tolist(),
            'stress_vm_MPa':np.round(node_vm[used],6).tolist(),
            'principal_strain':np.round(node_strain[used],7).tolist(),
            'source_surface_triangles':full_triangles,
            'display_surface_triangles':len(surface),
            'display_downsampled':bool(len(surface)<full_triangles),
            'note':'True nodal FE displacements; high-resolution surfaces may be sampled for browser preview. Full solid fields available in VTK/NPZ.'}
