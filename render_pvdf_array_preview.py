"""Render the legacy one-film and symmetric four-film geometry for inspection.

Requires matplotlib, trimesh and the application's usual Python dependencies.
This is a conceptual geometry view, not FEM deformation.
"""
import random
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from advanced import new_genome,detail_mesh

COLORS={'base':'#7592a1','flexure':'#6fcbb6','contact':'#b3e3d3',
        'sensor':'#e8a45e','piezo':'#ffbe42','inner':'#9b8fd5'}

def draw(ax,parts):
    for name in ('base','sensor','flexure','inner','piezo','contact'):
        if name not in parts:continue
        m=parts[name];tri=np.asarray(m.triangles)
        if name!='piezo':
            limit=2300
            if len(tri)>limit:tri=tri[np.linspace(0,len(tri)-1,limit,dtype=int)]
        poly=Poly3DCollection(tri,facecolor=COLORS[name],edgecolor='none',alpha=1 if name=='piezo' else (.69 if name=='contact' else .85))
        ax.add_collection3d(poly)
    ax.set_xlim(-9,9);ax.set_ylim(-9,9);ax.set_zlim(0,9)
    ax.set_box_aspect((1,1,.75));ax.view_init(elev=24,azim=225)
    ax.set_axis_off()
    ax.set_facecolor('white')

def main(out='PVDF_SYMMETRY_COMPARISON.png'):
    p=new_genome('quadrant',random.Random(33));p['piezo_count']=4;p['piezo_wiring']=0
    p['topology']='diagonal'
    original=dict(p);original.pop('piezo_count');original.pop('piezo_wiring')
    fig=plt.figure(figsize=(12.8,5.3),facecolor='#f9fbfc')
    for k,(genome,title,sub) in enumerate([
        (original,'Legacy v1.3 · single PVDF','Asymmetric material placement'),
        (p,'v1.4 · four PVDF films','Balanced placement · independent channels')]):
        ax=fig.add_subplot(1,2,k+1,projection='3d')
        draw(ax,detail_mesh('quadrant',genome,quality=16))
        ax.set_title(title,fontweight='bold',fontsize=14,color='#173246',pad=2)
        ax.text2D(.5,.015,sub,transform=ax.transAxes,ha='center',color='#516875',fontsize=10)
    fig.suptitle('NeuroSkin PVDF layout: conceptual 3D geometry (not mechanical FEM)',fontsize=13,color='#37515c')
    fig.subplots_adjust(top=.84,bottom=.06,wspace=.03)
    fig.savefig(out,dpi=155,facecolor=fig.get_facecolor(),bbox_inches='tight')
    plt.close(fig)
    return out
if __name__=='__main__':print(main())
