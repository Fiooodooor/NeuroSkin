from fastapi.testclient import TestClient
from server import app
from neuroskin_v30.integration import TileInput, diagnostic_context


def test_normalized_experiment_fingerprint_separates_candidate_and_settings():
    base={'contacts':[{'x_mm':20,'y_mm':20,'force_N':.1}]}
    a=diagnostic_context({},'tile',TileInput(**base),{'id':'a','family':'quadrant'},{'r':1})['diagnostic_context']
    b=diagnostic_context({},'tile',TileInput(**base,piezo_count_override=4),{'id':'b','family':'quadrant'},{'r':2})['diagnostic_context']
    c=diagnostic_context({},'tile',TileInput(**base,noise_N=.01),{'id':'a','family':'quadrant'},{'r':1})['diagnostic_context']
    assert a['comparison_key']==b['comparison_key']!=c['comparison_key']
    assert a['genome_hash']!=b['genome_hash'] and a['schema']==1
    assert len(a['solver_hash'])==64 and 'numpy' in a['runtime']


def test_tile_api_attaches_effective_defaults_and_candidate_identity():
    with TestClient(app) as client:
        req={'selection':'hybrid','index':'h01_serpentine_quadrant','contacts':[{'x_mm':20,'y_mm':20,'force_N':.1}]}
        r=client.post('/api/v30/tile',json=req)
        assert r.status_code==200,r.text
        d=r.json();c=d['diagnostic_context']
        assert c['candidate_id']==d['candidate_id'] and c['settings']['size']==3
        assert c['selection']['index']==req['index'] and len(c['genome_hash'])==64
        assert d['tier']=='T0'
