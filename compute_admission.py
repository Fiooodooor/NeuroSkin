"""Atomic process-local resource reservations for manual analyses.

Evolution remains exclusive until its existing controller actually exits.
Manual analyses may coexist under conservative CPU/RAM estimates and one
explicit GPU slot. No queue, hard memory enforcement or cross-process lock.
"""
from collections import deque
from contextlib import contextmanager
from functools import wraps
from threading import Lock,local
from time import monotonic
from dataclasses import asdict


class ComputeBusy(RuntimeError):
    pass


def allocate_manual(name,req,cpu,ram_mb,gpu_busy,has_active):
    """Choose a bounded reservation from the *remaining* estimated capacity."""
    from manual_evaluation import plan_manual, fem_base_ram_mb
    if cpu<1:raise ComputeBusy('No CPU worker budget remaining')
    device='cpu';plan=None
    if name=='evaluate_all':
        device=req.get('fem_compute_device','cpu') if req.get('fem_enabled',True) else 'cpu'
        device='cpu' if device=='auto' else device
        if device not in ('cpu','gpu'):raise ComputeBusy('Unknown compute device')
        desired=max(1,min(cpu,int(req.get('compute_workers') or 1)))
        plan=plan_manual(desired,None if ram_mb is None else 2*ram_mb,req.get('fem_enabled',True),
                         req.get('fem_backend','hex8'),req.get('fem_pitch_mm',.625),device,True)
        count=plan.surrogate_processes+plan.fem_case_workers+plan.matvec_workers
        memory=plan.reserved_ram_mb_estimate
    elif name=='linear_fem':
        count=1;device='gpu' if req.get('compute_device')=='gpu' else 'cpu'
        memory=fem_base_ram_mb(True,req.get('backend','hex8'),req.get('pitch_mm',.3125))
    elif name=='nonlinear_tile':
        count=1;memory=1024+64*int(req.get('size',3))**2
    elif name in ('nonlinear_contact','verification_box','sensor_fusion'):
        count=1;memory=1024
    else:
        count=1;memory=1024
    if device=='gpu' and gpu_busy:raise ComputeBusy('GPU slot reserved by another analysis')
    # Preserve the legacy single-job solver guards on low-memory or unknown
    # systems. Never admit a second heavy request without budget evidence.
    exclusive=ram_mb is None or memory>ram_mb
    if exclusive and has_active:raise ComputeBusy('Insufficient known RAM reservation capacity')
    return {'cpu_workers':count,'ram_mb_estimate':memory,'gpu_slot':device=='gpu',
            'exclusive_fallback':exclusive,'plan':None if plan is None else asdict(plan)}


