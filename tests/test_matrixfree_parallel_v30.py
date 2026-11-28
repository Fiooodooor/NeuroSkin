import numpy as np
import pytest
from concurrent.futures import ThreadPoolExecutor
from physical_fem import CORNERS,SolidMesh,HexElasticSolver
import matrixfree_fem as mf


@pytest.mark.skipif(mf.njit is None,reason='Numba acceleration unavailable')
def test_parallel_gather_same_operator_and_concurrent_rhs():
    cells=np.stack(np.meshgrid(np.arange(3),np.arange(3),np.arange(4),indexing='ij'),-1).reshape(-1,3)
    nodes,inv=np.unique((cells[:,None,:]+CORNERS[None,:,:]).reshape(-1,3),axis=0,return_inverse=True)
    nodes=nodes.astype(float)*.5
    m=SolidMesh(nodes,inv.reshape(-1,8),np.zeros((0,3),int),np.where(nodes[:,2]==0)[0],np.where(nodes[:,2]==2)[0],len(cells),len(cells)*.125,.5,.5,0,'box')
    a=HexElasticSolver(m,3.,.3,matrixfree_threshold=1,cg_rtol=1e-8)
    with ThreadPoolExecutor(max_workers=4) as pool:
        b=HexElasticSolver(m,3.,.3,matrixfree_threshold=1,cg_rtol=1e-8,matvec_executor=pool,matvec_chunks=4)
        rng=np.random.default_rng(42)
        xs=[rng.normal(size=3*len(nodes)) for i in range(4)]
        expected=[a.matrixfree.multiply(x) for x in xs]
        with ThreadPoolExecutor(max_workers=4) as rhs:
            actual=list(rhs.map(b.matrixfree.multiply,xs))
        np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-12)
        x=a.solve(force=(0,0,-.1),patch_radius_mm=4)
        y=b.solve(force=(0,0,-.1),patch_radius_mm=4)
        np.testing.assert_allclose(x['displacement'],y['displacement'],atol=1e-9,rtol=1e-7)
        assert y['force_equilibrium_relative']<1e-6
        assert y['energy_Nmm']==pytest.approx(x['energy_Nmm'],rel=1e-7)

def test_incidence_partition_balances_and_covers_all_nodes():
    offsets=np.r_[0,np.cumsum([1]*32+[8]*32)]
    ranges=mf.balanced_node_ranges(offsets,4)
    assert ranges[0][0]==0 and ranges[-1][1]==64
    assert all(a[1]==b[0] for a,b in zip(ranges,ranges[1:]))
    loads=[offsets[hi]-offsets[lo] for lo,hi in ranges]
    assert max(loads)-min(loads)<=8
    assert mf.balanced_node_ranges(np.array([0,2]),32)==[(0,1)]
