import numpy as np
import pytest
from neuroskin_v30.mesh import box_mesh
from neuroskin_v30.nonlinear_fem import NeoHookean,TetNeoHookeanSolver
from neuroskin_v30.material_regions import layered_box_ids,surface_topology


def test_batched_assembly_matches_scalar_material_tangents():
    mesh=box_mesh(1,1,2);mats=[NeoHookean(2,.3),NeoHookean(8,.2)]
    ids=layered_box_ids(mesh);s=TetNeoHookeanSolver(mesh,mats[0],materials=mats,material_ids=ids)
    u=np.random.default_rng(42).normal(0,.01,mesh.nodes.shape);force=np.zeros_like(u)
    energy,r,K,*_=s._assemble(u,force,None,None,0,True)
    R=np.zeros_like(u);dense=np.zeros((s.ndof,s.ndof));E=0.
    for i,t in enumerate(mesh.tets):
        G=s.grad[i];vol=s.volumes[i];F=np.eye(3)+u[t].T@G
        W,P,C,J=mats[ids[i]].energy_stress_tangent(F)
        E+=vol*W;R[t]+=vol*(G@P.T)
        d=s.dofs[i];dense[np.ix_(d,d)]+=vol*np.einsum('aJ,iJkL,bL->aibk',G,C,G).reshape(12,12)
    assert energy==pytest.approx(E)
    np.testing.assert_allclose(r,R.ravel(),atol=1e-12)
    np.testing.assert_allclose(K.toarray(),dense,atol=1e-12)


def test_layered_stiffness_and_elastic_unloading():
    mesh=box_mesh(2,2,4);ids=layered_box_ids(mesh);soft=NeoHookean(2,.3);hard=NeoHookean(20,.3)
    a=TetNeoHookeanSolver(mesh,soft).contact_cycle([0,.025,0])
    s=TetNeoHookeanSolver(mesh,soft,materials=[soft,hard],material_ids=ids)
    b=s.contact_cycle([0,.025,0])
    assert b[1]['contact_force_N']>a[1]['contact_force_N']
    assert b[-1]['displacement_max_mm']<1e-6
    assert b[1]['reactions_sum_N'][2]==pytest.approx(b[1]['contact_force_N'],abs=1e-6)
    assert sum(x['volume_mm3'] for x in s.material_summary())==pytest.approx(1.)
    used,surf=surface_topology(mesh,ids)
    assert set(surf['face_material_ids'])=={0,1}
    with pytest.raises(ValueError):TetNeoHookeanSolver(mesh,soft,materials=[soft,hard],material_ids=ids+.5)


def test_layered_box_api_returns_real_fields():
    from server import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        r=c.post('/api/v30/nonlinear/contact-box',json={'layered':True,'second_young_MPa':10})
        assert r.status_code==200,r.text
        d=r.json();assert len(d['materials'])==2 and not d['T2_qualified']
        f=d['contact_fields'];assert len(f['stages'])==4 and set(f['face_material_ids'])=={0,1}
        assert len(f['stages'][2]['displacement_mm'])==len(f['vertices_mm'])
