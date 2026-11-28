"""NeuroSkin 3 local evolutionary design laboratory."""
from pathlib import Path
import os
for _v in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
 os.environ[_v]='1'
import argparse, csv, io, json, threading, webbrowser, zipfile, time, secrets, random, asyncio, logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import trimesh
import numpy as np
from advanced import EvolutionEngine, webmesh, detail_mesh, structural_struts
from electromechanics import examine, sweep, CASES
from optimization import PRESETS
from spatial_validation import spatial_pressure_test
from archive_store import ArchiveStore, ArchiveError

ROOT=Path(__file__).resolve().parent
EVO=EvolutionEngine(ROOT/'runs')
ARCHIVES=ArchiveStore(EVO.folder)
from compute_admission import ComputeAdmission

def evolution_alive():
 thread=getattr(EVO,'thread',None)
 return thread is not None and thread.is_alive()

def compute_capacity():
 from audit_scheduler import available_ram_mb
 return {'cpu':available_cores(),'ram_mb':available_ram_mb(),'default_cores':getattr(app.state,'default_cores',1)}

from hardware_profile import discover_gpu
COMPUTE=ComputeAdmission(evolution_alive,compute_capacity,gpu_probe=discover_gpu)
from resource_telemetry import ProcessTreeSampler
RESOURCE_TELEMETRY=ProcessTreeSampler()
@asynccontextmanager
async def application_lifespan(app):
 try:
  yield
 finally:
  # Stop evolution before Uvicorn tears down background threads.
  if not await asyncio.to_thread(EVO.shutdown,8.0):
   logging.getLogger('neuroskin.shutdown').warning(
    'Evolution still stopping; latest completed stage snapshots remain saved.')

app=FastAPI(title='NeuroSkin Evolution Lab',version=(ROOT/'VERSION').read_text(encoding='utf-8').strip(),lifespan=application_lifespan)
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')

class Start(BaseModel):
 mode:str='all'
 search_strategy:str='adaptive'
 search_precision:float=Field(default=.8,ge=0,le=1)
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
def index():return FileResponse(ROOT/'static'/'index.html',headers={'Cache-Control':'no-cache'})
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

@app.get('/api/search_spaces')
def search_spaces_api():
 from search_space import mode_options, SEARCH_STRATEGIES
 return {'modes':mode_options(),'strategies':[{'id':x,'label':{'adaptive':'Adaptive · global + quality-diversity + local',
      'explore':'Global exploration · broader topology jumps',
      'precision':'Precision · trust-region refinement of elite designs'}[x]} for x in SEARCH_STRATEGIES],
      'default_strategy':'adaptive','default_precision':0.8,
      'note':'All modes share identical FEM, spatial gate, Top-3 and score promotion policy.'}

@app.get('/api/hybrid_library')
def hybrid_library_api():
 from hybrid_library import library_json
 return library_json()

