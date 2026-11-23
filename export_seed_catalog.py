"""Export all 20 morphologies as inspectable, conceptual multi-part STL assemblies.

The exported STL contains component intersections and is NOT print-ready.
A coarse HEX8 smoke test is included separately, not interpreted as ranking.
"""
import argparse
import csv
import json
import random
from pathlib import Path
import numpy as np
import trimesh
from advanced import detail_mesh,structural_struts
from seed_library import SEEDS,CRITERIA,seed_genome,top_candidates,serialized_library
from physical_fem import voxel_mesh,HexElasticSolver,FEMConfig

def main():
    a=argparse.ArgumentParser();a.add_argument('--out',default='seed_models_v16');a.add_argument('--quality',type=int,default=14)
    a.add_argument('--skip-fem',action='store_true');args=a.parse_args()
    dst=Path(args.out);dst.mkdir(parents=True,exist_ok=True)
    metas=[];rankids={s.id for s in top_candidates()}
    for spec in SEEDS:
        g=seed_genome(spec,random.Random(10007),mutate=False)
        meshes=detail_mesh(spec.family,g,quality=args.quality)
        for group,mesh in meshes.items():
            if not np.isfinite(mesh.vertices).all():raise RuntimeError(f'Nonfinite mesh: {spec.id}/{group}')
        result={'id':spec.id,'name':spec.title,'origin':spec.category,'family':spec.family,
                'expert_prior_score':sum(spec.scores),'selected_top10':spec.id in rankids,
                'source':spec.source_url,'limitations':'Overlapping visual solids, not a watertight fused print-ready material assembly'}
        mesh=trimesh.util.concatenate(list(meshes.values()))
        file=dst/(spec.id+'.stl');file.write_bytes(mesh.export(file_type='stl'))
        (dst/(spec.id+'.json')).write_text(json.dumps({'genome':g,'model':result},indent=2),encoding='utf8')
        result.update({'stl':file.name,'triangles':int(len(mesh.faces)),'components':list(meshes)})
        if not args.skip_fem:
            try:
                v=voxel_mesh(spec.family,g,FEMConfig(pitch_mm=1.25))
                f=HexElasticSolver(v,g['material_E']).solve(force=(0,0,-.1))
                result['coarse_hex8']={'voxels':v.voxels,'mean_down_mm':float(f['mean_down_mm']),
                                       'max_von_mises_MPa':float(f['max_von_mises_MPa']),
                                       'strain_max_assumed':float(f['max_abs_principal_strain']),
                                       'force_equilibrium_relative':float(f['force_equilibrium_relative']),
                                       'mesh_warning':v.geometry_warning,
                                       'interpretation':'COARSE numerical smoke test only; no FEM convergence claim.'}
            except Exception as exc:result['coarse_hex8']={'failed':str(exc)}
        metas.append(result)
        print(spec.id,result['triangles'],'triangles',flush=True)
    (dst/'manifest.json').write_text(json.dumps({'catalog':serialized_library(),'models':metas},indent=2),encoding='utf8')
    with (dst/'scores_20x10.csv').open('w',encoding='utf8',newline='') as file:
        wr=csv.writer(file);wr.writerow(['id','name','origin','family']+[k for k,_ in CRITERIA]+['total','selected_top10','source_url'])
        for s in sorted(SEEDS,key=lambda x:(-sum(x.scores),x.id)):
            wr.writerow([s.id,s.title,s.category,s.family,*s.scores,sum(s.scores),s.id in rankids,s.source_url])
    return dst
if __name__=='__main__':main()
