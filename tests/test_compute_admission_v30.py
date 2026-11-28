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
