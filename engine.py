"""Reduced-order geometry and mechanics primitives used by NeuroSkin 3.
Units: mm, N, MPa. This module does not establish nonlinear or hardware qualification."""
from __future__ import annotations
import csv, io, json, math, random, threading, time, uuid
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
import trimesh

FAMILIES = ('crown','chiral','quadrant')
LIMITS = {
 'crown': {'ribs':(5,12),'radius':(5.5,8.5),'height':(4.0,7.1),'thickness':(.26,0.95),'gap':(.20,2.3),'stop_k':(.3,22.),'crown_curvature':(.05,.60)},
 'chiral':{'ribs':(4,12),'radius':(4.8,8.0),'height':(4.5,7.4),'thickness':(.28,0.92),'twist':(.15,1.55),'split':(.24,.76),'balance':(-1.,1.)},
 'quadrant':{'radius':(5.0,8.7),'height':(4.0,7.5),'thickness':(.26,0.98),'bow':(.15,1.9),'asymmetry':(-.48,.48),'coupling':(.05,.85),'sensor_gain':(.35,2.)}
}
INTEGER={'ribs'}


def random_genome(family,rng):
 return {k:(rng.randint(int(a),int(b)) if k in INTEGER else rng.uniform(a,b)) for k,(a,b) in LIMITS[family].items()}

def mutate(family, g, rng, strength=.13):
 out=dict(g)
 for k,(lo,hi) in LIMITS[family].items():
  if rng.random()<.42:
   v=out[k]+rng.gauss(0,strength*(hi-lo))
   v=min(hi,max(lo,v))
   out[k]=int(round(v)) if k in INTEGER else round(v,5)
 return out

def crossover(family,a,b,rng):
 return {key:(a[key] if rng.random()<.5 else b[key]) for key in LIMITS[family]}


def struts(family,p):
 """Return bottom/top endpoints and thickness; top plate 20x20 mm nominal."""
 ribs=[]
 if family=='crown':
  for i in range(int(p['ribs'])):
   a=2*np.pi*i/p['ribs']; radial=np.array([np.cos(a),np.sin(a)])
   b=np.r_[p['radius']*radial,0.9]
   t=np.r_[(2.1 + .9*p['crown_curvature'])*radial,p['height']]
   ribs.append((b,t,p['thickness']))
 elif family=='chiral':
  n=int(p['ribs']);rad=p['radius'];h=p['height'];t=p['twist']
  for i in range(n):
   a=2*np.pi*i/n
   b=np.array([rad*np.cos(a),rad*np.sin(a),0.9]);
   # balance controls net helical angle, but each strut still experiences twist
   phi=a+t*(1 if i%2==0 else p['balance']) + (p['split']-.5)*.18
   top=np.array([2.5*np.cos(phi),2.5*np.sin(phi),h])
   ribs.append((b,top,p['thickness']))
 else:
  for sx in (-1,1):
   for sy in (-1,1):
    b=np.array([sx*p['radius'],sy*p['radius'],.9])
    shift=p['asymmetry']*(sx-sy)
    top=np.array([sx*(2.8+.3*p['bow'])+shift,sy*(2.8-.3*p['coupling'])-shift,p['height']])
    ribs.append((b,top,p['thickness']))
 return ribs

def skew(r):
 x,y,z=r
 return np.array([[0,-z,y],[z,0,-x],[-y,x,0.]])

def stiffness_and_legs(family,p,E=1.):
 """6DOF rigid-top elastic rod proxy; includes axial and *approximate* transverse stiffness."""
 K=np.eye(6)*1.e-9
 legs=[]
 for b,t,r in struts(family,p):
  d=t-b;L=np.linalg.norm(d); n=d/L; A=np.pi*r*r; I=np.pi*r**4/4
  k_ax=E*A/L
  k_bend=12*E*I/max(L**3,1e-6)
  if family=='quadrant':k_bend*=1/(1+.2*p['bow'])
  kl=k_ax*np.outer(n,n)+k_bend*(np.eye(3)-np.outer(n,n))
  rp=t-np.array([0,0,p['height']]);B=np.column_stack((np.eye(3),-skew(rp)))
  K+=B.T@kl@B
  legs.append((B,kl,b,t,r))
 # Regularization simulates compliant stabilization of unsupported rigid body modes.
 K[3:,3:]+=np.eye(3)*1e-4
 return K,legs

