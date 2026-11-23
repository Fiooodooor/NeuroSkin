"""Opt-in CUDA 12 sparse conjugate-gradient solver for *small* assembled HEX8 systems.

The Quadro P1000 has only 4 GiB VRAM and weak FP64 throughput. This backend is
not assumed faster than CPU; benchmark every chosen geometry. Large high-res
matrix-free HEX8 solves must remain on CPU until a tested GPU matrix-free kernel
is available. Accuracy is checked against the original CPU FEM operator.
"""
from __future__ import annotations
import time
import warnings
import numpy as np

class GPUUnavailable(RuntimeError):
    pass

class GPUSparseCG:
    def __init__(self, A_cpu, *, rtol=5e-6, maxiter=5000, timeout_s=180, budget_mb=1024):
        try:
            # CuPy's toolkit-root discovery can warn with wheel-provided [ctk]
            # even when the CUDA 12 runtime works (verified on the P1000).
            # Filter *only* that warning during CUDA initialization; actual
            # runtime failures still raise GPUUnavailable with their cause.
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message=r'CUDA path could not be detected.*', category=UserWarning, module=r'cupy\._environment')
                import cupy as cp
                import cupyx.scipy.sparse as cps
                from cupyx.scipy.sparse.linalg import cg
                cp.cuda.runtime.getDeviceCount()
        except (ImportError, OSError, RuntimeError) as exc:
            raise GPUUnavailable("CuPy CUDA 12 runtime is unavailable. Install requirements.txt on Windows and validate with gpu_selftest.py. Quadro P1000 cannot use CUDA 13 toolkit kernels.") from exc
        self.cp=cp
        self.cg=cg
        try:
            device=cp.cuda.Device(0)
            with device:
                info=cp.cuda.runtime.getDeviceProperties(0)
                self.cc=(int(info['major']),int(info['minor']))
                if self.cc[0] < 6:
                    raise GPUUnavailable(f'GPU architecture {self.cc} is not supported by this solver')
                free, total=cp.cuda.runtime.memGetInfo()
                A_cpu=A_cpu.tocsr().astype(np.float64)
                # Conservative reservation for CSR matrix, preconditioner, and CG work arrays.
                est=A_cpu.data.nbytes+A_cpu.indices.nbytes+A_cpu.indptr.nbytes+200*A_cpu.shape[0]
                limit=min(int(budget_mb*1048576),int(free*.45))
                if est > limit:
                    raise GPUUnavailable(f'Estimated CUDA working set {est/1048576:.0f} MiB exceeds safety limit {limit/1048576:.0f} MiB. Use --compute-device cpu.')
                self.matrix=cps.csr_matrix(A_cpu)
                diag=self.matrix.diagonal()
                if bool(cp.any(diag<=0)):
                    raise GPUUnavailable('Non-positive diagonal in GPU stiffness matrix')
                self.diaginv=1.0/diag
                self.M=cps.diags(self.diaginv)
                self.device_name=info['name'].decode() if isinstance(info['name'],bytes) else str(info['name'])
                self.rtol=rtol;self.maxiter=maxiter;self.timeout_s=timeout_s
                self.iterations=0
        except GPUUnavailable:
            raise
        except Exception as exc:
            raise GPUUnavailable(f'CUDA initialization/allocation failed: {exc}') from exc

    def solve(self, rhs_cpu):
        cp=self.cp
        self.iterations=0
        start=time.monotonic()
        try:
            rhs=cp.asarray(rhs_cpu,dtype=cp.float64)
            def callback(_):
                self.iterations+=1
                if time.monotonic()-start>self.timeout_s:
                    raise GPUUnavailable(f'GPU CG exceeded {self.timeout_s:g}s time budget')
            # CuPy 14 uses rtol and atol (not the deprecated CuPy 13 `tol`).
            # GPU installs on Python 3.14 require the CuPy 14 wheel.
            x,info=self.cg(self.matrix,rhs,M=self.M,rtol=self.rtol,atol=0.0,maxiter=self.maxiter,callback=callback)
            cp.cuda.Stream.null.synchronize()
            x_cpu=cp.asnumpy(x)
            if info!=0:
                raise GPUUnavailable(f'CUDA CG not converged, info={info}; use CPU or increase iterations')
            if not np.all(np.isfinite(x_cpu)):
                raise GPUUnavailable('Nonfinite CUDA solution')
            return x_cpu
        except GPUUnavailable:
            raise
        except Exception as exc:
            raise GPUUnavailable(f'CUDA sparse CG failed: {exc}') from exc
