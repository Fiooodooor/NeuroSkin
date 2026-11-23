"""Reproducible solid FEM with VTK and JSON/NPZ outputs; no running GUI needed."""
import argparse, json, random, sys
from pathlib import Path
import numpy as np
from advanced import new_genome
from physical_fem import FEMConfig, voxel_mesh, HexElasticSolver, fem_sweep, InvalidGeometry

def export_vtk(path,mesh,solution):
    """Legacy VTK 3-D unstructured grid. Connectivity uses the solved HEX8 FE topology."""
    pts=mesh.nodes;cell=mesh.elements;U=solution['displacement'];vm=solution['von_mises_MPa']
    with open(path,'w',encoding='utf-8') as f:
        f.write('# vtk DataFile Version 3.0\nNeuroSkin 1.2 real HEX8 FEM\nASCII\nDATASET UNSTRUCTURED_GRID\n')
        f.write(f'POINTS {len(pts)} float\n')
        for xyz in pts:f.write(' '.join(f'{float(v):.8g}' for v in xyz)+'\n')
        f.write(f'CELLS {len(cell)} {len(cell)*9}\n')
        for c in cell:f.write('8 '+' '.join(map(str,c))+'\n')
        f.write(f'CELL_TYPES {len(cell)}\n');f.write('12\n'*len(cell))  # VTK_HEXAHEDRON
        f.write(f'POINT_DATA {len(pts)}\nVECTORS displacement_mm float\n')
        for xyz in U:f.write(' '.join(f'{float(v):.8g}' for v in xyz)+'\n')
        f.write(f'CELL_DATA {len(cell)}\nSCALARS von_mises_MPa float 1\nLOOKUP_TABLE default\n')
        for v in vm:f.write(f'{float(v):.8g}\n')

def export_beam_vtk(path, fem):
    """VTK centerline cells and true beam FEM nodal translations; no fabricated solid elements."""
    pts=[];u=[];stress=[];lines=[]
    for part in fem.parts:
        start=len(pts)
        pts.extend(part.nodes.tolist())
        u.extend(part.displacement[:,:3].tolist())
        stress.extend(part.stress.tolist())
        lines.extend((start+i,start+i+1) for i in range(len(part.nodes)-1))
    with open(path,'w',encoding='utf-8') as f:
        f.write('# vtk DataFile Version 3.0\nNeuroSkin linear space-frame BEAM FEM\nASCII\nDATASET POLYDATA\n')
        f.write(f'POINTS {len(pts)} float\n')
        for v in pts:f.write(' '.join(f'{x:.9g}' for x in v)+'\n')
        f.write(f'LINES {len(lines)} {3*len(lines)}\n')
        for a,b in lines:f.write(f'2 {a} {b}\n')
        f.write(f'POINT_DATA {len(pts)}\nVECTORS displacement_mm float\n')
        for v in u:f.write(' '.join(f'{x:.9g}' for x in v)+'\n')
        f.write('SCALARS beam_stress_vm_MPa float 1\nLOOKUP_TABLE default\n')
        for x in stress:f.write(f'{x:.9g}\n')

