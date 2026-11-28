"""Selection identity, preview overrides and live finalist lookup regressions."""
from fastapi.testclient import TestClient
from advanced import EvolutionEngine
import server


def test_current_finalist_lookup_before_records_checkpoint(tmp_path):
    evolution=EvolutionEngine(tmp_path)
    finalist={'id':'7-2','family':'quadrant','genome':{'topology':'orthogonal'}}
    evolution.state['audit_top3']=[finalist]
    assert not evolution.records
    found=evolution.lookup('id','7-2')
    assert found==finalist
    found['genome']['topology']='changed'
    assert evolution.lookup('id','7-2')['genome']['topology']=='orthogonal'
    assert evolution.lookup('gallery','not-an-index') is None


def test_guarded_requests_reject_stale_context_before_computation():
    with TestClient(server.app) as client:
        req={'selection':'hybrid','index':'h01_serpentine_quadrant','expected_live_run_id':'stale-run-id'}
        for path in ('/api/characterize','/api/spatial_pressure','/api/evaluate_all','/api/fem/simulate'):
            assert client.post(path,json=req).status_code==409
        assert client.get('/api/mesh',params={**req,'kind':req['selection']}).status_code==409
        assert client.get('/api/export/genome',params=req).status_code==409
        assert client.post('/api/v30/tile',json={**req,'contacts':[{'x_mm':20,'y_mm':20,'force_N':.1}]}).status_code==409


def test_candidate_expectation_and_spatial_preview_override():
    with TestClient(server.app) as client:
        req={'selection':'hybrid','index':'h01_serpentine_quadrant','expected_candidate_id':'wrong-id'}
        assert client.post('/api/spatial_pressure',json=req).status_code==409
        req['expected_candidate_id']='hybrid-h01_serpentine_quadrant'
        req['piezo_count_override']=999
        assert client.post('/api/spatial_pressure',json=req).status_code==422
        req['piezo_count_override']=4;req['piezo_wiring_override']=1;req['grid_size']=3
        response=client.post('/api/spatial_pressure',json=req)
        assert response.status_code==200,response.text
        assert response.json()['candidate_id']==req['expected_candidate_id']
