import numpy as np
from force_visualization import summarize,boundary_wrenches


def test_spatial_aggregation_preserves_force_and_moment():
    rng=np.random.default_rng(42);p=rng.normal(size=(500,3));f=rng.normal(size=(500,3));c=rng.normal(size=(500,3))*.1
    r=summarize(p,f,c)
    assert len(r['groups'])<=16
    assert sum(g['node_count'] for g in r['groups'])==500
    np.testing.assert_allclose(sum(np.asarray(g['force_N']) for g in r['groups']),f.sum(0),atol=1e-11)
    np.testing.assert_allclose(sum(np.cross(g['position_mm'],g['force_N'])+g['couple_Nmm'] for g in r['groups']),(np.cross(p,f)+c).sum(0),atol=1e-11)


def test_pure_torsion_retains_moment_when_force_cancels():
    p=[[1,0,0],[-1,0,0]];f=[[0,1,0],[0,-1,0]]
    r=summarize(p,f,bins=1)
    np.testing.assert_allclose(r['force_N'],[0,0,0])
    np.testing.assert_allclose(r['groups'][0]['couple_Nmm'],[0,0,2])
    b=boundary_wrenches(p,f,p,-np.asarray(f))
    np.testing.assert_allclose(b['force_balance_N'],[0,0,0])
    np.testing.assert_allclose(b['moment_balance_Nmm'],[0,0,0])


def test_section_traction_voigt_sign_units_and_layer_selection():
    from force_visualization import substrate_sections
    # Four columns with 2 mm pitch and three aligned z layers.
    centers=np.array([[x,y,z] for z in [1.,3.,5.] for x in [1.,3.] for y in [1.,3.]])
    stress=np.tile([0.,0.,-2.,0.,.5,-.25],(len(centers),1))
    cuts=substrate_sections(centers,stress,2.,0.,6.)
    assert len(cuts)==2
    for s in cuts:
        assert s['area_mm2']==16.
        np.testing.assert_allclose(s['force_N'],[4.,-8.,32.])
        assert sum(g['node_count'] for g in s['groups'])==4
