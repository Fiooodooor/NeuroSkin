"""NeuroSkin electromechanical *surrogate*, version 0.6.

Units: mm,N,MPa; capacitive outputs in pF; magnet proxy in mT.
This is NOT an FEA solution, Maxwell-field simulation, or a calibrated sensor.
All electrode gaps, dielectric factors, transduction constants and noise are explicit assumptions.
"""
import math
import numpy as np
from advanced import curve_stiffness, structural_struts
from engine import solve_force, skew

EPS0_PF_MM = 0.0088541878128
CASES={
 'normal': ('Normal pressure -Fz',[0,0,-0.1],0,(0,0),0),
 'shear_x': ('Lateral shear +Fx',[0.03,0,0],0,(0,0),0),
 'shear_y': ('Lateral shear +Fy',[0,0.03,0],0,(0,0),0),
 'torsion': ('Torsion Mz',[0,0,0],0.02,(0,0),0),
 'bend_x': ('Bending Mx',[0,0,-0.04],0,(0,0),0.02),
 'stretch_x': ('Substrate tensile strain 5% (proxy)',[0,0,0],0,(0,0),0),
 'offcenter': ('Off-centre pressure',[0,0,-0.1],0,(3,2),0),
 'compression': ('Substrate compression 5% (proxy)',[0,0,0],0,(0,0),0),
}

def _hybrid_raw_mechanics(family, genome, case='normal', force=None, moment=None, offset=None, strain=None):
 """Two rigid-body stage DOFs linked in SERIES; returns bottom-only reactions.

 The 6DOF stage stiffnesses are approximate beam models; they are not a
 replacement for HEX8. Intermediate plate displacement and channel groups
 are available for piezoelectric/optical-electrical transfer calculations.
 """
 from hybrid_geometry import stage_descriptors,stage_stiffnesses,mid_height
 from advanced import _single_stage_curve_stiffness,_single_stage_struts,stage_member_local_matrices
 _,base_force,mz,off,mx=CASES[case]
 F=np.asarray(base_force if force is None else force,dtype=float)
 off=off if offset is None else offset
 strain=(.05 if case=='stretch_x' else -.05 if case=='compression' else 0.) if strain is None else float(strain)
 M=np.array([mx,0,mz],float) if moment is None else np.asarray(moment,float)
 load=np.array([*F,M[0]+off[1]*F[2],M[1]-off[0]*F[2],M[2]+off[0]*F[1]-off[1]*F[0]])
 stages=list(stage_descriptors(family,genome))
 K=dict(stage_stiffnesses(family,genome,_single_stage_curve_stiffness))
 lower_stage=stages[0]
 _,subfam,sg,_=lower_stage
 members=stage_member_local_matrices(subfam,sg,E=genome.get('material_E',1.))
 from neuroskin_multiscale import transport
 T=transport([0.,0.,genome['height']-mid_height(genome)])
 lower_load=T.T@load
 if abs(strain)>0:
  for pts,kl,B in members:
   a=pts[0]
   moved=np.array([a[0]*strain,0.,0.])
   lower_load+=B.T@kl@moved
 u_lower=np.linalg.solve(K['lower'],lower_load)
 u_upper=np.linalg.solve(K['upper'],load)
 total=T@u_lower+u_upper
 foot=[]
 for pts,kl,B in members:
  moved=np.array([pts[0][0]*strain,0.,0.])
  reaction=kl@(B@u_lower-moved)
  foot.append([float(x) for x in reaction])
 return {'displacement_mm':total[:3].tolist(),'rotation_rad':total[3:].tolist(),
         'stage_displacements_mm':{'upper':u_upper[:3].tolist(),'lower':u_lower[:3].tolist()},
         'stage_rotations_rad':{'upper':u_upper[3:].tolist(),'lower':u_lower[3:].tolist()},
         'interface_displacement_mm':u_lower[:3].tolist(),
         'foot_reactions_N':foot,'applied_force_N':F.tolist(),
         'applied_moment_Nmm':M.tolist(),'offset_mm':list(off),
         'substrate_strain':strain,'hybrid_id':genome.get('hybrid_id'),
         'K_N_per_mm_proxy':np.linalg.solve(T@np.linalg.solve(K['lower'],T.T)+np.linalg.solve(K['upper'],np.eye(6)),np.eye(6)).tolist(),
         'stage_loads_N_Nmm':{'lower':(T.T@load).tolist(),'upper':load.tolist()},
         'model':'two_rigid_stage_6DOF_transported_series_proxy'}