@app.get('/api/hybrids/{hybrid_id}')
def hybrid_candidate_api(hybrid_id: str):
 c=select_candidate('hybrid',hybrid_id,'quadrant')
 if c is None:raise HTTPException(404,'Hybrid not found')
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
          'validation_protocol_hash':(audit.get('validation_v30') or {}).get('protocol_hash'),
          'validation_tier':(audit.get('validation_v30') or {}).get('tier'),
          'validation_noise_source':((audit.get('validation_v30') or {}).get('evidence') or {}).get('noise_provenance'),
          'evaluated':state.get('evaluated'),'generation':state.get('generation')}
 l,r=summary(first),summary(second)
 same_version=bool(l['source_hash']) and l['source_hash']==r['source_hash']
 comparable=(same_version and l['objective']==r['objective'] and l['audit_grid']==r['audit_grid']
             and bool(l['validation_protocol_hash']) and l['validation_protocol_hash']==r['validation_protocol_hash']
             and l['validation_tier']==r['validation_tier']
             and l['validation_noise_source']==r['validation_noise_source'])
 from validation_contract import ValidationReport, candidate_comparable
 try:
  reports=[((s.get('audited_champion') or s.get('best') or {}).get('audit') or {})['validation_v30'] for s in (first,second)]
  for report in reports:
   ValidationReport.model_validate(report)
   evidence=report['evidence']
   if not evidence.get('evaluation_settings_hash') or type(evidence.get('seed')) is not int:
    comparable=False
  comparable=bool(comparable and candidate_comparable(*reports)[0] and
                  all(key in first and key in second and first[key]==second[key]
                      for key in ('objective','audit_grid','fem_enabled','fem_backend','fem_pitch_mm')))
 except (ValueError,KeyError,TypeError):comparable=False
 delta=(round(float(r['audited_score'])-float(l['audited_score']),5) if comparable and
        l['audited_score'] is not None and r['audited_score'] is not None else None)
 return {'left':l,'right':r,'comparable':comparable,'score_delta_right_minus_left':delta,
         'warning':None if comparable else
         'Scores are NOT comparable: source, solver, seed, protocol, fidelity, noise, evaluation or FEM settings differ or are incomplete.'}

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
 import tempfile
 from starlette.background import BackgroundTask
 sources=[];total=0
 try:
  stage_dir=folder/'stages'
  if not stage_dir.resolve().is_relative_to(folder):raise ArchiveError('Invalid stages directory')
  names=list(selected)+['stages/'+p.name for p in sorted(stage_dir.glob('stage_*.json'))]
  if len(names)>10016:raise ArchiveError('Too many archive files for one download')
  for name in names:
   try:source=ARCHIVES.resolve_file(run_id,name,16*1024*1024 if name.startswith('stages/') else 100*1024*1024)
   except FileNotFoundError:continue
   total+=source.stat().st_size
   if total>256*1024*1024:raise ArchiveError('Archive download exceeds 256 MiB input limit')
   sources.append((name,source))
 except (ArchiveError,OSError,ValueError) as exc:raise HTTPException(422,str(exc))
 temporary=tempfile.TemporaryDirectory(prefix='neuroskin-download-',dir=EVO.folder)
 try:
  path=Path(temporary.name)/'archive.zip'
  with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
   for name,source in sources:z.write(source,arcname=name)
  return FileResponse(path,media_type='application/zip',filename=f'neuroskin_run_{run_id}.zip',background=BackgroundTask(temporary.cleanup))
 except BaseException:
  temporary.cleanup();raise

@app.get('/api/archives/{run_id}/audit')
def archive_audit(run_id:str,generation:int|None=None):
 try:
  saved=ARCHIVES.load(run_id)
  stage=ARCHIVES.load_stage(run_id,generation) if generation is not None else None
 except FileNotFoundError:raise HTTPException(404,'Saved run or stage not found')
 except (ArchiveError,OSError,ValueError,TypeError) as exc:raise HTTPException(422,str(exc))
 champion=stage.get('champion') if stage is not None else saved.get('audited_champion') or saved.get('best')
 if not champion or not champion.get('audit'):raise HTTPException(404,'No full audit for this selection')
 return Response(json.dumps({'run_id':run_id,'generation':generation,'champion':champion,
   'history':saved.get('audit_history',[]) if stage is None else [],
   'decisions':saved.get('stage_decisions',[]) if stage is None else [stage.get('decision')]}),media_type='application/json',
   headers={'Content-Disposition':f'attachment; filename="neuroskin_{run_id}_audit.json"'})

def select_candidate(kind:str,index:str,family:str,run_id:str|None=None,generation:int|None=None):
 if kind=='hybrid' and not run_id:
  from hybrid_library import BY_ID, genome_for
  from advanced import proxy
  spec=BY_ID.get(str(index))
  if spec is None:return None
  g=genome_for(spec,random.Random(1701))
  score,met,_=proxy(spec.upper_family,g)
  return {'id':'hybrid-'+spec.id,'family':spec.upper_family,'genome':g,
          'metrics':met,'fitness':float(score),'generation':0,'novelty':0.,
          'origin':'hybrid_expert_prior','expert_prior_score':sum(spec.scores)}
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
 try:
  with COMPUTE.start_guard():return EVO.start(req.mode,req.seconds,req.seed if req.seed is not None else secrets.randbits(31),req.population,req.exploration,req.objective,req.physical_gate,req.gate_grid,req.cores or getattr(app.state,'default_cores',1),req.audit_grid,req.fem_enabled,req.fem_pitch_mm,req.fem_backend,req.search_strategy,req.search_precision)
 except (ValueError,RuntimeError) as e:raise HTTPException(409,str(e))
@app.get('/api/compute/status')
def compute_status():
 from audit_scheduler import available_ram_mb
 return {**COMPUTE.snapshot(),'available_cpu':available_cores(),'available_ram_mb':available_ram_mb(),'observed':RESOURCE_TELEMETRY.snapshot()}

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

