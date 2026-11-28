"""On-demand process-tree telemetry. Never infer utilization from reservations."""
from threading import Lock
from time import monotonic


def cpu_equivalents(previous,current,elapsed):
    if elapsed<=0:return None
    # Matched (PID, creation time) only. Exited/new workers may be missed.
    return sum(max(0.,current[k]-previous[k]) for k in current.keys() & previous.keys())/elapsed


class ProcessTreeSampler:
    def __init__(self):
        self.lock=Lock();self.previous=None;self.time=None;self.last=None

    def snapshot(self):
        try:import psutil
        except ImportError:return {'available':False,'reason':'psutil unavailable'}
        with self.lock:
            now=monotonic()
            if self.time is not None and now-self.time<.25:return dict(self.last)
            try:
                root=psutil.Process()
                processes=[root,*root.children(recursive=True)]
            except (psutil.Error,OSError):return {'available':False,'reason':'process tree unavailable'}
            current={};rss=0
            for p in processes:
                try:
                    with p.oneshot():
                        ident=(p.pid,p.create_time());t=p.cpu_times();mem=p.memory_info().rss
                    current[ident]=float(t.user+t.system);rss+=mem
                except (psutil.Error,OSError):continue
            if not current:return {'available':False,'reason':'no readable processes'}
            elapsed=None if self.time is None else now-self.time
            equivalents=None if self.previous is None else cpu_equivalents(self.previous,current,elapsed)
            self.previous=current;self.time=now
            self.last={'available':True,'logical_cpu_equivalents_lower_estimate':None if equivalents is None else round(equivalents,2),
                       'sample_interval_s':None if elapsed is None else round(elapsed,3),
                       'process_count':len(current),'rss_sum_mib':round(rss/1048576,1),
                       'note':'Matched process-tree CPU time delta; short-lived workers may be missed. RSS sum may double-count shared pages. Not a scheduler limit.'}
            return dict(self.last)
