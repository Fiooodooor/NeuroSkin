"""Generates a static example illustration (NOT a screenshot of the live application)."""
import json,random
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from engine import random_genome,metrics,mesh_for,FAMILIES
P=Path(__file__).parent
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
fig=plt.figure(figsize=(14,7.5),facecolor='#0a1119')
gs=GridSpec(2,3,figure=fig,height_ratios=[3,1],hspace=.10,wspace=.05)
labels={'crown':'A5 · Progressive Crown','chiral':'B5 · Chiral Torsion','quadrant':'C5 · Differential Quadrant'}
for k,fam in enumerate(FAMILIES):
 ax=fig.add_subplot(gs[0,k],projection='3d');ax.set_facecolor('#111d29')
 p=random_genome(fam,random.Random(22+k));m=mesh_for(fam,p,quality=8)
 verts=m.vertices; faces=m.faces
 triangles=verts[faces][::2]
 poly=Poly3DCollection(triangles,linewidths=0,alpha=.90,facecolor='#7bd3b7',edgecolor='#467d83')
 ax.add_collection3d(poly)
 ax.set_xlim(-11,11);ax.set_ylim(-11,11);ax.set_zlim(0,9);ax.set_box_aspect((1,1,.6));ax.view_init(25,-52)
 ax.set_xticks([]);ax.set_yticks([]);ax.set_zticks([])
 ax.xaxis.pane.fill=False;ax.yaxis.pane.fill=False;ax.zaxis.pane.fill=False
 ax.set_title(labels[fam],color='#ecf9f4',fontsize=14,pad=8)
 ax.text2D(.5,-.02,'3D concept geometry · not validated',transform=ax.transAxes,ha='center',color='#9bb7bc',fontsize=9)
 ax2=fig.add_subplot(gs[1,k]);ax2.set_facecolor('#111d29');ax2.axis('off')
 met=metrics(fam,p);s=f"Example fitness: {met['fitness']:.3f}   |   kz: {met['kz_N_mm']:.3f} N/mm\nRod volume: {met['rod_volume_mm3']:.1f} mm³ | illustrative analytic proxy"
 ax2.text(.5,.45,s,ha='center',va='center',color='#8cd7bf',fontsize=10,linespacing=2)
fig.suptitle('NeuroSkin Evolution Lab · example candidates',fontsize=21,fontweight='bold',color='white',y=.985)
fig.text(.5,.015,'The real interactive application animates evolutionary progress and updates the rotatable 3D champion. This image is a static illustration.',ha='center',color='#c3ced2',fontsize=9)
fig.savefig(P/'concept_preview.png',dpi=145,facecolor=fig.get_facecolor(),bbox_inches='tight');plt.close(fig)