def solve_force(K, force, offset=(0,0), moment_z=0):
 Fx,Fy,Fz=force;ox,oy=offset
 load=np.array([Fx,Fy,Fz,oy*Fz,-ox*Fz, moment_z+ox*Fy-oy*Fx],float)
 return np.linalg.solve(K,load)

def sensing(family,p,K,legs,force,offset=(0,0)):
 u=solve_force(K,force,offset)
 foot=[]
 for B,kl,*_ in legs:
  rb=-(kl@(B@u))
  foot.append(rb[2])
 if family=='quadrant':
  # Four Z reactions and two *hypothetical* displacement pickups plus two position readings.
  # Independent position readings are assumed, not implemented in a real device.
  return np.array(foot + [u[0]*p['sensor_gain'],u[1]*p['sensor_gain'],offset[0],offset[1]])
 if family=='chiral':
  return np.array([u[2],u[5],u[0],u[1]])
 return np.array([u[2],sum(foot),u[0],u[1]])

def metrics(family,p):
 E=1.
 K,legs=stiffness_and_legs(family,p,E)
 try:
  center=solve_force(K,[0,0,-.1]); shear=solve_force(K,[.05,0,-.05]); torque=solve_force(K,[0,0,-.1],moment_z=.05)
  kz=.1/max(abs(center[2]),1e-10)
  kxy=.05/max(abs(shear[0]),1e-10)
  # rod material proxy: geometrical member volume, no meshed plate included
  v=sum(math.pi*r*r*np.linalg.norm(t-b) for _,_,b,t,r in legs)
  # bending strain proxy; NOT actual stress or fatigue life
  strain_proxy=max(np.linalg.norm((B@center))/max(np.linalg.norm(t-b),1e-8) for B,_,b,t,_ in legs)
  if family=='crown':
   # Progressive stop: nominal stop engages when u_z crosses gap.
   gap=p['gap']; stop=p['stop_k']; u_at_force=abs(center[2]);
   activated=max(0.,u_at_force-gap); extra_load=stop*activated
   balance=1-min(1.,abs(np.log10(max(kz,1e-8)/3))/3)
   # reward measurable first-stage motion, usable gap, and gradual additional stiffness
   score=2.2*balance+1.8*math.exp(-((gap-.65)/.52)**2)+1.0*math.exp(-((stop/kz-1.5)/2)**2)-.003*v-12*max(0,strain_proxy-.06)
   signal_quality=balance
   extra={'activation_force_N_proxy':round(kz*gap,4),'post_stop_k_N_mm_proxy':round(kz+stop,4),'early_compliance_mm_N':round(1/kz,5),'stop_engaged_at_0p1N':bool(activated>0)}
  elif family=='chiral':
   twist_signal=abs(center[5]); torque_signal=abs(torque[5]);
   norm=twist_signal/max(abs(center[2]),1e-8)
   # aim for moderate coupled axial-rotational sensitivity and good torque response
   score=2.8*np.tanh(norm*8)+1.6*np.tanh(torque_signal*12)-.0025*v-12*max(0,strain_proxy-.06)-5*max(0,abs(center[5])-.08)
   signal_quality=norm
   extra={'normal_to_rotation_rad_per_mm_proxy':round(norm,6),'twist_at_0p1N_rad_proxy':round(float(center[5]),7),'torque_rotation_rad_proxy':round(float(torque[5]),7)}
  else:
   # 5 unknowns Fx,Fy,Fz,contact_x,contact_y, not only 3; finite difference Jacobian at offset !=0
   base=np.array([.01,-.01,-.1,.9,-.7]); ds=np.array([.004,.004,.006,.12,.12]);
   def response(x):return sensing(family,p,K,legs,x[:3],x[3:])
   J=np.column_stack([(response(base+np.eye(5)[i]*ds[i])-response(base-np.eye(5)[i]*ds[i]))/(2*ds[i]) for i in range(5)])
   # Normalize by assumed scales of loading and sensor noise. Synthetic, NOT hardware precision.
   scales=np.array([.1,.1,.1,3,3]); noise=np.array([.005]*4+[.003,.003,.15,.15])
   whitened=(J*scales[None,:])/noise[:,None]
   sv=np.linalg.svd(whitened,compute_uv=False)
   sigma=float(sv[-1]);condition=float(sv[0]/max(sigma,1e-10))
   signal_quality=sigma
   score=3*np.tanh(sigma/3)+1.5*np.exp(-np.log10(max(condition,1))**2/4)-.003*v-12*max(0,strain_proxy-.06)
   extra={'min_singular_value_proxy':round(sigma,5),'condition_proxy':round(condition,4),'sensor_model':'4 ideal reactions +2 top XY displacements +2 independent contact position values'}
  return {'fitness':round(float(score),6),'kz_N_mm':round(float(kz),5),'kx_N_mm_proxy':round(float(kxy),5),'rod_volume_mm3':round(float(v),2),'max_linear_strain_proxy':round(float(strain_proxy),5),'signal_metric':round(float(signal_quality),6),**extra}
 except (np.linalg.LinAlgError,OverflowError,ValueError):
  return {'fitness':-1e5,'error':'singular or invalid mechanics proxy'}


