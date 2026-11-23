import unittest
import numpy as np
from types import SimpleNamespace
from gpu_sparse_fem import GPUSparseCG


class TestCuPy14CGCall(unittest.TestCase):
    def test_iterative_solver_uses_rtol_atol_not_tol(self):
        args = {}
        def fake_cg(A, b, **kw):
            args.update(kw)
            return np.array([0.5, 1.5]), 0
        null_stream = SimpleNamespace(synchronize=lambda: None)
        cuda = SimpleNamespace(Stream=SimpleNamespace(null=null_stream))
        fake_cp = SimpleNamespace(asarray=lambda x, dtype=None: np.array(x),
                                  float64=np.float64, asnumpy=lambda x: np.asarray(x), cuda=cuda)
        solver = GPUSparseCG.__new__(GPUSparseCG)
        solver.cp=fake_cp
        solver.cg=fake_cg
        solver.matrix='fake_sparse_matrix'
        solver.M='jacobi'
        solver.rtol=1e-6
        solver.maxiter=50
        solver.timeout_s=1.0
        sol=solver.solve(np.array([1.,3.]))
        np.testing.assert_allclose(sol, [0.5,1.5])
        self.assertEqual(args['rtol'], 1e-6)
        self.assertEqual(args['atol'], 0.0)
        self.assertNotIn('tol', args)

if __name__ == '__main__':
    unittest.main()