def _live_run_id():
 with EVO.lock:return str(EVO.state['id'])


def _guarded_candidate(kind,index,family,run_id=None,generation=None,expected_live_run_id=None,expected_candidate_id=None):
 def check_run():
  if expected_live_run_id is not None and _live_run_id()!=expected_live_run_id:
   raise HTTPException(409,'Live experiment changed; reselect the candidate')
 check_run()
 c=select_candidate(kind,index,family,run_id,generation)
 check_run()
 if c is None:raise HTTPException(404,'Candidate not found')
 if expected_candidate_id is not None and str(c['id'])!=expected_candidate_id:
  raise HTTPException(409,'Candidate changed; reselect the candidate')
 return c


class SelectionExpectation(BaseModel):
 expected_live_run_id:str|None=None
 expected_candidate_id:str|None=None


def _request_candidate(req):
 return _guarded_candidate(req.selection,req.index,req.family,req.run_id,req.generation,
                           req.expected_live_run_id,req.expected_candidate_id)


from neuroskin_v30.integration import build_router
app.include_router(build_router(select_candidate,_preview_genome,_live_run_id,COMPUTE))

@app.get('/api/mesh')
def mesh(kind:str='best',index:str="0",family:str='crown',quality:int=10,run_id:str|None=None,generation:int|None=None,piezo_count_override:int|None=None,piezo_wiring_override:int|None=None,expected_live_run_id:str|None=None,expected_candidate_id:str|None=None):
 if quality<5 or quality>20:raise HTTPException(400,'Quality must be 5..20')
 candidate=_guarded_candidate(kind,index,family,run_id,generation,expected_live_run_id,expected_candidate_id)
 g=_preview_genome(candidate,piezo_count_override,piezo_wiring_override)
 from pvdf_array import choose_film_members,layout_metrics
 layout=layout_metrics(structural_struts(candidate['family'],g),g)
 return {'candidate':{k:v for k,v in candidate.items() if k not in ('genome','metrics')},
         'model':webmesh(candidate['family'],g,quality),
         'pvdf_layout':layout,'pvdf_preview_override':piezo_count_override is not None,
         'pvdf_warning':'Preview override is not saved and does not update archived scores. Re-run Evaluate All for the modified configuration; bonded PVDF reinforcement is modeled approximately in FEM.',
         'strut_paths':[pts.round(4).tolist() for pts,_,_ in structural_struts(candidate['family'],g)]}

class Characterize(SelectionExpectation):
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


class FEMRequest(SelectionExpectation):
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
@COMPUTE.route('linear_fem')
def simulate_fem(req:FEMRequest):
 """Actual continuum HEX8 solution; browser receives the solver's FE surface nodes."""
 c=_request_candidate(req)
 from physical_fem import voxel_mesh, HexElasticSolver, FEMConfig, _serialize_mesh_fields, InvalidGeometry
 family,g=c['family'],_preview_genome(c,req.piezo_count_override,req.piezo_wiring_override)
 cfg=FEMConfig(pitch_mm=req.pitch_mm,young_MPa=float(g.get('material_E',1.)))
 try:
  if req.compute_device not in ('cpu','gpu','auto'):
   raise ValueError('Compute device must be cpu, gpu or auto')
  if req.backend not in ('auto','beam','hex8'):
   raise HTTPException(400,'Backend must be auto, beam or hex8')
  hybrid=g.get('hybrid_id','none') not in ('none',None,'')
  if hybrid and req.backend=='beam':raise ValueError('Two-stage hybrid requires connected solid HEX8 FEM')
  beam_selected=req.backend=='beam' or (req.backend=='auto' and req.pitch_mm<.7 and not hybrid)
  if beam_selected and req.compute_device=='gpu':
   raise ValueError('GPU mode only supports small solid HEX8 CSR meshes')
  if beam_selected:
   from beam_fem import BeamFEM
   s=BeamFEM(family,g,pitch_mm=req.pitch_mm)
   m=None
  else:
   m=voxel_mesh(family,g,cfg);s=HexElasticSolver(m,cfg.young_MPa,cfg.poisson,compute_device=req.compute_device,family=family,genome=g,
       gpu_budget_mb=(COMPUTE.current_allocation() or {}).get('vram_mb_estimate',1024) or 1024)
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

