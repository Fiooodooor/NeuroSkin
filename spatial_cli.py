"""Offline spatial scan of the three reference NeuroSkin morphology families.
Usage: python spatial_cli.py --out spatial_reports --grid 5 --force 0.1
"""
import argparse, csv, json, random
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from advanced import new_genome
from spatial_validation import spatial_pressure_test


def run(out='spatial_reports',grid=5,force=.1,seed=42):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 report={}
 fig,axarr=plt.subplots(1,3,figsize=(14,4.5),constrained_layout=True)
 for ax,fam in zip(axarr,('crown','chiral','quadrant')):
  g=new_genome(fam,random.Random(seed));r=spatial_pressure_test(fam,g,force_n=force,grid_size=grid)
  report[fam]={'genome':g,'spatial':r}
  pts=r['points'];sc=ax.scatter([p['x_mm'] for p in pts],[p['y_mm'] for p in pts],c=[p['snr_proxy'] for p in pts],s=165,cmap='viridis',vmin=0,vmax=max(10,max(p['snr_proxy'] for p in pts)),edgecolor=['#3ca47b' if p['passed'] else '#bb3e46' for p in pts],linewidth=2)
  for p in pts:
   if not p['passed']:ax.text(p['x_mm'],p['y_mm'],'×',ha='center',va='center',color='white',weight='bold')
  t=np.linspace(0,2*np.pi,200);rad=r['test_radius_mm'];ax.plot(rad*np.cos(t),rad*np.sin(t),color='#879fa8',linestyle='--',linewidth=.8)
  ax.set_title(f'{fam.upper()} — {r["passing_points"]}/{r["total_points"]} PASS')
  ax.set_xlabel('Contact X [mm]');ax.set_ylabel('Contact Y [mm]');ax.set_aspect('equal');ax.grid(alpha=.2)
 fig.colorbar(sc,ax=axarr,shrink=.7,label='Pressure-electrode SNR (assumed)')
 fig.suptitle(f'NeuroSkin 0.7 · spatial vertical load −Fz={force:g} N · screening surrogate')
 fig.savefig(out/'spatial_pressure_preview.png',dpi=160)
 (out/'spatial_report.json').write_text(json.dumps(report,indent=2))
 with (out/'spatial_points.csv').open('w',newline='') as f:
  cols=['family','x_mm','y_mm','passed','snr_proxy','signal_norm_pF','signal_sum_pF','vertical_deflection_mm','lateral_mm','tilt_rad','negative_reaction_fraction','flags']
  w=csv.DictWriter(f,cols);w.writeheader()
  for fam,d in report.items():
   for p in d['spatial']['points']:
    w.writerow({k:(fam if k=='family' else ','.join(p['flags']) if k=='flags' else p.get(k)) for k in cols})
 return report

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--out',default='spatial_reports');a.add_argument('--grid',type=int,choices=[3,5,7],default=5);a.add_argument('--force',type=float,default=.1);a.add_argument('--seed',type=int,default=42)
 opt=a.parse_args();data=run(opt.out,opt.grid,opt.force,opt.seed)
 for k,v in data.items():print(k,v['spatial']['status'],v['spatial']['passing_points'],'/',v['spatial']['total_points'],v['spatial']['failure_reasons'])
