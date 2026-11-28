"""Explicit two-stage structural layout around one shared, mechanically connected plate.

The top stage receives the contact load, the middle plate couples both stages,
and the lower stage is grounded to the robot chassis. There is NO parallel
short-circuit path from the top pad to the bottom base. 3D continuum FEM uses
these exact centerlines and the same intermediate plate as the 3D viewer.
"""
from __future__ import annotations
import math
import numpy as np
from hybrid_library import BY_ID
from types import SimpleNamespace
from engine import LIMITS


def mid_height(genome):
 return float(genome['height'])*float(genome.get('hybrid_split',.49))


def mid_radius(genome):
 return max(float(genome['radius'])*1.18,float(genome['pad_radius'])*1.5+1.2)


def stage_descriptors(family, genome):
 spec=BY_ID.get(genome.get('hybrid_id'))
 if spec is None and genome.get('hybrid_id')=='procedural':
  upper_family=str(genome.get('hybrid_upper_family',family))
  lower_family=str(genome.get('hybrid_lower_family','quadrant'))
  if upper_family != family or upper_family not in LIMITS or lower_family not in LIMITS:
   raise ValueError('Procedural hybrid stage family mismatch')
  spec=SimpleNamespace(id='procedural',upper_family=upper_family,lower_family=lower_family,
       upper_topology=str(genome.get('hybrid_upper_topology','arched')),
       lower_topology=str(genome.get('hybrid_lower_topology','orthogonal')),
       split=.5,upper_scale=1.,lower_scale=1.,phase=0.)
 if spec is None:raise ValueError('Unknown hybrid architecture')
 H=float(genome['height'])
 split=float(genome.get('hybrid_split',spec.split))
 if not .34<=split<=.66:raise ValueError('Hybrid split must stay within 0.34..0.66')
 mid=H*split
 # stage coordinates both begin at z=0.8; upper is lifted by mid-0.8.
 for stage, stage_family, topology, local_h, shift, scale in (
    ('lower', spec.lower_family, spec.lower_topology, mid, 0.,float(genome.get('hybrid_lower_scale',spec.lower_scale))),
    ('upper', spec.upper_family, spec.upper_topology, H-mid+.8, mid-.8,float(genome.get('hybrid_upper_scale',spec.upper_scale)))):
  g=dict(genome)
  for key,(lo,hi) in LIMITS[stage_family].items():
   if key not in g:g[key]=.5*(lo+hi)
  g['hybrid_id']='none'  # stage stiffness / PVDF cannot recurse into the full hybrid
  from pvdf_array import film_count
  n=film_count(genome)
  g['piezo_count']=(n+1)//2 if stage=='upper' else n//2
  g['height']=local_h
  g['radius']=float(genome['radius'])*(.98 if stage=='lower' else 1.02)
  g['thickness']=max(.22,float(genome['thickness'])*scale)
  g['topology']=topology
  g['pad_offset_x']=float(genome.get('pad_offset_x',0.))*.25
  g['pad_offset_y']=float(genome.get('pad_offset_y',0.))*.25
  if stage=='upper':
   # Rotation is applied exactly once to the generated upper-stage mesh
   # and the 6-DOF stage stiffness; adding it again here would double-rotate
   # geometric phase and break proxy/HEX8 consistency.
   if stage_family=='chiral':g['twist']=abs(float(g.get('twist',.7)))
  if stage=='lower' and stage_family=='chiral' and (spec.id=='h10_dual_chiral' or (spec.id=='procedural' and genome.get('hybrid_opposed_chirality',0))):
   g['twist']=-abs(float(g.get('twist',.7)))
  yield stage,stage_family,g,shift


def make_struts(family,genome,single_stage_fn):
 out=[]
 for stage,subfamily,sg,shift in stage_descriptors(family,genome):
  paths=single_stage_fn(subfamily,sg)
  for points,r,tag in paths:
   pts=np.asarray(points,float).copy()
   if stage=='upper':
    angle=float(genome.get('hybrid_phase',0.))
    ca,sa=math.cos(angle),math.sin(angle)
    R=np.array([[ca,-sa],[sa,ca]])
    pts[:,:2]=pts[:,:2]@R.T
   pts[:,2]+=shift
   out.append((pts,r,tag))
 return out


def stage_models(family,genome):
 """Bind each local stiffness model to the globally selected physical films."""
 from advanced import _single_stage_struts
 from pvdf_array import choose_film_members
 descriptors=list(stage_descriptors(family,genome))
 paths=make_struts(family,genome,_single_stage_struts)
 selected=set(choose_film_members(paths,genome))
 start=0
 for stage,subfamily,sg,shift in descriptors:
  count=len(_single_stage_struts(subfamily,sg))
  sg['_film_indices']=tuple(i-start for i in sorted(selected) if start<=i<start+count)
  sg['piezo_count']=len(sg['_film_indices'])
  start+=count
  yield stage,subfamily,sg,shift
 if start!=len(paths):raise ValueError('Stage member mapping differs from global geometry')


def stage_stiffnesses(family,genome,single_stage_k_fn,models=None):
 result=[]
 for stage,subfamily,sg,shift in (stage_models(family,genome) if models is None else models):
  K=single_stage_k_fn(subfamily,sg,E=float(genome.get('material_E',1.0)))
  if stage=='upper':
   angle=float(genome.get('hybrid_phase',0.))
   ca,sa=math.cos(angle),math.sin(angle)
   R=np.array([[ca,-sa,0.],[sa,ca,0.],[0.,0.,1.]])
   T=np.zeros((6,6));T[:3,:3]=R;T[3:,3:]=R
   K=T@K@T.T
  result.append((stage,K))
 return result