def _cylinder_between(a,b,r,sections=8):
 a=np.asarray(a);b=np.asarray(b);delta=b-a;L=float(np.linalg.norm(delta));
 if L<1e-7:return None
 return trimesh.creation.cylinder(radius=r,height=L,sections=sections,transform=trimesh.geometry.align_vectors([0,0,1],delta/L)@trimesh.transformations.translation_matrix([0,0,0])) .apply_translation((a+b)/2)

def mesh_for(family,p,quality=9):
 parts=[];H=p['height']
 if family=='quadrant':
  for sx in (-1,1):
   for sy in (-1,1):
    base=trimesh.creation.box(extents=[2.2,2.2,.75]);base.apply_translation([sx*p['radius'],sy*p['radius'],.38]);parts.append(base)
 else:
  base=trimesh.creation.cylinder(radius=9.2,height=.75,sections=32);base.apply_translation([0,0,.375]);parts.append(base)
 top=trimesh.creation.cylinder(radius=3.2 if family!='quadrant' else 4.2,height=.65,sections=32);top.apply_translation([0,0,H]);parts.append(top)
 for b,t,r in struts(family,p):
  # centerline curvature is illustrative only; mechanics uses a straight equivalent beam
  if family=='crown':
   mid=(b+t)/2;mid[:2]*=1+p['crown_curvature']*.3
   pts=[b,mid,t]
  elif family=='chiral':
   mid=(b+t)/2;mid[:2]+=np.array([-b[1],b[0]])*.06
   pts=[b,mid,t]
  else:
   mid=(b+t)/2;mid[:2]+=np.array([b[0],-b[1]])*.08*p['bow'];pts=[b,mid,t]
  for x,y in zip(pts[:-1],pts[1:]):
   cyl=_cylinder_between(x,y,r,sections=quality)
   if cyl is not None:parts.append(cyl)
 if family=='crown':
  stop=trimesh.creation.cylinder(radius=1.7,height=max(.5,H-p['gap']-.9),sections=24);stop.apply_translation([0,0,.8+stop.extents[2]/2]);parts.append(stop)
 if family=='chiral':
  ring=trimesh.creation.annulus(r_min=2.6,r_max=3.0,height=.4,sections=24);ring.apply_translation([0,0,H*p['split']]);parts.append(ring)
 return trimesh.util.concatenate(parts)

@dataclass
class RunState:
 id:str='';status:str='idle';family:str='quadrant';duration:float=60;started:float=0.;elapsed:float=0.;generation:int=0;evaluated:int=0;best:dict|None=None;history:list|None=None;hall:list|None=None;error:str='';seed:int=42

