import numpy as np
import pytest
from readout_gain import study_feedback


def fixture():
    rng=np.random.default_rng(42);n=90
    x=rng.normal(size=(n,8))*.05
    x[:,7]=np.linspace(-4,4,n)
    y=np.column_stack([x[:,:3],x[:,7],x[:,3]])
    t,v,e=np.arange(50),np.arange(50,70),np.arange(70,90)
    sigma=np.ones(8)*.001
    return x,y,t,v,e,sigma,7,40.,.5,rng.normal(size=x.shape)*sigma,np.zeros((20,8)),np.array([.1,.1,.1,3.,3.])


def test_feedback_selection_no_test_leakage_and_correct_rc():
    args=fixture();a=study_feedback(*args)
    x,y,*rest=args;x=x.copy();y=y.copy();x[args[4]]*=1000;y[args[4]]+=1000
    b=study_feedback(x,y,*rest)
    assert a['selected_feedback_pF']==b['selected_feedback_pF']
    assert a['validation_trials']==b['validation_trials']
    assert a['model']==b['model']
    assert a['test_force_rmse_norm_N']!=b['test_force_rmse_norm_N']
    assert a['selected_feedback_pF']>=80.
    assert a['test_saturated_fraction']<=a['nominal_test_saturated_fraction']
    assert a['required_feedback_resistance_Gohm_assumed']==pytest.approx(500/a['selected_feedback_pF'])
    assert not a['genome_modified']


def test_feedback_invalid_capacitance():
    a=list(fixture());a[7]=0.
    with pytest.raises(ValueError):study_feedback(*a)
