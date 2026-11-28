"""Multi-film PVDF dynamic readout *surrogate*, not coupled piezoelectric FEM.

Units: mm, N, MPa, pC, pF, V, seconds. Distinguishes individual channels,
parallel charge addition, and signed differential wiring. A missing piezo_count
preserves the original single-film archival behavior. PVDF/adhesive stiffness,
poling, bond shear lag, wiring parasitics, and real strain fields are NOT modeled.
"""
from __future__ import annotations
import math
import numpy as np
from pvdf_array import choose_film_members, layout_metrics

D31_PC_PER_N=-23.0
D33_PC_PER_N=33.0
EPS0_PF_MM=.0088541878128
EPSR=12.0
E_PVDF_MPA=2000.0
NOISE_V_RMS=.003


def _amplitude(volt, tau, frequency_hz):
    w=2*math.pi*frequency_hz
    mag=w*tau/math.sqrt(1+(w*tau)**2) if w>0 else 0.
    return float(volt)*mag


def transduction(family,genome,mechanics):
    p=lambda key,default:float(genome.get(key,default))
    width=p('piezo_width_mm',2.5)
    length=p('piezo_span_mm',4.0)
    thickness=p('piezo_thickness_um',28.0)/1000.
    orientation=p('piezo_orientation_rad',0.)
    u=np.array(mechanics['displacement_mm'],float)
    rot=np.array(mechanics['rotation_rad'],float)
    h=max(.5,p('height',6.0))
    pos=p('piezo_position',.5)
    from advanced import structural_struts
    paths=structural_struts(family,genome)
    from laminate_fem import effective_film_properties, film_interval
    chosen=choose_film_members(paths,genome)
    layout=layout_metrics(paths,genome,chosen)
    channels=[]
    for idx in chosen:
        path=np.array(paths[idx][0],float)
        arc=max(.1,float(np.linalg.norm(np.diff(path,axis=0),axis=1).sum()))
        chord=path[-1]-path[0]
        chord/=max(.001,np.linalg.norm(chord))
        if 'stage_displacements_mm' in mechanics:
            from hybrid_geometry import mid_height
            mid=mid_height(genome)
            stage='upper' if path[0,2]>mid-.25 else 'lower'
            uv=np.asarray(mechanics['stage_displacements_mm'][stage],float)
            rv=np.asarray(mechanics['stage_rotations_rad'][stage],float)
            target_h=h if stage=='upper' else mid
            anchor=path[-1]-np.array([p('pad_offset_x',0.),p('pad_offset_y',0.),target_h])
            displacement=uv+np.cross(rv,anchor)
            stage_rot=rv
        else:
            stage='single'
            anchor=path[-1]-np.array([p('pad_offset_x',0.),p('pad_offset_y',0.),h])
            displacement=u+np.cross(rot,anchor)
            stage_rot=rot
        axial=float(np.dot(displacement,chord)/arc)
        transverse=float(np.linalg.norm(displacement-np.dot(displacement,chord)*chord))
        bending=2.0*transverse*thickness/(arc*arc)
        local_strain=axial*math.cos(orientation)+bending*math.sin(orientation)
        local_strain+=(stage_rot[1]*math.cos(orientation)-stage_rot[0]*math.sin(orientation))*(thickness/arc)*(.2+.6*pos)
        local_strain+=float(mechanics.get('substrate_strain',0.))*math.cos(orientation)**2
        _,_,film_lo,film_hi=film_interval(path,genome)
        bond=effective_film_properties(genome,film_hi-film_lo,float(paths[idx][1]))
        strain=local_strain*p('piezo_strain_transfer',.40)*bond['shear_lag_transfer']
        stress=bond['pvdf_E_MPa']*strain
        axial_force=stress*bond['effective_width_mm']*thickness
        dcoeff=D33_PC_PER_N if int(genome.get('piezo_mode',0))==1 else D31_PC_PER_N
        charge=dcoeff*axial_force
        capacitance=EPS0_PF_MM*EPSR*width*length/max(thickness,.001)
        feedback=p('piezo_feedback_pf',100.)
        initial=charge/feedback
        channels.append({'member_index':int(idx),'stage':stage,'base_xy_mm':path[0,:2].round(5).tolist(),
            'strain_proxy':float(strain),'strain_over_2_percent':bool(abs(strain)>.02),
            'charge_pC':float(charge),'capacitance_pF':float(capacitance),
            'initial_charge_amplifier_V':float(initial),
            'arc_length_mm':float(arc),'film_length_mm':min(length,arc*.82),
            'adhesive_shear_lag_transfer':bond['shear_lag_transfer'],
            'adhesive_G_MPa_assumed':bond['adhesive_G_MPa'],
            'pvdf_E_MPa_assumed':bond['pvdf_E_MPa']})
    volts=np.asarray([c['initial_charge_amplifier_V'] for c in channels],float)
    charges=np.asarray([c['charge_pC'] for c in channels],float)
    count=len(volts)
    wiring=int(genome.get('piezo_wiring',0))
    if wiring not in (0,1,2,3,4): raise ValueError('PVDF wiring mode must be 0..4')
    # Mode 0: all channels independently measured. A displayed waveform is from
    # the strongest channel, NOT a fictional voltage summed across amplifiers.
    # Mode 1: signed charge sum on a single assumed charge amp.
    # Mode 2: opposing-polarity differential sum (specific wiring/poling required).
    if wiring==0:
        primary=int(np.argmax(np.abs(volts)))
        effective_v=float(volts[primary]);effective_q=float(charges[primary]);effective_c=float(channels[primary]['capacitance_pF'])
        mode_name='independent';weights=np.eye(count).tolist()
    else:
        signs=np.ones(count)
        if wiring in (2,3):
            # Opposed sensor halves referenced to global X or Y axis.
            positions=np.asarray([c['base_xy_mm'] for c in channels])
            axis=0 if wiring==2 else 1
            signs=np.where(positions[:,axis]>=float(np.mean(positions[:,axis])),1.,-1.)
            if count==1:signs[:]=1.0
        elif wiring==4:
            # Alternating poling / wiring around azimuth (requires physical wiring).
            positions=np.asarray([c['base_xy_mm'] for c in channels]);mean=positions.mean(axis=0)
            order=np.argsort(np.arctan2(positions[:,1]-mean[1],positions[:,0]-mean[0]))
            signs[order]=np.where(np.arange(count)%2==0,1.,-1.)
        effective_q=float(np.dot(signs,charges))
        effective_c=float(sum(c['capacitance_pF'] for c in channels))
        effective_v=effective_q/max(p('piezo_feedback_pf',100.),1e-12)
        mode_name={1:'signed_sum',2:'differential_x',3:'differential_y',4:'alternating_polarity'}[wiring]
        weights=[signs.astype(int).tolist()]
    delta_xy=np.asarray([c['base_xy_mm'] for c in channels],float)
    mean_xy=np.mean(delta_xy,axis=0)
    xsign=np.where(delta_xy[:,0]>=mean_xy[0],1.,-1.)
    ysign=np.where(delta_xy[:,1]>=mean_xy[1],1.,-1.)
    return {
      'strain_proxy':float(max((c['strain_proxy'] for c in channels),key=abs)),
      'max_abs_strain_proxy':float(max(abs(c['strain_proxy']) for c in channels)),
      'strain_over_2_percent':bool(any(c['strain_over_2_percent'] for c in channels)),
      'charge_pC':effective_q,'capacitance_pF':effective_c,
      'initial_charge_amplifier_V':effective_v,
      'leak_tau_s':p('piezo_leak_tau_s',.75),'noise_rms_V_assumed':NOISE_V_RMS,
      'd_coefficient_pC_per_N_assumed':float(D33_PC_PER_N if int(genome.get('piezo_mode',0)) else D31_PC_PER_N),
      'piezo_position':pos,'film_count':count,'layout':layout,'channels':channels,
      'wiring':mode_name,'wiring_matrix':weights,
      'differential_charge_x_pC_proxy':float(np.dot(xsign,charges)),
      'differential_charge_y_pC_proxy':float(np.dot(ysign,charges)),
      'total_pvdf_mass_g_estimate':count*width*min(length,4.0)*thickness*.00178,
      'note':'Fast readout uses composite-augmented 6DOF mechanics and adhesive shear-lag. Finalist FEM computes local embedded-film strain; not coupled field FEM.'}