def main(argv=None):
    ap=argparse.ArgumentParser(description='Compute linear FEM on NeuroSkin genotype: fine 3D space frame or coarse HEX8 solid')
    ap.add_argument('--family',choices=('crown','chiral','quadrant'),default='quadrant')
    ap.add_argument('--genome',help='Genome JSON file (otherwise seeded procedural genotype)')
    ap.add_argument('--seed',type=int,default=42)
    ap.add_argument('--pitch',type=float,default=.3125,help='HEX8 solid pitch or beam element length [mm]. 0.3125=4x, 0.15625=8x linear refinement vs 1.25 mm.')
    ap.add_argument('--backend',choices=('auto','beam','hex8'),default='hex8',help='hex8: actual volumetric solid FEM (default); beam: fast 3D frame; auto chooses beam below .7 mm')
    ap.add_argument('--max-cells',type=int,default=800000)
    ap.add_argument('--memory-mb',type=int,default=3072)
    ap.add_argument('--cg-maxiter',type=int,default=5000)
    ap.add_argument('--cg-rtol',type=float,default=5e-5)
    ap.add_argument('--cg-timeout',type=float,default=180.)
    ap.add_argument('--force',type=float,default=.1,help='Vertical downward force in N')
    ap.add_argument('--offset-x',type=float,default=0.)
    ap.add_argument('--offset-y',type=float,default=0.)
    ap.add_argument('--compute-device',choices=['cpu','gpu','auto'],default='cpu',
        help='cpu default; gpu opt-in sparse CG on small HEX8 only; auto remains CPU until benchmarked')
    ap.add_argument('--convergence',action='store_true',help='repeat at 0.8x pitch and report sensitivity')
    ap.add_argument('--out',default='fem_results')
    args=ap.parse_args(argv)
    g=json.loads(Path(args.genome).read_text()) if args.genome else new_genome(args.family,random.Random(args.seed))
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    try:
        backend='beam' if args.backend=='beam' or (args.backend=='auto' and args.pitch<.7) else 'hex8'
        if backend=='beam' and args.compute_device=='gpu':
            raise ValueError('GPU backend is only supported for small solid HEX8 CSR meshes; beam FEM runs on CPU')
        if backend=='beam':
            from beam_fem import BeamFEM, BeamFEMError
            beam=BeamFEM(args.family,g,pitch_mm=args.pitch)
            result=beam.solve(force=(0.,0.,-args.force),offset=(args.offset_x,args.offset_y),include_fields=True)
            # Export beam lines with actual FE nodal displacements, NOT a fake solid mesh.
            export_beam_vtk(out/'deformed_beam_FEM.vtk',beam)
            np.savez_compressed(out/'beam_surface_fields.npz',
                vertices_mm=np.asarray(result['fields']['vertices_mm']),
                faces=np.asarray(result['fields']['faces']),
                displacement_mm=np.asarray(result['fields']['displacement_mm']),
                stress_vm_MPa=np.asarray(result['fields']['stress_vm_MPa']))
            summary={k:v for k,v in result.items() if k!='fields'}
            summary.update(family=args.family,genome=g,mesh_pitch_mm=args.pitch,
                mesh_elements=beam.n_elements,mesh_nodes=beam.n_nodes,
                model='linear_3D_Euler_Bernoulli_beam_FEM_not_solid',
                meshing_warning='Axial segment length, not 3D voxel pitch; continuum stress/contact not resolved.')
            if args.convergence:
                fine=BeamFEM(args.family,g,pitch_mm=args.pitch*.5)
                rf=fine.solve(force=(0.,0.,-args.force),offset=(args.offset_x,args.offset_y))
                dc=float(result['mean_down_mm']);df=float(rf['mean_down_mm'])
                summary['convergence']={'coarse_pitch_mm':args.pitch,'fine_pitch_mm':args.pitch*.5,
                    'coarse_deflection_mm':dc,'fine_deflection_mm':df,
                    'relative_deflection_change':abs(df-dc)/max(abs(df),1e-12),
                    'note':'Beam discretization convergence only; no solid continuum convergence claim.'}
        else:
            cfg=FEMConfig(pitch_mm=args.pitch,young_MPa=float(g.get('material_E',1.)),
            max_cells=args.max_cells,max_memory_mb=args.memory_mb,
            cg_maxiter=args.cg_maxiter,cg_rtol=args.cg_rtol,cg_timeout_s=args.cg_timeout)
            mesh=voxel_mesh(args.family,g,cfg)
            solid=HexElasticSolver(mesh,cfg.young_MPa,cfg.poisson,
                 matrixfree_threshold=cfg.matrixfree_threshold,cg_maxiter=cfg.cg_maxiter,
                 cg_rtol=cfg.cg_rtol,cg_timeout_s=cfg.cg_timeout_s,compute_device=args.compute_device)
            result=solid.solve(force=(0.,0.,-args.force),offset=(args.offset_x,args.offset_y))
            export_vtk(out/'deformed_solid_FEM.vtk',mesh,result)
            np.savez_compressed(out/'fields.npz',nodes=mesh.nodes,elements=mesh.elements,
                displacement=result['displacement'],element_strain=result['element_strain'],element_stress=result['element_stress'],
                von_mises=result['von_mises_MPa'],principal_strain=result['principal_strain'])
            summary={k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in result.items()
                if k not in ('displacement','element_strain','element_stress','von_mises_MPa','principal_strain')}
            summary.update(family=args.family,genome=g,mesh_pitch_mm=args.pitch,mesh_cells=mesh.voxels,
            linear_solver=solid.solver_mode,compute_device=solid.compute_device,solver_maxiter=cfg.cg_maxiter,solver_tol=cfg.cg_rtol,
                meshing_warning=mesh.geometry_warning,volumetric_3D_fem=True,model='linear_isotropic_small_strain_HEX8')
            if args.convergence:
                fine=voxel_mesh(args.family,g,FEMConfig(pitch_mm=args.pitch*.8,young_MPa=cfg.young_MPa,
                 max_cells=cfg.max_cells,max_memory_mb=cfg.max_memory_mb))
                s2=HexElasticSolver(fine,cfg.young_MPa,cfg.poisson,
                 matrixfree_threshold=cfg.matrixfree_threshold,cg_maxiter=cfg.cg_maxiter,cg_rtol=cfg.cg_rtol,cg_timeout_s=cfg.cg_timeout_s,compute_device=args.compute_device)
                v2=s2.solve(force=(0.,0.,-args.force),offset=(args.offset_x,args.offset_y))
                coarse_defl=float(result['mean_down_mm']);fine_defl=float(v2['mean_down_mm'])
                change=abs(fine_defl-coarse_defl)/max(abs(fine_defl),1e-12)
                summary['convergence']={'coarse_pitch_mm':args.pitch,'fine_pitch_mm':args.pitch*.8,
                    'coarse_deflection_mm':coarse_defl,'fine_deflection_mm':fine_defl,
                    'relative_deflection_change':change,'screen_pass_under_10pct':bool(change<.1),
                    'note':'Two voxel meshes only; solid convergence remains unproven.'}
        (out/'FEM_report.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
        print(json.dumps({'output':str(out),'backend':backend,'elements':summary.get('mesh_elements',summary.get('mesh_cells')),
                          'displacement_mm':result['mean_down_mm'],
                          'moment_equilibrium_error':result['moment_equilibrium_relative'],
                          'mesh_convergence':summary.get('convergence')},indent=2))
        return 0
    except (InvalidGeometry,ValueError,RuntimeError,MemoryError) as e:
        print(f'INVALID: {e}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
