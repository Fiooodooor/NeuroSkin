from pathlib import Path
import random
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from advanced import FAMILIES, new_genome, detail_mesh, proxy

out=Path(__file__).resolve().parent
fig=plt.figure(figsize=(15,5.5),facecolor='#0a1520')
colors={'base':'#7595ae','flexure':'#6bd2b4','contact':'#b3e7d4','sensor':'#ffca73','inner':'#ab9cde'}
for k,fam in enumerate(FAMILIES):
 ax=fig.add_subplot(1,3,k+1,projection='3d',facecolor='#111f2d')
 p=new_genome(fam,random.Random(k+11));p['topology']={'crown':'spiral','chiral':'braided','quadrant':'serpentine'}[fam]
 group=detail_mesh(fam,p,8)
 for name,m in group.items():
  tris=m.triangles
  if len(tris)>900:tris=tris[::int(np.ceil(len(tris)/900))]
  pc=Poly3DCollection(tris,facecolor=colors[name],edgecolor='#314c5d',linewidth=.025,alpha=.84)
  ax.add_collection3d(pc)
 ax.set(xlim=(-10,10),ylim=(-10,10),zlim=(0,9));ax.view_init(elev=27,azim=-55)
 ax.set_axis_off()
 ax.set_title(f'{["A5  PROGRESSIVE CROWN","B5  CHIRAL TORSION","C5  DIFFERENTIAL QUADRANT"][k]}\n{p["topology"].upper()}  |  heuristic {proxy(fam,p)[0]:.1f}/100',color='white',fontsize=11,pad=14)
fig.text(.5,.98,'NEUROSKIN EVOLUTION LAB 0.5   /   MORE TOPOLOGIES + INTERACTIVE 3D',ha='center',color='#b7eadd',fontsize=14,weight='bold')
fig.text(.5,.025,'GEOMETRY PREVIEW  •  NOT FEM  •  NOT PRINT-READY CAD',ha='center',color='#b7c6d1',fontsize=10)
fig.subplots_adjust(top=.84,bottom=.10,wspace=.01,left=.03,right=.97)
fig.savefig(out/'geometry_preview_v05.png',dpi=165,facecolor=fig.get_facecolor())
print(out/'geometry_preview_v05.png')
