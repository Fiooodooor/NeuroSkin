"""Small-scale total-Lagrangian TET4 compressible Neo-Hookean solver.

Coordinates: mm. Modulus: MPa = N/mm². Force: N. Energy: N mm.
F = I + grad_X(u), J = det(F) > 0.
W = μ/2 [tr(FᵀF)-3-2 ln J] + λ/2 [ln J]².
P = μ(F-F⁻ᵀ) + λ ln(J) F⁻ᵀ.
C_iJkL = μ δik δJL + λ F⁻ᵀ_iJ F⁻ᵀ_kL
         + (μ-λ ln(J)) F⁻ᵀ_iL F⁻ᵀ_kJ.

Frictionless rigid horizontal plane via quadratic *penalty*; this is not
exact complementarity and needs penetration vs penalty convergence. No
viscoelasticity, self-contact, damage, mixed incompressibility or electromechanics.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve, MatrixRankWarning
import warnings
from .mesh import TetMesh

class NonlinearFEMError(RuntimeError):
    pass

class InvertedElement(NonlinearFEMError):
    pass

@dataclass(frozen=True)
class NeoHookean:
    young_MPa: float
    poisson: float

    def __post_init__(self):
        if not math.isfinite(self.young_MPa) or self.young_MPa<=0:
            raise ValueError('Young modulus must be positive finite MPa')
        if not math.isfinite(self.poisson) or not (0 <= self.poisson <= .45):
            raise ValueError('Poisson ratio must be in [0,0.45]; auxetic constitutive law and near-incompressible TET4 are unsupported')

    @property
    def mu(self): return self.young_MPa/(2*(1+self.poisson))

    @property
    def lam(self): return self.young_MPa*self.poisson/((1+self.poisson)*(1-2*self.poisson))

    def energy_stress_tangent(self,F:np.ndarray):
        J=float(np.linalg.det(F))
        if J<=1e-8 or not np.isfinite(J):
            raise InvertedElement(f'Nonpositive/degenerated deformation Jacobian: {J}')
        invT=np.linalg.inv(F).T
        logJ=math.log(J)
        mu,lam=self.mu,self.lam
        W=mu*.5*(float(np.sum(F*F))-3-2*logJ)+lam*.5*logJ**2
        P=mu*(F-invT)+lam*logJ*invT
        I=np.eye(3)
        C=(mu*np.einsum('ik,JL->iJkL',I,I)
           +lam*np.einsum('iJ,kL->iJkL',invT,invT)
           +(mu-lam*logJ)*np.einsum('iL,kJ->iJkL',invT,invT))
        return W,P,C,J


@dataclass
class Solution:
    displacement_mm: np.ndarray
    iterations: int
    converged: bool
    energy_Nmm: float
    min_deformation_J: float
    reaction_N: np.ndarray
    contact_force_N: float
    max_penetration_mm: float
    residual_force_N: float
    line_search_reductions: int

    def summary(self):
        return {'converged':bool(self.converged),'iterations':int(self.iterations),
                'energy_Nmm':float(self.energy_Nmm),
                'min_deformation_J':float(self.min_deformation_J),
                'contact_force_N':float(self.contact_force_N),
                'max_penetration_mm':float(self.max_penetration_mm),
                'residual_force_N':float(self.residual_force_N),
                'line_search_reductions':int(self.line_search_reductions),
                'displacement_max_mm':float(np.linalg.norm(self.displacement_mm,axis=1).max()),
                'reactions_sum_N':np.sum(self.reaction_N,axis=0).tolist()}


def horizontal_surface_weights(mesh:TetMesh, *, top:bool=True, atol:float=1e-9):
    """Lumped surface areas for a planar external top/bottom face (mm²)."""
    t=mesh.tets
    faces=np.concatenate([t[:,[0,1,2]],t[:,[0,1,3]],t[:,[0,2,3]],t[:,[1,2,3]]])
    canonical=np.sort(faces,axis=1)
    _, inv,counts=np.unique(canonical,axis=0,return_inverse=True,return_counts=True)
    boundary=faces[counts[inv]==1]
    h=(mesh.nodes[:,2].max() if top else mesh.nodes[:,2].min())
    aligned=np.all(np.abs(mesh.nodes[boundary,2]-h)<=atol,axis=1)
    planar=boundary[aligned]
    if len(planar)==0:raise ValueError('No planar boundary facets for selected contact surface')
    pts=mesh.nodes[planar]
    a=.5*np.linalg.norm(np.cross(pts[:,1]-pts[:,0],pts[:,2]-pts[:,0]),axis=1)
    weights=np.zeros(len(mesh.nodes))
    np.add.at(weights,planar.ravel(),np.repeat(a/3.,3))
    return weights


class TetNeoHookeanSolver:
    def __init__(self,mesh:TetMesh, material:NeoHookean):
        self.mesh,self.material=mesh,material
        x=mesh.nodes; t=mesh.tets
        self.grad=np.empty((len(t),4,3))
        self.volumes=np.empty(len(t))
        for e,ids in enumerate(t):
            dm=(x[ids[1:]]-x[ids[0]]).T
            inv=np.linalg.inv(dm)
            self.grad[e,1:]=inv
            self.grad[e,0]=-inv.sum(axis=0)
            self.volumes[e]=np.linalg.det(dm)/6.
        self.dofs=np.arange(3*len(x)).reshape(-1,3)[t].reshape(len(t),12)
        self.ndof=3*len(x)

    def _assemble(self,u,force,plane,weights,penalty,with_tangent):
        grad_total=np.zeros((len(self.mesh.nodes),3))
        rows=[];cols=[];vals=[]
        energy=0.; minJ=np.inf
        for k,ids in enumerate(self.mesh.tets):
            F=np.eye(3)+u[ids].T@self.grad[k]
            W,P,C,J=self.material.energy_stress_tangent(F)
            minJ=min(minJ,J)
            vol=self.volumes[k]
            energy+=vol*W
            grad_total[ids]+=vol*(self.grad[k]@P.T)
            if with_tangent:
                ke=vol*np.einsum('aJ,iJkL,bL->aibk',self.grad[k],C,self.grad[k],optimize=True)
                ke=ke.reshape(12,12)
                d=self.dofs[k]
                rows.append(np.repeat(d,12));cols.append(np.tile(d,12));vals.append(ke.ravel())
        contact_force=0.; max_pen=0.
        if plane is not None:
            gap=self.mesh.nodes[:,2]+u[:,2]-plane
            intrusion=np.maximum(gap,0.)
            reaction=penalty*weights*intrusion
            grad_total[:,2]+=reaction
            energy+=.5*float(np.dot(reaction,intrusion))
            contact_force=float(reaction.sum())
            max_pen=float(intrusion[weights>0].max())
            if with_tangent:
                active=np.flatnonzero(intrusion>0)
                d=3*active+2
                rows.append(d);cols.append(d);vals.append(penalty*weights[active])
        energy-=float(np.dot(u.reshape(-1),force.reshape(-1)))
        grad_total-=force
        mat=None
        if with_tangent:
            if rows:
                mat=coo_matrix((np.concatenate(vals),(np.concatenate(rows),np.concatenate(cols))),
                               shape=(self.ndof,self.ndof)).tocsr()
            else:mat=coo_matrix((self.ndof,self.ndof)).tocsr()
        return energy,grad_total.reshape(-1),mat,minJ,contact_force,max_pen

    def solve(self, *, forces_N=None, fixed_dofs=None, prescribed_mm=None,
              plane_z_mm=None, contact_weights_mm2=None,
              contact_penalty_N_per_mm3:float=100., initial_mm=None,
              tol_abs_N:float=1e-8, tol_rel:float=1e-7,max_iterations:int=45):
        """Nonlinear static equilibrium by damped Newton and backtracking.

        fixed_dofs specifies 0-based Cartesian DOF indices, not node indices.
        prescribed_mm maps DOF -> displacement in mm; zero constraints default.
        A contact plane exerts downward compression on nodes above it.
        """
        n=len(self.mesh.nodes)
        force=np.zeros((n,3)) if forces_N is None else np.asarray(forces_N,float)
        if force.shape!=(n,3) or not np.all(np.isfinite(force)):
            raise ValueError('forces_N must be finite [nodes,3] N')
        if prescribed_mm is None:prescribed_mm={}
        prescribed_mm={int(k):float(v) for k,v in prescribed_mm.items()}
        fix=np.unique(np.r_[np.asarray(fixed_dofs if fixed_dofs is not None else [],dtype=int),
                            np.asarray(list(prescribed_mm),dtype=int)])
        if np.any(fix<0) or np.any(fix>=self.ndof):raise ValueError('invalid fixed DOF')
        if not np.all(np.isfinite(list(prescribed_mm.values()))):raise ValueError('nonfinite prescribed values')
        if len(fix)==0:raise ValueError('fixed DOFs required to eliminate rigid modes')
        # Even at zero load a free rigid-body mode is not a valid solution.
        x=self.mesh.nodes-self.mesh.nodes.mean(axis=0)
        rigid=np.zeros((n,3,6));rigid[:,:,:3]=np.eye(3)
        for k in range(3):rigid[:,:,3+k]=np.cross(np.eye(3)[k],x)
        if np.linalg.matrix_rank(rigid.reshape(-1,6)[fix])<6:
            raise ValueError('constraints do not eliminate all six rigid modes')
        if not np.isfinite(tol_abs_N) or not np.isfinite(tol_rel) or tol_abs_N<=0 or tol_rel<=0:
            raise ValueError('positive finite convergence tolerances required')
        free=np.setdiff1d(np.arange(self.ndof),fix)
        if len(free)==0:raise ValueError('no free DOFs')
        if max_iterations<1:raise ValueError('max_iterations must be positive')
        if plane_z_mm is None:
            weights=np.zeros(n);penalty=0.
        else:
            if not np.isfinite(plane_z_mm) or not np.isfinite(contact_penalty_N_per_mm3) or contact_penalty_N_per_mm3<=0:
                raise ValueError('invalid plane or contact penalty')
            weights=(horizontal_surface_weights(self.mesh) if contact_weights_mm2 is None
                     else np.asarray(contact_weights_mm2,float))
            if weights.shape!=(n,) or not np.all(np.isfinite(weights)) or np.any(weights<0) or not np.any(weights>0):
                raise ValueError('contact weights must be nonnegative nodal mm²')
            penalty=contact_penalty_N_per_mm3
        u=np.zeros(self.ndof) if initial_mm is None else np.asarray(initial_mm,float).reshape(-1).copy()
        if len(u)!=self.ndof or not np.all(np.isfinite(u)):raise ValueError('invalid starting displacements')
        u[fix]=0.
        for d,v in prescribed_mm.items():u[d]=v
        total_reductions=0
        threshold=max(tol_abs_N,tol_rel*max(np.linalg.norm(force.reshape(-1)[free]),1e-12))
        for iteration in range(max_iterations+1):
            energy,r,K,J,cforce,penetration=self._assemble(u.reshape(-1,3),force,plane_z_mm,weights,penalty,True)
            norm=float(np.linalg.norm(r[free]))
            if norm<=threshold:
                return Solution(u.reshape(-1,3).copy(),iteration,True,float(energy),float(J),
                                r.reshape(-1,3).copy(),float(cforce),float(penetration),norm,total_reductions)
            if iteration>=max_iterations:break
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('error',MatrixRankWarning)
                    step=spsolve(K[free][:,free],-r[free])
            except Exception as exc:
                raise NonlinearFEMError(f'singular or invalid tangent matrix: {exc}') from exc
            if not np.all(np.isfinite(step)):
                raise NonlinearFEMError('nonfinite Newton increment')
            direction=float(r[free]@step)
            if direction>=0:
                raise NonlinearFEMError('non-descent Newton direction; unstable equilibrium')
            alpha=1.
            accepted=False
            for ls in range(28):
                trial=u.copy();trial[free]+=alpha*step
                try:
                    Et,*_=self._assemble(trial.reshape(-1,3),force,plane_z_mm,weights,penalty,False)
                    if Et <= energy + 1e-4*alpha*direction:
                        u=trial; accepted=True;total_reductions+=ls;break
                except InvertedElement:
                    pass
                alpha*=.5
            if not accepted:
                raise NonlinearFEMError('line search failed (inversion, unstable tangent or infeasible constraints)')
        raise NonlinearFEMError(f'Newton did not converge in {max_iterations} iterations; residual {norm:.6g} N')

    def contact_cycle(self,indents_mm, *,penalty_N_per_mm3=100., fixed_dofs=None):
        """Displacement-driven frictionless contact path; not viscoelastic recovery.

        Returns all stages with explicit penetration and equilibrium checks.
        """
        indents=list(map(float,indents_mm))
        if not indents or min(indents)<0 or not np.isfinite(indents).all():
            raise ValueError('indentations must be nonnegative finite mm')
        ztop=float(self.mesh.nodes[:,2].max())
        fix=(3*np.flatnonzero(np.isclose(self.mesh.nodes[:,2],self.mesh.nodes[:,2].min()))[:,None]
             +np.arange(3)[None,:]).ravel() if fixed_dofs is None else fixed_dofs
        old=None;data=[]
        for displacement in indents:
            result=self.solve(fixed_dofs=fix,initial_mm=old,
                              plane_z_mm=ztop-displacement,
                              contact_penalty_N_per_mm3=penalty_N_per_mm3)
            old=result.displacement_mm
            data.append({'indentation_mm':displacement,**result.summary()})
        return data
