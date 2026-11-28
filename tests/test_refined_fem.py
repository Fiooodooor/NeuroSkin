"""Regression and physical sanity checks for fine space-frame FEM and contact recovery."""
import math
import random
import unittest
import numpy as np
from advanced import new_genome, structural_struts, continuous_tube
from beam_fem import BeamFEM, local_beam_stiffness, beam_sweep
from physical_fem import FEMConfig, HexElasticSolver, voxel_mesh, fem_sweep


class FineFemTests(unittest.TestCase):
    def test_3d_cantilever_hermite_compliance(self):
        E=2.;L=6.;r=.35
        A=math.pi*r*r;I=math.pi*r**4/4
        k=local_beam_stiffness(E,E/(2*1.35),A,I,I,2*I,L)
        F=.05
        u=np.linalg.solve(k[6:,6:],np.array([0,F,0,0,0,0],float))
        exact=F*L**3/(3*E*I)
        self.assertAlmostEqual(u[1],exact,places=8)
        self.assertAlmostEqual(u[5],F*L**2/(2*E*I),places=8)

    def test_fine_pitch_8x_is_real_beam(self):
        for fam in ('crown','chiral','quadrant'):
            g=new_genome(fam,random.Random(123))
            coarse=fem_sweep(fam,g,pitch_mm=.3125)
            fine=fem_sweep(fam,g,pitch_mm=.15625)
            self.assertEqual(fine['fem_backend'],'actual_3d_beam_frame_EB')
            self.assertGreater(fine['elements'],coarse['elements']*1.85)
            self.assertLess(fine['force_equilibrium_max'],1e-6)
            self.assertLess(fine['moment_equilibrium_max'],1e-6)
            self.assertEqual(fine['inflated_features'],0)

    def test_archived_old_candidate_has_contact_fallback(self):
        g=new_genome('crown',random.Random(41))
        m=voxel_mesh('crown',g,FEMConfig(pitch_mm=1.25))
        solver=HexElasticSolver(m,g['material_E'])
        # Deliberately undersized patch with no nodes at the exact center.
        r=solver.solve(force=(0,0,-.1),patch_radius_mm=.001,offset=(1.8,-1.8))
        self.assertGreaterEqual(r['loaded_nodes'],4)
        self.assertNotEqual(r['contact_patch_mode'],'requested')
        self.assertLess(r['force_equilibrium_relative'],1e-6)

    def test_smooth_surface_is_watertight(self):
        for fam in ('crown','chiral','quadrant'):
            g=new_genome(fam,random.Random(3))
            points,r,tag=structural_struts(fam,g)[0]
            mesh=continuous_tube(points,r,g,tag,sections=12)
            self.assertTrue(mesh.is_watertight)
            self.assertEqual(len(mesh.faces),2*(len(points)-1)*12 + 2*12)

    def test_beam_results_3d_view_shape(self):
        g=new_genome('quadrant',random.Random(42))
        solver=BeamFEM('quadrant',g,pitch_mm=.15625)
        result=solver.solve(force=(0,0,-.02),include_fields=True)
        f=result['fields']
        self.assertEqual(len(f['vertices_mm']),len(f['displacement_mm']))
        self.assertEqual(len(f['vertices_mm']),len(f['principal_strain']))
        self.assertGreater(len(f['faces']),100)
        self.assertLess(result['force_equilibrium_relative'],1e-6)
        self.assertTrue(np.isfinite(result['max_von_mises_MPa']))

    def test_thin_unphysical_candidates_are_rejected(self):
        g=new_genome('quadrant',random.Random(42))
        g['thickness']=.26
        result=beam_sweep('quadrant',g,pitch_mm=.3125)
        if result['max_motion_over_height']>=.15 or result['max_abs_principal_strain']>=.08:
            self.assertFalse(result['feasible_linear'])
            self.assertLessEqual(result['fem_score'],14.99)


if __name__=='__main__':unittest.main()
