"""v1.3: high-resolution FEM and geometry consistency regression tests."""
import os,random,unittest
import numpy as np
from advanced import new_genome, structural_struts, tapered_tube, _profile_radius
from physical_fem import FEMConfig,HexElasticSolver,InvalidGeometry,voxel_mesh

class HighResTests(unittest.TestCase):
 def setUp(self):
  self.g=new_genome('quadrant',random.Random(42))
 def test_8x_pitch_is_accepted_and_budgeted(self):
  self.assertAlmostEqual(FEMConfig(pitch_mm=.15625).pitch_mm,.15625)
  with self.assertRaises(ValueError):FEMConfig(pitch_mm=.05)
  with self.assertRaises(InvalidGeometry):
   voxel_mesh('quadrant',self.g,FEMConfig(pitch_mm=.3125,max_cells=100),build_surface=False)
 def test_swept_beams_are_closed_and_tapered(self):
  for family in ('crown','chiral','quadrant'):
   g=new_genome(family,random.Random(41))
   path,r,tag=structural_struts(family,g)[0]
   tube=tapered_tube(path,r,g,tag)
   self.assertTrue(tube.is_watertight,family)
   self.assertGreater(len(tube.faces),400)
   self.assertGreater(_profile_radius(r,0.0,g,tag),_profile_radius(r,.5,g,tag))
 def test_adaptive_contact_does_not_fail_at_missing_nodes(self):
  m=voxel_mesh('quadrant',self.g,FEMConfig(pitch_mm=1.25),build_surface=False)
  s=HexElasticSolver(m,self.g['material_E'])
  result=s.solve(force=(0,0,-.1),offset=(1.6,1.6),patch_radius_mm=.01)
  self.assertGreaterEqual(result['loaded_nodes'],4)
  self.assertNotEqual(result['contact_patch_mode'],'requested')
  self.assertLess(result['moment_equilibrium_relative'],1e-5)
 def test_finer_voxel_mesh_and_equilibrium(self):
  m0=voxel_mesh('quadrant',self.g,FEMConfig(pitch_mm=1.25),build_surface=False)
  m1=voxel_mesh('quadrant',self.g,FEMConfig(pitch_mm=.3125),build_surface=False)
  self.assertGreater(m1.voxels,m0.voxels*4)
  s=HexElasticSolver(m1,self.g['material_E'])
  result=s.solve(force=(0,0,-.1))
  self.assertGreater(result['mean_down_mm'],0)
  self.assertLess(result['force_equilibrium_relative'],1e-5)
 def test_matrix_free_matches_assembled_on_same_mesh(self):
  m=voxel_mesh('quadrant',self.g,FEMConfig(pitch_mm=1.25),build_surface=False)
  direct=HexElasticSolver(m,self.g['material_E'],matrixfree_threshold=10000).solve(force=(0,0,-.1))
  iterative=HexElasticSolver(m,self.g['material_E'],matrixfree_threshold=1,cg_maxiter=1000,cg_rtol=1e-6).solve(force=(0,0,-.1))
  self.assertEqual(iterative['solver_mode'],'matrix_free_cg')
  self.assertLess(abs(direct['mean_down_mm']-iterative['mean_down_mm'])/direct['mean_down_mm'],.002)
  self.assertLess(iterative['force_equilibrium_relative'],1e-4)
 @unittest.skipUnless(os.getenv('NEUROSKIN_SLOW_TESTS')=='1','Set NEUROSKIN_SLOW_TESTS=1 to test an actual 8x solve')
 def test_actual_8x_resolution(self):
  m=voxel_mesh('quadrant',self.g,FEMConfig(pitch_mm=.15625),build_surface=False)
  s=HexElasticSolver(m,self.g['material_E'],cg_maxiter=5000,cg_timeout_s=180)
  result=s.solve(force=(0,0,-.1))
  self.assertEqual(s.solver_mode,'matrix_free_cg')
  self.assertGreater(result['mean_down_mm'],0)
  self.assertLess(result['force_equilibrium_relative'],1e-4)

if __name__=='__main__':unittest.main()
