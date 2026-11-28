"""Transparent, user-selectable multiobjective screening. No physical performance claims."""
import math
import numpy as np
from advanced import proxy
from electromechanics import screening_electrical
from piezoelectric import screen as piezo_screen

PRESETS={
 'balanced':{'geometry':.36,'electrical':.28,'robustness':.18,'piezo':.18},
 'touch':{'geometry':.25,'electrical':.43,'robustness':.12,'piezo':.20},
 'robust':{'geometry':.30,'electrical':.17,'robustness':.38,'piezo':.15},
 'dynamic':{'geometry':.22,'electrical':.18,'robustness':.10,'piezo':.50},
 'electronics':{'geometry':.22,'electrical':.18,'robustness':.15,'piezo':.15,'readout':.30},
}


def evaluate(fam,p,preset='balanced',physical_gate=False,gate_grid=3):
 if preset not in PRESETS:raise ValueError('Unknown preset')
 base,metrics,desc=proxy(fam,p)
 if base<-1000:return base,metrics,desc
 try:
  e=screening_electrical(fam,p,include_readout=preset=='electronics')
  # Soft saturation; 6-sigma synthetic *assumptions*, not actual detection accuracy.
  signal=100*(.6*(1-math.exp(-e['normal_snr_proxy']/6))+.4*(1-math.exp(-e['shear_snr_proxy']/6)))
  strain=e['substrate_strain_signal_snr_proxy']
  # Unwanted signal under substrate deformation is a cost, not a virtue.
  robust=100*math.exp(-strain/18.)
  # similarity of an off-center pressure signature to shear is a warning
  ambiguity=abs(e['offcentre_similarity_proxy'])
  robust*=1-.35*ambiguity
  piezo=piezo_screen(fam,p)
  w=PRESETS[preset]
  fitness=float(np.clip(w['geometry']*base+w['electrical']*signal+w['robustness']*robust+w['piezo']*piezo['piezo_score']+w.get('readout',0.)*e.get('fitness_readout',0.),0,100))
  hybrid_stage=None
  if p.get('hybrid_id','none') not in ('none',None,''):
   from electromechanics import examine
   responses=[examine(fam,p,case)['electrical'].get('hybrid_stage_channels') for case in ('normal','shear_x','shear_y')]
   if all(responses):
    signatures=np.array([x['readout_vector_pF_assumed'] for x in responses])
    norm=np.linalg.norm(signatures,axis=1)
    distinct=float(np.clip(np.std(norm)/max(np.mean(norm),1e-12),0,1))
    # A two-electrode-stage stack alone cannot have full rank for 3 force
    # components. Do not pretend this is 3-axis observability.
    independent=int(np.linalg.matrix_rank(signatures,tol=1e-10))
    variation=float(np.clip(np.linalg.norm(signatures[0]-signatures[1]),0,0.02)/.02)
    hybrid_score=100*(.55*distinct+.45*variation)*min(1.,independent/2.)
    fitness=.9*fitness+.1*hybrid_score
    hybrid_stage={'hybrid_id':p['hybrid_id'],'stage_signature_rank_max2':independent,
                  'stage_readout_diversity_score_0_100':round(hybrid_score,4),
                  'stage_readouts_assumed_pF':signatures.tolist(),
                  'note':'Two series stages, independent electrodes. Two channels alone cannot identify Fx,Fy,Fz uniquely.'}
  metrics=dict(metrics,**e,**piezo,fitness=round(fitness,4),fitness_geometry=round(base,4),fitness_electrical=round(signal,4),fitness_robustness=round(robust,4),fitness_preset=preset,
      fitness_weights=w,score_explanation='Weighted engineering utility of approximate geometry, assumed SNR, piezo transient response and nuisance sensitivity; NOT a success probability, accuracy or FEM outcome.')
  if hybrid_stage:metrics['hybrid_stage_screen']=hybrid_stage
  if physical_gate:
   from spatial_validation import cheap_gate
   plausibility=cheap_gate(fam,p,grid_size=gate_grid)
   metrics['spatial_gate']=plausibility
   metrics['physical_plausibility_gate_enabled']=True
   if plausibility['status']=='PASS':
    # Explicitly separate feasible and infeasible score bands.
    fitness=15.+.85*fitness
    metrics['fitness']=round(fitness,4)
   else:
    # Feasibility-first ranking, with a CONTINUOUS improvement direction.
    # A 2.95-SNR near-miss must outrank a 0.1-SNR failure when both have
    # zero binary pass coverage. No unverified candidate can enter the
    # feasible (15+) band.
    coverage=float(plausibility['coverage_fraction'])
    quality=float(plausibility.get('mean_point_quality',coverage))
    fitness=min(14.99,14.99*(.55*coverage+.45*quality))
    metrics['fitness']=round(fitness,4)
    metrics['spatial_continuous_quality']=round(quality,5)
    metrics['rejection_reasons']=plausibility['failure_reasons']
   metrics['spatial_feasible']=plausibility['status']=='PASS'
  else:
   metrics['physical_plausibility_gate_enabled']=False
  return fitness,metrics,desc
 except Exception as exc:
  return -1e4,dict(metrics,error=f'electrical proxy failed: {exc}',fitness=-1e4),desc
