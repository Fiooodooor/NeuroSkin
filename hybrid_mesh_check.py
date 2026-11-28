"""Reproducible pitch-sensitivity checks for hybrid sensor structures.

No mesh-convergence claim is made unless the requested pitches satisfy the
explicit displacement-change tolerance and all physical screens. This does not
supersede a nonlinear material/contact or experimental validation study.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from hybrid_library import BY_ID,genome_for
from physical_fem import fem_sweep


def check(codes=('h01_serpentine_quadrant','h10_dual_chiral'),
          pitches=(1.25,.625),out='hybrid_mesh_check_v20', tolerance=.10):
    outdir=Path(out);outdir.mkdir(exist_ok=True,parents=True)
    rows=[]
    for name in codes:
        spec=BY_ID[name]
        g=genome_for(spec)
        history=[]
        for pitch in pitches:
            try:
                report=fem_sweep(spec.upper_family,g,pitch_mm=float(pitch),backend='hex8',include_fields=False)
                shell=report.get('laminate_shell') or {}
                value=float(report['load_cases']['press_center']['mean_down_mm'])
                rec=dict(hybrid_id=spec.id,pitch_mm=float(pitch),elements=report['elements'],
                         centre_down_mm=value,voxel_inflated_flexures=report['inflated_features'],
                         fem_feasible=bool(report['feasible_linear']),
                         shell_feasible=bool(shell.get('feasible_shell_screen',False)),
                         shell_max_stress_MPa=shell.get('max_eq_stress_MPa'),
                         shell_max_shear_MPa=shell.get('max_interfacial_shear_MPa'),
                         force_balance_relative=report['force_equilibrium_max'],
                         moment_balance_relative=report['moment_equilibrium_max'],
                         relative_deflection_change_vs_previous=None,
                         mesh_converged_to_previous=False,solver_error='')
                if history and 'centre_down_mm' in history[-1]:
                    prev=history[-1]['centre_down_mm']
                    ratio=abs(value-prev)/max(abs(value),1e-12)
                    rec['relative_deflection_change_vs_previous']=ratio
                    rec['mesh_converged_to_previous']=bool(
                        ratio<=tolerance and rec['fem_feasible'] and rec['shell_feasible']
                        and history[-1]['fem_feasible'] and history[-1]['shell_feasible'])
            except (ValueError,RuntimeError,MemoryError) as exc:
                rec=dict(hybrid_id=spec.id,pitch_mm=float(pitch),elements=None,centre_down_mm=None,
                         voxel_inflated_flexures=None,fem_feasible=False,shell_feasible=False,
                         shell_max_stress_MPa=None,shell_max_shear_MPa=None,
                         force_balance_relative=None,moment_balance_relative=None,
                         relative_deflection_change_vs_previous=None,
                         mesh_converged_to_previous=False,solver_error=f'{type(exc).__name__}: {exc}')
            rows.append(rec);history.append(rec)
            print(name, pitch, rec['elements'], rec['centre_down_mm'], 'mesh converged', rec['mesh_converged_to_previous'])
    with (outdir/'check.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    payload={'protocol':'v2.0_3D_hex8_pitch_sensitivity','acceptance_relative_deflection_change':tolerance,
             'note':'Voxel HEX8 thickness inflation is pitch dependent; 2 meshes alone cannot certify asymptotic convergence.',
             'records':rows}
    (outdir/'check.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    return payload


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--models',default='h01_serpentine_quadrant,h10_dual_chiral')
    parser.add_argument('--pitches',default='1.25,0.625')
    parser.add_argument('--tolerance',type=float,default=.10)
    parser.add_argument('--out',default='hybrid_mesh_check_v20')
    args=parser.parse_args()
    codes=args.models.split(',')
    if any(c not in BY_ID for c in codes):parser.error('Unknown hybrid architecture')
    check(codes,tuple(float(t) for t in args.pitches.split(',')),args.out,args.tolerance)
