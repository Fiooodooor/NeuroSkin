"""Matched-load T0 readout ablation; not a calibrated dynamic sensor model."""
import math
import numpy as np
from sensor_metrics import NOISE_SIGMA, FEATURE_SCALES, grouped_position_split, response_vector
from validation_design import select_decoder, shear_pairs


def wired_features(electrical, piezo, frequency_hz):
    """Signed RC amplitude at known excitation, not absolute per-film peaks.

    This is an amplitude surrogate, not a phase-resolved dynamic mechanics solve.
    Static force must not be reconstructed from a sustained PVDF DC voltage.
    """
    if not math.isfinite(frequency_hz) or not 0 <= frequency_hz <= 150.:
        raise ValueError('Frequency must be finite in 0..150 Hz')
    static = response_vector({'electrical':electrical})
    stage = np.asarray(electrical.get('hybrid_stage_channels',{}).get('readout_vector_pF_assumed',[]),float)
    films = np.asarray([c['initial_charge_amplifier_V'] for c in piezo['channels']],float)
    wiring = np.asarray(piezo['wiring_matrix'],float)
    tau, noise = float(piezo['leak_tau_s']), float(piezo['noise_rms_V_assumed'])
    if stage.ndim != 1 or len(stage)>2 or not np.isfinite(stage).all():
        raise ValueError('Invalid stage readout')
    if (wiring.ndim!=2 or wiring.shape[1]!=len(films) or not 1<=len(wiring)<=8
            or not np.isin(wiring,[-1.,0.,1.]).all() or np.any(np.sum(np.abs(wiring),axis=1)==0)
            or not np.isfinite(films).all() or not math.isfinite(tau) or tau<=0
            or not math.isfinite(noise) or noise<=0):
        raise ValueError('Invalid PVDF readout or RC assumptions')
    wt=2*math.pi*frequency_hz*tau
    dynamic=(wiring@films)*wt/math.hypot(1.,wt)
    if not np.isfinite(dynamic).all():raise ValueError('Nonfinite output amplitude')
    sigma=np.r_[NOISE_SIGMA,np.full(len(stage),.001),np.full(len(dynamic),noise)]
    return np.r_[static,stage,dynamic],sigma,len(stage)


def compare_readouts(x,y,groups,sigma,stage_count,*,seed=3322):
    """Fit ablations on the same samples, group split and shared noise realization."""
    x,y,sigma=np.asarray(x,float),np.asarray(y,float),np.asarray(sigma,float)
    if (x.ndim!=2 or not 8<=x.shape[1]<=17 or y.shape!=(len(x),5) or len(groups)!=len(x)
            or sigma.shape!=(x.shape[1],) or not np.isfinite(x).all() or not np.isfinite(y).all()
            or not np.isfinite(sigma).all() or np.any(sigma<=0) or not 0<=stage_count<=2
            or 7+stage_count>=x.shape[1]):
        raise ValueError('Invalid matched readout dataset')
    train,val,test=grouped_position_split(groups,seed)
    rng=np.random.default_rng(seed+13)
    noisy=x+rng.normal(size=x.shape)*sigma
    zero=rng.normal(size=(128,x.shape[1]))*sigma
    first_pvdf=7+stage_count
    saturated=np.abs(x[:,first_pvdf:])>1.65
    # Assumed ideal centered 3.3V range, applied to PVDF voltage only.
    noisy[:,first_pvdf:]=np.clip(noisy[:,first_pvdf:],-1.65,1.65)
    zero[:,first_pvdf:]=np.clip(zero[:,first_pvdf:],-1.65,1.65)
    variants=[('static',7)]
    if stage_count:variants.append(('static_and_stage',first_pvdf))
    variants.append(('static_stage_pvdf',x.shape[1]))
    reports={}
    for name,n in variants:
        pred,pred_zero,_,model=select_decoder(noisy[:,:n],y,train,val,test,sigma[:n],FEATURE_SCALES,zero[:,:n])
        error=pred-y[test]
        reports[name]={'channels':n,'model':model,'force_rmse_N':np.sqrt(np.mean(error[:,:3]**2,axis=0)).tolist(),
                       'force_rmse_norm_N':float(np.sqrt(np.mean(np.sum(error[:,:3]**2,axis=1)))),
                       'position_mae_mm':float(np.mean(np.linalg.norm(error[:,3:],axis=1))),
                       'false_positive_fraction_assumed':float(np.mean(np.linalg.norm(pred_zero[:,:3],axis=1)>.025))}
    return {'models':reports,'group_counts':{k:len({groups[i] for i in v}) for k,v in (('train',train),('validation',val),('test',test))},
            'sample_counts':{'train':len(train),'validation':len(val),'test':len(test)},
            'assumed_noise_std_channels':sigma.tolist(),'pvdf_saturated_sample_fraction_assumed':float(np.mean(np.any(saturated,axis=1))),
            'pvdf_ideal_span_V':[-1.65,1.65],'seed':seed,'shared_noise_realization':True}


def evaluate_fusion(family,genome,*,grid=3,frequency_hz=25.,seed=3322):
    from electromechanics import raw_mechanics,signals
    from piezoelectric import transduction
    from validation_contract import load_protocol,digest
    if grid not in (3,5):raise ValueError('Fusion grid must be 3 or 5')
    protocol=load_protocol()
    rad=min(3.,float(genome.get('pad_radius',3.))*.8)
    if not math.isfinite(rad) or rad<=0:raise ValueError('Invalid contact radius')
    points=[(x,y) for x in np.linspace(-rad,rad,grid) for y in np.linspace(-rad,rad,grid) if x*x+y*y<=rad*rad+1e-10]
    xdata,ydata,groups=[],[],[]
    layout=None
    for i,(x,y) in enumerate(points):
        for fz in protocol.load_cases['normal_forces_N']:
            for fx,fy in shear_pairs(protocol.load_cases['shear_forces_N']):
                mech=raw_mechanics(family,genome,'normal',force=[fx,fy,-fz],offset=(x,y))
                el=signals(family,genome,mech);piezo=transduction(family,genome,mech)
                vector,sigma,stage_count=wired_features(el,piezo,frequency_hz)
                identity=(tuple(c['member_index'] for c in piezo['channels']),tuple(tuple(row) for row in piezo['wiring_matrix']),tuple(sigma),stage_count)
                if layout is None:layout=identity
                elif layout!=identity:raise ValueError('Readout layout changed during load sweep')
                xdata.append(vector);ydata.append([fx,fy,-fz,x,y]);groups.append(i)
    result=compare_readouts(xdata,ydata,groups,sigma,stage_count,seed=seed)
    result.update(tier='T0',evidence='DIAGNOSTIC_ONLY',frequency_hz=frequency_hz,grid=grid,
                  stage_output_count=stage_count,pvdf_output_count=len(layout[1]),wiring_matrix=[list(r) for r in layout[1]],
                  genome_hash=digest({'family':family,'genome':genome}),protocol_hash=digest(protocol.model_dump(mode='json')),
                  limitations=['Known excitation amplitude/frequency; no solved dynamics or phase',
                               'At DC PVDF output is zero; no sustained-force piezoelectric claim',
                               'Assumed independent noise at final logical outputs; no measured covariance',
                               'Hall/capacitive transfer laws and ideal ADC clipping are uncalibrated',
                               'Ablation is synthetic and cannot change fitness or qualification'])
    return result
