import sys,random,math,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from advanced import new_genome
from electromechanics import examine, sweep, CASES, raw_mechanics
from optimization import evaluate, PRESETS
from fastapi.testclient import TestClient
from server import app,EVO

class ElectromechanicalTests(unittest.TestCase):
 def setUp(self):
  self.gs={f:new_genome(f,random.Random(42)) for f in ('crown','chiral','quadrant')}
 def test_zero_load_electrical_baseline(self):
  for f,p in self.gs.items():
   r=examine(f,p,'normal',force=[0,0,0])
   e=r['electrical']
   self.assertAlmostEqual(sum(e['pressure_delta_pF']),0,places=5)
   self.assertAlmostEqual(e['hall_torsion_delta_mT'],0,places=5)
 def test_all_cases_finite(self):
  for f,p in self.gs.items():
   for case in CASES:
    r=examine(f,p,case)
    a=np.array(r['electrical']['pressure_delta_pF']+r['electrical']['lateral_delta_pF']+[r['electrical']['hall_torsion_delta_mT']])
    self.assertEqual(len(a),7)
    self.assertTrue(np.isfinite(a).all(),(f,case))
 def test_linear_mechanics_scaling(self):
  for f,p in self.gs.items():
   a=raw_mechanics(f,p,'normal',force=[0,0,-.1])
   b=raw_mechanics(f,p,'normal',force=[0,0,-.2])
   np.testing.assert_allclose(np.array(b['displacement_mm']),2*np.array(a['displacement_mm']),rtol=1e-6,atol=1e-8)
 def test_nonlinear_electrode_gap(self):
  for f,p in self.gs.items():
   rows=sweep(f,p,'normal',9)['rows'];self.assertEqual(len(rows),9)
   self.assertGreater(abs(rows[-1]['pressure_sum_pF']),abs(rows[0]['pressure_sum_pF']))
 def test_objective_presets(self):
  for f,p in self.gs.items():
   results=[evaluate(f,p,x) for x in PRESETS]
   for fit,met,_ in results:
    self.assertTrue(0<=fit<=100);self.assertAlmostEqual(sum(met['fitness_weights'].values()),1)
    self.assertEqual(met['fitness'],round(fit,4))
   self.assertTrue(len(set(round(x[0],6) for x in results))>1)
 def test_invalid_preset(self):
  with self.assertRaises(ValueError):evaluate('crown',self.gs['crown'],'does-not-exist')
 def test_api_catalog(self):
  c=TestClient(app);r=c.get('/api/physics_info');self.assertEqual(r.status_code,200)
  self.assertEqual(len(r.json()['cases']),8)
 def test_api_load_case_selected_candidate(self):
  from advanced import EvolutionV5
  # manually provide a cached champion without running optimizer
  item=dict(id='test-1',family='quadrant',genome=self.gs['quadrant'],fitness=60.,generation=1)
  with EVO.lock:
   previous=EVO.state
   EVO.state=EVO.empty();EVO.state['best']=item
  try:
   c=TestClient(app);r=c.post('/api/characterize',json={'selection':'best','case':'stretch_x','fraction':1.0})
   self.assertEqual(r.status_code,200,r.text)
   self.assertAlmostEqual(r.json()['result']['mechanics']['substrate_strain'],.05)
   self.assertEqual(len(r.json()['sweep']['rows']),17)
  finally:
   with EVO.lock:EVO.state=previous

if __name__=='__main__':unittest.main()
