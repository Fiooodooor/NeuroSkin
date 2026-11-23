import random
import unittest
from unittest.mock import patch
from advanced import new_genome
from physical_fem import FEMConfig, HexElasticSolver, voxel_mesh
from hardware_profile import _parse_gpu_line, profile


class TestHardwareProfile(unittest.TestCase):
    def test_parse_gpu(self):
        x=_parse_gpu_line('NVIDIA Quadro P1000, 4096 MiB, 3456, 538.0, 6.1')
        self.assertEqual(x['total_vram_mb'],4096)
        self.assertEqual(x['free_vram_mb'],3456)
        self.assertEqual(x['compute_capability'],'6.1')

    def test_cpu_only_profile(self):
        with patch('hardware_profile.discover_gpu',return_value={'available':False,'reason':'missing'}):
            p=profile()
        self.assertEqual(p['recommended']['default_fem_device'],'cpu')
        self.assertGreaterEqual(p['recommended']['evolution_cores'],1)
        self.assertTrue(p['recommended']['gpu_is_opt_in'])

    def test_cpu_solver_not_changed(self):
        g=new_genome('quadrant',random.Random(17))
        m=voxel_mesh('quadrant',g,FEMConfig(pitch_mm=1.25))
        solver=HexElasticSolver(m,g['material_E'])
        r=solver.solve(force=(0,0,-0.1))
        self.assertEqual(r['compute_device'],'cpu')
        self.assertGreater(r['mean_down_mm'],0)
        self.assertLess(r['force_equilibrium_relative'],1e-4)

    def test_gpu_rejects_excessive_elements_before_importing_cupy(self):
        g=new_genome('quadrant',random.Random(17))
        m=voxel_mesh('quadrant',g,FEMConfig(pitch_mm=1.25))
        with self.assertRaisesRegex(ValueError,'GPU CUDA CSR path'):
            HexElasticSolver(m,g['material_E'],compute_device='gpu',matrixfree_threshold=1)

    def test_bad_device_value(self):
        g=new_genome('quadrant',random.Random(17))
        m=voxel_mesh('quadrant',g,FEMConfig(pitch_mm=1.25))
        with self.assertRaisesRegex(ValueError,'compute_device'):
            HexElasticSolver(m,g['material_E'],compute_device='bad')

if __name__=='__main__':unittest.main()
