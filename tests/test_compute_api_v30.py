from fastapi.testclient import TestClient
import server


def test_conflicting_heavy_routes_and_lightweight_tile(monkeypatch):
    class Live:
        def is_alive(self):return True
    monkeypatch.setattr(server.EVO,'thread',Live())
    client=TestClient(server.app)
    assert client.get('/api/compute/status').json()['evolution_active']
    sel={'selection':'hybrid','index':'h01_serpentine_quadrant'}
    for path,body in [('/api/evaluate_all',sel),('/api/fem/simulate',sel),
                      ('/api/v30/nonlinear/contact-box',{}),('/api/v30/nonlinear/candidate',sel),
                      ('/api/v30/fusion',sel)]:
        r=client.post(path,json=body)
        assert r.status_code==409,(path,r.text)
    r=client.post('/api/v30/tile',json={**sel,'contacts':[{'x_mm':20,'y_mm':20,'force_N':.1}]})
    assert r.status_code==200,r.text


def test_manual_reservation_rejects_start_and_releases():
    client=TestClient(server.app)
    with server.COMPUTE.manual('test'):
        assert client.get('/api/compute/status').json()['manual_active']['name']=='test'
        assert client.post('/api/start',json={}).status_code==409
    assert client.get('/api/compute/status').json()['manual_active'] is None
