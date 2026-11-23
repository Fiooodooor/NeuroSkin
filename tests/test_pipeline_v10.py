import unittest,random, tempfile, time
import numpy as np
from advanced import new_genome, structural_struts, detail_mesh, EvolutionV5
from full_evaluation import audit_candidate,promote
from geometry_fixes import pvdf_ribbon

class TestPipelineV10(unittest.TestCase):
 def test_pvdf_is_bent_strip_and_watertight_all_families(self):
  rng=random.Random(29)
  for family in ('crown','chiral','quadrant'):
   p=new_genome(family,rng);members=structural_struts(family,p)
   m=detail_mesh(family,p)['piezo']
   self.assertTrue(m.is_watertight)
   self.assertGreater(len(m.faces),40)
   self.assertTrue(np.isfinite(m.vertices).all())
   # A balanced array naturally spans several distant legs; each individual
   # film must be close to SOME selected load-bearing member.
   from pvdf_array import choose_film_members
   selected=choose_film_members(members,p)
   curves=np.concatenate([members[k][0] for k in selected],axis=0)
   dist=np.linalg.norm(m.vertices[:,None,:]-curves[None,:,:],axis=2).min(axis=1)
   self.assertLess(np.quantile(dist,.9),max(.6,max(members[k][1] for k in selected)*2.5))
 def test_patch_has_controlled_roll_and_bounded_width(self):
  path=np.array([[0.,0.,0.],[0.,0.,2.],[.3,0.,4.],[1.,0.,6.]])
  x=pvdf_ribbon(path,.6,.5,5.,4.,.03)
  self.assertTrue(x.is_watertight)
  self.assertLess(x.extents[1],1.1)
 def test_all_three_full_audit_same_protocol(self):
  rng=random.Random(52)
  for family in ('crown','chiral','quadrant'):
   a=audit_candidate(family,new_genome(family,rng),grid_size=3)
   self.assertEqual(len(a['pressure_spatial']),3)
   self.assertEqual(len(a['piezo_frequency_sweep']),3)
   self.assertEqual(a['force_reconstruction']['holdout_count'],30)
   self.assertEqual(a['force_reconstruction']['train_count'],70)
   self.assertIn('condition_whitened',a['observability'])
 def test_incumbent_only_replaced_after_full_audit(self):
  d=lambda s,ok: {'id':s,'audit':{'feasible':ok,'audit_score':float(s[1:])}}
  old=d('x85',True)
  champ,decision=promote(old,[d('x99',False),d('x80',True),d('x84',True)])
  self.assertEqual(champ['id'],'x85')
  self.assertFalse(decision['replaced'])
  champ,decision=promote(old,[d('x86',True),d('x99',False),d('x50',True)])
  self.assertEqual(champ['id'],'x86')
  self.assertTrue(decision['replaced'])
 def test_full_live_evolution_audits_three(self):
  with tempfile.TemporaryDirectory() as folder:
   e=EvolutionV5(folder)
   e.start('all',3,13,12,.5,cores=1,audit_grid=3)
   until=time.monotonic()+22
   while e.snapshot()['status'] not in ('completed','stopped','failed') and time.monotonic()<until:time.sleep(.12)
   s=e.snapshot()
   self.assertEqual(s['status'],'completed',s.get('error'))
   self.assertGreaterEqual(len(s['audit_history']),1)
   self.assertEqual(len(s['audit_top3']),3)
   self.assertIsNotNone(s['audited_champion'])
   self.assertIn('audit',s['best'])
   from archive_store import ArchiveStore
   store=ArchiveStore(folder)
   self.assertEqual(store.load(s['id'])['status'],'completed')
   steps=store.list_stages(s['id'])
   self.assertGreaterEqual(len(steps),1)
   stage=store.load_stage(s['id'],steps[-1]['generation'])
   self.assertEqual(len(stage['top3']),3)
   self.assertTrue(all('audit' in x for x in stage['top3']))

if __name__=='__main__':unittest.main()
