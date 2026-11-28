"""Geometrically nonlinear transverse membrane + condensed 3D elastic substrate.

Units N, mm, MPa. Fixed in-plane reference displacement (no in-plane
relaxation); moderate-rotation von Karman membrane energy, prescribed tension.
Pad springs are bilateral. Substrate is linear isotropic TET4 with clamped
bottom, free side faces and finite pad footprints. Its exact discrete static
compliance couples all receptors. No unilateral contact or hardware evidence.
"""
import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.linalg import splu, spsolve
from membrane_tile import MembraneTile
from neuroskin_v30.mesh import box_mesh
from neuroskin_v30.nonlinear_fem import NeoHookean, TetNeoHookeanSolver


class Substrate3D:
    def __init__(self,n,pitch,thickness,young,poisson=.35):
        if n not in (3,5,8) or not np.isfinite([pitch,thickness,young,poisson]).all() or min(pitch,thickness,young)<=0:
            raise ValueError('Invalid substrate geometry/material')
        m=4*n+1;self.m=m;self.n=n;self.pitch=pitch;self.thickness=thickness
        self.mesh=box_mesh(m-1,m-1,2,(n*pitch,n*pitch,thickness))
        self.solver=TetNeoHookeanSolver(self.mesh,NeoHookean(young,poisson))
        x=self.mesh.nodes;zero=np.zeros_like(x)
        _,_,self.K,*_=self.solver._assemble(zero,zero,None,None,0,True)
        bottom=np.flatnonzero(x[:,2]==0)
        fixed=(3*bottom[:,None]+np.arange(3)).ravel()
        self.free=np.setdiff1d(np.arange(3*len(x)),fixed)
        self.top=np.flatnonzero(x[:,2]==thickness)
        # Exact mean of piecewise-linear top triangles over the h/2 pad.
        # box_mesh top quads split along local lower-left to upper-right.
        rr=[];cc=[];vv=[]
        for j in range(n):
            for i in range(n):
                for y in range(j*4+1,j*4+3):
                    for z in range(i*4+1,i*4+3):
                        a=y*m+z
                        rr.extend([j*n+i]*4)
                        cc.extend(3*self.top[[a,a+1,a+m+1,a+m]]+2)
                        vv.extend([1/12,1/24,1/12,1/24])
        self.B=coo_matrix((vv,(rr,cc)),shape=(n*n,3*len(x))).tocsr()
        self.factor=splu(self.K[self.free][:,self.free].tocsc())
        self.influence=self.factor.solve(self.B[:,self.free].T.toarray())
        S=np.asarray(self.B[:,self.free]@self.influence)
        if not np.allclose(S,S.T,atol=1e-10,rtol=1e-9):raise RuntimeError('Substrate reciprocity failed')
        self.S=(S+S.T)/2
        np.linalg.cholesky(self.S)

    def fields(self,r):
        # Positive displacement convention = compression; physical z is negative.
        u=np.zeros(self.K.shape[0]);u[self.free]=self.influence@r
        applied=np.asarray(self.B.T@r).ravel()
        residual=self.K@u-applied
        xyz=u.reshape(-1,3)
        grad=np.einsum('eai,eaJ->eiJ',xyz[self.mesh.tets],self.solver.grad)
        strain=(grad+grad.transpose(0,2,1))/2
        max_strain=float(np.abs(np.linalg.eigvalsh(strain)).max())
        return {'surface':{'axis_mm':(np.arange(self.m)*self.pitch/4-self.pitch/2).tolist(),
                    'displacement_mm':xyz[self.top,2].reshape(self.m,self.m).tolist(),
                    'reference_z_mm':-self.thickness},
                'pad_displacement_mm':(self.S@r).reshape(self.n,self.n).tolist(),
                'max_abs_principal_strain':max_strain,'small_strain_screen':bool(max_strain<=.03),
                'force_balance_error_N':abs(float(residual[2::3].sum()+r.sum())),
                'free_residual_N':float(np.linalg.norm(residual[self.free])),
                'energy_Nmm':float(r@self.S@r/2),'mesh':self.mesh.metrics()}


