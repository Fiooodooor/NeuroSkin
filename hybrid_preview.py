"""Generate a visual catalogue from the actual two-stage centerline geometry."""
from __future__ import annotations
import random
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from hybrid_library import ranked,genome_for
from hybrid_geometry import mid_height,mid_radius
from advanced import structural_struts


def render(out='artifacts/previews/hybrid_top10.png'):
    specs=ranked();fig=plt.figure(figsize=(16.5,7.7),dpi=150)
    fig.patch.set_facecolor('#0c1723')
    for k,spec in enumerate(specs):
        g=genome_for(spec,random.Random(1701))
        h=mid_height(g)
        ax=fig.add_subplot(2,5,k+1,projection='3d',computed_zorder=False)
        ax.set_facecolor('#0c1723')
        for pts,r,tag in structural_struts(spec.upper_family,g):
            color='#6ce1b9' if pts[0,2]>h-.25 else '#e7ad73'
            ax.plot(pts[:,0],pts[:,1],pts[:,2],color=color,linewidth=max(1.1,r*3),solid_capstyle='round')
        for z,r,clr in ((.3,8.8,'#536c82'),(h,mid_radius(g),'#b19dc5'),(g['height'],g['pad_radius']+.4,'#92d7cb')):
            a=np.linspace(0,2*np.pi,64)
            ax.plot(r*np.cos(a),r*np.sin(a),np.ones(len(a))*z,color=clr,linewidth=2,alpha=.95)
        ax.set(xlim=(-10,10),ylim=(-10,10),zlim=(0,9))
        ax.view_init(elev=17,azim=-60)
        ax.set_box_aspect((1,1,.8))
        ax.set_xticks([]);ax.set_yticks([]);ax.set_zticks([])
        ax.set_title(f'{k+1}. {spec.name}\n{sum(spec.scores)}/100 expert prior',color='#d7eaf0',fontsize=9,pad=3)
        for axis in (ax.xaxis,ax.yaxis,ax.zaxis):axis.pane.set_facecolor((.045,.09,.14,0))
        ax.grid(False)
    fig.suptitle('NeuroSkin 3 · 10 hybrid double-stage morphologies\nTeal = upper receptor  |  Orange = lower reference  |  Purple = shared interface',color='#d6ebed',fontsize=16,y=.99)
    fig.subplots_adjust(top=.85,bottom=.03,hspace=.34,wspace=.05)
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(out,bbox_inches='tight',facecolor=fig.get_facecolor())
    return out


if __name__=='__main__':render()
