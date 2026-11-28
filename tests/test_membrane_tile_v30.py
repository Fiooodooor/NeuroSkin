import numpy as np
import pytest
from membrane_tile import MembraneTile


@pytest.mark.parametrize('q',[4,8])
def test_center_load_equilibrium_symmetry_and_transfer(q):
    m=MembraneTile(np.full((3,3),.4),20,.2,q)
    r=m.solve([(20,20,.1)])
    assert r['force_balance_error_N']<1e-10
    assert r['energy_balance_error_Nmm']<1e-10
    assert r['free_residual_N']<1e-10
    a=r['reaction_N']
    np.testing.assert_allclose(a,a.T,atol=1e-10)
    np.testing.assert_allclose(a,a[::-1],atol=1e-10)
    np.testing.assert_allclose(r['transfer'][:,4]*.1,a.ravel(),atol=1e-10)
    np.testing.assert_allclose(r['transfer'].sum(0),1.,atol=1e-10)
    np.testing.assert_allclose(m.B.sum(1),1.,atol=1e-12)


def test_pretension_increases_load_sharing_and_preserves_input_moment():
    low=MembraneTile(np.ones((3,3)),20,.02)
    high=MembraneTile(np.ones((3,3)),20,2.)
    a=low.solve([(20,20,.1)]);b=high.solve([(20,20,.1)])
    assert b['reaction_N'][1,1]<a['reaction_N'][1,1]
    f=high.point_load(13.2,24.7,.1).reshape(high.m,high.m)
    assert f.sum()==pytest.approx(.1)
    assert (f*high.axis[None,:]).sum()==pytest.approx(1.32)
    assert (f*high.axis[:,None]).sum()==pytest.approx(2.47)


def test_real_tile_api():
    from fastapi.testclient import TestClient
    from server import app
    with TestClient(app) as c:
        r=c.post('/api/v30/tile',json={'selection':'hybrid','index':'h01_serpentine_quadrant','membrane_model':'tensioned_q1','contacts':[{'x_mm':20,'y_mm':20,'force_N':.1}]})
        assert r.status_code==200,r.text
        d=r.json();assert d['tier']=='T0' and d['membrane_surface']['node_count']==169
        assert d['force_balance_error_N']<1e-8
        assert isinstance(d['small_slope_screen'],bool) and d['maximum_membrane_slope']>=0
        assert d['diagnostic_context']['settings']['membrane_model']=='tensioned_q1'


def test_small_slope_screen_scales_and_is_not_qualification():
    m=MembraneTile(np.full((3,3),.4),20,.2,4)
    a=m.solve([(20,20,.001)])
    b=m.solve([(20,20,10.)])
    assert a['small_slope_screen'] and not b['small_slope_screen']
    assert b['maximum_membrane_slope']==pytest.approx(10000*a['maximum_membrane_slope'])
    assert b['tier']=='T0'
    with pytest.raises(ValueError):MembraneTile(np.ones((3,3)),20,.2,4.)
