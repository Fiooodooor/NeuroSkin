"""Hardware discovery and resource recommendations for NeuroSkin (Windows and Linux).

No CUDA dependencies are imported. Profiles describe available hardware, not expected speedup.
On machines with multiple Windows processor groups, OS affinity may expose fewer logical
CPUs than the entire host; respect actual process affinity for worker planning.
"""
from __future__ import annotations
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass


def _memory_mb() -> tuple[int | None, int | None]:
    try:
        import psutil
        m = psutil.virtual_memory()
        return round(m.total / 1048576), round(m.available / 1048576)
    except (ImportError, OSError, AttributeError):
        return None, None


def _cpu() -> dict:
    logical = os.cpu_count() or 1
    physical = None
    allowed = logical
    try:
        import psutil
        logical = psutil.cpu_count(logical=True) or logical
        physical = psutil.cpu_count(logical=False)
        try:
            allowed = len(psutil.Process().cpu_affinity())
        except (OSError, AttributeError, ValueError):
            allowed = logical
    except ImportError:
        try:
            allowed = len(os.sched_getaffinity(0))
        except (AttributeError, OSError):
            pass
    allowed=max(1, min(int(allowed),int(logical)))
    # On multi-socket Windows, psutil.Process().cpu_affinity() can expose only
    # one processor group. Do not equate a logical CPU in that subset to a
    # *physical* core: on the user's Z840, 44 allowed threads likely represent
    # roughly 22 cores with SMT. This is a conservative estimate, not a topology map.
    if physical:
        threads_per_core=max(1, round(logical / physical))
        available_physical=max(1, min(physical, allowed // threads_per_core))
    else:
        threads_per_core=None
        available_physical=max(1,allowed//2)
    return {"logical_host": logical, "physical_host": physical,
            "process_available_logical": allowed,
            "threads_per_physical_core_estimate": threads_per_core,
            "process_available_physical_estimate": available_physical,
            "affinity_subset_of_host": allowed < logical}


def _parse_gpu_line(line: str) -> dict | None:
    fields = [s.strip() for s in line.split(',')]
    if len(fields) < 4:
        return None
    try:
        return {"name": fields[0], "total_vram_mb": int(float(re.search(r"[0-9]+(?:\.[0-9]+)?", fields[1]).group())),
                "free_vram_mb": int(float(re.search(r"[0-9]+(?:\.[0-9]+)?", fields[2]).group())), "driver": fields[3],
                "compute_capability": fields[4] if len(fields) >= 5 else None}
    except (ValueError,AttributeError):
        return None


def discover_gpu() -> dict:
    """Detect Nvidia without importing cupy or loading a CUDA context."""
    exe = shutil.which('nvidia-smi')
    if not exe:
        return {"available": False, "reason": "nvidia-smi executable not found"}
    fields = 'name,memory.total,memory.free,driver_version,compute_cap'
    def query(cols: str):
        return subprocess.run([exe, f'--query-gpu={cols}', '--format=csv,noheader,nounits'],
                              text=True, capture_output=True, timeout=5, check=False)
    try:
        proc = query(fields)
        if proc.returncode != 0:
            proc = query('name,memory.total,memory.free,driver_version')
        if proc.returncode:
            return {"available": False, "reason": proc.stderr.strip()[:200] or "nvidia-smi query failed"}
        devices = [v for line in proc.stdout.splitlines() if (v := _parse_gpu_line(line)) is not None]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "reason": str(exc)}
    if not devices:
        return {"available": False, "reason": "nvidia-smi returned no devices"}
    gpu = devices[0]
    gpu["available"] = True
    gpu["cuda12_recommended_for_pascal"] = ('P1000' in gpu['name'] or 'Pascal' in gpu['name'])
    gpu["gpu_solver_memory_budget_mb"] = max(0, min(1024, int(.45 * gpu['free_vram_mb'])))
    return gpu


def profile() -> dict:
    cpu = _cpu()
    total, available = _memory_mb()
    gpu = discover_gpu()
    available_cpus = cpu['process_available_logical']
    physical = cpu['process_available_physical_estimate']
    # Reserve a couple of physical cores for OS, the API/browser, and I/O.
    # This avoids recommending 40 workers for only 22 available physical
    # cores in a Windows processor-group affinity subset.
    workers = min(40,max(1,physical - 2)) if physical >= 8 else max(1, physical)
    per_job_mb = min(4096, max(1024, int((available or 16384) * .12)))
    max_heavy_fem = max(1, min(4, int((available or 16384) * .45 / per_job_mb)))
    advisories = [
        "CPU multiprocessing is the default for evolutionary screening; use the GPU only after benchmarking.",
        "FEM elements scale roughly with 1/(mesh pitch)^3; 8x finer pitch can mean ~512x more cells.",
        "In dual-socket systems, NUMA locality and memory bandwidth can limit 44+ concurrent CPU workers.",
        "CPU logical threads are not equivalent to physical cores; benchmark 16/24/32/40 workers.",
    ]
    if gpu.get('available'):
        if gpu.get('total_vram_mb', 0) <= 6144:
            advisories.append('Small-VRAM GPU detected: reserve GPU for 3D visualization and optional small CSR CG; high-resolution solid FEM stays CPU matrix-free.')
        if gpu.get('cuda12_recommended_for_pascal') or str(gpu.get('compute_capability','')).startswith('6.'):
            advisories.append('Pascal compute capability 6.x: CUDA 12.x/CuPy CUDA12 wheel only; CUDA 13 has dropped this architecture.')
    if available_cpus < cpu['logical_host']:
        advisories.append('Process affinity exposes fewer logical CPUs than the host (Windows processor group, affinity mask, or job limits). Worker planning uses the conservative accessible physical-core estimate.')
    if platform.system()=='Windows' and cpu['logical_host']>64:
        advisories.append('Windows 11 process groups can span the host, but Python/psutil affinity is not proof that workers reach both CPU sockets. Benchmark NUMA/affinity before scaling beyond the accessible group.')
    advisories.append('CuPy CUDA_PATH warning may be benign when the [ctk] wheel works; never set a fake CUDA_PATH to silence it.')
    return {"platform": platform.platform(), "cpu": cpu,
            "ram_total_mb": total, "ram_available_mb": available,
            "nvidia_gpu": gpu,
            "recommended": {"evolution_cores": workers, "heavy_fem_concurrency": max_heavy_fem,
                            "per_fem_job_ram_mb": per_job_mb,
                            "default_fem_device": "cpu", "gpu_is_opt_in": True,
                            "recommended_evolution_population": max(96, workers * 3)},
            "advisories": advisories}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Hardware-aware NeuroSkin compute resource planner')
    parser.add_argument('--json', action='store_true', help='Print full machine-readable profile')
    args=parser.parse_args(argv)
    p=profile()
    print(json.dumps(p,indent=2,ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