class NonlinearSkinTile:
    def __init__(self,kz,pitch,tension,young,thickness,poisson=.3,subdivisions=4,substrate=None):
        self.linear=MembraneTile(kz,pitch,tension,subdivisions)
        m=self.linear
        if not np.isfinite([young,thickness,poisson]).all() or young<0 or thickness<=0 or not 0<=poisson<.5:
            raise ValueError('Invalid membrane material')
        self.alpha=young*thickness/(2*(1-poisson**2))
        self.substrate=substrate
        S=np.zeros((len(m.k),len(m.k))) if substrate is None else substrate.S
        if S.shape!=(len(m.k),len(m.k)):raise ValueError('Substrate grid mismatch')
        self.H=np.linalg.solve(np.diag(1/m.k)+S,np.eye(len(m.k)))
        self.H=(self.H+self.H.T)/2
        self.K0=(m.Km+m.B.T@csr_matrix(self.H)@m.B).tocsc()
        self.factor=splu(self.K0)
        iy,ix=np.indices((m.m-1,m.m-1));a=(iy*m.m+ix).ravel()
        self.cells=np.column_stack([a,a+1,a+m.m+1,a+m.m])
        # 3x3 Gauss integrates the quartic energy exactly for bilinear Q1.
        points,weights=np.polynomial.legendre.leggauss(3);G=[];W=[]
        for i,x in enumerate(points):
            for j,y in enumerate(points):
                G.append(np.array([[-(1-y),-(1-x)],[(1-y),-(1+x)],[(1+y),(1+x)],[-(1+y),(1-x)]])/(2*m.step))
                W.append(weights[i]*weights[j]*m.step**2/4)
        self.G=np.array(G);self.W=np.array(W)
        self.rows=np.repeat(self.cells,4,axis=1).ravel();self.cols=np.tile(self.cells,(1,4)).ravel()

    def assemble(self,u,f,tangent=True):
        g=np.einsum('ea,qai->eqi',u[self.cells],self.G)
        norm2=np.sum(g*g,axis=2)
        quartic=float(self.alpha/4*np.sum(norm2**2*self.W))
        r=self.K0@u-f
        local=self.alpha*np.einsum('q,eq,eqi,qai->ea',self.W,norm2,g,self.G)
        np.add.at(r,self.cells.ravel(),local.ravel())
        K=None
        if tangent:
            C=self.alpha*(norm2[:,:,None,None]*np.eye(2)+2*g[:,:,:,None]*g[:,:,None,:])
            ke=np.einsum('q,qai,eqij,qbj->eab',self.W,self.G,C,self.G,optimize=True)
            K=(self.K0+coo_matrix((ke.ravel(),(self.rows,self.cols)),shape=self.K0.shape)).tocsc()
        return float(u@self.K0@u/2)+quartic-float(f@u),r,K,quartic

    def solve(self,contacts):
        m=self.linear;f=np.zeros(m.m*m)
        for x,y,F in contacts:f+=m.point_load(x,y,F)
        u=np.zeros_like(f);iterations=0
        # Fixed continuation, deterministic; fail rather than report unconverged.
        for fraction in (.25,.5,.75,1.):
            target=f*fraction
            for i in range(40):
                E,r,K,_=self.assemble(u,target)
                if np.linalg.norm(r)<=max(1e-9,np.linalg.norm(target)*1e-8):break
                step=spsolve(K,-r);direction=float(r@step)
                if not np.isfinite(step).all() or direction>=0:raise RuntimeError('Invalid membrane Newton direction')
                for j in range(25):
                    trial=u+step*(.5**j)
                    if self.assemble(trial,target,False)[0]<=E+1e-4*(.5**j)*direction:
                        u=trial;iterations+=1;break
                else:raise RuntimeError('Membrane line search failed')
            else:raise RuntimeError('Membrane Newton failed to converge')
        _,res,_,quartic=self.assemble(u,f,False)
        pad=m.B@u;reaction=self.H@pad
        Em=float(u@m.Km@u/2);Es=float(np.sum(reaction**2/m.k)/2)
        sub=None if self.substrate is None else self.substrate.fields(reaction)
        Eb=0. if sub is None else sub['energy_Nmm']
        # Nonlinear work identity (Euler homogeneous energies), not 1/2 f^T u.
        error=abs(float(f@u)-2*(Em+Es+Eb)-4*quartic)
        rhs=np.zeros((len(f),len(m.k)));rhs[m.center_ids,np.arange(len(m.k))]=1
        transfer=self.H@(m.B@self.factor.solve(rhs))
        w=u.reshape(m.m,m.m);gx=np.diff(w,axis=1)/m.step;gy=np.diff(w,axis=0)/m.step
        slope=float(max(np.hypot(a,b).max() for a in (gx[:-1],gx[1:]) for b in (gy[:,:-1],gy[:,1:])))
        return {'tier':'T0','reaction_N':reaction.reshape(m.n,m.n),'displacement_mm':pad.reshape(m.n,m.n),
                'receptor_compression_mm':(reaction/m.k).reshape(m.n,m.n).tolist(),
                'transfer':transfer,'force_balance_error_N':abs(float(reaction.sum()-f.sum())),
                'membrane_energy_Nmm':Em+quartic,'membrane_stretch_energy_Nmm':quartic,
                'spring_energy_Nmm':Es,'substrate_energy_Nmm':Eb,'energy_balance_error_Nmm':error,
                'energy_balance_definition':'abs(f dot u - 2*quadratic_energy - 4*quartic_energy)',
                'free_residual_N':float(np.linalg.norm(res)),'minimum_reaction_N':float(reaction.min()),
                'maximum_membrane_slope':slope,'small_slope_screen':bool(slope<=.1),'small_slope_screen_limit':.1,
                'moderate_slope_screen':bool(slope<=.5),'iterations':iterations,
                'substrate':sub,'inverse_basis':'zero_load_linearization',
                'membrane_surface':{'axis_mm':m.axis.tolist(),'displacement_mm':w.tolist(),'pad_width_mm':m.pitch/2,
                                    'tension_N_mm':m.T,'node_count':m.m*m}}
