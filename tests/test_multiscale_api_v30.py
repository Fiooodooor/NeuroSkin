import numpy as np
import pytest
from fastapi.testclient import TestClient
from server import app
from neuroskin_v30.integration import Contact,distribute_contacts,CONTACT_SLOT


def test_contact_basis_force_and_moments():
    f=distribute_contacts(3,20.,[Contact(x_mm=14.,y_mm=31.,force_N=.3)])
    iy,ix=np.indices(f.shape)
    assert f.sum()==pytest.approx(.3)
    assert (f*ix*20).sum()==pytest.approx(.3*14.)
    assert (f*iy*20).sum()==pytest.approx(.3*31.)


def test_tile_api_matches_two_loads():
    with TestClient(app) as client:
        p={'selection':'hybrid','index':'h01_serpentine_quadrant','size':3,'contacts':[
            {'x_mm':10,'y_mm':17,'force_N':.1},{'x_mm':40,'y_mm':40,'force_N':.2}]}
        r=client.post('/api/v30/tile',json=p)
        assert r.status_code==200,r.text
        d=r.json();assert d['tier']=='T0'
        assert d['force_balance_error_N']<1e-12
        np.testing.assert_allclose(d['load_grid_N'],d['reconstructed_load_N'],atol=1e-9)
        p['contacts'][0]['x_mm']=41
        assert client.post('/api/v30/tile',json=p).status_code==422


def test_nonlinear_api_and_busy_guard():
    with TestClient(app) as client:
        r=client.post('/api/v30/nonlinear/contact-box',json={})
        assert r.status_code==200,r.text
        d=r.json();assert not d['T2_qualified']
        assert max(s['vertical_balance_error_N'] for s in d['stages'])<1e-6
        assert d['stages'][2]['contact_force_N']>0
        assert d['stages'][-1]['contact_force_N']<1e-6
        assert client.post('/api/v30/nonlinear/contact-box',json={'n':4}).status_code==422
        assert CONTACT_SLOT.acquire(blocking=False)
        try:assert client.post('/api/v30/nonlinear/contact-box',json={}).status_code==409
        finally:CONTACT_SLOT.release()


def test_candidate_geometry_rejection_and_page():
    with TestClient(app) as client:
        p={'selection':'hybrid','index':'h01_serpentine_quadrant'}
        r=client.post('/api/v30/nonlinear/candidate',json=p)
        assert r.status_code==422 and 'inflated' in r.text
        assert client.get('/v30').status_code==200
        assert client.get('/api/v30/capabilities').json()['T3_required_for_release'] is False


def test_candidate_diagnostic_override_does_not_promote_tier():
    with TestClient(app) as client:
        p={'selection':'hybrid','index':'h01_serpentine_quadrant','allow_inflated_geometry':True}
        r=client.post('/api/v30/nonlinear/candidate',json=p)
        assert r.status_code==200,r.text
        d=r.json();assert d['inflated_features']>0 and not d['T2_qualified']
        assert d['mesh']['tetrahedra']<=1500
        assert max(s['vertical_balance_error_N'] for s in d['stages'])<1e-6
        assert d['stages'][-1]['displacement_max_mm']<1e-5