class EvaluateAllRequest(SelectionExpectation):
 compute_workers:int|None=Field(default=None,ge=1,le=256)
 fem_include_previews:bool=False
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
@COMPUTE.route('evaluate_all')
def evaluate_all(req:EvaluateAllRequest):
 """Unified characterization, spatial scan, dynamic PVDF, inverse tests,
 material-recovery screening, and optional 3D/beam mechanical FEM.
 As with the evolutionary audit, electronic channels remain synthetic.
 """
 from manual_evaluation import plan_manual, run_manual, attach_fem_evidence
 from audit_scheduler import available_ram_mb
 candidate=_request_candidate(req)
 g=_preview_genome(candidate,req.piezo_count_override,req.piezo_wiring_override)
 try:
  hybrid=g.get('hybrid_id','none') not in ('none',None,'')
  allocation=COMPUTE.current_allocation()
  from manual_evaluation import ManualPlan
  if allocation and allocation.get('plan'):
   plan=ManualPlan(**allocation['plan'])
  else:
   cores=min(req.compute_workers or getattr(app.state,'default_cores',1),available_cores())
   plan=plan_manual(cores,available_ram_mb(),req.fem_enabled,req.fem_backend,req.fem_pitch_mm,req.fem_compute_device,hybrid)
  options={'objective':req.objective,'audit_grid':req.audit_grid,'candidate_id':candidate['id'],
           'hybrid':hybrid,'fem_enabled':req.fem_enabled,'inspector_force':req.fem_inspection_force_n}
  def solve_fem(phase_callback):
   from physical_fem import fem_sweep
   try:
    return fem_sweep(candidate['family'],g,pitch_mm=req.fem_pitch_mm,backend=req.fem_backend,include_fields=True,
                  inspector_case=req.fem_inspection_case,inspector_force_N=req.fem_inspection_force_n,
                  inspector_offset=(req.fem_inspection_offset_x,req.fem_inspection_offset_y),compute_device=plan.device,
                  include_previews=req.fem_include_previews,case_workers=plan.fem_case_workers,matvec_workers=plan.matvec_workers,phase_callback=phase_callback,gpu_budget_mb=(allocation or {}).get('vram_mb_estimate',1024) or 1024),None
   except (ValueError,RuntimeError,MemoryError) as exc:
    return None,exc
  results=run_manual(candidate['family'],g,options,plan,solve_fem,COMPUTE.progress_callback())
  audit=results['audit'];fem,error=results.get('fem',(None,None))
  if req.fem_enabled:
   from audit_combine import merge_fem_into_audit,mark_fem_failure
   if error is not None:mark_fem_failure(audit,error,fem_backend=req.fem_backend)
   else:
    try:merge_fem_into_audit(audit,fem,candidate['family'],g,fem_backend=req.fem_backend,include_fields=False)
    except (ValueError,RuntimeError,MemoryError) as exc:mark_fem_failure(audit,exc,fem_backend=req.fem_backend)
  report=attach_fem_evidence(results['validation'],fem)
  audit['validation_v30']=report
  audit['decision_basis']['validation_protocol_hash']=report['protocol_hash']
  audit['decision_basis']['validation_level']='T0'
  audit['decision_basis']['validation_t0_pass']=report['pass_current_tier']
  audit['feasible']=bool(audit['feasible'] and report['pass_current_tier'])
  if not report['pass_current_tier']:
   audit.setdefault('screening_failure_reasons',[]).append('validation_v30_t0_failed')
  from selection_refinement import enforce_score_band
  enforce_score_band(audit)
  orientation=results.get('orientation')
  return {'candidate_id':candidate['id'],'family':candidate['family'],
          'orientation_study':orientation,'compute_telemetry':results['telemetry'],
          'audit':audit,'validation_v30':report,'fem':fem,'recovery':audit['unloading_recovery'],
          'historical_fitness_invalidated':bool(req.piezo_count_override is not None or req.piezo_wiring_override is not None),
          'warning':'Linear mechanics with approximate bonded PVDF/adhesive reinforcement (HEX8 or beam); assumed SLS recovery, synthetic electronics, uncalibrated PVDF and fatigue. FEM may not be converged.'}
 except (ValueError,RuntimeError,MemoryError,np.linalg.LinAlgError) as exc:
  raise HTTPException(422,f'Full evaluation failed: {exc}')

@app.get('/api/validation/protocol')
def validation_protocol():
 from validation_contract import load_protocol, digest
 p=load_protocol()
 return {'protocol':p.model_dump(mode='json'),'sha256':digest(p.model_dump(mode='json')),
         'description':'Validated and versioned protocol, synthetic inputs remain T0 only'}

