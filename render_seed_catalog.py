"""Overview of genuine generated seed centerlines (not stress/deformation plots)."""
import math,random
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from seed_library import top_candidates,SEEDS,seed_genome
from advanced import structural_struts

def main():
    top=top_candidates()
    fig=plt.figure(figsize=(18,8.5),facecolor='#f5f8f7')
    for i,s in enumerate(top):
        ax=fig.add_subplot(2,5,i+1,projection='3d',facecolor='#f5f8f7')
        g=seed_genome(s,random.Random(10007),mutate=False)
        H=float(g['height']);R=float(g['pad_radius'])+.4
        for path,r,tag in structural_struts(s.family,g):
            ax.plot(path[:,0],path[:,1],path[:,2],color='#168e80' if tag=='leg' else '#7199a4',lw=2.5 if tag=='leg' else 1.1)
            if tag=='leg':
                ax.scatter([path[0,0]],[path[0,1]],[path[0,2]],s=14,c='#d4a763')
        a=np.linspace(0,2*math.pi,65)
        ax.plot(R*np.cos(a)+g.get('pad_offset_x',0),R*np.sin(a)+g.get('pad_offset_y',0),H*np.ones_like(a),c='#425d70',lw=2)
        ax.set_box_aspect((1,1,.8));ax.set_xlim(-9,9);ax.set_ylim(-9,9);ax.set_zlim(0,9)
        ax.view_init(elev=25,azim=-57)
        ax.set_axis_off()
        ax.set_title(f'{i+1}. {s.title}\n{s.family.upper()} · {sum(s.scores)}/100 · {s.category}',fontweight='bold',fontsize=10,pad=0,color='#142b37')
    fig.suptitle('NEUROSKIN 3  ·  TOP 10 PARAMETRIC METAMECHANICAL RECEPTORS',fontsize=19,fontweight='bold',color='#173a3e',y=.98)
    fig.text(.5,.02,'3D centerlines from generated geometry  |  STL models contain detailed tapered closed beams  |  score = expert prior, not FEM',ha='center',fontsize=10,color='#596971')
    fig.subplots_adjust(top=.87,bottom=.05,left=.02,right=.98,hspace=.16,wspace=.01)
    dst=Path('artifacts/previews/seed_catalog.png');dst.parent.mkdir(parents=True,exist_ok=True);fig.savefig(dst,dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    print(dst)
if __name__=='__main__':main()
