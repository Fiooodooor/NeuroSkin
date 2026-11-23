"""Linear elastic HEX8 FEA: screening only. E [MPa], geometry [mm], force [N].
Known limitations: voxel staircasing, no hyperelasticity, no contact, no buckling,
no fatigue, no embedded electrodes; small-strain is assumed. Prescribed 3-D point
resultant distributed to TOP nodes. Exposes support reaction distribution.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu

def ke_hex(E,nu,h):
    if not E>0 or not -1<nu<.49:raise ValueError('Require E>0, -1<nu<0.49')
    la=E*nu/((1+nu)*(1-2*nu));mu=E/(2*(1+nu))
    D=np.zeros((6,6));D[:3,:3]=la;np.fill_diagonal(D[:3,:3],la+2*mu)
    D[3:,3:]=np.eye(3)*mu
    corner=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]],float)*2-1
    ke=np.zeros((24,24))
    for xi in (-1/np.sqrt(3),1/np.sqrt(3)):
     for eta in (-1/np.sqrt(3),1/np.sqrt(3)):
      for zeta in (-1/np.sqrt(3),1/np.sqrt(3)):
       grad=np.array([[a*(1+b*eta)*(1+c*zeta),b*(1+a*xi)*(1+c*zeta),c*(1+a*xi)*(1+b*eta)] for a,b,c in corner])/(4*h)
       B=np.zeros((6,24))
       for i,(gx,gy,gz) in enumerate(grad):
        j=3*i;B[0,j]=gx;B[1,j+1]=gy;B[2,j+2]=gz
        B[3,j]=gy;B[3,j+1]=gx;B[4,j+1]=gz;B[4,j+2]=gy;B[5,j]=gz;B[5,j+2]=gx
       ke+=B.T@D@B*(h/2)**3
    return ke

class VoxelFEM:
 def __init__(self,mesh,pitch=1.45,E=1.,nu=.35):
    vox=mesh.voxelized(pitch).fill()
    self.cells=np.asarray(vox.sparse_indices,dtype=np.int32)
    if len(self.cells)==0:raise ValueError('Empty mesh')
    corner=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]],int)
    nodes,ind=np.unique((self.cells[:,None,:]+corner[None,:,:]).reshape(-1,3),axis=0,return_inverse=True)
    self.nodes=nodes.astype(float)*pitch
    self.top=float(self.nodes[:,2].max());self.bottom=float(self.nodes[:,2].min())
    elem=ind.reshape(-1,8)
    self.edof=(3*elem[:,:,None]+np.arange(3)[None,None,:]).reshape(-1,24)
    n=3*len(nodes)
    ke=ke_hex(E,nu,pitch)
    rr=np.broadcast_to(self.edof[:,:,None],(len(elem),24,24)).reshape(-1)
    cc=np.broadcast_to(self.edof[:,None,:],(len(elem),24,24)).reshape(-1)
    vv=np.broadcast_to(ke[None,:,:],(len(elem),24,24)).reshape(-1)
    self.K=coo_matrix((vv,(rr,cc)),shape=(n,n)).tocsr()
    self.bottom_nodes=np.flatnonzero(self.nodes[:,2]<=self.bottom+.01)
    self.top_nodes=np.flatnonzero(self.nodes[:,2]>=self.top-.01)
    if len(self.bottom_nodes)<3 or len(self.top_nodes)<3:raise ValueError('Missing support/contact nodes')
    self.fixed=(3*self.bottom_nodes[:,None]+np.arange(3)[None,:]).reshape(-1)
    self.free=np.setdiff1d(np.arange(n),self.fixed)
    self.fac=splu(self.K[self.free,:][:,self.free].tocsc())
    self.E=E;self.nu=nu;self.pitch=pitch
 def solve(self,force=(0,0,-.1),offset=(0,0),radius=3.8,torque_z_Nmm=0.0):
    """Force N on top surface circular patch; offset relative to geometry center.
    If fewer than 3 nodes selected, use nearest 4 nodes (documented approximation).
    """
    top=self.top_nodes
    xy=self.nodes[top,:2]
    center=np.mean(self.nodes[:,:2],axis=0)
    offset=np.asarray(offset,dtype=float)
    rr=np.linalg.norm(xy-center-offset,axis=1)
    loaded=top[rr<=radius]
    if len(loaded)<3:loaded=top[np.argsort(rr)[:min(4,len(top))]]
    if len(loaded)<2:raise ValueError('insufficient patch nodes')
    load=np.asarray(force,float)
    f=np.zeros(len(self.nodes)*3)
    for ax in range(3):f[loaded*3+ax]=load[ax]/len(loaded)
    if torque_z_Nmm:
     # discrete couple: tangential forces tangent to centered top load patch
     loc=self.nodes[loaded,:2]-np.mean(self.nodes[loaded,:2],axis=0)
     m2=np.sum(loc[:,0]**2+loc[:,1]**2)
     if m2<1e-12:raise ValueError('zero lever arm for torque')
     f[loaded*3]+= -torque_z_Nmm*loc[:,1]/m2
     f[loaded*3+1]+= torque_z_Nmm*loc[:,0]/m2
    u=np.zeros_like(f);u[self.free]=self.fac.solve(f[self.free])
    r=self.K@u-f
    U=u.reshape(-1,3);R=r.reshape(-1,3)
    support_reactions=R[self.bottom_nodes]
    # sorted quadrants: (-,-), (+,-), (-,+), (+,+)
    xyB=self.nodes[self.bottom_nodes,:2]-center
    idx=(xyB[:,0]>=0).astype(int)+2*(xyB[:,1]>=0).astype(int)
    q=np.array([support_reactions[idx==i].sum(axis=0) for i in range(4)])
    topU=U[loaded].mean(axis=0)
    lever=self.nodes[loaded,:2]-center
    rotation_z=float(np.sum(lever[:,0]*U[loaded,1]-lever[:,1]*U[loaded,0])/np.sum(lever**2))
    middle=np.flatnonzero((abs(self.nodes[:,2]-(self.top+self.bottom)*.5)<=self.pitch*.55) & (np.linalg.norm(self.nodes[:,:2]-center,axis=1)>2.0))
    mid_rotation=None
    if len(middle)>3:
     lv=self.nodes[middle,:2]-center
     mid_rotation=float(np.sum(lv[:,0]*U[middle,1]-lv[:,1]*U[middle,0])/np.sum(lv**2))
    # Net moment around geometric center (including bottom reactions)
    rb=self.nodes[self.bottom_nodes,:2]-center
    moment_reaction=float(np.sum(rb[:,0]*support_reactions[:,1]-rb[:,1]*support_reactions[:,0]))
    moment_applied=float(np.sum((self.nodes[loaded,0]-center[0])*f[loaded*3+1]-(self.nodes[loaded,1]-center[1])*f[loaded*3]))
    return {'force_N':load.tolist(),'offset_mm':list(map(float,offset)),'loaded_nodes':int(len(loaded)),
            'mean_loaded_displacement_mm':topU.tolist(),'estimated_top_rotation_rad':rotation_z,'estimated_mid_rotation_rad':mid_rotation,
            'support_reaction_Mz_Nmm':moment_reaction,'applied_Mz_Nmm':moment_applied,'max_nodal_displacement_mm':float(np.linalg.norm(U,axis=1).max()),
            'quadrant_reactions_N':q.tolist(),'sum_support_reaction_N':support_reactions.sum(axis=0).tolist(),
            'force_equilibrium_error_N':float(np.linalg.norm(support_reactions.sum(axis=0)+load)),
            'reactions_all_fixed_N':support_reactions.tolist()}
 def responses(self,load=.1,offset=(0,0)):
    loadcases={'Fx':(load,0,0),'Fy':(0,load,0),'Fz':(0,0,-load)}
    out={key:self.solve(force=val,offset=offset) for key,val in loadcases.items()}
    out['Mz']=self.solve(force=(0,0,0),offset=offset,torque_z_Nmm=0.1)
    compliance=np.stack([np.asarray(out[k]['mean_loaded_displacement_mm'])/load for k in ('Fx','Fy','Fz')],axis=1)
    # Fz is compressive NEGATIVE. Convert to physically signed force map.
    # Instrumentation proxy: vertical reactions of 4 *separately instrumented* feet.
    J=np.stack([np.array(out[k]['quadrant_reactions_N'])[:,2]/load for k in ('Fx','Fy','Fz')],axis=1)
    S=np.linalg.svd(J,compute_uv=False)
    cn=float(S[0]/S[-1]) if S[-1]>1e-12 else None
    return {'cases':out,'compliance_mm_per_N':compliance.tolist(),
            'vertical_quadrant_sensitivity':J.tolist(),'singular_values':S.tolist(),
            'condition_number':cn,'observable_3axis':bool(S[-1]>1e-5)}
