"""Opt-in electronics co-design objective using assumed readout, not circuit specs."""
import math
import numpy as np
from electronics_budget import budget_for_response


def score_budgets(budgets):
    if not budgets:raise ValueError('Readout cases required')
    scores=[];ratios=[];clipped=[]
    for b in budgets:
        peak=np.asarray(b['pvdf_output_peak_V_assumed'],float)
        span=float(b['pvdf_peak_headroom_V_assumed'])
        noise=float(b['adc_total_rms_noise_V_assumed'])
        if peak.ndim!=1 or not len(peak) or not np.isfinite(peak).all() or np.any(peak<0) or not math.isfinite(span) or span<=0 or not math.isfinite(noise) or noise<=0:
            raise ValueError('Invalid readout budget')
        # Peak clipping is penalized separately; cap the useful sinusoid SNR
        # rather than claiming that a larger clipped amplitude is a better signal.
        snr=float(np.linalg.norm(np.minimum(peak,span))/(math.sqrt(2)*noise))
        scores.append(-math.expm1(-snr/12.))
        ratios.append(float(np.max(peak)/span))
        clipped.append(float(np.mean(peak>span)))
    worst=max(ratios)
    clipping=1/max(1.,worst)**2
    power=max(float(b['power_estimated_mW']) for b in budgets)
    if not math.isfinite(power) or power<0:raise ValueError('Invalid power')
    # 10 mW is an explicit engineering preference, not a component spec.
    power_utility=1/(1+power/10.)
    capacity=all(b['adc_capacity_pass'] and b['link_capacity_pass'] for b in budgets)
    score=100*(.75*float(np.mean(scores))+.25*power_utility)*clipping*float(capacity)
    return {'fitness_readout':float(np.clip(score,0.,100.)),
            'readout_worst_peak_to_span':worst,'readout_clipped_case_fraction_assumed':float(np.mean(np.asarray(ratios)>1)),
            'readout_mean_clipped_output_fraction_assumed':float(np.mean(clipped)),
            'readout_power_mW_assumed':power,'readout_capacity_pass_assumed':capacity,
            'readout_channel_count':max(b['channel_count'] for b in budgets),
            'readout_case_count':len(budgets),'readout_policy':'ideal wired outputs; assumed noise, ADC span, power and bandwidth; no circuit qualification'}


def screen_readout(responses):
    return score_budgets([budget_for_response(r) for r in responses])
