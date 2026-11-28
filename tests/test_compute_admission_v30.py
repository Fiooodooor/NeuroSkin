import threading
import pytest
from compute_admission import ComputeAdmission, ComputeBusy


def test_manual_exclusion_and_release_on_failure():
    c=ComputeAdmission(lambda:False)
    with pytest.raises(ValueError):
        with c.manual('contact'):
            assert c.snapshot()['manual_active']['name']=='contact'
            with pytest.raises(ComputeBusy):
                with c.manual('fusion'):pass
            with pytest.raises(ComputeBusy):
                with c.start_guard():pass
            raise ValueError('solver rejected')
    assert c.snapshot()['manual_active'] is None
    assert c.snapshot()['rejected_requests']==2
    assert c.snapshot()['recent_manual_requests'][-1]['outcome']=='request_failed'
    with c.manual('fusion'):pass
    assert c.snapshot()['recent_manual_requests'][-1]['outcome']=='request_completed'


def test_evolution_owns_slot_through_cleanup():
    alive=[False];c=ComputeAdmission(lambda:alive[0])
    with c.start_guard():alive[0]=True
    for _ in range(3):
        with pytest.raises(ComputeBusy):
            with c.manual('FEM'):pass
    alive[0]=False
    with c.manual('FEM'):pass


def test_atomic_start_and_manual_race():
    alive=[False];c=ComputeAdmission(lambda:alive[0]);entered=threading.Event();release=threading.Event();result=[]
    def start():
        with c.start_guard():
            entered.set();assert release.wait(5);alive[0]=True
    def manual():
        try:
            with c.manual('FEM'):result.append('admitted')
        except ComputeBusy:result.append('rejected')
    a=threading.Thread(target=start);a.start();assert entered.wait(5)
    b=threading.Thread(target=manual);b.start();release.set();a.join(5);b.join(5)
    assert not a.is_alive() and not b.is_alive() and result==['rejected']


def test_route_preserves_request_schema_and_returns_conflict():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from pydantic import BaseModel
    class Request(BaseModel):
        number:int
    alive=[True];c=ComputeAdmission(lambda:alive[0]);app=FastAPI()
    @app.post('/solve')
    @c.route('solve')
    def solve(req:Request):return {'result':req.number*2}
    client=TestClient(app)
    assert client.post('/solve',json={'number':3}).status_code==409
    alive[0]=False
    assert client.post('/solve',json={'number':3}).json()=={'result':6}
    assert client.post('/solve',json={}).status_code==422


def test_history_is_bounded():
    c=ComputeAdmission(lambda:False)
    for i in range(20):
        with c.manual(str(i)):pass
    h=c.snapshot()['recent_manual_requests']
    assert len(h)==16 and h[0]['id']==5 and h[-1]['id']==20


def test_budgeted_manual_concurrency_and_progress_isolation():
    c=ComputeAdmission(lambda:False,lambda:{'cpu':2,'ram_mb':10000})
    with c.manual('sensor_fusion',{}):
        first=c.progress_callback();first({'stage':'first'})
        with c.manual('verification_box',{}):
            second=c.progress_callback();second({'stage':'second'})
            jobs=c.snapshot()['manual_jobs']
            assert len(jobs)==2 and jobs[0]['progress']=={'stage':'first'} and jobs[1]['progress']=={'stage':'second'}
            assert c.snapshot()['reserved']['cpu_workers']==2
            with pytest.raises(ComputeBusy):
                with c.manual('nonlinear_contact',{}):pass
        assert len(c.snapshot()['manual_jobs'])==1
    assert c.snapshot()['reserved']['cpu_workers']==0


def test_gpu_and_ram_conflicts_and_unknown_capacity():
    c=ComputeAdmission(lambda:False,lambda:{'cpu':8,'ram_mb':20000})
    with c.manual('linear_fem',{'compute_device':'gpu','pitch_mm':1.25}):
        with pytest.raises(ComputeBusy,match='GPU'):
            with c.manual('linear_fem',{'compute_device':'gpu','pitch_mm':1.25}):pass
        with c.manual('sensor_fusion',{}):pass
    c=ComputeAdmission(lambda:False,lambda:{'cpu':8,'ram_mb':None})
    with c.manual('sensor_fusion',{}):
        assert c.snapshot()['manual_active']['allocation']['exclusive_fallback']
        with pytest.raises(ComputeBusy):
            with c.manual('verification_box',{}):pass

def test_gpu_vram_reservation_and_known_ram_rejection():
    gpu={'available':True,'free_vram_mb':1000}
    c=ComputeAdmission(lambda:False,lambda:{'cpu':8,'ram_mb':20000},gpu_probe=lambda:gpu)
    with c.manual('linear_fem',{'compute_device':'gpu','pitch_mm':1.25}):
        assert c.current_allocation()['vram_mb_estimate']==450
        assert c.snapshot()['reserved']['vram_mb_estimate']==450
    assert c.snapshot()['reserved']['vram_mb_estimate']==0
    gpu['free_vram_mb']=100
    with pytest.raises(ComputeBusy,match='GPU memory'):
        with c.manual('linear_fem',{'compute_device':'gpu'}):pass
    c=ComputeAdmission(lambda:False,lambda:{'cpu':8,'ram_mb':1000})
    with pytest.raises(ComputeBusy,match='RAM'):
        with c.manual('linear_fem',{'pitch_mm':.3125}):pass
