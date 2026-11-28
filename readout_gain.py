"""Validation-only ideal charge-amplifier feedback study, no genome mutation."""
import math
import numpy as np
from validation_design import select_decoder


def study_feedback(x,y,train,val,test,sigma,first_pvdf,nominal_pf,tau_s,noise,zero,scales):
    """Sweep supported Cf values; hold tau constant by adjusting Rf.

    Use train/validation saturation first, then validation normalized decoder
    error. Test labels and test clipping never enter the choice. This ideal
    voltage-noise model is not a real amplifier stability/noise calculation.
    """
    if not math.isfinite(nominal_pf) or not 20<=nominal_pf<=220 or not math.isfinite(tau_s) or tau_s<=0:
        raise ValueError('Feedback study requires 20..220 pF and positive finite tau')
    trials=[]
    candidates=sorted({20.,40.,80.,120.,160.,220.,float(nominal_pf)})
    def data(cf):
        scaled=x.copy()
        scaled[:,first_pvdf:]*=nominal_pf/cf
        saturated=np.any(np.abs(scaled[:,first_pvdf:])>1.65,axis=1)
        noisy=scaled+noise
        noisy[:,first_pvdf:]=np.clip(noisy[:,first_pvdf:],-1.65,1.65)
        return noisy,saturated
    for cf in candidates:
        noisy,saturated=data(cf)
        # Do not evaluate the outer test at all for competing gains.
        _,_,_,model=select_decoder(noisy,y,train,val,np.array([],dtype=int),sigma,scales,zero)
        trials.append({'feedback_pF':cf,'train_saturated_fraction':float(np.mean(saturated[train])),
                       'validation_saturated_fraction':float(np.mean(saturated[val])),
                       'validation_normalized_rmse':model['validation_normalized_rmse']})
    selected=min(trials,key=lambda t:(max(t['train_saturated_fraction'],t['validation_saturated_fraction']),
                                      t['validation_normalized_rmse'],abs(math.log(t['feedback_pF']/nominal_pf)),t['feedback_pF']))
    cf=selected['feedback_pF'];noisy,saturated=data(cf)
    pred,pred_zero,_,model=select_decoder(noisy,y,train,val,test,sigma,scales,zero)
    err=pred-y[test]
    return {'nominal_feedback_pF':nominal_pf,'selected_feedback_pF':cf,
            'fixed_tau_s':tau_s,'required_feedback_resistance_Gohm_assumed':1000*tau_s/cf,
            'validation_trials':trials,'selection_policy':'minimize_train_validation_saturation_then_validation_normalized_rmse',
            'test_saturated_fraction':float(np.mean(saturated[test])),
            'nominal_test_saturated_fraction':float(np.mean(np.any(np.abs(x[test,first_pvdf:])>1.65,axis=1))),
            'test_force_rmse_norm_N':float(np.sqrt(np.mean(np.sum(err[:,:3]**2,axis=1)))),
            'test_position_mae_mm':float(np.mean(np.linalg.norm(err[:,3:],axis=1))),
            'test_false_positive_fraction_assumed':float(np.mean(np.linalg.norm(pred_zero[:,:3],axis=1)>.025)),
            'model':model,'genome_modified':False,
            'limitations':['Ideal feedback scaling at fixed RC time constant; Rf adjusted algebraically',
                           'Fixed output noise assumption; no op-amp, parasitic, stability or resistor-noise model',
                           'Candidate gain choice uses training and validation only; test is a held-out diagnostic']}
