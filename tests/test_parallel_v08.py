import unittest, random, tempfile, os
from pathlib import Path
from fastapi.testclient import TestClient
from advanced import FAMILIES,KINDS,new_genome,structural_struts,evaluate_job,EvolutionV5,jump
from server import app

class V08Tests(unittest.TestCase):
 def test_topology_space(self):
  self.assertTrue(all(len(KINDS[f])>=10 for f in FAMILIES))
  self.assertTrue(all(len(new_genome(f,random.Random(5)))>=20 for f in FAMILIES))
 def test_procedural_endpoints_and_no_nans(self):
  for f in FAMILIES:
   p=new_genome(f,random.Random(11));p['topology']='wild';p['branch_factor']=2
   for pts,r,label in structural_struts(f,p):
    self.assertTrue((abs(pts[0,2]-.8)<.01))
    self.assertAlmostEqual(pts[-1,2],p['height'])
    self.assertGreater(r,.1)
 def test_deterministic_jobs(self):
  f='chiral';p=new_genome(f,random.Random(55));p['topology']='wild'
  job=(f,p,'balanced',True,3)
  self.assertEqual(evaluate_job(job),evaluate_job(job))
 def test_ui_api_cores(self):
  t=TestClient(app)
  r=t.get('/api/system')
  self.assertEqual(r.status_code,200)
  self.assertGreaterEqual(r.json()['logical_cores'],1)
  self.assertEqual(t.post('/api/start',json={'cores':999999}).status_code,422)
 def test_invalid_worker_count(self):
  with tempfile.TemporaryDirectory() as d:
   e=EvolutionV5(d)
   with self.assertRaises(ValueError):e.start(cores=0)
   with self.assertRaises(ValueError):e.start(cores=(os.cpu_count() or 1)+1)
if __name__=='__main__':unittest.main()
