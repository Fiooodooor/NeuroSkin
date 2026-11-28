"""Bounded two-level CPU scheduling for the identical Top-3 audit protocol.

RAM reservations are conservative scheduling estimates, not measured RSS limits.
A single job retains the FEM solver's own existing resource guards.
"""
from dataclasses import dataclass, asdict
import concurrent.futures as cf
import sys


@dataclass(frozen=True)
class AuditPlan:
    jobs: int
    processes: int
    case_workers: int
    available_ram_mb: int | None
    reserved_ram_mb_estimate: int
    memory_limited: bool

    def as_dict(self):
        return asdict(self)


def process_capacity(cores, population):
    # Windows ProcessPoolExecutor has a documented maximum of 61 workers.
    return max(1, min(int(cores), int(population), 61 if sys.platform == 'win32' else 256))


def available_ram_mb():
    try:
        import psutil
        return int(psutil.virtual_memory().available // 1048576)
    except (ImportError, OSError, AttributeError):
        return None


def plan_audits(jobs, cores, fem_enabled, backend, pitch_mm, ram_mb):
    if jobs < 0 or cores < 1:
        raise ValueError('Invalid audit job or CPU budget')
    if jobs == 0:
        return AuditPlan(0, 0, 0, ram_mb, 0, False)
    # AUTO may choose HEX8 for hybrids even at a fine pitch.
    solid = fem_enabled and backend != 'beam'
    base_mb = (6144 if pitch_mm < .4 else 4096) if solid else 512
    case_mb = 256  # extra RHS/CG/postprocessing workspace per additional case
    max_processes = process_capacity(cores, jobs)
    if ram_mb is None:
        # Never assume that unreported memory can support multiple large solves.
        slots = 1 if solid else max_processes
        return AuditPlan(jobs, slots, 1, None, slots*base_mb, solid)
    budget = max(0, int(ram_mb*.5))
    slots = max(1, min(max_processes, budget//base_mb))
    cpu_cases = min(8, max(1, cores//slots)) if solid else 1
    mem_cases = max(1, 1+(budget//slots-base_mb)//case_mb)
    cases = min(cpu_cases, mem_cases)
    return AuditPlan(jobs, slots, cases, ram_mb,
                     slots*(base_mb+(cases-1)*case_mb),
                     slots<max_processes or cases<cpu_cases or budget<base_mb)


def run_audit_batch(pool, worker, jobs, plan, *, check_stop, progress):
    """Keep at most plan.processes outstanding tasks; return input order.

    No new work is submitted after cancellation. Running tasks are drained or
    terminated by the owning evolution controller before it permits another run.
    Progress counts scheduled outstanding jobs, not OS-measured CPU activity.
    """
    if len(jobs)!=plan.jobs:
        raise ValueError('Audit plan/job count mismatch')
    if not jobs:
        progress(0,0)
        return []
    out=[None]*len(jobs)
    done=0
    if pool is None:
        for i,job in enumerate(jobs):
            check_stop();progress(1,done)
            out[i]=worker((*job,plan.case_workers))
            done+=1;progress(0,done);check_stop()
        return out
    pending={}
    cursor=0
    try:
        while done<len(jobs):
            check_stop()
            while cursor<len(jobs) and len(pending)<plan.processes:
                pending[pool.submit(worker,(*jobs[cursor],plan.case_workers))]=cursor
                cursor+=1
            progress(len(pending),done)
            ready,_=cf.wait(pending,timeout=.2,return_when=cf.FIRST_COMPLETED)
            for f in ready:
                i=pending.pop(f)
                out[i]=f.result();done+=1
            progress(len(pending),done)
        check_stop()
    finally:
        for f in pending:f.cancel()
        progress(0,done)
    return out
