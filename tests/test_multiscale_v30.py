import numpy as np
import pytest
from neuroskin_multiscale import stack_response, symmetry_error, tile_response


def test_stack_three_stages_and_wrench_transport():
    k=np.diag([2.,2.,4.,8.,8.,8.])
    w=np.array([1.,0.,-2.,0.,0.,0.])
    out=stack_response([k]*3,[[0,0,2],[0,0,1],[0,0,0]],w)
    assert out['stages'][0]['wrench'][4]==2.
    assert out['displacement'][2]==pytest.approx(-1.5)
    assert out['energy_balance_error_Nmm']<1e-12
    np.testing.assert_allclose(out['stiffness']@out['displacement'],w,atol=1e-12)


def test_symmetry_chiral_allowed_for_cn_not_dn():
    k=np.diag([2.,2.,4.,8.,8.,8.]); k[2,5]=k[5,2]=.5
    assert symmetry_error(k,4,3.)<1e-12
    assert symmetry_error(k,4,3.,mirror=True)>0.01
    k[0,0]=4.
    assert symmetry_error(k,4,3.)>0.1


@pytest.mark.parametrize('n',[3,5,8])
def test_tile_force_balance_and_superposition(n):
    k=np.ones((n,n))*2; f=np.zeros_like(k); f[0,0]=1; g=np.zeros_like(k); g[-1,-1]=.5
    a=tile_response(k,.5,f); b=tile_response(k,.5,g); c=tile_response(k,.5,f+g)
    assert c['force_balance_error_N']<1e-12
    assert a['reaction_N'][0,1]>0
    np.testing.assert_allclose(a['reaction_N']+b['reaction_N'],c['reaction_N'],atol=1e-12)
    np.testing.assert_allclose(tile_response(k,0,f)['reaction_N'],f)


def test_invalid_inputs_rejected():
    with pytest.raises(ValueError):stack_response([np.zeros((6,6))],[[0,0,0]],np.zeros(6))
    with pytest.raises(ValueError):tile_response(np.ones((3,3)),-1,np.ones((3,3)))
    with pytest.raises(ValueError):symmetry_error(np.eye(6),4,0)
