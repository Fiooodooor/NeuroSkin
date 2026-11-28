import numpy as np
import pytest
from validation_design import shear_pairs,select_decoder


def test_independent_signed_shear_axes():
    pairs=shear_pairs([-.1,-.05,.05,.1]);assert len(pairs)==9
    assert np.linalg.matrix_rank(pairs)==2
    assert len(shear_pairs([-.1,-.05,.05,.1],True))==25
    with pytest.raises(ValueError):shear_pairs([0,.1])


def test_model_selection_never_reads_test_targets():
    rng=np.random.default_rng(42);x=rng.normal(size=(90,7));y=x[:,:5]*[.05,.05,.1,1.,1.]
    t,v,e=np.arange(50),np.arange(50,70),np.arange(70,90)
    args=(t,v,e,np.ones(7)*.001,np.array([.1,.1,.1,3.,3.]),np.zeros((20,7)))
    a=select_decoder(x,y,*args)
    changed=y.copy();changed[e]+=1000
    b=select_decoder(x,changed,*args)
    np.testing.assert_array_equal(a[0],b[0]);assert a[3]==b[3]
    assert np.sqrt(np.mean((a[0]-y[e])**2))<.01
    assert a[3]['final_fit_count']==70


def test_nonlinear_candidates_are_considered_and_finite():
    rng=np.random.default_rng(12);x=rng.uniform(-1,1,(180,7));y=np.column_stack([x[:,0]**2,x[:,1]**2,x[:,2]**2,x[:,3]**2,x[:,4]**2])
    a=select_decoder(x,y,np.arange(100),np.arange(100,140),np.arange(140,180),np.full(7,.001),np.ones(5),np.zeros((20,7)))
    assert a[3]['family']=='rbf'
    assert np.isfinite(a[0]).all()


def test_protocol_design_has_independent_shear_and_static_equivalence():
    from evaluation_v30 import simulate_load_dataset,_respond
    from hybrid_library import ranked,genome_for
    s=ranked()[0];g=genome_for(s)
    X,Y,groups,labels,positions=simulate_load_dataset(s.upper_family,g)
    assert len(X)==len(positions)*5*9
    assert np.linalg.matrix_rank(Y[:,:2])==2
    for i in (0,1,len(X)-1):
        v,_=_respond(s.upper_family,g,*Y[i])
        np.testing.assert_allclose(X[i],v,atol=1e-12)


def test_common_robustness_scenarios_and_failed_trials(monkeypatch):
    import evaluation_v30 as ev
    def response(family,g,fx,fy,fz,x,y,strain=0.):
        if g.get('material_E',1.)!=1.:raise ValueError('synthetic numerical failure')
        return np.full(7,abs(fz)),{}
    monkeypatch.setattr(ev,'_respond',response)
    a=ev.robust_screen('quadrant',{'material_E':1.},seed=12,samples=8)
    b=ev.robust_screen('quadrant',{},seed=12,samples=8)
    assert a['scenario_hash']==b['scenario_hash']
    assert a['failed_trials']==8 and a['assumed_snr_below_3_fraction']==1.
    assert a['assumed_snr_below_3_upper95']==1.
    assert b['failed_trials']==0 and b['assumed_snr_below_3_fraction']==0.
    assert b['assumed_snr_below_3_upper95']==pytest.approx(1-.05**(1/8))


def test_decoder_rejects_bad_group_count_and_nonfinite_noise():
    from sensor_metrics import decoder_holdout
    X=np.zeros((20,7));Y=np.zeros((20,5))
    with pytest.raises(ValueError):decoder_holdout(X,Y,[1,2])
    with pytest.raises(ValueError):decoder_holdout(X,Y,np.repeat(np.arange(5),4),assumed_noise=[float('nan')]*7)


def test_protocol_settings_are_comparison_boundary():
    from validation_contract import candidate_comparable
    a={'protocol_hash':'a','tier':'T0','evidence':{'solver_hash':'b','seed':1,'evaluation_settings_hash':'c'}}
    b={'protocol_hash':'a','tier':'T0','evidence':{'solver_hash':'b','seed':1,'evaluation_settings_hash':'d'}}
    assert candidate_comparable(a,b)==(False,'different_evaluation_settings_hash')
