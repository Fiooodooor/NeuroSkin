"""Regression tests for symmetric PVDF geometry and multi-channel readout."""
import copy
import math
import random
import unittest
import numpy as np
from fastapi.testclient import TestClient
from advanced import new_genome, structural_struts, detail_mesh, jump, transmute
from pvdf_array import film_count, choose_film_members, layout_metrics
from piezoelectric import response, screen
from electromechanics import raw_mechanics
from server import app, EVO


class PVDFArrayTests(unittest.TestCase):
 def test_default_is_supported_multifilm_configuration(self):
  for family in ('crown','chiral','quadrant'):
   for seed in range(20):
    p=new_genome(family,random.Random(seed))
    self.assertIn(p['piezo_count'],(2,3,4) if family=='quadrant' else (2,3,4,6,8))
    self.assertEqual(len(choose_film_members(structural_struts(family,p),p)),p['piezo_count'])

 def test_four_is_angularly_balanced_for_three_families(self):
  for family in ('crown','chiral','quadrant'):
   p=new_genome(family,random.Random(123))
   p['piezo_count']=4
   # Force a symmetric number of primary legs as the new generator does.
   if family!='quadrant':p['ribs']=8
   layout=layout_metrics(structural_struts(family,p),p)
   self.assertLess(layout['normalized_imbalance'],1e-6,(family,layout))

 def test_pair_has_opposed_legs(self):
  p=new_genome('quadrant',random.Random(8));p['piezo_count']=2
  paths=structural_struts('quadrant',p)
  selected=choose_film_members(paths,p)
  v=np.asarray([paths[i][0][0,:2] for i in selected])
  self.assertLess(float(np.linalg.norm(v.mean(axis=0))),1e-6)

 def test_mutation_and_transmutation_retain_valid_count(self):
  for f in ('crown','chiral','quadrant'):
   p=new_genome(f,random.Random(11));rng=random.Random(12)
   for _ in range(35):
    p=jump(f,p,rng,'wide')
    self.assertIn(p['piezo_count'],(1,2,3,4) if f=='quadrant' else (1,2,3,4,6,8))
   q=transmute(f,p,'quadrant' if f!='quadrant' else 'crown',rng)
   self.assertIn(q['piezo_count'],(1,2,3,4,6,8))

 def test_legacy_one_film_unchanged(self):
  p=new_genome('quadrant',random.Random(9));p.pop('piezo_count')
  self.assertEqual(film_count(p),1)
  self.assertEqual(len(choose_film_members(structural_struts('quadrant',p),p)),1)
  r=response('quadrant',p,raw_mechanics('quadrant',p,'normal'))
  self.assertEqual(r['film_count'],1)
  self.assertTrue(r['layout']['legacy'])

 def test_mesh_has_all_films_and_is_watertight(self):
  for f in ('quadrant','crown','chiral'):
   p=new_genome(f,random.Random(7));p['piezo_count']=4
   film=detail_mesh(f,p)['piezo']
   self.assertTrue(film.is_watertight)
   self.assertTrue(np.isfinite(film.vertices).all())
   self.assertGreater(len(film.faces),100)

 def test_electrical_channels_match_geometry_and_idle_is_zero(self):
  for f in ('quadrant','crown','chiral'):
   p=new_genome(f,random.Random(7));p['piezo_count']=4;p['piezo_wiring']=0
   r=response(f,p,raw_mechanics(f,p,'normal'))
   self.assertEqual(r['film_count'],4)
   self.assertEqual(len(r['channels']),4)
   self.assertEqual(len({c['member_index'] for c in r['channels']}),4)
   z=response(f,p,raw_mechanics(f,p,'normal',force=[0,0,0]))
   self.assertAlmostEqual(z['peak_V'],0,places=8)

 def test_wiring_can_cancel_normal_and_preserve_lateral_component(self):
  p=new_genome('quadrant',random.Random(21));p['piezo_count']=4
  p['piezo_wiring']=0
  m=raw_mechanics('quadrant',p,'shear_x')
  independent=response('quadrant',p,m)
  p['piezo_wiring']=2
  differential=response('quadrant',p,m)
  self.assertEqual(differential['wiring'],'differential_x')
  self.assertEqual(len(differential['wiring_matrix'][0]),4)
  self.assertTrue(math.isfinite(differential['peak_V']))
  self.assertTrue(math.isfinite(independent['dynamic_snr_proxy']))

 def test_api_explicit_archive_safe_override(self):
  legacy=new_genome('quadrant',random.Random(23));legacy.pop('piezo_count')
  item={'id':'pvdf-legacy-v13','family':'quadrant','genome':legacy,'fitness':71.,'generation':7}
  with EVO.lock:
   old=EVO.state;EVO.state=EVO.empty();EVO.state['best']=item
  try:
   c=TestClient(app)
   orig=c.get('/api/mesh').json()
   self.assertEqual(orig['pvdf_layout']['film_count'],1)
   upgraded=c.get('/api/mesh',params={'piezo_count_override':4}).json()
   self.assertEqual(upgraded['pvdf_layout']['film_count'],4)
   self.assertTrue(upgraded['pvdf_preview_override'])
   analyzed=c.post('/api/characterize',json={'selection':'best','case':'normal','piezo_count_override':4}).json()
   self.assertEqual(analyzed['result']['piezoelectric']['film_count'],4)
   self.assertNotIn('piezo_count',legacy)
   derived=c.get('/api/export/genome',params={'piezo_count_override':4})
   self.assertEqual(derived.status_code,200)
   self.assertEqual(derived.json()['piezo_count'],4)
   self.assertEqual(derived.headers.get('x-neuroskin-fitness-invalidated'),'true')
   self.assertEqual(c.get('/api/mesh').json()['pvdf_layout']['film_count'],1)
   self.assertEqual(c.get('/api/mesh',params={'piezo_count_override':3}).status_code,200)
   self.assertEqual(c.get('/api/mesh',params={'piezo_count_override':7}).status_code,422)
  finally:
   with EVO.lock:EVO.state=old

if __name__=='__main__':unittest.main()
