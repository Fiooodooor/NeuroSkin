"""Convergence-oriented real HEX8 resolution study for one selected candidate.

Caution: comparing 1.25 and 0.15625 mm changes the *geometry rasterization*
(including artificial thickening) as well as finite-element discretization.
It is a practical resolution study, not a formal h-convergence certificate.
"""
from __future__ import annotations
import argparse, csv, json, random, sys, time
from pathlib import Path
import numpy as np
from advanced import new_genome
from physical_fem import FEMConfig, HexElasticSolver, InvalidGeometry, voxel_mesh


def run_study(family,genome,pitches=(1.25,.625,.3125,.15625),*,
              max_cells=800_000,memory_mb=3072,cg_maxiter=5000,cg_rtol=5e-5,
              cg_timeout=180,force_n=.1):
    out=[]
    for pitch in pitches:
        start=time.monotonic()
        row={'family':family,'pitch_mm':float(pitch),'status':'failed'}
        try:
            cfg=FEMConfig(pitch_mm=float(pitch),young_MPa=float(genome.get('material_E',1.)),
                  max_cells=max_cells,max_memory_mb=memory_mb,cg_maxiter=cg_maxiter,
                  cg_rtol=cg_rtol,cg_timeout_s=cg_timeout)
            mesh=voxel_mesh(family,genome,cfg,build_surface=False)
            solver=HexElasticSolver(mesh,cfg.young_MPa,cfg.poisson,
                    matrixfree_threshold=cfg.matrixfree_threshold,cg_maxiter=cfg.cg_maxiter,
                    cg_rtol=cfg.cg_rtol,cg_timeout_s=cfg.cg_timeout_s)
            result=solver.solve(force=(0.,0.,-force_n))
            row.update(status='solved',elements=mesh.voxels,nodes=len(mesh.nodes),
                       artificial_feature_inflation_count=mesh.inflated_features,
                       model_volume_mm3=mesh.volume_mm3,solver=solver.solver_mode,
                       cg_iterations=result['cg_iterations'],
                       deflection_mm=result['mean_down_mm'],
                       max_von_mises_MPa=result['max_von_mises_MPa'],
                       max_abs_principal_strain=result['max_abs_principal_strain'],
                       equilibrium_error=result['force_equilibrium_relative'],
                       free_residual=result['free_residual_relative'],
                       patch_selection_mode=result['contact_patch_mode'],
                       mesh_warning=mesh.geometry_warning)
        except (InvalidGeometry,ValueError,RuntimeError,MemoryError) as exc:
            row['error']=f'{type(exc).__name__}: {exc}'
        row['wall_seconds']=round(time.monotonic()-start,3)
        out.append(row)
        print(f"{pitch:8g} mm : {row['status']} : {row.get('elements','?')} elements : "
              f"{row.get('deflection_mm','?')} mm deflection : {row['wall_seconds']} s",flush=True)
    previous=None
    for row in out:
        if row['status']=='solved':
            row['relative_deflection_change_from_previous']=None if previous is None else (
                abs(row['deflection_mm']-previous['deflection_mm'])/max(abs(row['deflection_mm']),1e-12))
            row['relative_volume_change_from_previous']=None if previous is None else (
                abs(row['model_volume_mm3']-previous['model_volume_mm3'])/max(abs(row['model_volume_mm3']),1e-12))
            row['preliminary_not_validated']=True
            previous=row
    return out


def main(argv=None):
    ap=argparse.ArgumentParser(description='Actual 3D HEX8 mesh-refinement study (4x / 8x finer resolution)')
    ap.add_argument('--family',choices=['crown','chiral','quadrant'],default='quadrant')
    ap.add_argument('--seed',type=int,default=42)
    ap.add_argument('--genome',help='Optional JSON file with an archived genome')
    ap.add_argument('--pitches',default='1.25,0.625,0.3125,0.15625',help='Comma-separated pitch values in mm')
    ap.add_argument('--force',type=float,default=.1,help='Vertical load magnitude [N]')
    ap.add_argument('--max-cells',type=int,default=800000)
    ap.add_argument('--memory-mb',type=int,default=3072)
    ap.add_argument('--cg-maxiter',type=int,default=5000)
    ap.add_argument('--cg-rtol',type=float,default=5e-5)
    ap.add_argument('--cg-timeout',type=float,default=180.)
    ap.add_argument('--out',default='mesh_study')
    args=ap.parse_args(argv)
    if args.force<=0:ap.error('--force must be >0')
    try:pitches=[float(x.strip()) for x in args.pitches.split(',')]
    except ValueError:ap.error('--pitches requires comma-separated positive numbers')
    if len(pitches)<2 or any(not (.12<=v<=2.5) for v in pitches):ap.error('At least two pitches in 0.12..2.5 mm are required')
    g=json.loads(Path(args.genome).read_text()) if args.genome else new_genome(args.family,random.Random(args.seed))
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows=run_study(args.family,g,pitches,max_cells=args.max_cells,memory_mb=args.memory_mb,
                   cg_maxiter=args.cg_maxiter,cg_rtol=args.cg_rtol,cg_timeout=args.cg_timeout,force_n=args.force)
    (out/'study.json').write_text(json.dumps(dict(genome=g,pitches=pitches,rows=rows,
                  limitations='Voxel-geometry and element-size changes are coupled; more elements do not prove physical accuracy.'),indent=2,allow_nan=False))
    columns=sorted({k for row in rows for k in row})
    with (out/'study.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        passed=[x for x in rows if x['status']=='solved']
        fig,ax=plt.subplots(figsize=(7.8,4.8))
        ax.plot([r['pitch_mm'] for r in passed],[r['deflection_mm'] for r in passed],'-o')
        ax.invert_xaxis();ax.set_xlabel('HEX8 mesh pitch [mm] (smaller = finer)')
        ax.set_ylabel('Computed downward deflection [mm]')
        ax.set_title('NeuroSkin 3D FEM: mesh-resolution comparison')
        ax.grid(True,alpha=.25)
        fig.tight_layout();fig.savefig(out/'study.png',dpi=160);plt.close(fig)
    except ImportError:pass
    print(f'Results in: {out.resolve()}')
    return 0 if all(row['status']=='solved' for row in rows) else 2

if __name__=='__main__':raise SystemExit(main())
