import pytest
from tile_optimization import designs,optimize,pareto,evaluate_design


def receptor():
    return dict(id='test',family='crown',genome_hash='test',kz_N_mm=.4,envelope_mm=19.,
                power_per_taxel_mW=5.,channels_per_taxel=7,bytes_per_taxel_s=8000,
                readout_capacity=True,pvdf_saturated_outputs_assumed=0)


def test_fixed_patch_and_two_fidelity_search():
    ds,excluded=designs([receptor()],60,[3,5],[.3],[4.],1.,2.,.5,.001,42)
    assert len(ds)==1 and excluded[0]['size']==5
    d=ds[0];assert d['size']*d['pitch_mm']==60
    result=optimize(ds,excluded,1)
    assert len(result['screening'])==len(result['refined'])==1
    assert not result['refined'][0].get('failed'),result['refined'][0]
    assert result['screening'][0]['metrics']['power_mW']==45
    assert result['refined'][0]['metrics']['max_balance_error_N']<1e-7
    with pytest.raises(ValueError,match='Mixed'):pareto(result['screening']+result['refined'])


def test_common_noise_deterministic_screen():
    ds,_=designs([receptor()],60,[3],[.3],[4.],1.,2.,.5,.001,42)
    a=evaluate_design((ds[0],'screen'));b=evaluate_design((ds[0],'screen'))
    assert a==b


def test_tile_optimization_api():
    from fastapi.testclient import TestClient
    from server import app
    req={'selection':'hybrid','index':'h01_serpentine_quadrant','include_library':False,'sizes':[3],
         'tensions':[.3],'substrate_depths_mm':[4.],'finalists':1,'compute_workers':1}
    with TestClient(app) as c:
        r=c.post('/api/v30/tile/optimize',json=req)
        assert r.status_code==200,r.text
        d=r.json();assert d['tier']=='T0' and d['diagnostic_context']['path']=='tile/optimize'
        assert d['screening'] and d['refined'] and not d['refined'][0].get('failed'),d