def raw_mechanics(family, genome, case='normal', force=None, moment=None, offset=None, strain=None):
 if case not in CASES:raise ValueError('Unknown load case')
 if genome.get('hybrid_id','none') not in ('none',None,''):
  return _hybrid_raw_mechanics(family,genome,case,force,moment,offset,strain)
 _,base_force,mz,off,mx=CASES[case]
 F=np.asarray(base_force if force is None else force,dtype=float)
 off=off if offset is None else offset
 strain=(.05 if case=='stretch_x' else -.05 if case=='compression' else 0.) if strain is None else float(strain)
 K=curve_stiffness(family,genome,E=genome.get('material_E',1.0))
 M=np.array([mx,0,mz],float) if moment is None else np.asarray(moment,float)
 load=np.array([*F,M[0]+off[1]*F[2],M[1]-off[0]*F[2],M[2]+off[0]*F[1]-off[1]*F[0]])
 # Very simplified substrate stretch: prescribed affine movement at strut foot.
 # Solve equivalent nodal load on rigid pad induced by moving the bases.
 paths=structural_struts(family,genome)
 if abs(strain)>0:
  for pts,r,_ in paths:
   a,b=pts[0],pts[-1]; d=b-a;L=np.linalg.norm(d);n=d/L
   arc=sum(np.linalg.norm(y-x) for x,y in zip(pts[:-1],pts[1:]));r=float(r)
   A=np.pi*r*r;I=np.pi*r**4/4; E=genome.get('material_E',1.0)
   kl=(E*A/arc*(L/arc)**2)*np.outer(n,n)+(12*E*I/arc**3)*(np.eye(3)-np.outer(n,n))
   rp=b-np.array([0,0,genome['height']]); B=np.column_stack((np.eye(3),-skew(rp)))
   moved=np.array([a[0]*strain,0.,0.])
   load+=B.T@kl@moved
 u=np.linalg.solve(K,load)
 foot=[]
 for pts,r,_ in paths:
  a,b=pts[0],pts[-1];d=b-a;L=np.linalg.norm(d);n=d/L
  arc=sum(np.linalg.norm(y-x) for x,y in zip(pts[:-1],pts[1:]));r=float(r)
  A=np.pi*r*r;I=np.pi*r**4/4;E=genome.get('material_E',1.0)
  kl=(E*A/arc*(L/arc)**2)*np.outer(n,n)+(12*E*I/arc**3)*(np.eye(3)-np.outer(n,n))
  rp=b-np.array([0,0,genome['height']]);B=np.column_stack((np.eye(3),-skew(rp)))
  moved=np.array([a[0]*strain,0,0])
  reaction=kl@(B@u-moved)
  foot.append([float(x) for x in reaction])
 return {'displacement_mm':u[:3].tolist(),'rotation_rad':u[3:].tolist(),'foot_reactions_N':foot,'applied_force_N':F.tolist(),'applied_moment_Nmm':M.tolist(),'offset_mm':list(off),'substrate_strain':strain,'K_N_per_mm_proxy':K.tolist()}

