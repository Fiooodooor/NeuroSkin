"""NeuroSkin v0.7 local evolutionary design laboratory."""
from pathlib import Path
import os
for _v in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
 os.environ[_v]='1'
import argparse, csv, io, json, threading, webbrowser, zipfile, time, secrets, random
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import trimesh
import numpy as np
from advanced import EvolutionV5, webmesh, detail_mesh, structural_struts
from electromechanics import examine, sweep, CASES
from optimization import PRESETS
from spatial_validation import spatial_pressure_test
from archive_store import ArchiveStore, ArchiveError

ROOT=Path(__file__).resolve().parent
EVO=EvolutionV5(ROOT/'runs_v05')
ARCHIVES=ArchiveStore(EVO.folder)
app=FastAPI(title='NeuroSkin Evolution Lab',version='1.6')
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')

class Start(BaseModel):
 mode:str='all'
 seconds:float=Field(default=60,ge=3,le=3600)
 population:int=Field(default=48,ge=12,le=256)
 seed:int|None=None
 exploration:float=Field(default=.55,ge=0,le=1)
 objective:str="balanced"
 physical_gate:bool=False
 gate_grid:int=Field(default=3,ge=3,le=7)
 cores:int|None=Field(default=None,ge=1,le=256)
 audit_grid:int=Field(default=5,ge=3,le=7)
 fem_enabled:bool=True
 fem_backend:str='hex8'
 fem_pitch_mm:float=Field(default=.3125,ge=.12,le=2.)

@app.get('/')
def index():return FileResponse(ROOT/'static'/'index.html')
def available_cores():
 # Linux affinity reflects CPUs available to this process; os.cpu_count() can overestimate.
 try:
  return len(os.sched_getaffinity(0))
 except (AttributeError, OSError):
  return os.cpu_count() or 1

@app.get('/api/system')
def system_info():
 available=available_cores()
 from hardware_profile import profile
 hw=profile()
 return {'hardware':hw,'logical_cores':available,'physical_host_logical_cores':os.cpu_count() or 1,
         'default_cores':min(getattr(app.state,'default_cores',1),available),
         'population_max':256,
         'note':'CPU utilization depends on workload; very large worker pools may incur memory and startup overhead.'}
@app.get('/api/seed_library')
def seed_library():
 from seed_library import serialized_library
 return serialized_library()

@app.get('/api/seeds/{seed_id}')
def get_seed_candidate(seed_id:str):
 c=select_candidate('seed',seed_id,'crown')
 if c is None:raise HTTPException(404,'Seed model not found')
 return c

@app.get('/api/archives')
def archive_list(limit:int=100):
 try:return {'runs':ARCHIVES.list_runs(limit)}
 except ArchiveError as exc:raise HTTPException(422,str(exc))

@app.get('/api/archives/compare')
def archive_compare(left:str,right:str):
 try:
  first=ARCHIVES.load(left);second=ARCHIVES.load(right)
 except FileNotFoundError:raise HTTPException(404,'One or both runs not found')
 except (ArchiveError,OSError,ValueError) as exc:raise HTTPException(422,str(exc))
 def summary(state):
  champ=state.get('audited_champion') or state.get('best') or {}
  audit=champ.get('audit') or {}
  provenance=state.get('provenance') or {}
  return {'id':state['id'],'objective':state.get('objective'),
          'audit_grid':state.get('audit_grid'),'source_hash':provenance.get('sha256'),
          'audited_score':audit.get('audit_score'),'audited_feasible':audit.get('feasible'),
          'family':champ.get('family'),'champion_id':champ.get('id'),
          'evaluated':state.get('evaluated'),'generation':state.get('generation')}
 l,r=summary(first),summary(second)
 same_version=bool(l['source_hash']) and l['source_hash']==r['source_hash']
 comparable=same_version and l['objective']==r['objective'] and l['audit_grid']==r['audit_grid']
 delta=(round(float(r['audited_score'])-float(l['audited_score']),5) if comparable and
        l['audited_score'] is not None and r['audited_score'] is not None else None)
 return {'left':l,'right':r,'comparable':comparable,'score_delta_right_minus_left':delta,
         'warning':None if comparable else
         'Scores are NOT comparable: source hash, objective or audit protocol differs or is unknown.'}

