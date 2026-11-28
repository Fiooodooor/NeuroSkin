# NeuroSkin 1.5: HP Z840 Windows 11 hardware guide

## Hardware assumptions

- Windows 11 Pro build 26100.
- 2 x Xeon E5-2699C v4. If 22 cores / 44 logical threads is **per socket**, total is 44 physical and 88 logical CPUs. Check the actual allowed CPUs using the profiler. Dual-socket NUMA and Windows processor groups may affect processes.
- System RAM 128 GB. The user-reported 69,585 MB available is most likely **system RAM**, not GPU VRAM.
- Quadro P1000 Pascal CC 6.1 with 4 GB VRAM; CUDA 12.x, NOT CUDA 13.

## Windows PowerShell setup

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python hardware_profile.py --json
python server.py --cores auto --open --port 8765
```

For optional GPU tests:

```powershell
nvidia-smi
python -m pip install -r requirements.txt
python hardware_benchmark.py --family quadrant --pitch 1.25 --out gpu_vs_cpu.json
python fem_cli.py --family quadrant --backend hex8 --pitch 1.25 --compute-device gpu --force 0.1 --out gpu_test
```

Recommended CPU evolution:

```powershell
python evolve_cli.py --cores 32 --seconds 300 --population 128 --mode all --fem --fem-backend hex8 --fem-pitch 0.3125 --out runs_v05
```

On the reported 88-host-logical / 44-process-available configuration, only about 22 physical cores may be accessible per group. The corrected `--cores auto` recommendation is roughly **20**; benchmark 12/16/20/24/32. Windows 11 multi-group scheduling needs direct measurement to confirm cross-socket usage. High-resolution HEX8 0.15625 mm should use the Numba-accelerated CPU matrix-free solver. A voxel pitch 8x smaller can generate approximately 512x as many volume cells.

## Backend implementation and limitations

- CPU multi-process evolution and Top-3 FEM are retained and are the default.
- Manual GPU CUDA sparse conjugate gradient can be used only on small assembled HEX8 systems up to 6000 elements. The GPU working-set allowance is the smaller of 1 GiB and 45% of currently free VRAM.
- GPU `--compute-device gpu` is not automatically faster than CPU. The P1000 has poor FP64 throughput and limited VRAM; benchmark and verify displacement agreement.
- `--compute-device auto` **currently means CPU**, deliberately, until validated GPU results justify automatic selection.
- CPU high-resolution matrix-free HEX8 is **not offloaded to GPU**; a tested custom matrix-free CUDA kernel would be needed for this.
- Earlier versions had not been hardware-tested; the user subsequently ran and passed the CUDA sparse CG smoke test and supplied a benchmark, documented below.
- Both backends implement isotropic linear elasticity and the same underlying HEX8 stiffness; they do not model nonlinear hyperelasticity, contact or piezoelectric FEM.

Sources:
- https://www.nvidia.com/content/dam/en-zz/Solutions/design-visualization/quadro-product-literature/301968-DS-NV-Quadro-Pascal-P1000-US-03Feb17-NV-fnl-WEB.pdf
- https://docs.nvidia.com/cuda/archive/13.0.0/cuda-toolkit-release-notes/
- https://docs.cupy.dev/en/v13.5.1/reference/generated/cupyx.scipy.sparse.linalg.cg.html

## Windows 11 / Python 3.14 / Quadro P1000 hotfix (v1.5.1)

A previous optional dependency erroneously required `cupy-cuda12x>=13,<14`,
which lacks Windows CPython 3.14 wheels. Install CuPy 14 with **CUDA 12.x**
runtime and libraries (not CUDA 13.x):

```powershell
python -m pip install -r requirements.txt
python gpu_selftest.py
python hardware_benchmark.py --family quadrant --pitch 1.25 --out gpu_vs_cpu.json
```

CuPy 14's sparse conjugate-gradient API uses `rtol`, not `tol`; corrected in
`gpu_sparse_fem.py`. `nvidia-smi` reporting CUDA 13.0 only means that the
installed driver supports up to CUDA 13 APIs; the P1000 still requires
CUDA **12.x toolkit/runtime** code for its Pascal architecture.

With ~2361 MiB already used out of 4096 MiB VRAM, only ~1735 MiB is free
*before* CuPy initializes, and Windows WDDM may reserve more. The GPU path
uses conservative limits and remains optional. CPU is the recommended
backend for 0.3125/0.15625 mm matrix-free HEX8. If GPU runtime is not
available, choose CPU; do not try to force CUDA 13 for the P1000.

## v1.7 hardware result and installation update (2026-11-23)

Your P1000 actually completed CUDA sparse CG correctly. Benchmark for 125 elements:
- CPU: 0.014618 s cold, 0.011629 s setup, 0.002074 s solve.
- GPU: 21.964896 s cold, 20.752149 s setup, 1.210976 s solve.
- Relative displacement difference: 2.351772055e-10.

**Do not force CUDA for this workload.** Use `--compute-device cpu` or `auto` (which deliberately maps to CPU) for FEM. The GPU driver/CTK compatibility is confirmed by the smoke test, but GPU acceleration is not.

Only `requirements.txt` remains; it installs all packages with a single command. `environment_doctor.py --gpu` verifies the CUDA runtime. The newer `hardware_benchmark.py` separates cold and warm performance and full displacement-field agreement. Windows 11 affinity detection may show a subset of the host's 88 logical CPUs; the auto worker count is conservative and does not guarantee a two-socket spread.
