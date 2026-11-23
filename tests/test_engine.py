import sys,time,unittest,random,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from engine import FAMILIES,LIMITS,random_genome,mutate,metrics,stiffness_and_legs,solve_force,mesh_for,Evolution

class EngineTests(unittest.TestCase):
 def test_family_fitness_deterministic(self):
  for f in FAMILIES:
   g=random_genome(f,random.Random(42))
   self.assertEqual(metrics(f,g),metrics(f,g));self.assertTrue(np.isfinite(metrics(f,g)['fitness']))
 def test_mutation_in_bounds(self):
  rng=random.Random(8)
  for f in FAMILIES:
   g=random_genome(f,rng)
   for _ in range(20):
    g=mutate(f,g,rng)
    for k,(a,b) in LIMITS[f].items():self.assertGreaterEqual(g[k],a);self.assertLessEqual(g[k],b)
 def test_stiffness_symmetric_positive(self):
  for f in FAMILIES:
   g=random_genome(f,random.Random(13));K,_=stiffness_and_legs(f,g)
   self.assertTrue(np.allclose(K,K.T));self.assertGreater(np.linalg.eigvalsh(K).min(),0)
 def test_linear_load_scaling(self):
  for f in FAMILIES:
   g=random_genome(f,random.Random(9));K,_=stiffness_and_legs(f,g)
   self.assertTrue(np.allclose(2*solve_force(K,[0,0,-.05]),solve_force(K,[0,0,-.1])))
 def test_offcenter_moment(self):
  g=random_genome('quadrant',random.Random(4));K,_=stiffness_and_legs('quadrant',g)
  self.assertFalse(np.allclose(solve_force(K,[0,0,-.1],[0,0]),solve_force(K,[0,0,-.1],[3,0])))
 def test_mesh_export(self):
  for f in FAMILIES:
   m=mesh_for(f,random_genome(f,random.Random(5)))
   self.assertGreater(len(m.vertices),50)
   self.assertGreater(len(m.faces),80)
   self.assertLess(m.extents[0],30)
 def test_evolution_duration_and_save(self):
  with tempfile.TemporaryDirectory() as td:
   e=Evolution(td);e.start('crown',3,42,8)
   t=time.monotonic()
   while e.snapshot()['status'] in ('running','saving') and time.monotonic()-t<12:time.sleep(.05)
   s=e.snapshot();self.assertEqual(s['status'],'completed');self.assertGreater(s['generation'],1)
   self.assertTrue((Path(td)/s['id']/'results.json').is_file())
   self.assertTrue((Path(td)/s['id']/'champion.stl').is_file())
 def test_pause_resume(self):
  with tempfile.TemporaryDirectory() as td:
   e=Evolution(td);e.start('quadrant',3,7,8);time.sleep(.12)
   e.pause();time.sleep(.2);a=e.snapshot()['elapsed'];time.sleep(.25)
   self.assertAlmostEqual(e.snapshot()['elapsed'],a,places=3)
   e.pause();e.stop();time.sleep(.15)
   self.assertIn(e.snapshot()['status'],('running','stopped'))
if __name__=='__main__':unittest.main()
