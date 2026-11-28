import numpy as np
import pytest
from neuroskin_v30.mesh import MeshError, TetMesh, box_mesh
from neuroskin_v30.nonlinear_fem import (InvertedElement, NeoHookean,NonlinearFEMError,
    TetNeoHookeanSolver, horizontal_surface_weights)


def test_box_geometry_and_measure():
    m=box_mesh(2,2,2,(2,3,4))
    assert len(m.tets)==48
    assert m.volume_mm3==pytest.approx(24.)
    assert m.metrics()['min_cell_volume_mm3']>0
    assert horizontal_surface_weights(m).sum()==pytest.approx(6)


def test_mesh_inverted_singular_and_nonfinite_rejected():
    m=box_mesh(1,1,1)
    t=m.tets.copy()
    t[0,[0,1]]=t[0,[1,0]]
    with pytest.raises(MeshError):TetMesh(m.nodes,t)
    with pytest.raises(MeshError):TetMesh(m.nodes,np.array([[0,1,2,2]]))
    x=m.nodes.copy();x[0]=[np.nan,0,0]
    with pytest.raises(MeshError):TetMesh(x,m.tets)


def test_neo_hookean_exact_derivatives():
    mat=NeoHookean(2.4,.32)
    F=np.array([[1.1,.04,.03],[-.03,.96,.01],[.02,-.04,.91]])
    W,P,C,J=mat.energy_stress_tangent(F)
    h=1e-6
    for k in range(3):
        for L in range(3):
            plus=F.copy();minus=F.copy()
            plus[k,L]+=h;minus[k,L]-=h
            wp,pp,*_=mat.energy_stress_tangent(plus)
            wm,pm,*_=mat.energy_stress_tangent(minus)
            assert (wp-wm)/(2*h)==pytest.approx(P[k,L],abs=2e-8)
            np.testing.assert_allclose((pp-pm)/(2*h),C[:,:,k,L],atol=2e-8,rtol=2e-7)


def test_invalid_material_and_deformation_rejected():
    with pytest.raises(ValueError):NeoHookean(-1.,.3)
    with pytest.raises(ValueError):NeoHookean(1.,.49)
    with pytest.raises(InvertedElement):NeoHookean(1.,.3).energy_stress_tangent(np.diag([-1,1,1]))


def solver():
    m=box_mesh(1,1,1)
    s=TetNeoHookeanSolver(m,NeoHookean(2,.3))
    fixed=(3*np.flatnonzero(m.nodes[:,2]==0)[:,None]+np.arange(3)[None,:]).ravel()
    return m,s,fixed


def test_force_balanced_and_returned_reaction():
    m,s,fixed=solver()
    f=np.zeros((len(m.nodes),3));f[m.nodes[:,2]==1,2]=-.02/4
    r=s.solve(fixed_dofs=fixed,forces_N=f)
    assert r.converged
    assert r.min_deformation_J>.9
    assert np.sum(r.reaction_N[:,2])==pytest.approx(.02,abs=1e-6)
    assert r.residual_force_N<1e-7
    assert r.displacement_mm[m.nodes[:,2]==1,2].mean()<0


def test_contact_cyclic_load_and_release_is_elastic():
    m,s,fix=solver()
    cycle=s.contact_cycle([.0,.01,.025,.01,.0],penalty_N_per_mm3=100.)
    assert all(c['converged'] for c in cycle)
    assert cycle[2]['contact_force_N']>cycle[1]['contact_force_N']>0
    assert cycle[2]['max_penetration_mm']<.01
    assert cycle[-1]['displacement_max_mm']<1e-5
    assert cycle[-1]['contact_force_N']==pytest.approx(0,abs=1e-6)


def test_missing_support_fails_closed():
    m,s,fixed=solver()
    with pytest.raises(ValueError):s.solve()
    with pytest.raises(ValueError):s.solve(fixed_dofs=fixed,plane_z_mm=.5,contact_penalty_N_per_mm3=-1)


def test_disconnected_mesh_and_orphan_nodes_rejected():
    from neuroskin_v30.mesh import TetMesh,MeshError
    mesh=box_mesh()
    extra=np.array([[5.,5.,5.]])
    with pytest.raises(MeshError,match='orphan'):
        TetMesh(np.vstack([mesh.nodes,extra]),mesh.tets)
    two=np.vstack([mesh.nodes,mesh.nodes+[4.,0,0]])
    cells=np.vstack([mesh.tets,mesh.tets+len(mesh.nodes)])
    with pytest.raises(MeshError,match='disconnected'):
        TetMesh(two,cells)


def test_invalid_rigid_modes_rejected_at_zero_load():
    m,s,_=solver()
    with pytest.raises(ValueError,match='six rigid modes'):
        s.solve(fixed_dofs=[0,1,2])
    with pytest.raises(ValueError):NeoHookean(2.,-.3)


def test_duplicate_and_noninteger_connectivity_rejected():
    m=box_mesh()
    with pytest.raises(MeshError):TetMesh(m.nodes,m.tets.astype(float))
    with pytest.raises(MeshError,match='duplicate tetrahedra'):TetMesh(m.nodes,np.vstack([m.tets,m.tets[0]]))


def test_hex8_subdivision_is_conforming_and_preserves_volume():
    from neuroskin_v30.mesh import hex8_to_tet4
    from physical_fem import CORNERS
    coords,inv=np.unique((np.array([[0,0,0],[1,0,0]])[:,None,:]+CORNERS).reshape(-1,3),axis=0,return_inverse=True)
    m=hex8_to_tet4(coords,inv.reshape(2,8))
    assert len(m.tets)==12
    assert m.volume_mm3==pytest.approx(2.)
    assert horizontal_surface_weights(m).sum()==pytest.approx(2.)