class ComputeAdmission:
    def __init__(self,evolution_alive,capacity=None,max_manual=4,gpu_probe=None):
        self._alive=evolution_alive;self._capacity=capacity;self._max_manual=max_manual;self._gpu_probe=gpu_probe
        self._lock=Lock();self._active={};self._local=local()
        self._history=deque(maxlen=16);self._sequence=0;self._rejected=0

    def _reject(self,message):
        self._rejected+=1
        raise ComputeBusy(message)

    @contextmanager
    def start_guard(self):
        with self._lock:
            if self._active:self._reject('Heavy analysis active: '+next(iter(self._active.values()))['name'])
            if self._alive():self._reject('Evolution still owns the compute slot (including pause/stop cleanup)')
            yield

    def _reserved(self):
        allocations=[j['allocation'] for j in self._active.values()]
        return {'cpu_workers':sum(a['cpu_workers'] for a in allocations),
                'ram_mb_estimate':sum(a['ram_mb_estimate'] for a in allocations),
                'gpu_slots':sum(a['gpu_slot'] for a in allocations),
                'vram_mb_estimate':sum(a.get('vram_mb_estimate',0) for a in allocations)}

    @contextmanager
    def manual(self,name,request=None):
        req=request or {}
        wants_gpu=(name=='linear_fem' and req.get('compute_device')=='gpu') or (name=='evaluate_all' and req.get('fem_enabled',True) and req.get('fem_compute_device')=='gpu')
        gpu=self._gpu_probe() if wants_gpu and self._gpu_probe is not None else None
        with self._lock:
            ram=None
            if self._alive():self._reject('Evolution owns the compute slot; stop it and wait for cleanup before heavy analysis')
            if len(self._active)>=self._max_manual:self._reject('Manual analysis concurrency limit reached')
            if any(j['allocation']['exclusive_fallback'] for j in self._active.values()):
                self._reject('An exclusive heavy analysis is active')
            if self._capacity is None or request is None:
                if self._active:self._reject('Heavy analysis active')
                allocation={'cpu_workers':1,'ram_mb_estimate':0,'gpu_slot':False,'exclusive_fallback':True,'plan':None}
            else:
                cap=self._capacity();used=self._reserved()
                cpu=max(0,int(cap['cpu'])-used['cpu_workers'])
                ram=cap.get('ram_mb')
                ram=None if ram is None else max(0,int(ram*.5)-used['ram_mb_estimate'])
                if name=='evaluate_all' and request.get('compute_workers') is None:request={**request,'compute_workers':cap.get('default_cores',1)}
                try:allocation=allocate_manual(name,request,cpu,ram,bool(used['gpu_slots']),bool(self._active))
                except ComputeBusy as exc:self._reject(str(exc))
            if allocation['gpu_slot']:
                if gpu is not None:
                    free=gpu.get('free_vram_mb')
                    if not gpu.get('available') or free is None:
                        self._reject('GPU unavailable or VRAM unknown: '+str(gpu.get('reason','no VRAM measurement')))
                    vram=min(1024,int(.45*free))
                    if vram<128:self._reject('Insufficient free GPU memory for CSR solve')
                else:vram=1024
                allocation['vram_mb_estimate']=vram
            else:allocation['vram_mb_estimate']=0
            if ram is not None and allocation['ram_mb_estimate']>ram:
                self._reject('Insufficient RAM budget for requested analysis; use coarser mesh or free memory')
            self._sequence+=1
            job={'id':self._sequence,'name':name,'started':monotonic(),'allocation':allocation}
            self._active[job['id']]=job
        previous=getattr(self._local,'job_id',None);self._local.job_id=job['id']
        outcome='request_completed'
        try:
            yield
        except BaseException:
            outcome='request_failed';raise
        finally:
            self._local.job_id=previous
            with self._lock:
                self._history.append({'id':job['id'],'name':name,'outcome':outcome,'allocation':allocation,
                                      'elapsed_s':round(monotonic()-job['started'],3),'progress':job.get('progress')})
                self._active.pop(job['id'],None)

    def current_allocation(self):
        with self._lock:
            job=self._active.get(getattr(self._local,'job_id',None))
            return None if job is None else dict(job['allocation'])

    def progress_callback(self):
        # Capture request identity before handing callback to process-future thread.
        job_id=getattr(self._local,'job_id',None)
        def publish(progress):
            with self._lock:
                if job_id in self._active:self._active[job_id]['progress']=progress
        return publish

    def snapshot(self):
        with self._lock:
            jobs=[{'id':a['id'],'name':a['name'],'elapsed_s':round(monotonic()-a['started'],3),
                   'progress':a.get('progress'),'allocation':a['allocation']} for a in self._active.values()]
            return {'policy':'budgeted_manual_jobs_exclusive_evolution','evolution_active':bool(self._alive()),
                    'manual_active':jobs[0] if jobs else None,'manual_jobs':jobs,'reserved':self._reserved(),
                    'recent_manual_requests':list(self._history),'rejected_requests':self._rejected,'queue_enabled':False,
                    'note':'Estimated CPU/RAM/VRAM reservations, one GPU slot; not hard limits. Request completion is not solver qualification.'}

    def route(self,name):
        def decorate(fn):
            @wraps(fn)
            def wrapped(*args,**kwargs):
                from fastapi import HTTPException
                req=kwargs.get('req',args[0] if args else None)
                request=req.model_dump() if hasattr(req,'model_dump') else None
                try:
                    with self.manual(name,request):return fn(*args,**kwargs)
                except ComputeBusy as exc:raise HTTPException(409,str(exc)) from exc
            return wrapped
        return decorate