@app.get('/api/archives/{run_id}')
def archive_load(run_id:str):
 try:return ARCHIVES.load(run_id)
 except FileNotFoundError:raise HTTPException(404,'Saved run not found')
 except (ArchiveError, OSError, ValueError) as exc:raise HTTPException(422,str(exc))

@app.get('/api/archives/{run_id}/stages')
def archive_stages(run_id:str):
 try:
  ARCHIVES.load(run_id)
  return {'stages':ARCHIVES.list_stages(run_id)}
 except FileNotFoundError:raise HTTPException(404,'Saved run not found')
 except (ArchiveError,OSError,ValueError) as exc:raise HTTPException(422,str(exc))

@app.get('/api/archives/{run_id}/stages/{generation}')
def archive_stage(run_id:str,generation:int):
 try:return ARCHIVES.load_stage(run_id,generation)
 except FileNotFoundError:raise HTTPException(404,'Saved stage not found')
 except (ArchiveError,OSError,ValueError) as exc:raise HTTPException(422,str(exc))

@app.get('/api/archives/{run_id}/download')
def archive_download(run_id:str):
 try:
  ARCHIVES.load(run_id)
  folder=ARCHIVES.path(run_id)
 except FileNotFoundError:raise HTTPException(404,'Saved run not found')
 except (ArchiveError, OSError, ValueError) as exc:raise HTTPException(422,str(exc))
 selected=('results.json','history.csv','audit_history.csv','stage_decisions.json',
           'champion_full_audit.json','champion_CONCEPT_NOT_PRINT_READY.stl',
           'crown_concept.stl','chiral_concept.stl','quadrant_concept.stl')
 file=io.BytesIO()
 with zipfile.ZipFile(file,'w',zipfile.ZIP_DEFLATED) as z:
  for name in selected:
   source=folder/name
   if source.is_file() and not source.is_symlink():
    z.write(source,arcname=name)
  stage_dir=folder/'stages'
  if stage_dir.is_dir():
   for stage in sorted(stage_dir.glob('stage_*.json')):
    if stage.is_file() and not stage.is_symlink():z.write(stage,arcname='stages/'+stage.name)
 return Response(file.getvalue(),media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="neuroskin_run_{run_id}.zip"'})

def select_candidate(kind:str,index:str,family:str,run_id:str|None=None,generation:int|None=None):
 if kind=='seed' and not run_id:
  from seed_library import SEEDS, seed_genome
  from advanced import proxy
  spec=next((x for x in SEEDS if x.id==str(index)),None)
  if spec is None:return None
  g=seed_genome(spec,random.Random(10007),mutate=False)
  score,met,_=proxy(spec.family,g)
  return {'id':'seed-'+spec.id,'family':spec.family,'genome':g,'metrics':met,
          'fitness':float(score),'generation':0,'novelty':0.,'origin':spec.category,
          'expert_prior_score':sum(spec.scores)}
 if not run_id:
  return EVO.lookup(kind,int(index) if kind=='gallery' and index.isdigit() else index,family)
 try:
  archived=ARCHIVES.load(run_id)
  if generation is not None:
   stage=ARCHIVES.load_stage(run_id,generation)
   stage_view={'best':stage.get('champion'),'audited_champion':stage.get('champion'),
               'audit_top3':stage.get('top3',[]),'gallery':stage.get('top3',[])}
   return ARCHIVES.lookup(stage_view,kind,index,family)
  return ARCHIVES.lookup(archived,kind,index,family)
 except (FileNotFoundError,ArchiveError,ValueError) as exc:
  raise HTTPException(404,f'Archived run unavailable: {exc}')

@app.get('/api/state')
def state():return EVO.snapshot()
@app.post('/api/start')
def start(req:Start):
 try:return EVO.start(req.mode,req.seconds,req.seed if req.seed is not None else secrets.randbits(31),req.population,req.exploration,req.objective,req.physical_gate,req.gate_grid,req.cores or getattr(app.state,'default_cores',1),req.audit_grid,req.fem_enabled,req.fem_pitch_mm,req.fem_backend)
 except (ValueError,RuntimeError) as e:raise HTTPException(409,str(e))
@app.get('/api/audit')
def audit_state():
 s=EVO.snapshot()
 return {'phase':s.get('phase'),'top3':s.get('audit_top3',[]),
         'champion':s.get('audited_champion'),
         'history':s.get('audit_history',[]),
         'decisions':s.get('stage_decisions',[]),
         'disclaimer':'FEM audit values are linear space-frame beam or linear voxel solid equilibrium results. Electrical and other outputs remain synthetic; no hardware or nonlinear contact qualification.'}

@app.get('/api/audit/report')
def audit_report():
 s=EVO.snapshot();c=s.get('audited_champion')
 if not c:raise HTTPException(404,'No fully audited champion yet')
 return Response(json.dumps({'run_id':s['id'],'champion':c,'history':s.get('audit_history',[]),
   'decisions':s.get('stage_decisions',[])},indent=2),media_type='application/json',
   headers={'Content-Disposition':'attachment; filename="neuroskin_full_evaluation.json"'})

@app.post('/api/pause')
def pause():return EVO.pause()
@app.post('/api/stop')
def stop():return EVO.stop()

def _preview_genome(candidate, piezo_count_override:int|None, piezo_wiring_override:int|None=None):
 # An override creates only a transient preview/configuration. Stored genotypes,
 # archived results and previous fitness scores remain immutable.
 genome=dict(candidate['genome'])
 if piezo_count_override is not None:
  if piezo_count_override not in (1,2,3,4,6,8):
   raise HTTPException(422,'PVDF layout must be 1, 2, 3, 4, 6 or 8 films (subject to available legs)')
  available_primary=sum(tag=='leg' for _,_,tag in structural_struts(candidate['family'],genome))
  if piezo_count_override>available_primary:
   raise HTTPException(422,f'{piezo_count_override} films requested but only {available_primary} primary structural members are available')
  genome['piezo_count']=piezo_count_override
 if piezo_wiring_override is not None:
  if piezo_wiring_override not in (0,1,2,3,4):
   raise HTTPException(422,'PVDF wiring override must be 0..4')
  genome['piezo_wiring']=piezo_wiring_override
 return genome

@app.get('/api/mesh')
def mesh(kind:str='best',index:str="0",family:str='crown',quality:int=10,run_id:str|None=None,generation:int|None=None,piezo_count_override:int|None=None,piezo_wiring_override:int|None=None):
 if quality<5 or quality>20:raise HTTPException(400,'Quality must be 5..20')
 candidate=select_candidate(kind,index,family,run_id,generation)
 if candidate is None:raise HTTPException(404,'Candidate not found')
 g=_preview_genome(candidate,piezo_count_override,piezo_wiring_override)
 from pvdf_array import choose_film_members,layout_metrics
 layout=layout_metrics(structural_struts(candidate['family'],g),g)
 return {'candidate':{k:v for k,v in candidate.items() if k not in ('genome','metrics')},
         'model':webmesh(candidate['family'],g,quality),
         'pvdf_layout':layout,'pvdf_preview_override':piezo_count_override is not None,
         'pvdf_warning':'Preview override is not saved and does not update archived scores. Re-run Evaluate All for the modified configuration; bonded PVDF reinforcement is modeled approximately in FEM.',
         'strut_paths':[pts.round(4).tolist() for pts,_,_ in structural_struts(candidate['family'],g)]}

class Characterize(BaseModel):
 selection:str='best'
 index:str='0'
 family:str='crown'
 case:str='normal'
 fraction:float=Field(default=1.,ge=0,le=2.)
 frequency_hz:float=Field(default=25.,ge=.01,le=1000.)
 piezo_count_override:int|None=None
 piezo_wiring_override:int|None=None
 run_id:str|None=None
 generation:int|None=None


class FEMRequest(BaseModel):
 piezo_count_override:int|None=None
 piezo_wiring_override:int|None=None
 compute_device:str='cpu'
 selection:str='best'
 index:str='0'
 family:str='crown'
 run_id:str|None=None
 generation:int|None=None
 pitch_mm:float=Field(default=.3125,ge=.12,le=2.)
 backend:str='hex8'
 case:str='press_center'
 offset_x_mm:float=Field(default=0.,ge=-2,le=2)
 offset_y_mm:float=Field(default=0.,ge=-2,le=2)
 load_n:float=Field(default=.1,gt=0,le=.5)

@app.post('/api/fem/simulate')
def simulate_fem(req:FEMRequest):
 """Actual continuum HEX8 solution; browser receives the solver's FE surface nodes."""
 c=select_candidate(req.selection,req.index,req.family,req.run_id,req.generation)
 if c is None:raise HTTPException(404,'Candidate not found')
 from physical_fem import voxel_mesh, HexElasticSolver, FEMConfig, _serialize_mesh_fields, InvalidGeometry
 family,g=c['family'],_preview_genome(c,req.piezo_count_override,req.piezo_wiring_override)
 cfg=FEMConfig(pitch_mm=req.pitch_mm,young_MPa=float(g.get('material_E',1.)))
 try:
  if req.compute_device not in ('cpu','gpu','auto'):
   raise ValueError('Compute device must be cpu, gpu or auto')
  if req.backend not in ('auto','beam','hex8'):
   raise HTTPException(400,'Backend must be auto, beam or hex8')
  beam_selected=req.backend=='beam' or (req.backend=='auto' and req.pitch_mm<.7)
  if beam_selected and req.compute_device=='gpu':
   raise ValueError('GPU mode only supports small solid HEX8 CSR meshes')
  if beam_selected:
   from beam_fem import BeamFEM
   s=BeamFEM(family,g,pitch_mm=req.pitch_mm)
   m=None
  else:
   m=voxel_mesh(family,g,cfg);s=HexElasticSolver(m,cfg.young_MPa,cfg.poisson,compute_device=req.compute_device,family=family,genome=g)
  if req.case not in ('press_center','press_offset','shear_x','shear_y','torsion_z'):
   raise ValueError('Unsupported FEM case')
  off=(req.offset_x_mm,req.offset_y_mm) if req.case=='press_offset' else (0.,0.)
  v={'press_center':(0.,0.,-req.load_n),
     'press_offset':(0.,0.,-req.load_n),
     'shear_x':(req.load_n*.3,0.,-req.load_n*.4),
     'shear_y':(0.,req.load_n*.3,-req.load_n*.4),
     'torsion_z':(0.,0.,-req.load_n*.4)}[req.case]
  r=s.solve(force=v,offset=off,torque_z_Nmm=.02*(req.load_n/.1) if req.case=='torsion_z' else 0.,**({'include_fields':True} if beam_selected else {}))
  fields=r['fields'] if beam_selected else _serialize_mesh_fields(m,r)
  metrics={k:v for k,v in r.items() if k not in ('displacement','element_strain','element_stress','von_mises_MPa','principal_strain','fields')}
  return {'candidate_id':c['id'],'family':family,'genome':g,
          'backend':('actual_3d_linear_space_frame_beam' if beam_selected else 'actual_3d_hex8_linear'),
          'solver_mode':('space_frame_beam' if beam_selected else s.solver_mode),
          'compute_device':('cpu' if beam_selected else s.compute_device),
          'cg_iterations':(0 if beam_selected else r['cg_iterations']),
          'mesh':fields,'metrics':metrics,'elements':(s.n_elements if beam_selected else m.voxels),
          'nodes':(s.n_nodes if beam_selected else len(m.nodes)),
          'volume_mm3':(None if beam_selected else m.volume_mm3),'setup_s':s.setup_s,'pitch_mm':req.pitch_mm,
          'pvdf_stiffness_included':bool(r.get('pvdf_stiffness_included',False)),
          'pvdf_adhesive_model':r.get('pvdf_adhesive_model','none'),
          'pvdf_response':r.get('pvdf_laminate_response'),
          'historical_fitness_invalidated':bool(req.piezo_count_override is not None or req.piezo_wiring_override is not None),
          'meshing_warning':('Beam cross-sections modeled analytically; pitch controls axial element length. No voxel inflation.' if beam_selected else m.geometry_warning),
          'limitations':('Euler-Bernoulli space-frame with approximate bonded-film stiffening; not continuum shell, no true contact/hyperelasticity/piezoelectric fields.' if beam_selected else 'Small strain isotropic SOLID HEX8 plus bonded PVDF membrane with assumed adhesive shear-lag; voxel substrate, no full layered shell, peel, contact, hyperelasticity or coupled electrode fields.')}
 except (InvalidGeometry,ValueError,RuntimeError,MemoryError) as exc:
  raise HTTPException(422, f'FEM geometry/solver rejected candidate: {exc}')

class EvaluateAllRequest(BaseModel):
 fem_inspection_case:str='press_center'
 fem_inspection_force_n:float=Field(default=.1,gt=0,le=.5)
 fem_inspection_offset_x:float=Field(default=0.,ge=-2,le=2)
 fem_inspection_offset_y:float=Field(default=0.,ge=-2,le=2)
 fem_compute_device:str='cpu'
 selection:str='best'
 index:str='0'
 family:str='crown'
 run_id:str|None=None
 generation:int|None=None
 piezo_count_override:int|None=None
 piezo_wiring_override:int|None=None
 audit_grid:int=Field(default=5,ge=3,le=7)
 fem_pitch_mm:float=Field(default=.625,ge=.12,le=2.)
 fem_backend:str='hex8'
 fem_enabled:bool=True
 objective:str='balanced'

@app.post('/api/evaluate_all')
def evaluate_all(req:EvaluateAllRequest):
 """Unified characterization, spatial scan, dynamic PVDF, inverse tests,
 material-recovery screening, and optional 3D/beam mechanical FEM.
 As with the evolutionary audit, electronic channels remain synthetic.
 """
 from full_evaluation import audit_candidate
 from recovery_sim import recovery_for_candidate
 candidate=select_candidate(req.selection,req.index,req.family,req.run_id,req.generation)
 if candidate is None:raise HTTPException(404,'Candidate not found')
 g=_preview_genome(candidate,req.piezo_count_override,req.piezo_wiring_override)
 try:
  audit=audit_candidate(candidate['family'],g,req.objective,req.audit_grid)
  fem=None
  if req.fem_enabled:
   from physical_fem import fem_sweep
   try:
    fem=fem_sweep(candidate['family'],g,pitch_mm=req.fem_pitch_mm,backend=req.fem_backend,include_fields=True,
                  inspector_case=req.fem_inspection_case,inspector_force_N=req.fem_inspection_force_n,
                  inspector_offset=(req.fem_inspection_offset_x,req.fem_inspection_offset_y),compute_device=req.fem_compute_device)
    audit['fem']=dict(fem,fields=None)
    audit['audited_surrogate_score']=audit['audit_score']
    audit['audit_score']=round(.4*audit['audit_score_before_feasibility_band']+.6*fem['fem_score'],5)
    audit['feasible']=bool(audit['feasible'] and fem['feasible_linear'])
    bas=fem.get('load_cases',{}).get('press_center',{})
    if bas.get('mean_down_mm') is not None:
     recovery=recovery_for_candidate(candidate['family'],g,
                  fem_max_strain=fem.get('max_abs_principal_strain'),
                  fem_displacement_mm=bas['mean_down_mm'])
     audit['unloading_recovery']=recovery
     audit['audit_score']=round(.93*audit['audit_score']+.07*recovery['recovery_score_0_100_assumed'],5)
     audit['feasible']=bool(audit['feasible'] and recovery['strain_screen_passed'])
    shell=fem.get('laminate_shell') if fem else None
    if isinstance(shell,dict) and not shell.get('failed'):
     audit['laminate_shell']=shell
     audit['audit_score']=round(.88*audit['audit_score']+.12*shell['shell_score'],5)
     audit['feasible']=bool(audit['feasible'] and shell['feasible_shell_screen'])
     audit.setdefault('decision_basis',{})['laminate_shell_score']=float(shell['shell_score'])
     audit['decision_basis']['laminate_shell_feasible']=bool(shell['feasible_shell_screen'])
     audit['decision_basis']['laminate_shell_max_eq_stress_MPa']=float(shell['max_eq_stress_MPa'])
     audit['decision_basis']['laminate_shell_max_interfacial_shear_MPa']=float(shell['max_interfacial_shear_MPa'])
     audit['decision_basis']['laminate_shell_max_top_strain_abs']=float(shell['max_top_fiber_strain_abs'])
   except (ValueError,RuntimeError,MemoryError) as exc:
    audit['fem']={'failed':True,'message':str(exc)}
    audit['feasible']=False
    audit['audit_score']=0
   shell=fem.get('laminate_shell') if isinstance(fem,dict) else None
   if req.fem_backend=='hex8' and (not isinstance(shell,dict) or shell.get('failed')):
    audit['feasible']=False
    audit.setdefault('screening_failure_reasons',[]).append('laminate_shell_stage_missing_or_failed')
  from selection_refinement import enforce_score_band
  enforce_score_band(audit)
  return {'candidate_id':candidate['id'],'family':candidate['family'],
          'audit':audit,'fem':fem,'recovery':audit['unloading_recovery'],
          'historical_fitness_invalidated':bool(req.piezo_count_override is not None or req.piezo_wiring_override is not None),
          'warning':'Linear mechanics with approximate bonded PVDF/adhesive reinforcement (HEX8 or beam); assumed SLS recovery, synthetic electronics, uncalibrated PVDF and fatigue. FEM may not be converged.'}
 except (ValueError,RuntimeError,MemoryError,np.linalg.LinAlgError) as exc:
  raise HTTPException(422,f'Full evaluation failed: {exc}')

@app.get('/api/physics_info')
def physics_info():return {'cases':{k:v[0] for k,v in CASES.items()},'objective_presets':PRESETS,'note':'Electrical and mechanics results are synthetic surrogate predictions, not FEM/experimental validation.'}

@app.post('/api/characterize')
def characterize(req:Characterize):
 c=select_candidate(req.selection,req.index,req.family,req.run_id,req.generation)
 if c is None:raise HTTPException(404,'Candidate not found')
 if req.case not in CASES:raise HTTPException(400,'Unknown case')
 g=_preview_genome(c,req.piezo_count_override,req.piezo_wiring_override)
 _,F,mz,off,mx=CASES[req.case]
 if req.case=='stretch_x': r=examine(c['family'],g,req.case,strain=.05*req.fraction,frequency_hz=req.frequency_hz)
 elif req.case=='compression':r=examine(c['family'],g,req.case,strain=-.05*req.fraction,frequency_hz=req.frequency_hz)
 else:r=examine(c['family'],g,req.case,force=[x*req.fraction for x in F],moment=[mx*req.fraction,0,mz*req.fraction],offset=off,frequency_hz=req.frequency_hz)
 return {'candidate_id':c['id'],'family':c['family'],'case':req.case,'fraction':req.fraction,
         'piezo_preview_override':req.piezo_count_override is not None or req.piezo_wiring_override is not None,
         'result':r,'sweep':sweep(c['family'],g,req.case)}

class SpatialTest(BaseModel):
 selection:str='best'
 index:str='0'
 family:str='crown'
 grid_size:int=Field(default=5)
 force_n:float=Field(default=.1,gt=0,le=10)
 run_id:str|None=None
 generation:int|None=None

@app.post('/api/spatial_pressure')
def spatial_pressure(req:SpatialTest):
 c=select_candidate(req.selection,req.index,req.family,req.run_id,req.generation)
 if c is None:raise HTTPException(404,'Candidate not found')
 try:
  data=spatial_pressure_test(c['family'],c['genome'],force_n=req.force_n,grid_size=req.grid_size)
 except (ValueError,np.linalg.LinAlgError) as exc:
  raise HTTPException(422,str(exc))
 return {'candidate_id':c['id'],'family':c['family'],'spatial':data}

@app.get('/api/export/{kind}')
def export(kind:str, selection:str='best',index:str="0",family:str='crown',run_id:str|None=None,generation:int|None=None,piezo_count_override:int|None=None,piezo_wiring_override:int|None=None):
 s=ARCHIVES.load(run_id) if run_id else EVO.snapshot()
 if kind=='json':return Response(json.dumps(s,indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename="neuroskin_evolution_v07.json"'})
 if kind=='csv':
  buf=io.StringIO();w=csv.DictWriter(buf,['generation','elapsed','best','median','diversity']);w.writeheader();w.writerows(s['history'])
  return Response(buf.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="neuroskin_history_v07.csv"'})
 if kind=='genome':
  c=select_candidate(selection,index,family,run_id,generation)
  if c is None:raise HTTPException(404,'Candidate not found')
  g=_preview_genome(c,piezo_count_override,piezo_wiring_override)
  # Flat genome JSON matches fem_cli.py --genome. The historical score is NOT exported.
  return Response(json.dumps(g,indent=2),media_type='application/json',headers={
      'Content-Disposition':f'attachment; filename="neuroskin_{c["family"]}_genome_pvdf_{g.get("piezo_count",1)}.json"',
      'X-NeuroSkin-Fitness-Invalidated':'true' if piezo_count_override is not None or piezo_wiring_override is not None else 'false'})
 if kind=='stl':
  c=select_candidate(selection,index,family,run_id,generation)
  if c is None:raise HTTPException(404,'Candidate not found')
  components=detail_mesh(c['family'],_preview_genome(c,piezo_count_override,piezo_wiring_override));data=trimesh.util.concatenate(list(components.values())).export(file_type='stl')
  return Response(data,media_type='model/stl',headers={'Content-Disposition':f'attachment; filename="neuroskin_{c["family"]}_{c["id"]}_concept.stl"'})
 raise HTTPException(404,'Unknown export type')

if __name__=='__main__':
 import uvicorn
 a=argparse.ArgumentParser();a.add_argument('--port',type=int,default=8765);a.add_argument('--host',default='127.0.0.1');a.add_argument('--open',action='store_true');a.add_argument('--cores',default='1',help='Process count or auto (hardware-aware) used as default for runs');a.add_argument('--hardware',action='store_true',help='Show CPU/RAM/GPU profile and exit');args=a.parse_args()
 if args.hardware:
  import json as _json
  from hardware_profile import profile
  print(_json.dumps(profile(),indent=2));raise SystemExit(0)
 if args.cores=='auto':
  from hardware_profile import profile
  args.cores=profile()['recommended']['evolution_cores']
 else:
  try:args.cores=int(args.cores)
  except ValueError:a.error('--cores must be an integer or auto')
 if args.cores<1 or args.cores>available_cores():a.error(f'--cores must be 1..{available_cores()} (available CPUs)')
 app.state.default_cores=args.cores
 if args.open:threading.Timer(1.2,lambda:webbrowser.open(f'http://{args.host}:{args.port}')).start()
 uvicorn.run(app,host=args.host,port=args.port,log_level='warning')
