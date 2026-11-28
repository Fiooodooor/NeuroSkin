import numpy as np
import pytest
from nonlinear_skin_tile import NonlinearSkinTile,Substrate3D
from membrane_tile import MembraneTile


def test_membrane_tangent_and_linear_limit():
    k=np.full((3,3),.4)
    a=NonlinearSkinTile(k,20,.2,0.,.5)
    b=MembraneTile(k,20,.2)
    contacts=[(20,20,.1)]
    np.testing.assert_allclose(a.solve(contacts)['reaction_N'],b.solve(contacts)['reaction_N'],atol=1e-8)
    a=NonlinearSkinTile(k,20,.2,3.,.5)
    rng=np.random.default_rng(42);u=rng.normal(0,.1,a.linear.m**2);v=rng.normal(size=len(u));f=np.zeros_like(u)
    E,r,K,_=a.assemble(u,f);h=1e-6
    ep,rp,*_=a.assemble(u+h*v,f,False);em,rm,*_=a.assemble(u-h*v,f,False)
    assert (ep-em)/(2*h)==pytest.approx(r@v,abs=1e-7)
    np.testing.assert_allclose((rp-rm)/(2*h),K@v,atol=1e-7)


def test_coupled_substrate_reciprocity_and_equilibrium():
    k=np.ones((3,3))
    sub=Substrate3D(3,10,4,1.)
    np.testing.assert_allclose(sub.S,sub.S.T,atol=1e-10)
    np.testing.assert_allclose(sub.B.sum(1),1.,atol=1e-12)
    np.linalg.cholesky(sub.S)
    model=NonlinearSkinTile(k,10,.2,2.,.5,substrate=sub)
    r=model.solve([(10,10,.3),(4,7,.1)])
    assert r['force_balance_error_N']<1e-8
    assert r['energy_balance_error_Nmm']<1e-8
    assert r['substrate']['force_balance_error_N']<1e-8
    assert r['substrate']['energy_Nmm']>0
    np.testing.assert_allclose(r['displacement_mm'],np.asarray(r['receptor_compression_mm'])+r['substrate']['pad_displacement_mm'],atol=1e-9)
    assert r['membrane_stretch_energy_Nmm']>0
    assert r['tier']=='T0'


def test_nonlinear_tile_api_and_legacy_guard():
    from fastapi.testclient import TestClient
    from server import app
    req={'selection':'hybrid','index':'h01_serpentine_quadrant','membrane_model':'nonlinear_coupled',
         'contacts':[{'x_mm':20,'y_mm':20,'force_N':.1}]}
    with TestClient(app) as c:
        assert c.post('/api/v30/tile',json=req).status_code==422
        r=c.post('/api/v30/tile/nonlinear',json=req)
        assert r.status_code==200,r.text
        d=r.json();assert d['tier']=='T0' and d['substrate']['mesh']['tetrahedra']>0
        assert d['inverse_basis']=='zero_load_linearization'

def test_relaxed_membrane_consistent_tangent_and_fixed_limit_energy():
    from relaxed_membrane import RelaxedSkinTile
    k=np.full((3,3),.4);a=RelaxedSkinTile(k,10,.2,2.,.5);b=NonlinearSkinTile(k,10,.2,2.,.5)
    n=a.nodal_count;rng=np.random.default_rng(42)
    q=np.zeros(3*n);q[a.free]=rng.normal(0,.01,len(a.free));v=np.zeros_like(q);v[a.free]=rng.normal(size=len(a.free))
    f=np.zeros_like(q);E,r,K,_=a.assemble_relaxed(q,f);h=1e-6
    ep,rp,*_=a.assemble_relaxed(q+h*v,f,False);em,rm,*_=a.assemble_relaxed(q-h*v,f,False)
    assert (ep-em)/(2*h)==pytest.approx(r@v,abs=1e-7)
    np.testing.assert_allclose((rp-rm)/(2*h),K@v,atol=1e-7)
    q[:2*n]=0
    assert a.assemble_relaxed(q,f,False)[0]==pytest.approx(b.assemble(q[2*n:],f[2*n:],False)[0],abs=1e-12)
    out=a.solve([(10,10,.2)])
    assert out['force_balance_error_N']<1e-8
    assert out['energy_balance_error_Nmm']<1e-8
    assert out['inplane_displacement_max_mm']>0
    uv=np.asarray(out['membrane_surface']['inplane_x_mm'])
    assert np.max(np.abs(uv[[0,-1]]))==0
    assert np.max(np.abs(uv[:,[0,-1]]))==0
