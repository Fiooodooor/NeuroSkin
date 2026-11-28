"""Foppl-von Karman Q1 membrane with in-plane relaxation and normal substrate coupling.

In-plane perimeter fixed at zero; transverse perimeter free. Prescribed initial
isotropic tension is held fixed. No bending, wrinkling, tangential receptor
attachment, large finite-strain shell kinematics or material calibration.
"""
import numpy as np
from scipy.sparse import coo_matrix, block_diag, csr_matrix
from scipy.sparse.linalg import spsolve
from nonlinear_skin_tile import NonlinearSkinTile


class RelaxedSkinTile(NonlinearSkinTile):
    def __init__(self,kz,pitch,tension,young,thickness,poisson=.3,subdivisions=4,substrate=None):
        if young<=0:raise ValueError('Relaxed membrane requires positive modulus')
        super().__init__(kz,pitch,tension,young,thickness,poisson,subdivisions,substrate)
        self.D=young*thickness/(1-poisson**2)*np.array([[1,poisson,0],[poisson,1,0],[0,0,(1-poisson)/2]])
        m=self.linear.m;n=m*m;self.nodal_count=n
        self.edof=np.concatenate([self.cells,self.cells+n,self.cells+2*n],axis=1)
        self.rr=np.repeat(self.edof,12,axis=1).ravel();self.cc=np.tile(self.edof,(1,12)).ravel()
        self.base=block_diag((csr_matrix((2*n,2*n)),self.K0),format='csc')
        iy,ix=np.indices((m,m));boundary=np.flatnonzero(((ix==0)|(ix==m-1)|(iy==0)|(iy==m-1)).ravel())
        self.fixed=np.r_[boundary,boundary+n]
        self.free=np.setdiff1d(np.arange(3*n),self.fixed)
        self.B0=np.zeros((len(self.G),3,12))
        gx,gy=self.G[:,:,0],self.G[:,:,1]
        self.B0[:,0,:4]=gx;self.B0[:,1,4:8]=gy
        self.B0[:,2,:4]=gy;self.B0[:,2,4:8]=gx

    def assemble_relaxed(self,q,f,tangent=True):
        n=self.nodal_count
        g=np.einsum('eza,qai->eqzi',q.reshape(3,n)[:,self.cells].transpose(1,0,2),self.G)
        wx,wy=g[:,:,2,0],g[:,:,2,1]
        e=np.stack([g[:,:,0,0]+.5*wx**2,g[:,:,1,1]+.5*wy**2,
                    g[:,:,0,1]+g[:,:,1,0]+wx*wy],axis=2)
        stress=e@self.D.T
        stretch=float(.5*np.einsum('q,eqi,eqi->',self.W,e,stress))
        B=np.broadcast_to(self.B0,(len(self.cells),*self.B0.shape)).copy()
        gx,gy=self.G[:,:,0],self.G[:,:,1]
        B[:,:,0,8:]=wx[:,:,None]*gx
        B[:,:,1,8:]=wy[:,:,None]*gy
        B[:,:,2,8:]=wy[:,:,None]*gx+wx[:,:,None]*gy
        r=self.base@q-f
        local=np.einsum('q,eqia,eqi->ea',self.W,B,stress)
        np.add.at(r,self.edof.ravel(),local.ravel())
        K=None
        if tangent:
            ke=np.einsum('q,eqia,ij,eqjb->eab',self.W,B,self.D,B,optimize=True)
            S=np.empty((*stress.shape[:2],2,2))
            S[:,:,0,0]=stress[:,:,0];S[:,:,1,1]=stress[:,:,1];S[:,:,0,1]=S[:,:,1,0]=stress[:,:,2]
            ke[:,8:,8:]+=np.einsum('q,qai,eqij,qbj->eab',self.W,self.G,S,self.G,optimize=True)
            K=(self.base+coo_matrix((ke.ravel(),(self.rr,self.cc)),shape=self.base.shape)).tocsc()
        return float(q@self.base@q/2)+stretch-float(f@q),r,K,stretch

    def solve(self,contacts):
        m=self.linear;n=self.nodal_count;f=np.zeros(3*n)
        for x,y,F in contacts:f[2*n:]+=m.point_load(x,y,F)
        q=np.zeros_like(f);iterations=0
        for fraction in (.25,.5,.75,1.):
            target=f*fraction
            for i in range(40):
                E,r,K,_=self.assemble_relaxed(q,target)
                rf=r[self.free]
                if np.linalg.norm(rf)<=max(1e-9,np.linalg.norm(target)*1e-8):break
                step=spsolve(K[self.free][:,self.free],-rf)
                direction=float(rf@step)
                if not np.isfinite(step).all() or direction>=0:
                    raise RuntimeError('Relaxed membrane tangent not a descent direction; unstable or unsupported state')
                for j in range(25):
                    trial=q.copy();trial[self.free]+=step*(.5**j)
                    if self.assemble_relaxed(trial,target,False)[0]<=E+1e-4*(.5**j)*direction:
                        q=trial;iterations+=1;break
                else:raise RuntimeError('Relaxed membrane line search failed')
            else:raise RuntimeError('Relaxed membrane Newton failed to converge')
        _,r,_,stretch=self.assemble_relaxed(q,f,False)
        result=self.report(q[2*n:],f[2*n:],float(np.linalg.norm(r[self.free])),iterations,stretch)
        uv=q[:2*n].reshape(2,m.m,m.m)
        result['membrane_kinematics']='relaxed_inplane_fixed_perimeter'
        result['membrane_surface']['inplane_x_mm']=uv[0].tolist()
        result['membrane_surface']['inplane_y_mm']=uv[1].tolist()
        result['inplane_displacement_max_mm']=float(np.hypot(*uv).max())
        # At in-plane equilibrium with homogeneous prescribed displacements,
        # the reduced stretching energy is quartic in w. The same work identity
        # applies, with all free in-plane residuals included in the check.
        result['energy_balance_definition']='abs(f dot w - 2*quadratic_energy - 4*relaxed_stretch_energy) at in-plane equilibrium'
        return result
