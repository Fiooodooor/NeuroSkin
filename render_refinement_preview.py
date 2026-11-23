"""Compare spatial pressure sensitivity for identical mechanics and two readout designs.

The plots depict synthetic capacitance/SNR predictions, not measured results.
"""
from __future__ import annotations
import random
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from advanced import new_genome
from spatial_validation import spatial_pressure_test


def make_preview(out='REFINEMENT_V191_PREVIEW.png'):
    g=new_genome('quadrant',random.Random(33))
    g.update(topology='orthogonal',asymmetry=0.,pad_offset_x=0.,pad_offset_y=0.,
             strut_gradient=0.,wave_amp=0.,piezo_count=4)
    designs=[
        ('Baseline electrode geometry',dict(g,electrode_area_mm2=7.,dielectric_gap_mm=.45,mount_compliance_mm_N=.09)),
        ('Tuned electrode geometry',dict(g,electrode_area_mm2=9.5,dielectric_gap_mm=.25,mount_compliance_mm_N=.43)),
    ]
    outcomes=[spatial_pressure_test('quadrant',x,force_n=.1,grid_size=5) for _,x in designs]
    fig,axes=plt.subplots(1,2,figsize=(11.2,4.8),dpi=160,layout='constrained')
    norm=Normalize(vmin=0,vmax=max(6.,max(p['snr_proxy'] for z in outcomes for p in z['points'])))
    for ax,(name,genome),s in zip(axes,designs,outcomes):
        pts=s['points']
        xs=np.array([p['x_mm'] for p in pts]);ys=np.array([p['y_mm'] for p in pts]);vals=np.array([p['snr_proxy'] for p in pts]);passed=np.array([p['passed'] for p in pts])
        sc=ax.scatter(xs,ys,c=vals,cmap='viridis',norm=norm,s=155,edgecolors=np.where(passed,'#f0fff2','#d9544d'),linewidths=2)
        for x,y,p in zip(xs,ys,pts):
            ax.annotate(f"{p['snr_proxy']:.1f}",(x,y),ha='center',va='center',color='white',fontsize=7,fontweight='bold')
        t=np.linspace(0,2*np.pi,240);r=s['test_radius_mm'];ax.plot(r*np.cos(t),r*np.sin(t),':',color='#546575',lw=1.5)
        ax.axhline(0,color='#d1dce4',lw=.6);ax.axvline(0,color='#d1dce4',lw=.6)
        ax.set_xlim(-r*1.18,r*1.18);ax.set_ylim(-r*1.18,r*1.18);ax.set_aspect('equal');ax.grid(alpha=.12)
        ax.set_title(name+'\n'+f"Pass {s['passing_points']}/{s['total_points']} · min SNR {s['min_snr_proxy']:.2f}",fontsize=10)
        ax.set_xlabel('Contact X [mm]');ax.set_ylabel('Contact Y [mm]')
    cb=fig.colorbar(sc,ax=axes,shrink=.8,pad=.02);cb.set_label('Assumed pressure-channel SNR')
    fig.suptitle('NeuroSkin 1.9.1 · identical Quadrant mechanics, revised capacitive readout\nSynthetic 0.1 N spatial screen · RED outline = failed screen',fontsize=12)
    fig.savefig(out,bbox_inches='tight')
    return outcomes

if __name__=='__main__':
    make_preview()
