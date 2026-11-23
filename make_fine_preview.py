"""Render an actual beam-FEM result; a scientific visualization, not a photo."""
from pathlib import Path
import random
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib import cm, colors
from advanced import new_genome
from beam_fem import BeamFEM

p=new_genome('quadrant',random.Random(42))
solver=BeamFEM('quadrant',p,pitch_mm=.15625)
result=solver.solve(force=(0,0,-.015),include_fields=True)
field=result['fields']
vertices=np.asarray(field['vertices_mm']);faces=np.asarray(field['faces'])
U=np.asarray(field['displacement_mm']);S=np.asarray(field['stress_vm_MPa'])
fig=plt.figure(figsize=(13,6),facecolor='#091725')
for idx,scale in enumerate((0,4)):
 ax=fig.add_subplot(1,2,idx+1,projection='3d')
 ax.set_facecolor('#091725')
 vv=vertices+scale*U
 keep=faces[::2]
 face_stress=S[keep].mean(axis=1)
 norm=colors.Normalize(vmin=0,vmax=max(S.max(),1e-4))
 if idx==0:
  poly=Poly3DCollection(vv[keep],facecolor='#7dc4b0',edgecolor='none',alpha=.98)
  title='Undeformed geometry'
 else:
  poly=Poly3DCollection(vv[keep],facecolors=cm.viridis(norm(face_stress)),edgecolors='none',alpha=.98)
  title='Solved beam FEM · displacement ×4'
 ax.add_collection3d(poly)
 ax.set(xlim=(-9,9),ylim=(-9,9),zlim=(-1,9))
 ax.view_init(elev=24,azim=-55)
 ax.set_box_aspect((1.2,1.2,.8))
 ax.set_title(title,color='#f2f5f6',fontsize=14,pad=14)
 for axis in (ax.xaxis,ax.yaxis,ax.zaxis):
  axis.set_pane_color((.04,.10,.15,1))
  axis.line.set_color('#496373')
  axis.label.set_color('#bed6db')
  axis.set_tick_params(colors='#abc4d0',labelsize=8)
 ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)');ax.set_zlabel('Z (mm)')
fig.suptitle('NeuroSkin 1.3 · Differential Quadrant · 0.15625 mm axial beam-FEM pitch',color='#edf7f6',fontsize=15)
fig.text(.5,.03,'Linear Euler-Bernoulli beam FEM — not a volumetric 8× solid mesh; color indicates estimated beam stress.',ha='center',color='#c9d3d8',fontsize=10)
fig.subplots_adjust(left=.01,right=.99,bottom=.05,top=.9,wspace=.01)
file=Path(__file__).with_name('FINE_BEAM_8X_PREVIEW.png')
fig.savefig(file,dpi=140,facecolor=fig.get_facecolor(),bbox_inches='tight');plt.close(fig)
print(file,result['mean_down_mm'],solver.n_elements)
