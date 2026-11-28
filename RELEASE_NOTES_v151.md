# NeuroSkin Evolution Lab 1.5.1 — Python 3.14 / Pascal CUDA installation hotfix

- Fix optional GPU installation on Windows Python 3.14: replace unsupported
  CuPy 13 package constraint with CuPy 14 `cupy-cuda12x[ctk]>=14.0.1,<15`.
- Fix sparse CG argument `tol=` to `rtol=..., atol=0.0` as required by CuPy 14.
- Add `gpu_selftest.py` for CUDA runtime + sparse CG numerical residual check.
- Add fake CuPy 14 compatibility regression test, runnable on machines without GPU.
- Extend HP Z840 instructions; NVIDIA driver `CUDA Version: 13.0` is **not**
  CUDA 13 toolkit and **not** a reason to install cupy-cuda13x on Pascal.
- GPU simulation remains opt-in, limited to assembled sparse HEX8 meshes
  and available VRAM, and is **not** known to be faster on P1000.