@app.get('/api/validation/status')
def validation_status():
 s=EVO.snapshot()
 incumbent=s.get('audited_champion') or {}
 report=(incumbent.get('audit') or {}).get('validation_v30')
 return {'current_incumbent_id':incumbent.get('id'),'report':report,
         'warning':'No laboratory sensor calibration supplied; T0 synthetic validation only'}

@app.get('/api/physics_info')
def physics_info():return {'cases':{k:v[0] for k,v in CASES.items()},'objective_presets':PRESETS,'note':'Electrical and mechanics results are synthetic surrogate predictions, not FEM/experimental validation.'}

@app.post('/api/characterize')
def characterize(req:Characterize):
 c=_request_candidate(req)
 if req.case not in CASES:raise HTTPException(400,'Unknown case')
 g=_preview_genome(c,req.piezo_count_override,req.piezo_wiring_override)
 _,F,mz,off,mx=CASES[req.case]
 if req.case=='stretch_x': r=examine(c['family'],g,req.case,strain=.05*req.fraction,frequency_hz=req.frequency_hz)
 elif req.case=='compression':r=examine(c['family'],g,req.case,strain=-.05*req.fraction,frequency_hz=req.frequency_hz)
 else:r=examine(c['family'],g,req.case,force=[x*req.fraction for x in F],moment=[mx*req.fraction,0,mz*req.fraction],offset=off,frequency_hz=req.frequency_hz)
 return {'candidate_id':c['id'],'family':c['family'],'case':req.case,'fraction':req.fraction,
         'piezo_preview_override':req.piezo_count_override is not None or req.piezo_wiring_override is not None,
         'result':r,'sweep':sweep(c['family'],g,req.case)}

class SpatialTest(SelectionExpectation):
 piezo_count_override:int|None=None
 piezo_wiring_override:int|None=None
 selection:str='best'
 index:str='0'
 family:str='crown'
 grid_size:int=Field(default=5)
 force_n:float=Field(default=.1,gt=0,le=10)
 run_id:str|None=None
 generation:int|None=None

@app.post('/api/spatial_pressure')
def spatial_pressure(req:SpatialTest):
 c=_request_candidate(req)
 try:
  data=spatial_pressure_test(c['family'],_preview_genome(c,req.piezo_count_override,req.piezo_wiring_override),force_n=req.force_n,grid_size=req.grid_size)
 except (ValueError,np.linalg.LinAlgError) as exc:
  raise HTTPException(422,str(exc))
 return {'candidate_id':c['id'],'family':c['family'],'spatial':data}

@app.get('/api/export/{kind}')
def export(kind:str, selection:str='best',index:str="0",family:str='crown',run_id:str|None=None,generation:int|None=None,piezo_count_override:int|None=None,piezo_wiring_override:int|None=None,expected_live_run_id:str|None=None,expected_candidate_id:str|None=None):
 try:s=ARCHIVES.load(run_id) if run_id else EVO.snapshot()
 except FileNotFoundError:raise HTTPException(404,'Saved run not found')
 except (ArchiveError,OSError,ValueError,TypeError) as exc:raise HTTPException(422,str(exc))
 if kind=='json':return Response(json.dumps(s,indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename="neuroskin_evolution.json"'})
 if kind=='csv':
  buf=io.StringIO();w=csv.DictWriter(buf,['generation','elapsed','best','median','diversity']);w.writeheader();w.writerows(s['history'])
  return Response(buf.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="neuroskin_history.csv"'})
 if kind=='genome':
  c=_guarded_candidate(selection,index,family,run_id,generation,expected_live_run_id,expected_candidate_id)
  g=_preview_genome(c,piezo_count_override,piezo_wiring_override)
  # Flat genome JSON matches fem_cli.py --genome. The historical score is NOT exported.
  return Response(json.dumps(g,indent=2),media_type='application/json',headers={
      'Content-Disposition':f'attachment; filename="neuroskin_{c["family"]}_genome_pvdf_{g.get("piezo_count",1)}.json"',
      'X-NeuroSkin-Fitness-Invalidated':'true' if piezo_count_override is not None or piezo_wiring_override is not None else 'false'})
 if kind=='stl':
  c=_guarded_candidate(selection,index,family,run_id,generation,expected_live_run_id,expected_candidate_id)
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
