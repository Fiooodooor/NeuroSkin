from fastapi.testclient import TestClient
from server import app


def test_fusion_api_is_diagnostic_and_honors_wiring():
    with TestClient(app) as client:
        p={'selection':'hybrid','index':'h01_serpentine_quadrant','grid':3,'frequency_hz':0.,
           'piezo_count_override':4,'piezo_wiring_override':1}
        r=client.post('/api/v30/fusion',json=p)
        assert r.status_code==200,r.text
        d=r.json()
        assert d['tier']=='T0' and d['evidence']=='DIAGNOSTIC_ONLY'
        assert d['pvdf_output_count']==1
        assert d['pvdf_saturated_sample_fraction_assumed']==0.
        assert sum(d['sample_counts'].values())==225
        assert client.get('/api/v30/capabilities').json()['sensor_fusion_T0']
        p['frequency_hz']=151
        assert client.post('/api/v30/fusion',json=p).status_code==422
