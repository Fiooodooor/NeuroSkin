"""Optional real-CUDA smoke test. Exits cleanly if the GPU runtime is unavailable.

Run on Windows after: python -m pip install -r requirements.txt
This is a sparse linear-algebra smoke test, NOT a FEM speed or accuracy validation.
"""
from __future__ import annotations
import json
import sys
import warnings
import numpy as np
from scipy.sparse import csr_matrix
from gpu_sparse_fem import GPUSparseCG, GPUUnavailable


def main() -> int:
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message=r'CUDA path could not be detected.*', category=UserWarning, module=r'cupy\._environment')
            import cupy as cp
            info = cp.cuda.runtime.getDeviceProperties(0)
        cc = (int(info['major']), int(info['minor']))
        cuda_runtime = int(cp.cuda.runtime.runtimeGetVersion())
        available, total = cp.cuda.runtime.memGetInfo()
        # Pascal uses CUDA 12.x. nvidia-smi CUDA 13 means driver API capability.
        if cc != (6, 1):
            print(f'Note: GPU compute capability {cc}, expected P1000 (6, 1).')
        print(json.dumps({'cupy':cp.__version__, 'compute_capability':cc,
                          'runtime_version':cuda_runtime,
                          'free_gpu_mib':round(available / 1048576, 1),
                          'total_gpu_mib':round(total / 1048576, 1)}, indent=2))
        A = csr_matrix(np.array([[6., -1., 0.], [-1., 5., -1.], [0., -1., 4.]], dtype=np.float64))
        rhs = np.array([1., 2., 3.], dtype=np.float64)
        solver = GPUSparseCG(A, rtol=1e-9, maxiter=1000, budget_mb=64)
        sol = solver.solve(rhs)
        residual = float(np.linalg.norm(A @ sol - rhs) / np.linalg.norm(rhs))
        print(f'CUDA sparse CG relative residual: {residual:.3e}; iterations: {solver.iterations}')
        if residual >= 1e-7:
            print('FAILED: GPU sparse CG did not meet the smoke-test tolerance.', file=sys.stderr)
            return 2
        print('GPU sparse CG smoke test PASSED. Next run hardware_benchmark.py.')
        return 0
    except (ImportError, OSError, GPUUnavailable, RuntimeError) as exc:
        print(f'GPU CUDA 12 smoke test unavailable: {type(exc).__name__}: {exc}', file=sys.stderr)
        print('CPU simulation is unaffected. Check package, CUDA 12 runtime and VRAM availability.', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
