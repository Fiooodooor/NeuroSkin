"""v0.5 speculative morphological optimization. No nonlinear FEM is performed.
Parameters are dimensionalized in mm. All metrics are surrogate screening estimates.
"""
from __future__ import annotations
import copy, csv, io, json, math, random, threading, time, uuid, os, concurrent.futures, multiprocessing, hashlib
from pathlib import Path
from audit_scheduler import available_ram_mb, plan_audits, process_capacity, run_audit_batch
# Avoid nested BLAS pools competing with the evolutionary worker processes.
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
import numpy as np
import trimesh
from engine import LIMITS, FAMILIES, random_genome, solve_force, skew
from geometry_fixes import pvdf_ribbon

KINDS={
 'crown':['radial','offset','split','spiral','arched','woven','branching','procedural','hybrid','wild'],
 'chiral':['helical','counter','braided','staggered','double_helix','lattice','branching','procedural','hybrid','wild'],
 'quadrant':['diagonal','serpentine','orthogonal','crossed','kirigami','auxetic','branching','procedural','hybrid','wild']
}
# Each curated archetype is a genuine evolvable topology, not only a preview label.
from seed_library import SEEDS
for _seed in SEEDS:
 KINDS[_seed.family].append(_seed.id)

PARAM_EXTRA={'crown':{'taper':(.5,1.65),'tier_count':(1,4),'pitch':(-.7,.7),'pad_radius':(2.3,4.9),'wave_amp':(0.,1.3),'wave_count':(1,5),'phase':(-3.14,3.14),'radial_mod':(-.45,.45),'strut_gradient':(-.35,.35),'pad_offset_x':(-.8,.8),'pad_offset_y':(-.8,.8),'hub_ratio':(.15,.75),'branch_factor':(0,2),'material_E':(.35,2.5),'morph_seed':(0,999999)},
 'chiral':{'taper':(.5,1.65),'tier_count':(1,3),'pitch':(-.7,.7),'pad_radius':(2.3,4.9),'wave_amp':(0.,1.3),'wave_count':(1,5),'phase':(-3.14,3.14),'radial_mod':(-.45,.45),'strut_gradient':(-.35,.35),'pad_offset_x':(-.8,.8),'pad_offset_y':(-.8,.8),'hub_ratio':(.15,.75),'branch_factor':(0,2),'material_E':(.35,2.5),'morph_seed':(0,999999)},
 'quadrant':{'taper':(.5,1.65),'tier_count':(1,4),'pitch':(-.7,.7),'pad_radius':(2.3,4.9),'wave_amp':(0.,1.3),'wave_count':(1,5),'phase':(-3.14,3.14),'radial_mod':(-.45,.45),'strut_gradient':(-.35,.35),'pad_offset_x':(-.8,.8),'pad_offset_y':(-.8,.8),'hub_ratio':(.15,.75),'branch_factor':(0,2),'material_E':(.35,2.5),'morph_seed':(0,999999)}}

# Piezoelectric material placement and coupling parameters are optimized along with geometry.
# These are assumed physical parameters, not fitted PVDF device measurements.
PIEZO_GENES={
 'piezo_span_mm': (2.0,8.0),
 'piezo_width_mm': (1.2,5.0),
 'piezo_thickness_um': (20.0,90.0),
 'piezo_position': (.15,.85),
 'piezo_strain_transfer': (.08,.85),
 'piezo_orientation_rad': (-1.57,1.57),
 'piezo_feedback_pf': (20.0,220.0),
 'piezo_leak_tau_s': (.05,8.0),
 'piezo_mode': (0,1),
 'piezo_count': (1,8),
 'piezo_azimuth_rad': (-3.14159,3.14159),
 'piezo_wiring': (0,4),
}
for _family in PARAM_EXTRA:
 PARAM_EXTRA[_family].update(PIEZO_GENES)
 # Constrained readout geometry influences the assumed capacitive transfer,
 # rather than mutating an imaginary circuit noise floor.
 PARAM_EXTRA[_family].update({
  'electrode_area_mm2':(4.0,9.5),
  'dielectric_gap_mm':(.25,.65),
  'dielectric_epsilon_r':(2.3,3.5),
  'mount_compliance_mm_N':(.10,.48),
 })
 PARAM_EXTRA[_family].update({
  'hybrid_split':(.35,.65),
  'hybrid_upper_scale':(.52,1.55),
  'hybrid_lower_scale':(.52,1.70),
  'hybrid_phase':(-3.14159,3.14159),
  'hybrid_plate_thickness':(.48,.95),
  'hybrid_sensor_mode':(0,2),
  'hybrid_opposed_chirality':(0,1),
 })
 # 1D PVDF membrane + compliant shear-transfer bond; these are assumptions
 # optimized during fast screening and re-evaluated with true HEX8 kinematics.
 PARAM_EXTRA[_family].update({
  'piezo_E_MPa':(1200.,4000.),
  'piezo_adhesive_G_MPa':(.15,5.0),
  'piezo_adhesive_thickness_um':(20.,130.),
  'piezo_bond_fraction':(.50,1.0),
 })
PIEZO_INTEGER={'piezo_count','piezo_wiring'}
INTEGER_GENES={'ribs','tier_count','wave_count','branch_factor','morph_seed','piezo_mode','hybrid_sensor_mode','hybrid_opposed_chirality'}|PIEZO_INTEGER

def _snap_piezo_count(p,family=None):
 if 'piezo_mode' in p:p['piezo_mode']=0  # only broad-face d31 has a physical model
 if 'piezo_count' not in p:return p  # old archived genomes retain one film
 requested=int(p['piezo_count'])
 options=(1,2,3,4) if family=='quadrant' else (1,2,3,4,6,8)
 p['piezo_count']=min(options,key=lambda x:(abs(x-requested),x))
 if 'ribs' in p:
  lo,hi=LIMITS.get(family or 'chiral',{}).get('ribs',(4,12))
  if int(p['ribs'])<p['piezo_count']:
   p['ribs']=min(hi,max(lo,p['piezo_count']))
 return p

def new_genome(family,rng):
 p=random_genome(family,rng);p.update({k:(rng.randint(int(lo),int(hi)) if k in INTEGER_GENES else round(rng.uniform(lo,hi),5)) for k,(lo,hi) in PARAM_EXTRA[family].items()});p['piezo_count']=rng.choices((2,3,4) if family=='quadrant' else (2,3,4,6,8),
                           weights=(.18,.04,.78) if family=='quadrant' else (.13,.03,.53,.22,.09))[0];p['piezo_wiring']=rng.choices([0,1,2,3,4],[.65,.08,.10,.10,.07])[0];p['topology']=rng.choice([k for k in KINDS[family] if k!='hybrid']);p['hybrid_id']='none'
 if rng.random()<.16:
  from hybrid_library import SPECS
  ids=[x.id for x in SPECS if x.upper_family==family]
  if ids:
   p['hybrid_id']=rng.choice(ids);p['topology']='hybrid';p['piezo_count']=4
   p['height']=max(6.2,p['height'])
 return _snap_piezo_count(p,family)

