"""Reproducible FEM + Top-3 protocol screening of the 10 two-stage architectures.

Outputs are MODEL outputs from synthetic electrical tests and linear HEX8;
never measured performance or an experimentally validated ranking.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import random
import time
import numpy as np

from hybrid_library import ranked, genome_for
from advanced import audit_job, detail_mesh, structural_struts


def run(pitch=1.25, audit_grid=3, output='artifacts/hybrid_validation', export_stl=True):
    folder=Path(output);folder.mkdir(parents=True,exist_ok=True)
    models=folder/'genomes';models.mkdir(exist_ok=True)
    if export_stl:(folder/'stl').mkdir(exist_ok=True)
    records=[]
    for rank,spec in enumerate(ranked(),1):
        genome=genome_for(spec, random.Random(1701))
        (models/f'{spec.id}.json').write_text(json.dumps(genome,indent=2),encoding='utf-8')
        tic=time.monotonic()
        audit=audit_job((spec.upper_family,genome,'balanced',audit_grid,True,pitch,'hex8'))
        fem=audit.get('fem') or {}
        stage=fem.get('hybrid_stages') or {}
        film=(fem.get('laminate_shell') or {})
        rec={'rank_prior':rank,'id':spec.id,'name':spec.name,
             'family':spec.upper_family,'expert_prior_100':sum(spec.scores),
             'audit_score_100':audit.get('audit_score'),
             'audit_feasible':audit.get('feasible'),
             'fast_screen_feasible':audit.get('audited_surrogate_feasible'),
             'fem_score_100':fem.get('fem_score'),
             'fem_feasible_linear':fem.get('feasible_linear'),
             'fem_elements':fem.get('elements'),
             'fem_inflated_members':fem.get('inflated_features'),
             'pressure_uniformity':fem.get('pressure_uniformity'),
             'force_equilibrium_error':fem.get('force_equilibrium_max'),
             'shell_score_100':film.get('shell_score'),
             'shell_max_stress_MPa':film.get('max_eq_stress_MPa'),
             'shell_max_shear_MPa':film.get('max_interfacial_shear_MPa'),
             'hybrid_lower_compression_mm':stage.get('lower_compression_mm'),
             'hybrid_upper_compression_mm':stage.get('upper_compression_mm'),
             'hybrid_lower_share':stage.get('lower_compression_share'),
             'hybrid_response_rank':stage.get('stage_response_rank_max3'),
             'hybrid_response_condition':stage.get('stage_response_condition'),
             'hybrid_mode_score':stage.get('mode_separation_score_0_100'),
             'runtime_seconds':round(time.monotonic()-tic,3),
             'fem_error':fem.get('error',''),
             'warnings':fem.get('mesh_warning','')}
        records.append(rec)
        (folder/f'{spec.id}_audit.json').write_text(json.dumps(audit,indent=2,default=str),encoding='utf-8')
        if export_stl:
            import trimesh
            parts=detail_mesh(spec.upper_family,genome,quality=12)
            trimesh.util.concatenate(list(parts.values())).export(str(folder/'stl'/f'{spec.id}_CONCEPT_NOT_PRINT_READY.stl'))
        print(f"{rank:02d} {spec.id}: prior={rec['expert_prior_100']} audit={rec['audit_score_100']} "
              f"gate={rec['audit_feasible']} hex={rec['fem_feasible_linear']} elements={rec['fem_elements']}")
    cols=list(records[0]);path=folder/'comparison.csv'
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader();writer.writerows(records)
    (folder/'comparison.json').write_text(json.dumps({'protocol':{'version':'2.0-hybrid-audit',
      'pitch_mm':pitch,'audit_grid':audit_grid,'force_levels_N':[.025,.1,.4],
      'measurements':'linear HEX8 + surrogate electrical + assumed PVDF, not experimentally calibrated'},
      'results':records},indent=2),encoding='utf-8')
    return records


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--pitch',type=float,default=1.25)
    ap.add_argument('--grid',type=int,default=3,choices=[3,5,7])
    ap.add_argument('--out',default='artifacts/hybrid_validation')
    ap.add_argument('--no-stl',action='store_true')
    args=ap.parse_args()
    run(args.pitch,args.grid,args.out,not args.no_stl)
