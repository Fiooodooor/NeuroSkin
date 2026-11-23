import sys,unittest,random,math,subprocess,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from advanced import new_genome,jump,transmute,webmesh
from piezoelectric import response,screen
from electromechanics import raw_mechanics,examine
from optimization import evaluate
from fastapi.testclient import TestClient
from server import app,EVO

class PiezoTests(unittest.TestCase):
 def setUp(self):self.g=new_genome('chiral',random.Random(43))
 def test_idle_is_zero(self):
  mech=raw_mechanics('chiral',self.g,'normal',force=[0,0,0]);p=response('chiral',self.g,mech)
  self.assertAlmostEqual(p['charge_pC'],0,places=8)
  self.assertAlmostEqual(p['peak_V'],0,places=8)
 def test_frequency_cutoff(self):
  mech=raw_mechanics('chiral',self.g,'shear_x')
  low=response('chiral',self.g,mech,.01);high=response('chiral',self.g,mech,300.)
  self.assertLessEqual(low['peak_V'],high['peak_V']+1e-12)
 def test_hold_leakage(self):
  p=response('chiral',self.g,raw_mechanics('chiral',self.g,'shear_x'))
  self.assertLessEqual(abs(p['step_hold_V'][-1]),abs(p['step_hold_V'][0])+.00001)
 def test_genotype_affects_fitness(self):
  p=dict(self.g);a=evaluate('chiral',p,'dynamic')[0]
  p['piezo_strain_transfer']*=.2;p['piezo_feedback_pf']*=2
  b=evaluate('chiral',p,'dynamic')[0]
  self.assertNotAlmostEqual(a,b,places=4)
 def test_piezo_mode_in_range_after_mutation(self):
  r=random.Random(1)
  for _ in range(40):
   p=jump('chiral',self.g,r,'wide')
   self.assertIn(p['piezo_mode'],(0,1))
 def test_all_families_all_cases_finite(self):
  for f in ('crown','chiral','quadrant'):
   p=new_genome(f,random.Random(22))
   for mode in ('normal','shear_x','shear_y','torsion','bend_x','stretch_x','compression','offcenter'):
    d=examine(f,p,mode)['piezoelectric']
    self.assertTrue(math.isfinite(d['charge_pC']),(f,mode))
    self.assertTrue(math.isfinite(d['peak_V']),(f,mode))
 def test_api_piezo(self):
  item={'id':'piezo-test','family':'chiral','genome':self.g,'fitness':50.,'generation':1}
  with EVO.lock:
   old=EVO.state;EVO.state=EVO.empty();EVO.state['best']=item
  try:
   c=TestClient(app)
   j=c.post('/api/characterize',json={'selection':'best','case':'shear_x'}).json()
   self.assertEqual(len(j['result']['piezoelectric']['waveform_V']),80)
   self.assertIn('piezo_peak_V',j['sweep']['rows'][-1])
   m=c.get('/api/mesh').json()
   self.assertGreater(len(m['strut_paths']),0)
   self.assertIn('piezo',[z['part'] for z in m['model']['components']])
  finally:
   with EVO.lock:EVO.state=old
if __name__=='__main__':unittest.main()
