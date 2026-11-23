# NeuroSkin v1.7 — dependency, CPU affinity and CUDA performance remediation

## Delivered changes

1. **Single installation file**: removed separate `requirements_highres.txt`, `requirements_gpu_pascal.txt` and `requirements_fem_optional.txt`. All requested packages are now in `requirements.txt`; the CUDA package is `cupy-cuda12x[ctk]>=14.0.1,<15`, never CUDA 13 for Pascal CC 6.1.
2. **Hardware worker-count bug**: added conservative `process_available_physical_estimate` based on CPU affinity and host SMT ratio. For 88 host logical and 44 process-available threads, estimate 22 accessible physical cores and recommend 20 workers initially, not 40. This is a planning estimate, not verified NUMA topology.
3. **Benchmark redesign**: one matrix factorization and first solve, then configurable warm-up and repeat solves; report cold/warm, full displacement-field comparison, and a break-even estimate. CPU is still default; even a correct GPU calculation is not automatically recommended.
4. **CuPy `CUDA_PATH` warning**: suppress only that precise misleading toolkit-path warning *inside the validated CUDA initialization path*; real CUDA exceptions remain visible. Never set an invalid CUDA_PATH merely to suppress diagnostics.
5. **Environment doctor**: `python environment_doctor.py [--gpu]` reports import health and can optionally run a real 2×2 sparse CUDA CG solve.
6. **Launcher**: `launch_windows.bat` starts without repeating large pip installations; `install_windows.bat` is the one-time all-dependency installer.
7. **Regression tests**: new checks for single manifest, Windows 88/44 affinity planning, benchmark field accuracy, GPU setup cost, and CPU fallback.

## Verified workload facts from the user's Z840

Quadro P1000 CC 6.1, Python 3.14, CuPy 14.2.0. CUDA sparse CG smoke residual ~1.22e-16. At 125 elements and one solve: CPU 0.014618s cold versus GPU 21.964896s. Full displacement difference was 2.35e-10 relative. Correctness and speed are separate. Small sparse jobs strongly favor CPU on this machine.

## Run

```powershell
python -m pip install -r requirements.txt
python -m pip check
python environment_doctor.py --gpu
python hardware_profile.py --json
python hardware_benchmark.py --family quadrant --pitch 1.25 --repeats 5 --warmup 2 --out gpu_vs_cpu_v17.json
python server.py --cores auto --open --port 8765
```

The new benchmark still needs execution on the user's P1000 to determine warm-solve performance. On systems without an NVIDIA GPU, CUDA is unavailable but CPU simulation and evolution still work if the CUDA package is installed.

## Not changed, and important limits

- Actual continuum FEM uses small-strain linear-elastic HEX8. TPU/silicone nonlinear large-deformation/contact fatigue are NOT solved.
- Finer voxel meshes are still expensive and must be checked for convergence.
- PVDF is represented electrically but its bonded laminate stiffness is not included in the solid mechanics.
- All 20 seed STL models are conceptual visual assemblies, not guaranteed printable CAD.
- Gmsh, scikit-fem, meshio and PyVista are installed but are not yet used by the principal HEX8 solver.