def response(family,genome,mechanics,frequency_hz=25.,steps=80):
    """Dynamic PVDF response with RC high pass on each independently wired channel."""
    p=transduction(family,genome,mechanics)
    tau=p['leak_tau_s'];frequency_hz=float(frequency_hz)
    amplitude=_amplitude(p['initial_charge_amplifier_V'],tau,frequency_hz)
    channel_amps=np.asarray([_amplitude(c['initial_charge_amplifier_V'],tau,frequency_hz) for c in p['channels']],float)
    # Matched-filter SNR is only a hypothetical upper-bound when channels are
    # independent and noise uncorrelated; the actual plotted output remains
    # the strongest channel's voltage, not sqrt-sum-squared volts.
    if p['wiring']=='independent':
        snr=float(np.linalg.norm(channel_amps)/NOISE_V_RMS)
    else:
        snr=abs(amplitude)/NOISE_V_RMS
    duration=max(.1,4./max(.01,frequency_hz))
    t=np.linspace(0,duration,steps)
    sinusoid=(np.sin(2*math.pi*frequency_hz*t)*amplitude).tolist()
    hold_t=np.linspace(0,4*tau,steps)
    hold=(p['initial_charge_amplifier_V']*np.exp(-hold_t/tau)).tolist()
    channels=[]
    for c,v in zip(p['channels'],channel_amps):
        channels.append(dict(c,peak_V=float(abs(v)),dynamic_snr_proxy=float(abs(v)/NOISE_V_RMS)))
    return dict(p,channels=channels,frequency_hz=frequency_hz,
        amplitude_V_rms=float(abs(amplitude)/math.sqrt(2)),peak_V=float(abs(amplitude)),
        dynamic_snr_proxy=snr,
        time_s=t.round(5).tolist(),waveform_V=np.round(sinusoid,7).tolist(),
        hold_time_s=hold_t.round(5).tolist(),step_hold_V=np.round(hold,7).tolist(),
        validity='Linearized multi-film PVDF RC surrogate; independence and polarity assumed. No coupled PVDF FEM.')


