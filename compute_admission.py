"""Conservative process-local admission for expensive CPU/RAM/GPU work.

Evolution owns the heavy-compute slot until its controller thread actually exits,
including pause and shutdown. Manual calls are synchronous, not queued. This
is not an RSS limiter, multi-process scheduler or cancellation mechanism.
"""
from collections import deque
from contextlib import contextmanager
from functools import wraps
from threading import Lock
from time import monotonic


class ComputeBusy(RuntimeError):
    pass


class ComputeAdmission:
    def __init__(self, evolution_alive):
        self._alive = evolution_alive
        self._lock = Lock()
        self._active = None
        self._history = deque(maxlen=16)
        self._sequence = 0
        self._rejected = 0

    def _reject(self, message):
        self._rejected += 1
        raise ComputeBusy(message)

    @contextmanager
    def start_guard(self):
        """Keep the admission lock through synchronous controller startup."""
        with self._lock:
            if self._active is not None:
                self._reject('Heavy analysis active: '+self._active['name'])
            if self._alive():
                self._reject('Evolution still owns the compute slot (including pause/stop cleanup)')
            yield

    @contextmanager
    def manual(self, name):
        with self._lock:
            if self._alive():
                self._reject('Evolution owns the compute slot; stop it and wait for cleanup before heavy analysis')
            if self._active is not None:
                self._reject('Heavy analysis active: '+self._active['name'])
            self._sequence += 1
            job = {'id':self._sequence,'name':name,'started':monotonic()}
            self._active = job
        outcome = 'request_completed'
        try:
            yield
        except BaseException:
            outcome = 'request_failed'
            raise
        finally:
            with self._lock:
                self._history.append({'id':job['id'],'name':name,'outcome':outcome,
                                      'elapsed_s':round(monotonic()-job['started'],3)})
                self._active = None

    def set_progress(self, progress):
        with self._lock:
            if self._active is not None:self._active['progress']=progress

    def snapshot(self):
        with self._lock:
            a = self._active
            return {'policy':'one_heavy_job_per_server_process','evolution_active':bool(self._alive()),
                    'manual_active':None if a is None else {'id':a['id'],'name':a['name'],
                                                           'elapsed_s':round(monotonic()-a['started'],3),'progress':a.get('progress')},
                    'recent_manual_requests':list(self._history),'rejected_requests':self._rejected,'queue_enabled':False,
                    'note':'Admission only; request completion is not solver qualification. Lightweight inspections remain available.'}

    def route(self, name):
        """FastAPI sync route wrapper; preserve the original typed signature."""
        def decorate(fn):
            @wraps(fn)
            def wrapped(*args, **kwargs):
                from fastapi import HTTPException
                try:
                    with self.manual(name):
                        return fn(*args, **kwargs)
                except ComputeBusy as exc:
                    raise HTTPException(409,str(exc)) from exc
            return wrapped
        return decorate