class Evolution:
 def __init__(self,folder):
  self.lock=threading.RLock();self.state=RunState(history=[],hall=[]);self.stop_event=threading.Event();self.pause_event=threading.Event();self.worker=None;self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True)
 def start(self,family,duration=60,seed=42,popsize=24):
  if family not in FAMILIES:raise ValueError('Invalid family')
  if not 3<=duration<=3600:raise ValueError('Duration must be 3..3600 seconds')
  if not 8<=popsize<=100:raise ValueError('Population must be 8..100')
  with self.lock:
   if self.worker is not None and self.worker.is_alive():raise RuntimeError('Stop current run first')
   self.stop_event.clear();self.pause_event.clear()
   self.state=RunState(id=str(uuid.uuid4())[:8],status='running',family=family,duration=float(duration),started=time.time(),seed=int(seed),history=[],hall=[])
   self.worker=threading.Thread(target=self._evolve,args=(family,float(duration),int(seed),int(popsize)),daemon=True);self.worker.start()
   return self.snapshot()
 def snapshot(self):
  with self.lock:
   d=asdict(self.state)
   d['paused']=self.pause_event.is_set()
   return d
 def pause(self):
  with self.lock:
   if self.state.status=='running':self.pause_event.set();self.state.status='paused'
   elif self.state.status=='paused':self.pause_event.clear();self.state.status='running'
   return self.snapshot()
 def stop(self):self.stop_event.set();return self.snapshot()
 def _evolve(self,family,duration,seed,popsize):
  rng=random.Random(seed);pop=[random_genome(family,rng) for _ in range(popsize)]
  active=0.;prev=time.monotonic();gen=0;best=None;hall=[]
  try:
   while active<duration and not self.stop_event.is_set():
    now=time.monotonic();dt=min(1.,now-prev);prev=now
    if self.pause_event.is_set():time.sleep(.06);continue
    active+=dt
    scored=[]
    for p in pop:
     met=metrics(family,p)
     scored.append((met['fitness'],dict(p),met))
    scored.sort(key=lambda x:x[0],reverse=True)
    champ=scored[0]
    if best is None or champ[0]>best[0]:
     best=champ
     hall.append({'generation':gen,'fitness':champ[0],'genome':champ[1],'metrics':champ[2]})
     hall=hall[-18:]
    gen+=1
    if gen<=4 or gen%6==0:
     with self.lock:
      self.state.elapsed=min(duration,active);self.state.generation=gen;self.state.evaluated+=len(scored)
      self.state.best={'genome':best[1],'metrics':best[2],'generation':next((v['generation'] for v in reversed(hall) if v['fitness']==best[0]),0)}
      self.state.hall=list(reversed(hall))
      self.state.history.append({'generation':gen,'elapsed':round(active,2),'best':best[0],'median':float(np.median([s[0] for s in scored]))})
      self.state.history=self.state.history[-500:]
    # tournament selection / elitism / crossover / mutation / random immigrants
    elites=[x[1] for x in scored[:max(2,popsize//6)]]
    def tournament():return max((rng.choice(scored) for _ in range(3)),key=lambda x:x[0])[1]
    new=list(elites)
    while len(new)<popsize:
     if rng.random()<.12:new.append(random_genome(family,rng))
     else:
      child=crossover(family,tournament(),tournament(),rng)
      new.append(mutate(family,child,rng,strength=max(.04,.2*(1-active/duration))))
    pop=new
    time.sleep(.04)
   with self.lock:
    self.state.elapsed=min(duration,active);self.state.status='saving'
    self.state.generation=gen
    if best:self.state.best={'genome':best[1],'metrics':best[2],'generation':hall[-1]['generation']}
   self.save()
   with self.lock:self.state.status='stopped' if self.stop_event.is_set() else 'completed'
  except Exception as ex:
   with self.lock:self.state.status='failed';self.state.error=repr(ex)
 def save(self):
  state=self.snapshot()
  if not state['id']:return
  dest=self.folder/state['id'];dest.mkdir(exist_ok=True)
  (dest/'results.json').write_text(json.dumps(state,indent=2))
  with (dest/'history.csv').open('w',newline='') as f:
   w=csv.DictWriter(f,['generation','elapsed','best','median']);w.writeheader();w.writerows(state['history'])
  if state['best']:
   mesh_for(state['family'],state['best']['genome']).export(dest/'champion.stl')
 def best_mesh(self,record=None):
  state=self.snapshot()
  if not state['best']:return None
  if record is None:record=state['best']
  m=mesh_for(state['family'],record['genome'])
  # preview max ~3k tris; legs in distinct mesh pieces do not imply printable union
  v=m.vertices;f=m.faces
  if len(f)>5000:
   f=f[::int(np.ceil(len(f)/5000))]
  return {'vertices':np.round(v,3).tolist(),'faces':f.tolist(),'note':'Visual preview assembled from primitives; not a watertight fabrication CAD model.'}