def screen(family,genome):
    from electromechanics import raw_mechanics
    normal=response(family,genome,raw_mechanics(family,genome,'normal'),25.)
    shear=response(family,genome,raw_mechanics(family,genome,'shear_x'),80.)
    substrate=response(family,genome,raw_mechanics(family,genome,'stretch_x'),.2)
    desirable=max(normal['dynamic_snr_proxy'],shear['dynamic_snr_proxy'])
    detect=1-math.exp(-desirable/8.)
    nuisance=1/(1+substrate['dynamic_snr_proxy']/30.)
    peak_strain=max(normal['max_abs_strain_proxy'],shear['max_abs_strain_proxy'])
    safe=math.exp(-2.5*max(0.,peak_strain/.02-1.))
    # Layout stability: penalize offset, but only lightly when the primary
    # structures themselves are asymmetric; true bonded stiffness is excluded.
    imbalance=normal['layout']['normalized_imbalance']
    safe*=math.exp(-0.8*imbalance)
    for channel in normal['channels']:
        if genome.get('piezo_span_mm',4.)>channel['arc_length_mm']*.95:safe*=.85
    # More independent channels cost readout power/area: coarse engineering
    # penalty prevents '4 films' being a free score improvement.
    n=normal['film_count'];readout_cost=(n-1)*(.012 if normal['wiring']=='independent' else .004)
    score=100*(.72*detect+.28*nuisance)*safe - 100*readout_cost
    return {'piezo_score':round(max(0.,score),4),
      'piezo_impact_SNR_proxy':round(normal['dynamic_snr_proxy'],4),
      'piezo_shear_SNR_proxy':round(shear['dynamic_snr_proxy'],4),
      'piezo_strain_nuisance_SNR_proxy':round(substrate['dynamic_snr_proxy'],4),
      'piezo_valid':bool(peak_strain<=.02),
      'piezo_overstrain_factor':round(safe,5),
      'piezo_channels':n,'piezo_layout_imbalance':round(imbalance,5),
      'piezo_wiring':normal['wiring'],
      'piezo_model':'PVDF multi-channel d31/d33 + RC highpass, small-displacement beam strain surrogate, assumed noise'}
