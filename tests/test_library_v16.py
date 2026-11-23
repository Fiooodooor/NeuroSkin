"""v1.6: research-seed morphology, engineering prior rubric, SLS unloading,
expanded PVDF hardware arrangements, and unified API regressions."""
import random
import unittest
import numpy as np
from fastapi.testclient import TestClient
from seed_library import SEEDS,top_candidates,seed_genome,serialized_library
from advanced import KINDS,structural_struts,detail_mesh
from physical_fem import voxel_mesh,HexElasticSolver,FEMConfig
from pvdf_array import choose_film_members
from piezoelectric import response
from electromechanics import raw_mechanics
from recovery_sim import recovery_curve
from server import app

class LibraryV16Tests(unittest.TestCase):
 def test_twenty_origins_10criteria_10shortlist(self):
  self.assertEqual(len(SEEDS),20)
  self.assertEqual(sum(x.category=='hypothesis' for x in SEEDS),10)
  self.assertEqual(sum(x.category=='literature' for x in SEEDS),10)
  self.assertEqual(len(top_candidates()),10)
  self.assertTrue(all(0<=sum(x.scores)<=100 and len(x.scores)==10 for x in SEEDS))
  lib=serialized_library()
  self.assertEqual(len(lib['categories']),10)
  self.assertEqual(sum(x['selected'] for x in lib['seeds']),10)
  self.assertTrue(all(x.source_url for x in SEEDS if x.category=='literature'))
 def test_twenty_generate_connected_struts_and_solid_solve(self):
  for spec in SEEDS:
   with self.subTest(seed=spec.id):
    g=seed_genome(spec,random.Random(123),mutate=False)
    self.assertIn(g['topology'],KINDS[spec.family])
    paths=structural_struts(spec.family,g)
    self.assertGreaterEqual(len(paths),4)
    self.assertTrue(all(np.isfinite(p).all() for p,_,_ in paths))
    self.assertTrue(all((p[-1,2]-p[0,2])>.4 for p,_,t in paths if t=='leg'))
    mesh=voxel_mesh(spec.family,g,FEMConfig(pitch_mm=1.25))
    res=HexElasticSolver(mesh,g['material_E']).solve(force=(0,0,-.1))
    self.assertGreater(res['mean_down_mm'],0)
    self.assertLess(res['force_equilibrium_relative'],1e-3)
 def test_pvdf_1_to_8_wiring(self):
  spec=next(s for s in SEEDS if s.family=='crown')
  g=seed_genome(spec,random.Random(42),mutate=False);g['ribs']=8
  m=raw_mechanics('crown',g,'normal')
  for count in (1,2,3,4,6,8):
   g['piezo_count']=count
   self.assertEqual(len(choose_film_members(structural_struts('crown',g),g)),count)
   for wiring in (0,1,2,3,4):
    g['piezo_wiring']=wiring
    r=response('crown',g,m)
    self.assertEqual(r['film_count'],count)
    self.assertTrue(np.isfinite(r['peak_V']))
 def test_recovery_time_and_strain_screen(self):
  a=recovery_curve(.12,.02)
  self.assertGreater(a['residual_mm_after_release'][0],a['residual_mm_after_release'][6])
  self.assertTrue(a['recovery_5s_passed_assumed'])
  b=recovery_curve(.12,.3)
  self.assertFalse(b['recovery_5s_passed_assumed'])
 def test_api_library_seed_unified_evaluation(self):
  c=TestClient(app)
  self.assertEqual(len(c.get('/api/seed_library').json()['seeds']),20)
  seed=c.get('/api/seeds/s_mirror_flex')
  self.assertEqual(seed.status_code,200)
  r=c.post('/api/evaluate_all',json={'selection':'seed','index':'s_mirror_flex','family':'quadrant','audit_grid':3,'fem_enabled':False,'piezo_wiring_override':3})
  self.assertEqual(r.status_code,200,r.text[:250])
  self.assertIn('unloading_recovery',r.json()['audit'])
  
  electrical=c.post('/api/characterize',json={'selection':'seed','index':'s_mirror_flex','case':'normal','piezo_wiring_override':3})
  self.assertEqual(electrical.status_code,200)
  self.assertEqual(electrical.json()['result']['piezoelectric']['wiring'],'differential_y')
 def test_api_randomizes_seed_by_default(self):
  from server import Start
  self.assertIsNone(Start().seed)

if __name__=='__main__':unittest.main()
