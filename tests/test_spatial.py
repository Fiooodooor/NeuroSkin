import random, sys, unittest, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from advanced import new_genome, EvolutionV5
from spatial_validation import spatial_pressure_test, grid_points
from optimization import evaluate
from server import app,EVO

class SpatialTests(unittest.TestCase):
 def setUp(self):
  self.genomes={fam:new_genome(fam,random.Random(42)) for fam in ('crown','chiral','quadrant')}
 def test_grid_inside_real_pad(self):
  for n in (3,5,7):
   pts=grid_points(3.,n)
   self.assertTrue(any(abs(x)<1e-10 and abs(y)<1e-10 for x,y in pts))
   self.assertTrue(all(x*x+y*y <=9+1e-9 for x,y in pts))
   self.assertLess(len(pts),n*n)
 def test_vertical_load_generates_signal_all_families(self):
  for family,g in self.genomes.items():
   r=spatial_pressure_test(family,g,grid_size=5)
   self.assertEqual(r['total_points'],len(r['points']))
   self.assertTrue(any(p['signal_norm_pF']>0 for p in r['points']))
   # Off-centre loads may legitimately cause local lift/rocking in this simplified model.
   self.assertGreater(next(p['vertical_deflection_mm'] for p in r['points'] if p['x_mm']==0 and p['y_mm']==0),0)
   self.assertTrue(0<=r['coverage_fraction']<=1)
 def test_positive_force_and_gate(self):
  for family,g in self.genomes.items():
   no_gate=evaluate(family,g,'balanced')[0]
   with_gate,metrics,_=evaluate(family,g,'balanced',True,3)
   self.assertIn(metrics['spatial_gate']['status'],('PASS','FAIL'))
   self.assertTrue(metrics['physical_plausibility_gate_enabled'])
   self.assertEqual(metrics['fitness'],round(with_gate,4))
   if metrics['spatial_gate']['status']=='FAIL':self.assertLess(with_gate,15.)
   else:self.assertAlmostEqual(with_gate,15+.85*no_gate)
 def test_invalid_grid_and_load(self):
  with self.assertRaises(ValueError):grid_points(2,4)
  with self.assertRaises(ValueError):spatial_pressure_test('crown',self.genomes['crown'],force_n=0)
 def test_no_spurious_tensile_flag_center(self):
  # A symmetric reference has no central lift. A RANDOM asymmetric wild
  # structure may legitimately produce tensile leg reactions at center.
  g=dict(self.genomes['quadrant'],topology='orthogonal',asymmetry=0.,
         pad_offset_x=0.,pad_offset_y=0.,strut_gradient=0.,wave_amp=0.)
  r=spatial_pressure_test('quadrant',g,grid_size=3)
  center=next(p for p in r['points'] if p['x_mm']==0 and p['y_mm']==0)
  self.assertLess(center['negative_reaction_fraction'],.01)
 def test_api_spatial_selection(self):
  item={'id':'spatial-test','family':'crown','genome':self.genomes['crown'],'fitness':10,'generation':1}
  with EVO.lock:
   previous=EVO.state; EVO.state=EVO.empty();EVO.state['best']=item
  try:
   c=TestClient(app);r=c.post('/api/spatial_pressure',json={'selection':'best','grid_size':7,'force_n':.1})
   self.assertEqual(r.status_code,200,r.text)
   self.assertEqual(r.json()['candidate_id'],'spatial-test')
   self.assertGreater(len(r.json()['spatial']['points']),10)
   self.assertEqual(c.post('/api/spatial_pressure',json={'selection':'best','grid_size':4}).status_code,422)
  finally:
   with EVO.lock:EVO.state=previous
 def test_live_evolution_optional_gate(self):
  import tempfile
  for enabled in (False,True):
   with tempfile.TemporaryDirectory() as tmp:
    e=EvolutionV5(tmp);e.start('crown',3,123,12,.5,'balanced',enabled,3)
    e.thread.join(timeout=35)
    s=e.snapshot();self.assertEqual(s['status'],'completed',s.get('error'))
    self.assertEqual(s['physical_gate'],enabled)
    self.assertGreater(s['evaluated'],0)
    self.assertIsNotNone(s['best'])
    if enabled:self.assertIn('spatial_gate',s['best']['metrics'])

if __name__=='__main__':unittest.main()
