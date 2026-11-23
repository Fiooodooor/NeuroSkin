# NeuroSkin Evolution Lab 1.5 — hardware-aware CPU and experimental CUDA

- Retains balanced-PVDF v1.4 models, history, FEM and Basic/Advanced GUI.
- Adds `hardware_profile.py` for CPU physical/logical/available cores, RAM and NVIDIA GPU VRAM.
- Adds `--cores auto` to server and headless evolution.
- Extends `/api/system` and displays detected resources in GUI.
- Adds experimental **CUDA 12.x** CuPy sparse conjugate-gradient solver for **small assembled HEX8 systems only**; fails explicitly if unavailable.
- Adds `--compute-device cpu|gpu|auto` to manual FEM GUI/API and `fem_cli.py` (auto stays CPU).
- Adds 6000-element guard, GPU memory limits and a numerical/timing comparison script `hardware_benchmark.py`.
- Adds `requirements.txt` (historically a separate GPU file, merged in v1.7) for optional Quadro P1000 support.
- GPU-path runtime has not been tested on the target Quadro P1000 hardware. No claimed speedup.