def signals(family,genome,mechanics,readout='capacitive'):
 """Explicit synthetic circuit transfer. Not measured: default dielectric 2.8, 0.45 mm gap.
    4 basal capacitive pressure electrodes + two differential side capacitors + torsional Hall proxy.
 """
 u=np.array(mechanics['displacement_mm']);rot=np.array(mechanics['rotation_rad'])
 f=np.array(mechanics['foot_reactions_N']);fzs=f[:,2]
 if len(fzs)!=4:
  # group radial legs by quadrant to yield common 4-channel interface
  pts=structural_struts(family,genome)
  q=np.zeros(4)
  for (xyz,_,_),fz in zip(pts,fzs):
   foot=xyz[0];ix=(0 if foot[0]<0 else 1)+2*(0 if foot[1]<0 else 1);q[ix]+=fz
  fzs=q
 # Measurable geometry choices, with fixed assumed electronic noise: the
 # optimiser cannot cheat by arbitrarily lowering the input noise floor.
 gap=float(genome.get('dielectric_gap_mm',.45))
 epsr=float(genome.get('dielectric_epsilon_r',2.8))
 area=float(genome.get('electrode_area_mm2',7.0))
 compliance=float(genome.get('mount_compliance_mm_N',.09))
 if not (.20<=gap<=.8 and 2.<=epsr<=5. and 2.<=area<=12. and .025<=compliance<=.55):
  raise ValueError('Electrical geometry or mount compliance outside assumed engineering limits')
 C0=EPS0_PF_MM*epsr*area/gap
 # Equivalent dielectric displacement under per-foot reaction. Clipping is
 # numeric stabilization, NOT proof that electrical bottom-out is survivable.
 normal_deflection=np.clip(-fzs*compliance,-.65*gap,.80*gap)
 cpad=EPS0_PF_MM*epsr*area/np.maximum(.08,gap-normal_deflection)
 # lateral facing capacitor differential pair; 0.1 mm-equivalent change per 1mm pad shift
 lateral_gap=0.70; lateral_area=3.5
 cxp=EPS0_PF_MM*epsr*lateral_area/np.clip(lateral_gap-u[0]*.12,.18,2.)
 cxm=EPS0_PF_MM*epsr*lateral_area/np.clip(lateral_gap+u[0]*.12,.18,2.)
 cyp=EPS0_PF_MM*epsr*lateral_area/np.clip(lateral_gap-u[1]*.12,.18,2.)
 cym=EPS0_PF_MM*epsr*lateral_area/np.clip(lateral_gap+u[1]*.12,.18,2.)
 # torsion magnetic signal is an assumed local linearization of a Hall pickup
 hall=5.0*rot[2]  # mT/radian, illustrative
 out={'pressure_delta_pF':np.round(cpad-C0,7).tolist(),
      'lateral_delta_pF':[round(cxp-cxm,7),round(cyp-cym,7)],
      'hall_torsion_delta_mT':round(float(hall),7),
      'pressure_baseline_pF':round(C0,6),
      'pressure_dielectric_motion_mm':np.round(normal_deflection,7).tolist(),
      'pressure_sensor_geometry':{'electrode_area_mm2':area,'dielectric_gap_mm':gap,'dielectric_epsilon_r_assumed':epsr,
                                  'mount_compliance_mm_per_N_assumed':compliance},
      'noise_assumptions':{'pressure_rms_pF':.001,'lateral_rms_pF':.0003,'hall_rms_mT':.002}}
 if genome.get('hybrid_id','none') not in ('none',None,'') and 'stage_displacements_mm' in mechanics:
  stage=mechanics['stage_displacements_mm']
  def capacitance(d):
   # Separate assumed electrode gaps at midplate and top; no solved electric field.
   delta=np.clip(.20*max(0.,-float(d[2])),0.,.75*gap)
   return float(EPS0_PF_MM*epsr*area/max(gap-delta,.05)-C0)
  upper_c=capacitance(stage['upper']);lower_c=capacitance(stage['lower'])
  sensor_mode=int(genome.get('hybrid_sensor_mode',0))
  if sensor_mode not in (0,1,2):raise ValueError('Invalid hybrid sensor wiring mode')
  options={0:('independent',(upper_c,lower_c)),
           1:('common_plus_difference',(upper_c+lower_c,upper_c-lower_c)),
           2:('common_only',(upper_c+lower_c,))}
  mode_name,active_outputs=options[sensor_mode]
  out['hybrid_stage_channels']={
    'upper_capacitance_delta_pF_assumed':upper_c,
    'lower_capacitance_delta_pF_assumed':lower_c,
    'readout_mode':mode_name,
    'readout_vector_pF_assumed':list(active_outputs),
    'sum_pF_assumed':upper_c+lower_c,
    'difference_pF_assumed':upper_c-lower_c,
    'upper_displacement_mm':stage['upper'],
    'lower_displacement_mm':stage['lower'],
    'source':'Two-series-6DOF stage displacement + assumed parallel-plate readouts; no calibrated field solve'}
 if readout=='resistive':
  # illustration of *relative* piezoresistance; no absolute resistance or pressure calibration
  out['resistive_delta_percent']=np.round(100*(np.exp(-normal_deflection/0.18)-1),4).tolist()
 return out

