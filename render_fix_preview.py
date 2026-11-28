"""Generate an independent before/after visualization of the PVDF geometry fix."""
import random
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from advanced import new_genome,structural_struts,detail_mesh
from geometry_fixes import pvdf_ribbon

def draw_mesh(ax,mesh,color,alpha=1,max_faces=800):
 f=np.asarray(mesh.faces)
 if len(f)>max_faces:f=f[np.linspace(0,len(f)-1,max_faces,dtype=int)]
 polys=mesh.vertices[f]
 pc=Poly3DCollection(polys,facecolor=color,edgecolor='none',alpha=alpha)
 ax.add_collection3d(pc)

fig=plt.figure(figsize=(13,4.5),dpi=150,facecolor='#f7f8f9')
for i,fam in enumerate(['crown','chiral','quadrant']):
 rng=random.Random(7+i);g=new_genome(fam,rng)
 pts,r,_=structural_struts(fam,g)[0]
 # make support readable and compliant sensor visibly attached
 ax=fig.add_subplot(1,3,i+1,projection='3d')
 ax.set_facecolor('#f7f8f9')
 for path,rad,k in structural_struts(fam,g)[:min(8,len(structural_struts(fam,g)))]:
  ax.plot(path[:,0],path[:,1],path[:,2],color='#4cae98',linewidth=max(.8,rad*4),alpha=.78)
 mesh=detail_mesh(fam,g)
 draw_mesh(ax,mesh['piezo'],'#f0a645',alpha=1)
 pad=mesh['contact'];draw_mesh(ax,pad,'#b8d3d0',alpha=.22,max_faces=80)
 ax.set(xlim=(-10,10),ylim=(-10,10),zlim=(0,max(8,g['height']+1)))
 ax.set_box_aspect([1,1,.65]);ax.view_init(elev=22,azim=38)
 ax.set_axis_off();ax.set_title({'crown':'A5 · Progressive Crown','chiral':'B5 · Chiral Torsion','quadrant':'C5 · Differential Quadrant'}[fam],fontsize=11,fontweight='bold')
fig.suptitle('NeuroSkin 1.0 · PVDF conformal sensor strip (render geometry)',fontsize=15,weight='bold')
fig.text(.5,.015,'Gold: thin PVDF ribbon aligned with supporting strut  •  Green: support centerlines  •  Teal: contact pad\nIllustration is NOT a deformation field, FEA result, or manufacturability verification.',ha='center',fontsize=8,color='#52616b')
fig.subplots_adjust(top=.84,bottom=.17,wspace=.01)
Path('artifacts/previews').mkdir(parents=True,exist_ok=True)
fig.savefig(Path('artifacts/previews/pvdf_geometry_fix.png'),bbox_inches='tight',facecolor=fig.get_facecolor())
print('pvdf_geometry_fix.png created')
