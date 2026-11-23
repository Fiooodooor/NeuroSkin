"""Windows-friendly dependency and hardware diagnostics; no unintended GPU load.

Exit nonzero for missing mandatory packages. CUDA capability is reported as an
operational check only when --gpu is explicitly requested.
"""
from __future__ import annotations
import argparse
import importlib
import json
import platform
import sys
import warnings

PACKAGES = {
    'fastapi':'fastapi', 'uvicorn':'uvicorn', 'numpy':'numpy',
    'scipy':'scipy', 'trimesh':'trimesh', 'pydantic':'pydantic',
    'psutil':'psutil', 'numba':'numba', 'cupy-cuda12x':'cupy',
    'gmsh':'gmsh', 'scikit-fem':'skfem', 'meshio':'meshio',
    'pyvista':'pyvista'
}


def inspect_imports() -> dict:
    data={}
    for package,importname in PACKAGES.items():
        try:
            with warnings.catch_warnings():
                if importname=='cupy':
                    # Avoid a known non-fatal toolkit-path warning with [ctk]
                    # wheels; --gpu performs an actual solve to test CUDA.
                    warnings.filterwarnings('ignore',message=r'CUDA path could not be detected.*',category=UserWarning,module=r'cupy\._environment')
                mod=importlib.import_module(importname)
            data[package]={'ok':True,'version':str(getattr(mod,'__version__','installed'))}
        except Exception as exc:
            data[package]={'ok':False,'reason':f'{type(exc).__name__}: {exc}'}
    return data


def main(argv=None):
    ap=argparse.ArgumentParser(description='NeuroSkin full dependency and hardware check')
    ap.add_argument('--gpu',action='store_true',help='Also perform a real CUDA sparse CG smoke test')
    args=ap.parse_args(argv)
    imports=inspect_imports()
    from hardware_profile import profile
    report={'python':sys.version.split()[0], 'platform':platform.platform(),
            'packages':imports,'hardware':profile(),
            'cuda_check': 'not requested; use --gpu'}
    if args.gpu and imports['cupy-cuda12x']['ok']:
        from gpu_sparse_fem import GPUSparseCG
        from scipy.sparse import csr_matrix
        import numpy as np
        try:
            mat=csr_matrix(np.asarray([[4.,-1.],[-1.,3.]]))
            rhs=np.asarray([1.,2.]);sol=GPUSparseCG(mat,budget_mb=64,rtol=1e-9).solve(rhs)
            report['cuda_check']={'ok': True, 'relative_residual':float(np.linalg.norm(mat@sol-rhs)/np.linalg.norm(rhs))}
        except Exception as exc:
            report['cuda_check']={'ok':False, 'reason':f'{type(exc).__name__}: {exc}'}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    bad=[name for name,info in imports.items() if not info['ok']]
    if bad:
        print(f'Missing/unusable packages: {", ".join(bad)}. Install with python -m pip install -r requirements.txt',file=sys.stderr)
        return 2
    if args.gpu and isinstance(report['cuda_check'],dict) and not report['cuda_check']['ok']:
        return 3
    return 0

if __name__=='__main__': raise SystemExit(main())