def examine(family,genome,case='normal',force=None,moment=None,offset=None,strain=None,frequency_hz=25.):
 mech=raw_mechanics(family,genome,case,force,moment,offset,strain)
 from piezoelectric import response as piezo_response
 piezo=piezo_response(family,genome,mech,frequency_hz=frequency_hz)
 return {'case':case,'description':CASES[case][0],'mechanics':mech,'piezoelectric':piezo,'electrical':signals(family,genome,mech),
  'validity':'Analytical linear-elastic beam surrogate plus assumed capacitance/Hall transfer; not continuum FEM or measured hardware.'}

def sweep(family,genome,case='normal',steps=17):
 if not 3<=steps<=101:raise ValueError('steps must be 3..101')
 vals=np.linspace(0,1,steps);rows=[]
 for t in vals:
  _,F,mz,off,mx=CASES[case]
  if case=='stretch_x': result=examine(family,genome,case,strain=.05*t)
  elif case=='compression':result=examine(family,genome,case,strain=-.05*t)
  else:result=examine(family,genome,case,force=np.array(F)*t,moment=np.array([mx,0,mz])*t,offset=off)
  el=result['electrical'];me=result['mechanics']
  rows.append({'input_fraction':round(float(t),4),'pressure_sum_pF':round(float(sum(el['pressure_delta_pF'])),7),
   'pressure_channels_pF':el['pressure_delta_pF'],'lateral_x_pF':el['lateral_delta_pF'][0],
   'lateral_y_pF':el['lateral_delta_pF'][1],'hall_mT':el['hall_torsion_delta_mT'],'piezo_peak_V':result['piezoelectric']['peak_V'],
   'ux_mm':round(me['displacement_mm'][0],6),'uz_mm':round(me['displacement_mm'][2],6),'rotation_z_rad':round(me['rotation_rad'][2],7)})
 return {'case':case,'rows':rows,'validity':'Predicted electrical signals from assumed geometry and transfer laws. Not verified with circuits or materials.'}

def screening_electrical(family,p):
 """Cheap screening features, with explicit noise margins. This is not force accuracy."""
 scenarios=[examine(family,p,x) for x in ('normal','shear_x','torsion','offcenter','stretch_x')]
 features=[]
 for r in scenarios:
  e=r['electrical']; features.append(np.array(e['pressure_delta_pF']+e['lateral_delta_pF']+[e['hall_torsion_delta_mT']]))
 f=np.array(features)
 noise=np.array([.001]*4+[.0003]*2+[.002])
 # Signal-to-noise for normal and shear, and sensitivity to nuisance movement.
 norm=float(np.linalg.norm(f[0]/noise));shear=float(np.linalg.norm(f[1]/noise))
 nuisance=float(np.linalg.norm(f[4]/noise))
 # Do not claim observability from the sum of these metrics
 return {'normal_snr_proxy':round(norm,3),'shear_snr_proxy':round(shear,3),
    'substrate_strain_signal_snr_proxy':round(nuisance,3),'offcentre_similarity_proxy':round(float(np.dot(f[1],f[3])/(1e-12+np.linalg.norm(f[1])*np.linalg.norm(f[3]))),4),
    'electric_response_status':'Assumed electrostatic/magnetic transfer; no field solving or actual circuit noise.'}
