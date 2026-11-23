"""Version 1.1 archive/GUI API contract tests. No external network required."""
import json
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
import server
from archive_store import ArchiveStore

class ArchiveAPITest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.orig=server.ARCHIVES
        server.ARCHIVES=ArchiveStore(Path(self.temp.name))
        self.client=TestClient(server.app)
        root=server.ARCHIVES.path('run41')
        (root/'stages').mkdir(parents=True)
        def c(i,f):return {'id':i,'family':f,'generation':2,
                           'genome':{'topology':'arched'},'fitness':80.0,
                           'audit':{'audit_score':80.0,'feasible':True}}
        self.champion=c('2-1','crown')
        self.other=c('2-2','chiral')
        self.third=c('2-3','quadrant')
        state={'id':'run41','status':'completed','history':[{'generation':2,'elapsed':3.,'best':90.,'median':75.,'diversity':3}],
               'generation':2,'evaluated':30,'elapsed':3.,'best':self.champion,'audited_champion':self.champion,
               'audit_top3':[self.champion,self.other,self.third],'gallery':[self.other],'champions':{'crown':self.champion},
               'audit_history':[],'stage_decisions':[]}
        (root/'results.json').write_text(json.dumps(state),encoding='utf-8')
        (root/'stages'/'stage_000002.json').write_text(json.dumps({'schema_version':1,'run_id':'run41',
            'generation':2,'top3':[self.champion,self.other,self.third], 'champion':self.champion,
            'decision':{'replaced':True}}),encoding='utf-8')
    def tearDown(self):
        self.client.close();server.ARCHIVES=self.orig;self.temp.cleanup()
    def test_archive_reopen_and_stage_selection(self):
        r=self.client.get('/api/archives');self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['runs'][0]['id'],'run41')
        self.assertEqual(self.client.get('/api/archives/run41').json()['best']['id'],'2-1')
        r=self.client.get('/api/archives/run41/stages');self.assertEqual(r.json()['stages'][0]['generation'],2)
        self.assertEqual(self.client.get('/api/archives/run41/stages/2').json()['top3'][1]['id'],'2-2')
    def test_archive_not_found_and_bad_identifiers(self):
        self.assertEqual(self.client.get('/api/archives/notexist').status_code,404)
        self.assertEqual(self.client.get('/api/archives/run41/stages/111').status_code,404)
        self.assertEqual(self.client.get('/api/archives/run41/stages/0').status_code,422)
    def test_export_zip_and_json(self):
        r=self.client.get('/api/archives/run41/download')
        self.assertEqual(r.status_code,200)
        self.assertIn('application/zip',r.headers['content-type'])
        import io,zipfile
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            self.assertIn('results.json',z.namelist())
            self.assertIn('stages/stage_000002.json',z.namelist())
        j=self.client.get('/api/export/json?run_id=run41')
        self.assertEqual(j.status_code,200)
        self.assertEqual(j.json()['id'],'run41')
    def test_run_comparison_refuses_unknown_version(self):
        r=self.client.get('/api/archives/compare?left=run41&right=run41')
        self.assertEqual(r.status_code,200)
        self.assertFalse(r.json()['comparable'])
        self.assertIsNone(r.json()['score_delta_right_minus_left'])

    def test_saved_model_selection(self):
        c=server.select_candidate('id','2-2','chiral','run41',2)
        self.assertEqual(c['family'],'chiral')
        self.assertEqual(server.select_candidate('best','0','crown','run41',2)['id'],'2-1')

if __name__=='__main__':unittest.main()
