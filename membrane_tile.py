"""Small transverse displacement of a uniformly pre-tensioned membrane.

Energy: T/2 ∫ |grad w|² dA + 1/2 sum_i k_i (B_i w)².
Units: mm, N; T in N/mm, k in N/mm. Q1 FE on a square grid, natural
zero transverse traction edges. B integrates mean displacement over an
aligned square rigid-pad footprint. Springs are bonded (bilateral), not
unilateral contact. Prescribed in-plane prestress is not solved.
"""
import numpy as np
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import splu


class MembraneTile:
    def __init__(self,kz,pitch_mm,tension_N_mm,subdivisions=4):
        k=np.asarray(kz,float);h=float(pitch_mm);T=float(tension_N_mm);q=subdivisions
        if k.ndim!=2 or k.shape[0]!=k.shape[1] or k.shape[0] not in (3,5,7,8) or not np.isfinite(k).all() or np.any(k<=0):
            raise ValueError('Invalid taxel stiffness grid')
        if not np.isfinite([h,T]).all() or h<=0 or T<=0 or type(q) is not int or q not in (4,8):
            raise ValueError('Positive pitch/tension and 4 or 8 subdivisions required')
        n=k.shape[0];m=n*q+1;step=h/q
        self.n,self.m,self.pitch,self.step,self.k,self.T=n,m,h,step,k.ravel(),T
        self.axis=np.arange(m)*step-h/2
        # Exact bilinear Q1 integral of grad(Na) dot grad(Nb) on a square.
        ke=np.array([[4,-1,-2,-1],[-1,4,-1,-2],[-2,-1,4,-1],[-1,-2,-1,4]],float)/6
        iy,ix=np.indices((m-1,m-1));a=(iy*m+ix).ravel()
        cells=np.column_stack([a,a+1,a+m+1,a+m])
        rows=np.repeat(cells,4,axis=1).ravel();cols=np.tile(cells,(1,4)).ravel()
        self.Km=coo_matrix((np.tile(T*ke.ravel(),len(cells)),(rows,cols)),shape=(m*m,m*m)).tocsc()
        # Pad width h/2. Integral average of Q1 shape functions, exact on
        # cells fully covering this aligned square; no point support singularity.
        rr=[];cc=[];vv=[];center_ids=[]
        for y in range(n):
            for x in range(n):
                cx=x*q+q//2;cy=y*q+q//2;idx=y*n+x;center_ids.append(cy*m+cx)
                for j in range(cy-q//4,cy+q//4):
                    for i in range(cx-q//4,cx+q//4):
                        node=j*m+i
                        rr.extend([idx]*4);cc.extend([node,node+1,node+m+1,node+m])
                        vv.extend([1/(4*(q//2)**2)]*4)
        self.B=coo_matrix((vv,(rr,cc)),shape=(n*n,m*m)).tocsr()
        self.K=(self.Km+self.B.T@diags(self.k)@self.B).tocsc()
        self.factor=splu(self.K)
        self.center_ids=np.asarray(center_ids,int)
        self._transfer=None

    def point_load(self,x_mm,y_mm,force_N):
        x,y,F=map(float,(x_mm,y_mm,force_N))
        if not np.isfinite([x,y,F]).all() or F<0 or not (0<=x<=(self.n-1)*self.pitch and 0<=y<=(self.n-1)*self.pitch):
            raise ValueError('Invalid membrane contact')
        a=(x+self.pitch/2)/self.step;b=(y+self.pitch/2)/self.step
        i,j=min(int(a),self.m-2),min(int(b),self.m-2);dx,dy=a-i,b-j
        f=np.zeros(self.m*self.m)
        for ox,oy,w in ((0,0,(1-dx)*(1-dy)),(1,0,dx*(1-dy)),(0,1,(1-dx)*dy),(1,1,dx*dy)):
            f[(j+oy)*self.m+i+ox]+=F*w
        return f

    def solve(self,contacts):
        f=np.zeros(self.m*self.m)
        for x,y,F in contacts:f+=self.point_load(x,y,F)
        u=self.factor.solve(f);pad=self.B@u;reactions=self.k*pad
        # Center-point basis, independent of actual contacts. One factorization
        # and a multiple-RHS solve replace N separate matrix assemblies.
        if self._transfer is None:
            rhs=np.zeros((len(f),self.n*self.n))
            rhs[self.center_ids,np.arange(self.n*self.n)]=1.
            self._transfer=self.k[:,None]*(self.B@self.factor.solve(rhs))
            self._transfer.setflags(write=False)
        transfer=self._transfer
        Em=float(u@self.Km@u/2);Es=float(np.dot(pad,reactions)/2)
        # In a bilinear Q1 cell each gradient component varies linearly
        # along the other axis. The maximum gradient norm occurs at a corner.
        w=u.reshape(self.m,self.m)
        gx=np.diff(w,axis=1)/self.step;gy=np.diff(w,axis=0)/self.step
        slope=float(max(np.hypot(a,b).max() for a in (gx[:-1],gx[1:]) for b in (gy[:,:-1],gy[:,1:])))
        return {'displacement_mm':pad.reshape(self.n,self.n),'reaction_N':reactions.reshape(self.n,self.n),
                'transfer':transfer,'force_balance_error_N':abs(float(reactions.sum()-f.sum())),
                'strain_energy_Nmm':Em+Es,'membrane_energy_Nmm':Em,'spring_energy_Nmm':Es,
                'energy_balance_error_Nmm':abs(Em+Es-float(f@u/2)),
                'free_residual_N':float(np.linalg.norm(self.K@u-f)),
                'minimum_reaction_N':float(reactions.min()),
                'maximum_membrane_slope':slope,'small_slope_screen':bool(slope<=.1),'small_slope_screen_limit':.1,
                'membrane_surface':{'axis_mm':self.axis.tolist(),'displacement_mm':u.reshape(self.m,self.m).tolist(),
                                    'pad_width_mm':self.pitch/2,'tension_N_mm':self.T,
                                    'node_count':self.m*self.m},
                'tier':'T0'}
