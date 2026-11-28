import numpy as np
import pytest
from sensor_fusion import wired_features,compare_readouts


def response(wiring):
    return ({'pressure_delta_pF':[0.]*4,'lateral_delta_pF':[0.]*2,'hall_torsion_delta_mT':0.,'hybrid_stage_channels':{'readout_vector_pF_assumed':[.2,-.1]}},
            {'channels':[{'initial_charge_amplifier_V':1.},{'initial_charge_amplifier_V':-1.}], 'wiring_matrix':wiring,'leak_tau_s':.5,'noise_rms_V_assumed':.003})


def test_wired_signed_cancellation_dc_and_stage_count():
    e,p=response([[1,1]]);x,s,n=wired_features(e,p,25.)
    assert n==2 and len(x)==10 and x[-1]==0.
    e,p=response([[1,-1]]);x,s,n=wired_features(e,p,25.)
    assert x[-1]==pytest.approx(2*25*np.pi/np.hypot(1,25*np.pi))
    assert wired_features(e,p,0.)[0][-1]==0.
    e,p=response([[1,0],[0,1]]);x,s,n=wired_features(e,p,25.)
    assert x[-1]<0<x[-2] and len(x)==11
    with pytest.raises(ValueError):wired_features(e,p,float('nan'))
    e,p=response([[0,0]])
    with pytest.raises(ValueError):wired_features(e,p,25.)


def test_ablation_same_groups_and_added_information():
    rng=np.random.default_rng(42);n=150
    x=rng.normal(size=(n,10))*.1;y=x[:,[0,1,7,8,9]]
    a=compare_readouts(x,y,np.repeat(np.arange(15),10),np.full(10,.0001),2,seed=42)
    assert a==compare_readouts(x,y,np.repeat(np.arange(15),10),np.full(10,.0001),2,seed=42)
    assert a['models']['static_stage_pvdf']['position_mae_mm']<a['models']['static']['position_mae_mm']
    assert a['models']['static_stage_pvdf']['channels']==10
    assert a['models']['static_and_stage']['channels']==9
    assert sum(a['group_counts'].values())==15
    x[:,9]=3.
    assert compare_readouts(x,y,np.repeat(np.arange(15),10),np.full(10,.0001),2)['pvdf_saturated_sample_fraction_assumed']==1.
