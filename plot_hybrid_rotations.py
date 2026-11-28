"""Generate 3D comparison of *actual* generated upper and lower stage paths."""
from __future__ import annotations
import math
import random
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from advanced import structural_struts
from hybrid_geometry import mid_height
from hybrid_library import BY_ID, genome_for
from orientation_study import scan_rotations


def main(output='HYBRID_ROTATION_COMPARISON_v21.png', hybrid_id='h01_serpentine_quadrant'):
    spec = BY_ID[hybrid_id]
    g0 = genome_for(spec, random.Random(1701))
    scans = scan_rotations(spec.upper_family, g0)
    views = (0,45,90)
    fig = plt.figure(figsize=(14,5.4), dpi=170, facecolor='#07111b')
    for panel,angle in enumerate(views,1):
        g = dict(g0, hybrid_phase=math.radians(angle))
        ax = fig.add_subplot(1,3,panel,projection='3d', facecolor='#101e2b')
        mid = mid_height(g)
        paths = structural_struts(spec.upper_family,g)
        for points,_,tag in paths:
            upper = points[0,2] > mid-.25
            ax.plot(points[:,0],points[:,1],points[:,2],linewidth=2.8 if tag=='leg' else 1.7,
                    color='#75d3bf' if upper else '#e3a66f',alpha=.95 if tag=='leg' else .65)
        # Structural middle-plate perimeter; illustrative disk boundary
        th=np.linspace(0,2*np.pi,120)
        r=float(g['radius'])*1.18
        ax.plot(r*np.cos(th),r*np.sin(th),np.full_like(th,mid),color='#b7a5ed',linewidth=2)
        ax.plot(float(g['pad_radius'])*np.cos(th),float(g['pad_radius'])*np.sin(th),
                np.full_like(th,float(g['height'])),color='#a0ded1',linewidth=2)
        ax.set_xlim(-8,8);ax.set_ylim(-8,8);ax.set_zlim(0,9)
        ax.set_box_aspect((1,1,.85));ax.view_init(elev=26,azim=-52)
        ax.set_xlabel('X (mm)',color='#b9d4e4',fontsize=7)
        ax.set_ylabel('Y (mm)',color='#b9d4e4',fontsize=7)
        ax.set_zlabel('Z (mm)',color='#b9d4e4',fontsize=7)
        ax.tick_params(colors='#b9d4e4',labelsize=7)
        for axis in [ax.xaxis,ax.yaxis,ax.zaxis]:axis.pane.fill=False
        rec = next(item for item in scans['rows'] if item['angle_deg']==angle)
        ax.set_title(f"Upper rotation {angle}°\nTilt {rec['max_tilt_rad']:.3f} rad · {rec['coverage_fraction']*100:.0f}% pass",
                     color='#e9f4ef',fontsize=10,pad=12)
    fig.suptitle('NeuroSkin 2.1 · Relative stage rotation (same geometry and electrical model)\nTeal: upper sensing flexures · Orange: lower reference flexures · Purple: shared middle plate',
                 fontsize=13,color='#e6f3f4',y=.99)
    fig.tight_layout(rect=[0,.01,1,.90])
    fig.savefig(output,facecolor=fig.get_facecolor())
    return scans


if __name__=='__main__':
    main()
