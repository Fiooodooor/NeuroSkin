import unittest, random, time, tempfile
import numpy as np
from advanced import FAMILIES, new_genome, jump, cross, transmute, proxy, KINDS, webmesh, EvolutionV5

class TestAdvanced(unittest.TestCase):
 def test_family_random_candidates(self):
  r=random.Random(41)
  for f in FAMILIES:
   a=new_genome(f,r)
   self.assertIn(a['topology'],KINDS[f])
   self.assertTrue(np.isfinite(proxy(f,a)[0]))
 def test_mutation_and_switches(self):
  r=random.Random(5)
  for f in FAMILIES:
   a=new_genome(f,r)
   b=jump(f,a,r,'topology')
   self.assertNotEqual(a['topology'],b['topology'])
   c=jump(f,a,r,'wide')
   self.assertTrue(np.isfinite(proxy(f,c)[0]))
   d=cross(f,a,c,r)
   self.assertTrue(np.isfinite(proxy(f,d)[0]))
 def test_transmutation(self):
  r=random.Random(5);a=new_genome('crown',r)
  for f in ('quadrant','chiral'):
   b=transmute('crown',a,f,r)
   self.assertEqual(set(b.keys()),set(new_genome(f,r).keys()))
   self.assertTrue(np.isfinite(proxy(f,b)[0]))
 def test_mesh_has_components(self):
  r=random.Random(3)
  for f in FAMILIES:
   model=webmesh(f,new_genome(f,r),6)
   self.assertGreaterEqual(len(model['components']),3)
   for comp in model['components']:
    self.assertGreater(len(comp['faces']),0)
    self.assertLess(max(max(q) for q in comp['faces']),len(comp['vertices']))
 def test_time_evolution_and_pin(self):
  with tempfile.TemporaryDirectory() as d:
   e=EvolutionV5(d);e.start('all',3,10,24,.95,audit_grid=3)
   end=time.monotonic()+35
   while e.snapshot()['status'] not in ('completed','stopped','failed') and time.monotonic()<end:time.sleep(.12)
   if e.snapshot()['status'] not in ('completed','stopped','failed'):
    e.stop()
   if e.thread: e.thread.join(timeout=25)
   s=e.snapshot()
   self.assertEqual(s['status'],'completed',s.get('error'))
   self.assertGreaterEqual(s['evaluated'],24)
   self.assertGreaterEqual(s['generation'],1)  # Time budget measures progress, not hardware-specific throughput
   self.assertGreaterEqual(len(s['champions']),3)
   self.assertGreaterEqual(s['diversity'],3)
   c=s['gallery'][0];self.assertIsNotNone(e.lookup('id',c['id']))
   self.assertIn('topology',s['mutations'])
 def test_pause_does_not_use_budget(self):
  with tempfile.TemporaryDirectory() as d:
   e=EvolutionV5(d);e.start('crown',3,11,24,.5);time.sleep(.3);e.pause()
   before=e.snapshot()['elapsed'];time.sleep(.35);after=e.snapshot()['elapsed']
   self.assertLess(abs(after-before),.2)
   e.pause();e.stop();e.thread.join(timeout=35)

if __name__=='__main__':unittest.main()