def jump(family,p,rng,level='local'):
 q=dict(p);wide=(level!='local')
 if level=='restart':return new_genome(family,rng)
 if level=='topology':
  from hybrid_library import SPECS
  old=(p.get('hybrid_id','none') or 'none',p['topology'])
  singles=[('none',k) for k in KINDS[family] if k!='hybrid' and ('none',k)!=old]
  hybrids=[(s.id,'hybrid') for s in SPECS if s.upper_family==family and (s.id,'hybrid')!=old]
  # Select a distinct architecture, not a label that is later overwritten.
  q['hybrid_id'],q['topology']=rng.choice(hybrids if hybrids and rng.random()<.60 else singles)
 elif level=='wide' and rng.random()<.22:
  from hybrid_library import SPECS
  ids=[x.id for x in SPECS if x.upper_family==family]
  q['hybrid_id']=rng.choice(['none']+ids) if ids else 'none'
  if q['hybrid_id']=='none' and q['topology']=='hybrid':
   q['topology']=rng.choice([k for k in KINDS[family] if k!='hybrid'])
 keys=list(LIMITS[family])+list(PARAM_EXTRA[family]);rng.shuffle(keys)
 n=rng.randint(max(1,len(keys)//2),len(keys)) if wide else rng.randint(1,3)
 for k in keys[:n]:
  lo,hi=(LIMITS[family]|PARAM_EXTRA[family])[k]
  if wide and rng.random()<.55:v=rng.uniform(lo,hi)
  else:v=float(q[k])+rng.gauss(0,(hi-lo)*(.34 if wide else .085))
  q[k]=int(round(min(hi,max(lo,v)))) if k in INTEGER_GENES else round(float(min(hi,max(lo,v))),5)
 if q.get('hybrid_id','none')!='none':q['height']=max(6.2,q['height']);q['topology']='hybrid'
 return _snap_piezo_count(q,family)

def cross(family,a,b,rng):
 q={}
 for k in a:
  if k not in b:continue
  if k in ('topology','hybrid_id') or not isinstance(a[k],(int,float)) or not isinstance(b[k],(int,float)):q[k]=rng.choice([a[k],b[k]])
  elif rng.random()<.25 and k not in INTEGER_GENES:
   # A single interpolation coefficient is mandatory: separate draws can
   # produce weights summing above 1 and unphysical adhesive parameters.
   alpha=rng.random()
   q[k]=round(a[k]*alpha+b[k]*(1.-alpha),5)
  else:q[k]=rng.choice([a[k],b[k]])
 if q.get('hybrid_id','none')!='none':q['topology']='hybrid';q['height']=max(6.2,q['height'])
 elif q['topology']=='hybrid':q['topology']=rng.choice([k for k in KINDS[family] if k!='hybrid'])
 return _snap_piezo_count(jump(family,q,rng),family)

def transmute(family,genome,target,rng):
 """Recombine an inherited *normalized morphology* with new family-specific genetic axes."""
 child=new_genome(target,rng)
 for shared in ('radius','height','thickness','taper','pitch','pad_radius','tier_count','ribs','wave_amp','wave_count','phase','radial_mod','strut_gradient','hub_ratio','branch_factor','material_E','morph_seed','piezo_span_mm','piezo_width_mm','piezo_thickness_um','piezo_position','piezo_strain_transfer','piezo_orientation_rad','piezo_feedback_pf','piezo_leak_tau_s','piezo_mode','piezo_E_MPa','piezo_adhesive_G_MPa','piezo_adhesive_thickness_um','piezo_bond_fraction','piezo_count','piezo_azimuth_rad','piezo_wiring','electrode_area_mm2','dielectric_gap_mm','dielectric_epsilon_r','mount_compliance_mm_N','hybrid_split','hybrid_upper_scale','hybrid_lower_scale','hybrid_phase','hybrid_plate_thickness','hybrid_sensor_mode','hybrid_opposed_chirality'):
  if shared in genome and shared in child:
   old_range=(LIMITS.get(family,{})|PARAM_EXTRA[family]).get(shared)
   new_range=(LIMITS[target]|PARAM_EXTRA[target]).get(shared)
   if old_range and new_range:
    v=(genome[shared]-old_range[0])/(old_range[1]-old_range[0]);v=np.clip(v+rng.gauss(0,.12),0,1)
    val=new_range[0]+v*(new_range[1]-new_range[0]);child[shared]=int(round(val)) if shared in INTEGER_GENES else round(float(val),5)
 if genome.get('hybrid_id','none')!='none' and target==family:
  child['hybrid_id']=genome['hybrid_id'];child['topology']='hybrid'
 return _snap_piezo_count(child,target)

def _profile_radius(base_r: float, u: float, p: dict, branch_tag: str='leg') -> float:
 """Smooth thickness taper with a tiny manufacturable corrugation for visual and mechanical detail.
 Corrugation amplitude is deliberately small and never reduces radius below 0.18 mm.
 """
 taper=float(p.get('taper',1.0))
 gradient=float(p.get('strut_gradient',0.0))
 # thinner around the mid-span, slightly thicker at the anchors for robustness
 anchor=0.82 + 0.36*abs(2*u-1)
 taper_gain=(0.78 + 0.22*taper)
 gradient_gain=(1.0 + 0.18*gradient*(2*u-1))
 ripple=1.0 + 0.05*float(p.get('wave_amp',0.0))*math.sin(2*math.pi*(float(p.get('wave_count',2))*u + float(p.get('phase',0.0))/max(2*math.pi,1e-9)))
 if branch_tag!='leg':
  anchor*=0.82
  ripple=1.0
 return max(0.18, base_r*anchor*taper_gain*gradient_gain*ripple)

def _point_count(p: dict, minimum: int = 17) -> int:
 # More points = smoother and more detailed members in both viewer and voxelized FEM.
 return max(minimum, 2*int(p.get('wave_count',2))+11)

def _single_stage_struts(fam,p):
 """Curved beam centre-lines + groups. Screening uses the straight segment tangent surrogate.
 Curvature is geometric, not currently assembled in 6DOF mechanical solve.
 """
 radius=p['radius'];height=p['height'];th=p['thickness'];n=int(p.get('ribs',8 if fam!='quadrant' else 4))
 out=[]
 if fam=='quadrant':
  bases=[(sx,sy) for sx in (-1,1) for sy in (-1,1)]
  for ix,(sx,sy) in enumerate(bases):
   b=np.array([sx*radius*.77,sy*radius*.77,.8]);t=np.array([sx*p['pad_radius']*.7*(1+p.get('hub_ratio',.4)*.12),sy*p['pad_radius']*.7*(1+p.get('hub_ratio',.4)*.12),height]);t[:2]+=[p.get('pad_offset_x',0),p.get('pad_offset_y',0)]
   points=[]
   steps=_point_count(p)
   for j in range(steps):
    u=j/(steps-1);pos=b*(1-u)+t*u
    envelope=math.sin(math.pi*u)
    if p['topology']=='serpentine':pos[0]+=sx*p['bow']*math.sin(u*4*math.pi)*envelope
    elif p['topology']=='orthogonal':pos[0]+=sx*p['bow']*.5*envelope
    elif p['topology']=='crossed':pos[0]-=sx*p['bow']*envelope;pos[1]+=sy*p['asymmetry']*envelope
    else:pos[1]+=sy*p['bow']*.3*envelope
    # Procedural smooth deformation with endpoints pinned to manufactured mounts.
    if 0<j<steps-1:
     env=math.sin(math.pi*u)**2
     phase=p.get('phase',0.)+ix*1.618
     w=p.get('wave_count',2)
     if p['topology'] in ('procedural','hybrid','kirigami','auxetic','branching','wild'):
      pos[:2]+=p['wave_amp']*env*np.array([math.sin(w*2*math.pi*u+phase), math.cos(w*2*math.pi*u+phase)]) + (p['wave_amp']*.22*env*np.array([math.sin((w+1)*math.pi*u+phase*(1+int(p.get('morph_seed',0))%13)*.08),math.cos((w+2)*math.pi*u+phase*(1+int(p.get('morph_seed',0))%17)*.07)]) if p['topology']=='wild' else 0)
      pos[2]+=p['radial_mod']*env*math.sin(2*math.pi*u+phase)
    points.append(pos)
   base_r=th*(0.88+(ix%2)*.09*p['asymmetry'] + p.get('strut_gradient',0.)*(ix-1.5)/5)
   out.append((np.array(points),max(0.2,base_r),'leg'))
 else:
  for i in range(n):
   a=2*math.pi*i/n;b=np.array([radius*math.cos(a),radius*math.sin(a),.8]);
   phi=a+(p.get('twist',0) if fam=='chiral' else p['pitch']*.3)
   top_rad=p['pad_radius']*(.65+.35*p.get('hub_ratio',.5));t=np.array([top_rad*math.cos(phi)+p.get('pad_offset_x',0),top_rad*math.sin(phi)+p.get('pad_offset_y',0),height]);points=[]
   steps=_point_count(p)
   for j in range(steps):
    u=j/(steps-1);pos=b*(1-u)+t*u;envelope=math.sin(math.pi*u)
    if fam=='crown':
     radial=np.array([math.cos(a),math.sin(a),0]);pos+=radial*p['crown_curvature']*3*envelope
     if p['topology']=='spiral':pos[:2]+=np.array([-math.sin(a),math.cos(a)])*p['pitch']*envelope*1.8
     elif p['topology']=='offset':pos[0]+=p['pitch']*envelope
     elif p['topology']=='split':pos[2]+=math.sin(2*math.pi*u)*p['crown_curvature']*.5
    else:
     swirl=p['twist']*(u if p['topology']!='counter' else (u if u<.5 else 1-u))*1.1
     if p['topology']=='braided':swirl+=.18*math.sin(2*math.pi*u)*(1 if i%2 else -1)
     if p['topology']=='staggered':swirl*=1 if i%2==0 else -1
     r=(1-u)*radius+u*top_rad
     pos[:2]=[r*math.cos(a+swirl)+p.get('pad_offset_x',0)*u,r*math.sin(a+swirl)+p.get('pad_offset_y',0)*u]
    if 0<j<steps-1:
     env=math.sin(math.pi*u)**2
     phase=p.get('phase',0.)+i*1.618
     w=p.get('wave_count',2)
     if p['topology'] in ('procedural','hybrid','arched','woven','branching','double_helix','lattice','wild'):
      tang=np.array([-math.sin(a), math.cos(a)])
      pos[:2]+=p['wave_amp']*env*(math.sin(w*2*math.pi*u+phase)*tang + p['radial_mod']*math.cos(w*math.pi*u)*np.array([math.cos(a),math.sin(a)])) + (p['wave_amp']*.2*env*math.sin((w+int(p.get('morph_seed',0))%3+1)*math.pi*u+phase)*tang if p['topology']=='wild' else 0)
      pos[2]+=p['radial_mod']*env*math.sin(2*math.pi*u+phase)
    points.append(pos)
   base_r=th*(0.86+(i%2)*.08*p['taper'] + p.get('strut_gradient',0.)*.35*math.cos(a))
   out.append((np.array(points),max(0.2,base_r),'leg'))
 # Manufacturable alternative load paths, each anchored at both the base and contact pad.
 # This is *not* a claimed auxetic or origami mechanism until nonlinear FEM verifies it.
 if p.get('branch_factor',0)>0 and p['topology'] in ('branching','hybrid','procedural','lattice','woven','auxetic','wild'):
  original=list(out)
  for pts,r,_ in original:
   for k in range(int(p['branch_factor'])):
    u=(k+1)/(p['branch_factor']+1)
    start=pts[0].copy();end=pts[-1].copy()
    # alter the anchor azimuth a little while preserving attachment regions
    start[:2]=start[:2]*(1-.065*(k+1))
    end[:2]=(1-.09*u)*end[:2]+.09*u*np.array([p.get('pad_offset_x',0),p.get('pad_offset_y',0)])
    curve=[]
    steps=_point_count(p, minimum=15)
    for j in range(steps):
     t=j/(steps-1);v=(1-t)*start+t*end;envelope=math.sin(math.pi*t)**2
     v[:2]+=envelope*.28*(k+1)*np.array([-start[1],start[0]])/(max(1.,np.linalg.norm(start[:2])))
     curve.append(v)
    out.append((np.asarray(curve),max(.18,r*(.46+.11*k)),'support'))
 from archetype_geometry import apply as apply_archetype
 from symmetry_geometry import constrain_paths
 return constrain_paths(fam,p,apply_archetype(fam,p,out))

def structural_struts(fam,p):
 if p.get('hybrid_id','none') not in ('none',None,''):
  from hybrid_geometry import make_struts
  return make_struts(fam,p,_single_stage_struts)
 return _single_stage_struts(fam,p)

def stage_member_local_matrices(family,p,E=1.0):
 """Reusable local matrices for BOTH stage stiffness and support reactions.

 Identical radius/arc-length/PVDF/adhesive terms must be used for reaction
 estimates; using a bare rod here causes large force-balance errors.
 """
 from pvdf_array import choose_film_members
 from laminate_fem import effective_film_properties, film_interval
 paths=_single_stage_struts(family,p)
 selected=set(p['_film_indices']) if '_film_indices' in p else set(choose_film_members(paths,p))
 out=[]
 for member_index,(points,r,tag) in enumerate(paths):
  a,b=points[0],points[-1];d=b-a;chord=float(np.linalg.norm(d))
  length=float(np.sum(np.linalg.norm(np.diff(points,axis=0),axis=1)))
  if chord<1e-6 or length<1e-6:continue
  n=d/chord
  steps=np.linalg.norm(np.diff(points,axis=0),axis=1)
  radii=np.asarray([_profile_radius(r,(idx+.5)/len(steps),p,tag) for idx in range(len(steps))])
  axial_compliance=np.sum(steps/(np.pi*np.maximum(radii,1e-5)**2))
  effective_I=(np.pi/4.)*length/max(float(np.sum(steps/np.maximum(radii,1e-5)**4)),1e-12)
  ratio=chord/length
  k_ax=E/max(axial_compliance,1e-9)*ratio**2
  k_bend=12*E*effective_I/max(length**3,1e-6)
  if member_index in selected:
   _,_,lo,hi=film_interval(points,p)
   composite=effective_film_properties(p,hi-lo,r)
   coverage=(hi-lo)/max(length,1e-8)
   film_ea=composite['axial_EA_N']*coverage
   k_ax+=film_ea/max(length,1e-6)*ratio**2
   eccentricity=r+composite['adhesive_thickness_mm']+.5*composite['film_thickness_mm']
   k_bend+=12*film_ea*eccentricity**2/max(length**3,1e-6)
  kl=k_ax*np.outer(n,n)+k_bend*(np.eye(3)-np.outer(n,n))
  local=b-np.array([0,0,p['height']]);B=np.column_stack((np.eye(3),-skew(local)))
  out.append((points,kl,B))
 return out


def _single_stage_curve_stiffness(family,p,E=1.0):
 """6DOF equivalent curved-rod stiffness; NOT true curved beam FEM."""
 K=np.eye(6)*1e-9
 for _points,kl,B in stage_member_local_matrices(family,p,E):
  K+=B.T@kl@B
 K[3:,3:]+=np.eye(3)*1e-4
 return K

def curve_stiffness(family,p,E=1.0):
 if p.get('hybrid_id','none') not in ('none',None,''):
  from hybrid_geometry import stage_stiffnesses
  stages=stage_stiffnesses(family,p,_single_stage_curve_stiffness)
  # Two compliant stages are in SERIES, not parallel. The middle plate is
  # modeled as a rigid 6-DOF coupler in the fast screening model.
  from hybrid_geometry import mid_height
  from neuroskin_multiscale import transport
  T=transport([0.,0.,p['height']-mid_height(p)])
  C=T@np.linalg.solve(stages[0][1],T.T)+np.linalg.solve(stages[1][1],np.eye(6))
  return np.linalg.solve(C,np.eye(6))
 return _single_stage_curve_stiffness(family,p,E)

def proxy(family,p):
 # Geometry is represented by a straight-strut 6-DOF proxy; topology penalties reflect model uncertainty.
 # Never report as physical sensor calibration / FEM.
 q={k:p[k] for k in LIMITS[family]};q['thickness']=p['thickness']*p['taper']**.4
 if family=='quadrant':q['bow']*=1+.14*(p['tier_count']-1)
 if family=='chiral':q['twist']*=1+.06*(p['tier_count']-1)
 K=curve_stiffness(family,p,E=p.get('material_E',1.0))
 try:
  d=solve_force(K,[0,0,-.1]);dx=solve_force(K,[.05,0,0]);dy=solve_force(K,[0,.05,0]);tor=solve_force(K,[0,0,0],moment_z=.02)
  kz=.1/max(abs(d[2]),1e-9);kx=.05/max(abs(dx[0]),1e-9);ky=.05/max(abs(dy[1]),1e-9)
  paths=structural_struts(family,p)
  v=sum(float(np.sum(np.linalg.norm(np.diff(pts,axis=0),axis=1)*np.array([_profile_radius(r,(i+.5)/(len(pts)-1),p,tag)**2 for i in range(len(pts)-1)]))*math.pi) for pts,r,tag in paths)
  compliance=1/kz
  # Cross-family common goals: soft enough to sense, not too soft; 3D response; lighter members.
  target=.13 if family=='quadrant' else .045
  softness=math.exp(-(math.log(max(compliance,1e-9)/target)/1.15)**2)
  balanced=math.exp(-(math.log(max(kx,1e-9)/max(ky,1e-9))/.9)**2)
  material=math.exp(-v/450)
  coupling=min(1.,abs(d[5])/max(abs(d[2]),1e-8)*4.0) if family=='chiral' else 0
  # Orientation proxies intentionally coarse. They do not determine 3D force observability.
  if family=='crown':
   fc=kz*p['gap'];feature=math.exp(-((math.log(max(fc,1e-5)/2))/.9)**2)
  elif family=='chiral':feature=.75*coupling+.25*math.tanh(abs(tor[5])*12)
  else:feature=.55*balanced+.45*math.exp(-((kx/kz-.45)/.6)**2)
  # Conservative soft validity gates; topology retained as research categorical not physics miracle.
  slender=max(np.linalg.norm(pts[-1]-pts[0])/(2*r) for pts,r,_ in paths)
  gate=math.exp(-max(0,slender-21)*.13)
  # Approximate geometric feasibility, not stress or manufacturing certification.
  min_radius=min(r for _,r,_ in paths)
  if min_radius<.25:gate*=.25
  if p['height']<=.9+2*min_radius:gate*=.25
  # A large top offset should not be a free gain; it complicates sensing and mounting.
  offset=math.hypot(p.get('pad_offset_x',0),p.get('pad_offset_y',0))
  gate*=math.exp(-.1*offset**2)
  # Common 0..100 scale; arbitrary engineering objectives, transparent, not FEM.
  score=100*(.38*softness+.23*balanced+.20*material+.19*feature)*gate
  if not np.isfinite(score):raise ArithmeticError('Nonfinite')
  desc=np.array([np.log10(max(kz,1e-7)),np.log10(max(kx,1e-7)),np.log10(max(ky,1e-7)),np.log10(max(v,1e-7)),coupling],dtype=float)
  met={'fitness':round(float(score),4),'kz_N_mm_proxy':round(kz,4),'kx_N_mm_proxy':round(kx,4),'ky_N_mm_proxy':round(ky,4),'volume_struts_mm3_proxy':round(v,2),'compress_disp_0p1N_mm_proxy':round(abs(d[2]),5),'torsion_rad_proxy':round(abs(tor[5]),6),'coupling_proxy':round(coupling,5),'slenderness_proxy':round(slender,2),'minimum_strut_radius_mm':round(min_radius,4),'manufacturing_screen_factor':round(gate,4),'score_softness':round(softness,4),'score_balance':round(balanced,4),'score_material':round(material,4),'score_family_function':round(feature,4),'tier_count':int(p['tier_count']),'topology':p['topology'],'material_E_MPa_assumed':p.get('material_E',1.0),'physics':'6DOF composite-rod surrogate with PVDF membrane and bond shear-lag; not calibrated / not nonlinear FEM'}
  return score,met,desc
 except (np.linalg.LinAlgError,ArithmeticError,ValueError,ZeroDivisionError):
  return -1e4,{'fitness':-1e4,'invalid':True},np.zeros(5)

def cylinder_between(a,b,r,sections=10):
 a=np.asarray(a);b=np.asarray(b);v=b-a;L=float(np.linalg.norm(v))
 if L<1e-7:return None
 mesh=trimesh.creation.cylinder(radius=r,height=L,sections=sections)
 mesh.apply_transform(trimesh.geometry.align_vectors([0,0,1],v/L));mesh.apply_translation((a+b)/2)
 return mesh

def continuous_tube(points, base_radius, genome, tag='leg', sections=16):
 """Closed, smoothly tapered tube along a curved centerline with parallel-transport frames.
 Unlike segmented cylinders, the tube does not create false ribs or visible seams.
 This is display geometry, not a guarantee of a printable assembly.
 """
 pts=np.asarray(points,float)
 if len(pts)<2:raise ValueError('Need at least two centerline points')
 d=np.diff(pts,axis=0)
 if np.any(np.linalg.norm(d,axis=1)<1e-9):raise ValueError('Degenerate beam centerline')
 tang=np.empty_like(pts)
 tang[0]=d[0];tang[-1]=d[-1]
 tang[1:-1]=d[:-1]/np.linalg.norm(d[:-1],axis=1)[:,None]+d[1:]/np.linalg.norm(d[1:],axis=1)[:,None]
 tang/=np.linalg.norm(tang,axis=1)[:,None]
 reference=np.array([0.,0.,1.]) if abs(tang[0,2])<.9 else np.array([0.,1.,0.])
 normal=np.cross(tang[0],reference);normal/=np.linalg.norm(normal)
 normals=[]
 for i,t in enumerate(tang):
  if i:
   prev=tang[i-1];axis=np.cross(prev,t)
   sn=float(np.linalg.norm(axis));co=float(np.dot(prev,t))
   if sn>1e-10:
    axis/=sn
    normal=normal*co+np.cross(axis,normal)*sn+axis*np.dot(axis,normal)*(1-co)
   normal=normal-t*np.dot(t,normal)
   normal/=np.linalg.norm(normal)
  normals.append(normal.copy())
 count=max(8,int(sections))
 verts=[];faces=[]
 for i,(pt,t,n) in enumerate(zip(pts,tang,normals)):
  b=np.cross(t,n)
  r=_profile_radius(base_radius,i/(len(pts)-1),genome,tag)
  for k in range(count):
   a=2*math.pi*k/count
   verts.append(pt+r*(math.cos(a)*n+math.sin(a)*b))
 for i in range(len(pts)-1):
  for k in range(count):
   a=i*count+k; b=i*count+(k+1)%count
   c=(i+1)*count+k; d=(i+1)*count+(k+1)%count
   faces.extend(((a,b,d),(a,d,c)))
 i0=len(verts);verts.append(pts[0])
 i1=len(verts);verts.append(pts[-1])
 for k in range(count):
  faces.append((i0,(k+1)%count,k))
  a=(len(pts)-1)*count+k;b=(len(pts)-1)*count+(k+1)%count
  faces.append((i1,a,b))
 return trimesh.Trimesh(vertices=np.asarray(verts),faces=np.asarray(faces),process=False)

def tapered_tube(points, base_radius, p, tag='leg', sections=18):
 """Closed continuous variable-radius tube following a curved strut centerline.

 Uses a rotation-minimizing-style transported transverse frame, avoiding the
 scalloped joints and unnecessary mesh self-overlap of chained cylinders.
 The resulting surface describes the same sampled thickness profile as HEX8
 voxelization (within rasterization resolution).
 """
 points=np.asarray(points,float)
 if len(points)<2:raise ValueError('A tube requires at least two centerline points')
 n=len(points)
 tangents=np.empty((n,3),float)
 seg=np.diff(points,axis=0)
 seg_lengths=np.linalg.norm(seg,axis=1)
 if np.any(seg_lengths<=1e-9):raise ValueError('Degenerate strut segment')
 u_seg=seg/seg_lengths[:,None]
 tangents[0]=u_seg[0];tangents[-1]=u_seg[-1]
 for i in range(1,n-1):
  t=u_seg[i-1]+u_seg[i]
  tangents[i]=t/max(np.linalg.norm(t),1e-10)
 ref=np.array([0.,0.,1.]) if abs(float(np.dot(tangents[0],[0,0,1.])))<.85 else np.array([1.,0.,0.])
 normal=np.cross(tangents[0],ref);normal/=np.linalg.norm(normal)
 angles=np.linspace(0,2*math.pi,max(8,int(sections)),endpoint=False)
 m=len(angles);rings=[]
 for i,center in enumerate(points):
  t=tangents[i]
  normal=normal-np.dot(normal,t)*t
  length=np.linalg.norm(normal)
  if length<1e-9:
   alternate=np.array([1.,0.,0.]) if abs(t[0])<.85 else np.array([0.,1.,0.])
   normal=np.cross(t,alternate);length=np.linalg.norm(normal)
  normal/=length
  binormal=np.cross(t,normal)
  radius=_profile_radius(float(base_radius),i/(n-1),p,tag)
  rings.extend(center+radius*(math.cos(a)*normal+math.sin(a)*binormal) for a in angles)
 faces=[]
 for i in range(n-1):
  for j in range(m):
   k=(j+1)%m
   a=i*m+j;b=i*m+k;c=(i+1)*m+j;d=(i+1)*m+k
   faces.extend(((a,b,c),(b,d,c)))
 vertices=list(rings)
 vertices.extend([points[0],points[-1]])
 bottom_id=n*m;top_id=bottom_id+1
 for j in range(m):
  k=(j+1)%m
  faces.append((bottom_id,j,k))
  faces.append((top_id,(n-1)*m+k,(n-1)*m+j))
 return trimesh.Trimesh(vertices=np.asarray(vertices),faces=np.asarray(faces),process=False)

def detail_mesh(fam,p,quality=16):
 """Returns separate visual mesh component groups. Overlapping primitives are NOT fabrication CAD."""
 groups={'base':[],'flexure':[],'contact':[],'sensor':[],'inner':[]}
 if p.get('hybrid_id','none') not in ('none',None,''):
  from hybrid_geometry import mid_height,mid_radius
  base=trimesh.creation.cylinder(radius=9.3,height=.75,sections=48)
  base.apply_translation([0,0,.375]);groups['base'].append(base)
  mid_plate=trimesh.creation.cylinder(radius=mid_radius(p),height=float(p.get('hybrid_plate_thickness',.65)),sections=48)
  mid_plate.apply_translation([0,0,mid_height(p)]);groups['inner'].append(mid_plate)
  for i in range(4):
   a=2*math.pi*i/4
   sensor=trimesh.creation.box(extents=[2.,2.,.16])
   sensor.apply_translation([6.2*math.cos(a),6.2*math.sin(a),.82]);groups['sensor'].append(sensor)
 elif fam=='quadrant':
  for sx in (-1,1):
   for sy in (-1,1):
    foot=trimesh.creation.box(extents=[3.2,3.2,.6]);foot.apply_translation([sx*p['radius']*.77,sy*p['radius']*.77,.32]);groups['base'].append(foot)
    sensor=trimesh.creation.box(extents=[2.1,2.1,.18]);sensor.apply_translation([sx*p['radius']*.77,sy*p['radius']*.77,.73]);groups['sensor'].append(sensor)
 else:
  base=trimesh.creation.cylinder(radius=9.3,height=.75,sections=48);base.apply_translation([0,0,.375]);groups['base'].append(base)
  for i in range(4):
   a=2*math.pi*i/4
   sensor=trimesh.creation.box(extents=[2,2,.16]);sensor.apply_translation([6.3*math.cos(a),6.3*math.sin(a),.83]);groups['sensor'].append(sensor)
 pad=trimesh.creation.cylinder(radius=p['pad_radius']+0.4,height=.7,sections=48);pad.apply_translation([p.get('pad_offset_x',0),p.get('pad_offset_y',0),p['height']]);groups['contact'].append(pad)
 for pts,r,tag in structural_struts(fam,p):
  groups['flexure'].append(tapered_tube(pts,r,p,tag,sections=quality))
 # PVDF: independently routed mirrored films on 2 or 4 primary beams.
 # Missing 'piezo_count' preserves archived single-film model exactly.
 from pvdf_array import choose_film_members
 members=structural_struts(fam,p)
 films=[]
 for member_index in choose_film_members(members,p):
  support_pts,support_radius,_=members[member_index]
  try:
   films.append(pvdf_ribbon(support_pts,support_radius,
       position=p.get('piezo_position',.5),length_mm=p.get('piezo_span_mm',4.),
       width_mm=p.get('piezo_width_mm',2.5),
       thickness_mm=p.get('piezo_thickness_um',28.)/1000.))
  except ValueError:
   pass  # Invalid film excluded; candidate audit must flag missing film.
 if films:groups['piezo']=films
 if p.get('hybrid_id','none') not in ('none',None,''):
  pass # The actual intermediate plate already exists; do not add fake rings.
 elif fam=='crown':
  for tier in range(int(p['tier_count'])):
   r=1.25+(.45*tier);h=max(.25,p['height']-p['gap']-.7-.4*tier)
   t=trimesh.creation.cylinder(radius=r,height=.25,sections=32);t.apply_translation([0,0,h]);groups['inner'].append(t)
 elif fam=='chiral':
  for tier in range(int(p['tier_count'])):
   z=p['height']*(tier+1)/(p['tier_count']+1)
   ring=trimesh.creation.annulus(r_min=1.65,r_max=1.95,height=.2,sections=32);ring.apply_translation([0,0,z]);groups['inner'].append(ring)
  mag=trimesh.creation.cylinder(radius=1.4,height=.65,sections=32);mag.apply_translation([0,0,.9]);groups['sensor'].append(mag)
 else:
  hub=trimesh.creation.cylinder(radius=1,height=.4,sections=24);hub.apply_translation([0,0,p['height']-.5]);groups['inner'].append(hub)
 return {name:trimesh.util.concatenate(parts) for name,parts in groups.items() if parts}

def webmesh(fam,p,quality=10):
 out=[]
 for name,m in detail_mesh(fam,p,quality).items():
  # Do not subsample faces; doing so makes indexing inconsistent and can damage mesh.
  out.append({'part':name,'vertices':np.round(m.vertices,3).tolist(),'faces':m.faces.tolist()})
 return {'components':out,'note':'Concept geometry with tapered detailed flexures; separate mechanics uses reduced-order proxy and/or actual FEM depending on workflow.'}

def audit_job(job):
 """Heavy, identical second-stage audit of a shortlisted candidate."""
 fam,g,objective,grid,*options=job
 from full_evaluation import audit_candidate
 audit=audit_candidate(fam,g,objective,grid)
 fem_enabled=bool(options[0]) if options else False
 pitch=float(options[1]) if len(options)>1 else 1.25
 fem_backend=str(options[2]) if len(options)>2 else 'auto'
 case_workers=int(options[3]) if len(options)>3 else 1
 if fem_enabled:
  from physical_fem import fem_sweep, InvalidGeometry
  from audit_combine import merge_fem_into_audit, mark_fem_failure
  try:
   fem=fem_sweep(fam,g,pitch_mm=pitch,include_fields=False,backend=fem_backend,case_workers=case_workers)
   merge_fem_into_audit(audit,fem,fam,g,fem_backend=fem_backend,include_fields=True)
  except (InvalidGeometry,ValueError,MemoryError,RuntimeError) as exc:
   mark_fem_failure(audit,exc,fem_backend=fem_backend)
 # A versioned, identical synthetic validation protocol is run for every
 # finalist. The same seed gives common noise perturbations across candidates.
 from evaluation_v30 import safe_evaluate_protocol
 report=safe_evaluate_protocol(fam,g,candidate_id='audit-'+fam,seed=3322,
                          monte_carlo_samples=8,fem=audit.get('fem'))
 audit['validation_v30']=report
 audit['decision_basis']['validation_protocol_hash']=report['protocol_hash']
 audit['decision_basis']['validation_level']='T0'
 audit['decision_basis']['validation_t0_pass']=report['pass_current_tier']
 audit['decision_basis']['validation_position_mae_mm']=report['metrics'].get('decoder_holdout',{}).get('position_mae_mm')
 audit['decision_basis']['validation_force_rmse_N']=report['metrics'].get('decoder_holdout',{}).get('force_rmse_norm_N')
 audit['decision_basis']['validation_robust_snr_p10_assumed']=report['metrics'].get('robustness_monte_carlo',{}).get('assumed_snr_p10')
 audit['feasible']=bool(audit['feasible'] and report['pass_current_tier'])
 if not report['pass_current_tier']:
  audit.setdefault('screening_failure_reasons',[]).append('validation_v30_t0_failed')
 from selection_refinement import enforce_score_band
 return enforce_score_band(audit)

def evolution_worker_initializer():
 """Ctrl+C is handled by the parent, not by each spawned child."""
 import signal
 signal.signal(signal.SIGINT, signal.SIG_IGN)


class EvolutionStopped(Exception):
 """Normal cancellation requested by user."""


def evaluate_job(job):
 """Process-safe CPU-bound screening function (no UI state is shared)."""
 fam,p,objective,physical_gate,gate_grid=job
 from optimization import evaluate
 score,met,desc=evaluate(fam,p,objective,physical_gate,gate_grid)
 return (float(score),met,desc.tolist() if hasattr(desc,'tolist') else list(desc))

def engine_provenance():
 """SHA-256 source fingerprint prevents incompatible historical score comparison."""
 h=hashlib.sha256()
 for name in ('seed_library.py','archetype_geometry.py','recovery_sim.py','advanced.py','engine.py','optimization.py','electromechanics.py',
              'piezoelectric.py','spatial_validation.py','full_evaluation.py','geometry_fixes.py','physical_fem.py','laminate_fem.py','laminate_shell.py','hybrid_geometry.py','hybrid_library.py','pvdf_array.py',
              'reference_fem.py','beam_fem.py','matrixfree_fem.py','selection_refinement.py','search_space.py','orientation_study.py',
              'audit_combine.py','validation_contract.py','sensor_metrics.py','evaluation_v30.py','electronics_budget.py','validation_protocol_v30.json','pvdf_physics.py','neuroskin_multiscale.py','symmetry_geometry.py','audit_scheduler.py','validation_design.py','population_pareto.py','finalist_selection.py'):
  data=(Path(__file__).parent/name).read_bytes()
  h.update(name.encode('utf-8')+b'\0'+data)
 return {'release':(Path(__file__).parent/'VERSION').read_text(encoding='utf-8').strip(),'model_type':'spatial_feasibility_guided_evolution_plus_PVDF_shell',
         'sha256':h.hexdigest(),'schema':2}

class EvolutionV5:
 def __init__(self,folder):
  self.lock=threading.RLock();self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True)
  self.thread=None;self._pool=None;self.stop_event=threading.Event();self.pause_event=threading.Event();self.records={};self.state=self.empty()
 def empty(self):
  return dict(id='',status='idle',mode='all',family='all',duration=60.,elapsed=0.,generation=0,evaluated=0,seed=42,best=None,champions={},gallery=[],history=[],diversity=0,stagnation=0,mutations={},error='',objective='balanced',physical_gate=False,gate_grid=3,cores=1,audit_top3=[],audit_history=[],audited_champion=None,phase='idle',audit_grid=5,stage_decisions=[],search_strategy='adaptive',search_precision=.8,qd_archive_size=0,population_pareto_size=0)
 def snapshot(self):
  with self.lock:
   d=copy.deepcopy(self.state);d['paused']=self.pause_event.is_set();return d
 def start(self,mode='all',duration=60,seed=42,population=24,exploration=.55,objective="balanced",physical_gate=False,gate_grid=3,cores=1,audit_grid=5,fem=False,fem_pitch=1.25,fem_backend='hex8',search_strategy='adaptive',search_precision=.8):
  available = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else (os.cpu_count() or 1)
  if not (1<=int(cores)<=min(256,available)):raise ValueError(f'CPU workers must be 1..{min(256,available)}; requested {cores}')
  if not .12<=float(fem_pitch)<=2.0:raise ValueError('FEM pitch must be 0.12..2.0 mm')
  if fem_backend not in ('hex8','beam','auto'):raise ValueError('Invalid FEM backend: hex8, beam, auto')
  if gate_grid not in (3,5,7):raise ValueError('Gate grid must be 3, 5 or 7')
  if audit_grid not in (3,5,7):raise ValueError('Audit grid must be 3, 5 or 7')
  from search_space import SearchScope, SEARCH_STRATEGIES
  SearchScope.parse(mode)
  if search_strategy not in SEARCH_STRATEGIES:raise ValueError('Unknown search strategy')
  if not 0<=float(search_precision)<=1:raise ValueError('Search precision must be 0..1')
  from optimization import PRESETS
  if objective not in PRESETS:raise ValueError("Unknown objective")
  if not (3<=duration<=3600):raise ValueError('Duration outside 3..3600s')
  if not (12<=population<=256):raise ValueError('Population outside 12..256')
  if not (0<=exploration<=1):raise ValueError('Exploration must be 0..1')
  with self.lock:
   if self.thread is not None and self.thread.is_alive():raise RuntimeError('Stop current run before starting a new run')
   self.stop_event.clear();self.pause_event.clear();self.records={};self.state=self.empty()
   self.state.update(provenance=engine_provenance(),cores=int(cores),workers_active=0,screening_processes=process_capacity(cores,population),audit_progress={},evaluations_per_second=0,engine='spawn processes; bounded concurrent FEM load cases; BLAS threads capped to 1',id=str(uuid.uuid4())[:8],status='running',mode=mode,family=mode,duration=float(duration),seed=int(seed),objective=objective,physical_gate=bool(physical_gate),gate_grid=gate_grid,audit_grid=audit_grid,phase='initializing',fem_enabled=bool(fem),fem_pitch_mm=float(fem_pitch),fem_backend=fem_backend,search_strategy=search_strategy,search_precision=float(search_precision))
   self.thread=threading.Thread(target=self._loop,args=(mode,float(duration),int(seed),population,exploration,objective,bool(physical_gate),gate_grid,int(cores),audit_grid,bool(fem),float(fem_pitch),fem_backend,search_strategy,float(search_precision)),daemon=True);self.thread.start()
  return self.snapshot()
 def pause(self):
  with self.lock:
   if self.state['status']=='running':self.pause_event.set();self.state['status']='paused'
   elif self.state['status']=='paused':self.pause_event.clear();self.state['status']='running'
  return self.snapshot()
 def stop(self):
  self.stop_event.set()
  self.pause_event.clear()
  with self.lock:
   if self.state.get('status') in ('running','paused'):
    self.state.update(status='stopping',phase='stopping')
  return self.snapshot()

 def shutdown(self,timeout=8.0):
  """Stop controller, then terminate nonresponsive Python 3.14 workers."""
  self.stop()
  thread=self.thread
  if thread is None or not thread.is_alive():return True
  thread.join(timeout=max(0.,float(timeout)))
  if thread.is_alive():
   with self.lock:pool=self._pool
   if pool is not None:
    terminate=getattr(pool,'terminate_workers',None)
    if callable(terminate):
     try:terminate()
     except (OSError,RuntimeError,ValueError):
      import logging
      logging.getLogger(__name__).exception('Worker termination failed')
   thread.join(timeout=3.)
  return not thread.is_alive()

 def _check_stop(self):
  if self.stop_event.is_set():raise EvolutionStopped('User stopped evolution')

 def _loop(self,mode,duration,seed,population,exploration,objective,physical_gate,gate_grid,cores,audit_grid,fem_enabled,fem_pitch,fem_backend,search_strategy='adaptive',search_precision=.8):
  from search_space import SearchScope, local_refinement, EliteArchive
  from population_pareto import rank_population,parent_key,OBJECTIVES
  scope=SearchScope.parse(mode)
  rng=random.Random(seed);families=scope.families
  pop=[scope.generate(rng) for _ in range(population)]
  # Curated top-10 start the actual evolution; no synthetic fitness is substituted.
  from seed_library import top_candidates,seed_genome
  curated=[x for x in top_candidates(10) if x.family in families and scope.allow_single]
  for i,spec in enumerate(curated[:len(pop)]):
   pop[i]=(spec.family,scope.repair(spec.family,seed_genome(spec,rng,mutate=True),rng))
  # Ten engineering-prior two-stage architectures are genuine generation-0
  # members; they receive the EXACT same screening/FEM as other candidates.
  from hybrid_library import ranked as hybrid_ranked,genome_for as hybrid_genome_for
  slot=len(curated)
  for spec in hybrid_ranked():
   if spec.id not in scope.hybrid_ids or slot>=len(pop):continue
   pop[slot]=(spec.upper_family,scope.repair(spec.upper_family,hybrid_genome_for(spec,rng),rng))
   slot+=1
  archive=[];qd=EliteArchive();champions={};records={};history=[];stats={k:0 for k in ('random','guided','cross-family','topology','macro','crossover','precise','qd-elite')};best_score=-1e9;stall=0;active=0.;last=time.monotonic();gen=0;seen=0
  pool=None;incumbent=None;audit_history=[];decision_history=[];audits_by_fingerprint={}
  try:
   if cores>1:
    pool=concurrent.futures.ProcessPoolExecutor(max_workers=process_capacity(cores,population),mp_context=multiprocessing.get_context('spawn'),initializer=evolution_worker_initializer)
    with self.lock:self._pool=pool
   while active<duration and not self.stop_event.is_set():
    now=time.monotonic();active+=0 if self.pause_event.is_set() else max(0.,now-last);last=now
    if self.pause_event.is_set():time.sleep(.05);continue
    scored=[]
    with self.lock:self.state.update(phase='fast_screening',workers_active=process_capacity(cores,population),audit_progress={})
    jobs=[(fam,p,objective,physical_gate,gate_grid) for fam,p in pop]
    results=list(pool.map(evaluate_job,jobs,chunksize=max(1,population//max(1,cores*4)))) if pool else list(map(evaluate_job,jobs))
    self._check_stop()
    for (fam,p),(score,met,desc) in zip(pop,results):
     desc=np.asarray(desc,float);seen+=1
     # Descriptor distance uses a bounded distance between normalized log-mechanics.
     if archive:
      dist=sorted(float(np.linalg.norm((desc-q['descriptor'])/np.array([.8,.8,.8,.8,1.]))) for q in archive)
      novelty=float(np.mean(dist[:min(6,len(dist))]))
     else:novelty=2.
     novelty=min(2.,novelty)
     selection=score+exploration*novelty*9
     # Enforce feasible-first selection even with high novelty bonuses.
     if physical_gate and not met.get('spatial_feasible',False):
      selection=min(14.99,selection)
     candidate=dict(id=f'{gen}-{len(scored)}',family=fam,genome=p,metrics=met,fitness=float(score),novelty=round(novelty,4),selection=selection,generation=gen)
     scored.append((selection,candidate,desc))
     if score>best_score:best_score=score;stall=0
     if fam not in champions or score>champions[fam]['fitness']:champions[fam]=copy.deepcopy(candidate)
    scored.sort(key=lambda x:x[0],reverse=True)
    self._check_stop()
    # Stage 2: identical full audit, with cache-aware allocation of slots.
    from full_evaluation import promote
    from finalist_selection import nominate
    top,nomination=nominate([q[1] for q in scored],audits_by_fingerprint,
         (objective,audit_grid,fem_enabled,fem_pitch,fem_backend),physical_gate)
    if not top:raise RuntimeError('Population has no candidates for audit')
    with self.lock:self.state['phase']='top3_full_audit'
    audit_jobs=[];audit_indices=[];finalists=[None]*len(top)
    for i,c in enumerate(top):
     fingerprint=(c['family'],tuple(sorted(c['genome'].items())),objective,audit_grid,fem_enabled,fem_pitch,fem_backend)
     if fingerprint in audits_by_fingerprint:
      c['audit']=copy.deepcopy(audits_by_fingerprint[fingerprint]);finalists[i]=c
     else:
      audit_jobs.append((c['family'],c['genome'],objective,audit_grid,fem_enabled,fem_pitch,fem_backend));audit_indices.append((i,fingerprint))
    # Memory-aware finalist scheduling; all eight standardized load cases
    # remain unchanged. CPU budget is shared between processes and RHS threads.
    plan=plan_audits(len(audit_jobs),cores,fem_enabled,fem_backend,fem_pitch,available_ram_mb())
    cached=len(top)-len(audit_jobs)
    audit_started=time.monotonic()
    def audit_progress(inflight,completed):
     with self.lock:self.state.update(workers_active=inflight,audit_progress={**plan.as_dict(),
           'total':len(top),'cached':cached,'completed':cached+completed,'inflight':inflight,
           'elapsed_s':round(time.monotonic()-audit_started,1)})
    evaluations=run_audit_batch(pool,audit_job,audit_jobs,plan,check_stop=self._check_stop,progress=audit_progress)
    self._check_stop()
    for (i,key),a in zip(audit_indices,evaluations):
     audits_by_fingerprint[key]=a;top[i]['audit']=copy.deepcopy(a);finalists[i]=top[i]
    # FEM results affect survival/reproduction, not only the final displayed champion.
    if fem_enabled:
     for c in finalists:
      c['fem_score']=c['audit']['audit_score']
      if c['audit'].get('fem',{}).get('failed'):
       c['selection']=-100.
      elif c['audit']['feasible']:
       c['selection']=max(15.0, c['selection'] + (c['audit']['audit_score']-c['fitness'])*.85)
      else:
       # Finalist shown as impossible by the full audit must not receive a
       # 40+ parent selection score merely from mixing in FEM utility.
       c['selection']=min(14.99,max(0.,c['fitness']*.45+c['audit']['audit_score']*.14))
      for _,individual,_ in scored:
       if individual['id']==c['id']:
        individual['selection']=c['selection']
     scored.sort(key=lambda t:t[1]['selection'],reverse=True)
    # Reuse known audit status for every recurring genome, not just finalists.
    # Common cheap proxy objectives are ranked across the whole population;
    # expensive full audits remain a separate promotion evidence boundary.
    for _,candidate,_ in scored:
     fingerprint=(candidate['family'],tuple(sorted(candidate['genome'].items())),objective,audit_grid,fem_enabled,fem_pitch,fem_backend)
     known=audits_by_fingerprint.get(fingerprint)
     if known is not None:candidate['known_audit_feasible']=bool(known['feasible'])
    population_front=rank_population([x[1] for x in scored],physical_gate)
    scored.sort(key=lambda t:parent_key(t[1]),reverse=True)
    for _selection,_candidate,_desc in scored:
     qd.insert(_candidate)
    incumbent,decision=promote(incumbent,finalists)
    # Multi-objective audit: keep the Pareto set separate from scalar utility.
    # This is explicitly a T0 model-discovery metric, never hardware evidence.
    from sensor_metrics import pareto_front
    pareto_items=[]
    for c in finalists:
     report=(c['audit'].get('validation_v30') or {})
     m=report.get('metrics',{})
     d=m.get('decoder_holdout',{})
     robust=m.get('robustness_monte_carlo',{})
     if d and robust and c['audit'].get('feasible') and report.get('pass_current_tier'):
      pareto_items.append({'id':c['id'],
                           'force_rmse_N':float(d['force_rmse_norm_N']),
                           'position_mae_mm':float(d['position_mae_mm']),
                           'robust_signal_p10':float(robust['assumed_snr_p10'])})
    decision['pareto_front_T0']=[p['id'] for p in pareto_front(pareto_items,
                      {'force_rmse_N':'min','position_mae_mm':'min',
                       'robust_signal_p10':'max'})] if pareto_items else []
    decision['pareto_status']='synthetic_surrogate_only'
    decision['finalist_nomination']=nomination
    decision['distinct_finalists']=len(top)
    decision['screening_pareto_front_T0']=population_front
    decision['screening_pareto_objectives']=list(OBJECTIVES)
    decision['screening_pareto_policy']='common proxy objectives; feasible-first; not full validation'
    decision['generation']=gen+1;decision['top3']=[{'id':c['id'],'family':c['family'],
       'topology':c['genome']['topology'],'score':c['audit']['audit_score'],
       'feasible':c['audit']['feasible']} for c in finalists]
    audit_history.append({'generation':gen+1,'elapsed':round(active,2),
       'winner_id':incumbent['id'],'winner_score':incumbent['audit']['audit_score'],
       'feasible':incumbent['audit']['feasible'],
       'screened_three':[x['id'] for x in finalists],
       'decision':decision})
    decision_history.append(decision)
    self._check_stop()
    # Durable per-generation Top-3 snapshots, independently inspectable after restart.
    # The staged record is written atomically so a crash never creates a half JSON file.
    self._save_stage(gen+1, active, finalists, incumbent, decision)
    with self.lock:self.state.update(phase='selection',workers_active=0,population_pareto_size=len(population_front),audit_top3=copy.deepcopy(finalists),
       audited_champion=copy.deepcopy(incumbent),
       audit_history=copy.deepcopy(audit_history[-300:]),stage_decisions=copy.deepcopy(decision_history[-300:]))
    stall+=1;gen+=1
    for _,candidate,desc in scored[:max(2,population//7)]:
     if candidate['novelty']>.12 or len(archive)<5:
      archive.append({'descriptor':desc,'candidate':candidate});archive=archive[-160:]
    # Gallery: global champion, one per family, novel front, current diverse population.
    sorted_current=[s[1] for s in scored]
    gallery=[];keys=set()
    for item in list(sorted(champions.values(),key=lambda x:-x['fitness']))+sorted_current[:8]+sorted(sorted_current,key=lambda x:-x['novelty'])[:5]:
     identity=(item['family'],tuple(sorted(item['genome'].items())))
     if identity not in keys:gallery.append(item);keys.add(identity)
     if len(gallery)>=16:break
    family_counts={fam:sum(v[1]['family']==fam for v in scored) for fam in families}
    diversity=len(set((x[1]['family'],x[1]['genome'].get('hybrid_id','none') if x[1]['genome'].get('hybrid_id','none')!='none' else x[1]['genome']['topology']) for x in scored))
    if gen<=3 or gen%4==0:
     with self.lock:
      for c in gallery+finalists+[incumbent]:self.records[c["id"]]=copy.deepcopy(c)
     history.append({'generation':gen,'elapsed':round(active,2),'best':round(max(x['fitness'] for x in champions.values()),4),'median':round(float(np.median([x[1]['fitness'] for x in scored])),4),'diversity':diversity})
     with self.lock:self.state.update(elapsed=min(duration,active),generation=gen,evaluated=seen,workers_active=0,evaluations_per_second=round(seen/max(active,.001),2),best=copy.deepcopy(incumbent),champions=copy.deepcopy(champions),gallery=copy.deepcopy(gallery),history=copy.deepcopy(history[-600:]),diversity=diversity,stagnation=stall,mutations=stats.copy(),qd_archive_size=len(qd))
    elites=sorted_current[:max(2,population//8)]
    def tournament(fam=None):
     pool=[x[1] for x in scored if fam is None or x[1]['family']==fam]
     if not pool:return rng.choice(sorted_current)
     return max((rng.choice(pool) for _ in range(3)),key=parent_key)
    next_pop=([(incumbent['family'],copy.deepcopy(incumbent['genome']))] if fem_enabled and incumbent and incumbent['audit']['feasible'] else [])+[(x['family'],copy.deepcopy(x['genome'])) for x in elites]
    stagnating=stall>=25;scale=(.28 if stagnating else .06)+.5*exploration
    while len(next_pop)<population:
     action=rng.random()
     # Adaptive search splits compute budget across the global search space,
     # distinct QD niches and local trust-region refinement around elites.
     adaptive_local=(.30 if stall < 12 else .12)
     local_rate={'adaptive':adaptive_local,'explore':.08,'precision':.53}[search_strategy]
     qd_rate={'adaptive':.14,'explore':.19,'precision':.11}[search_strategy]
     if action<local_rate:
      # Prefer actually audited/feasible finalists as local refinement seeds;
      # otherwise use the highest-scoring fast candidate.
      viable=[c for c in finalists if c['audit'].get('feasible')]
      parent=rng.choice(viable[:3]) if viable and rng.random()<.70 else tournament()
      fam=parent['family']
      p=local_refinement(fam,parent['genome'],rng,precision=search_precision,stagnation=stall)
      op='precise'
     elif action<local_rate+qd_rate and len(qd)>0:
      parent=qd.sample(rng)
      fam=parent['family']
      p=local_refinement(fam,parent['genome'],rng,precision=max(.2,search_precision-.16),stagnation=stall)
      op='qd-elite'
     elif action<local_rate+qd_rate+.12+.05*exploration:
      from selection_refinement import guided_child
      a=tournament();fam=a['family'];p=guided_child(fam,a['genome'],a.get('metrics',{}),rng);op='guided'
     elif action<local_rate+qd_rate+.22+.10*exploration or (stagnating and rng.random()<.30):
      fam,p=scope.generate(rng);op='random'
     elif len(families)>1 and action<local_rate+qd_rate+.32+.12*exploration:
      a=tournament();fam=rng.choice([x for x in families if x!=a['family']]);p=transmute(a['family'],a['genome'],fam,rng);op='cross-family'
     elif action<local_rate+qd_rate+.47+.13*exploration:
      a=tournament();fam=a['family'];p=jump(fam,a['genome'],rng,'topology' if rng.random()<.5 else 'wide');op='topology' if p['topology']!=a['genome']['topology'] or p.get('hybrid_id')!=a['genome'].get('hybrid_id') else 'macro'
      if a['genome'].get('hybrid_id')=='procedural' and rng.random()<.55:
       from search_space import procedural_topology_mutation
       p=procedural_topology_mutation(fam,p,rng);op='topology'
     else:
      a=tournament();fam=a['family'];b=tournament(fam);p=cross(fam,a['genome'],b['genome'],rng);p=jump(fam,p,rng,'wide' if rng.random()<scale else 'local');op='crossover'
     p=scope.repair(fam,p,rng)
     assert scope.accepts(fam,p), 'Evolution operator violated active search scope'
     stats[op]=stats.get(op,0)+1;next_pop.append((fam,p))
    pop=next_pop
    if stagnating:stall=0
    if cores==1:time.sleep(.005)
   with self.lock:
    for c in gallery+finalists+([incumbent] if incumbent else []):self.records[c['id']]=copy.deepcopy(c)
    self.state.update(elapsed=min(duration,active),generation=gen,evaluated=seen,workers_active=0,evaluations_per_second=round(seen/max(active,.001),2),phase='exporting',status='finalizing',champions=copy.deepcopy(champions),gallery=copy.deepcopy(gallery),history=copy.deepcopy(history[-600:]),diversity=diversity,mutations=stats.copy())
    if incumbent:self.state['best']=copy.deepcopy(incumbent)
   self.save()
   # Publish the terminal state only AFTER the terminal snapshot has been
   # atomically committed. A test/client seeing "completed" can immediately
   # read a fully written results.json, including status="completed".
   terminal=self.snapshot()
   terminal['status']='stopped' if self.stop_event.is_set() else 'completed'
   terminal['phase']='exported'
   self._write_result(terminal)
   with self.lock:
    self.state['status']=terminal['status']
    self.state['phase']=terminal['phase']
  except Exception as exc:
   if self.stop_event.is_set() or isinstance(exc,EvolutionStopped):
    # Expected pool interruption: retain the last fully committed generation.
    with self.lock:self.state.update(status='stopped',phase='interrupted',error='',workers_active=0)
    try:self._write_result(self.snapshot())
    except OSError:
     import logging
     logging.getLogger(__name__).exception('Failed to persist stopped evolution')
   else:
    import traceback
    traceback.print_exc()
    with self.lock:self.state.update(status='failed',error=f'{type(exc).__name__}: {exc}. Check server terminal logs; reduce --cores if worker initialization fails.',workers_active=0)
  finally:
   with self.lock:
    if self._pool is pool:self._pool=None
   if pool:
    try:
     terminate=getattr(pool,'terminate_workers',None)
     if self.stop_event.is_set() and callable(terminate):terminate()
     else:pool.shutdown(wait=True,cancel_futures=True)
    except (RuntimeError,ValueError,OSError):
     import logging
     logging.getLogger(__name__).warning('Worker pool already terminated',exc_info=True)
 def _save_stage(self,generation,elapsed,finalists,incumbent,decision):
  run_id=self.state['id']
  if not run_id:return
  folder=self.folder/run_id/'stages';folder.mkdir(parents=True,exist_ok=True)
  document={'schema_version':1,'run_id':run_id,'generation':int(generation),
            'elapsed':round(float(elapsed),3),'top3':finalists,
            'champion':incumbent,'decision':decision,
            'validation_level':('linear_3d_HEX8_FEM_plus_surrogate' if self.state.get('fem_enabled') else 'surrogate_only')}
  path=folder/f'stage_{generation:06d}.json'
  tmp=path.with_suffix('.tmp')
  tmp.write_text(json.dumps(document,allow_nan=False),encoding='utf-8')
  os.replace(tmp,path)

 def _write_result(self,state):
  """Atomic replace prevents corrupted archives during GUI reading."""
  dest=self.folder/state['id'];dest.mkdir(parents=True,exist_ok=True)
  target=dest/'results.json';temp=dest/'results.json.tmp'
  temp.write_text(json.dumps(state,indent=2),encoding='utf-8')
  os.replace(temp,target)

 def save(self):
  state=self.snapshot()
  if not state['id']:return
  dest=self.folder/state['id'];dest.mkdir(parents=True,exist_ok=True)
  self._write_result(state)
  with (dest/'history.csv').open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=['generation','elapsed','best','median','diversity']);w.writeheader();w.writerows(state['history'])
  for fam,c in state['champions'].items():
   mesh=detail_mesh(fam,c['genome']);trimesh.util.concatenate(list(mesh.values())).export(dest/f'{fam}_concept.stl')
  audited=state.get('audited_champion')
  if audited:
   (dest/'champion_full_audit.json').write_text(json.dumps(audited,indent=2))
   mesh=detail_mesh(audited['family'],audited['genome']);trimesh.util.concatenate(list(mesh.values())).export(dest/'champion_CONCEPT_NOT_PRINT_READY.stl')
  with (dest/'audit_history.csv').open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=['generation','winner_id','winner_score','feasible','elapsed']);w.writeheader()
   for a in state.get('audit_history',[]):w.writerow({k:a.get(k) for k in w.fieldnames})
  (dest/'stage_decisions.json').write_text(json.dumps(state.get('stage_decisions',[]),indent=2))
 def lookup(self,kind='best',index=0,family=None):
  s=self.snapshot()
  if kind=='id':
   with self.lock:return copy.deepcopy(self.records.get(str(index)))
  if kind=='best':return s['best']
  if kind=='family':return s['champions'].get(family)
  if kind=='gallery':return s['gallery'][index] if 0<=index<len(s['gallery']) else None
  return None
