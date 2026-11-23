"""Physics-level tests not dependent on the previous surrogate."""
import random
import unittest
import numpy as np
from advanced import new_genome
from physical_fem import FEMConfig, InvalidGeometry, SolidMesh, HexElasticSolver, voxel_mesh, fem_sweep, _serialize_mesh_fields, CORNERS

class PhysicalFemTests(unittest.TestCase):
    def box_mesh(self, nx=4,ny=4,nz=10,p=.5):
        cells=np.stack(np.meshgrid(np.arange(nx),np.arange(ny),np.arange(nz),indexing='ij'),-1).reshape(-1,3)
        nodes,inv=np.unique((cells[:,None,:]+CORNERS[None,:,:]).reshape(-1,3),axis=0,return_inverse=True)
        nodes=nodes.astype(float)*p
        return SolidMesh(nodes,inv.reshape(-1,8),np.zeros((0,3),int),
            np.where(nodes[:,2]==0)[0],np.where(nodes[:,2]==nz*p)[0],len(cells),len(cells)*p**3,p,.5,0,'analytical box')
    def test_axial_bar_and_reactions(self):
        m=self.box_mesh(nx=4,ny=4,nz=12,p=.5)
        s=HexElasticSolver(m,young_MPa=3.,poisson=.3)
        # A 2x2 mm^2 bar, 6 mm long, Fz=-0.1 N, ideal delta 0.05 mm.
        r=s.solve(force=(0,0,-.1),patch_radius_mm=4)
        expected=.1*6/(3*4)
        self.assertLess(abs(r['mean_down_mm']-expected)/expected,.12)
        self.assertLess(r['force_equilibrium_relative'],1e-7)
        self.assertLess(r['moment_equilibrium_relative'],1e-7)
        self.assertGreater(r['max_von_mises_MPa'],0)
        self.assertGreater(r['energy_Nmm'],0)
    def test_families_react_to_pressure(self):
        for f in ('crown','chiral','quadrant'):
            g=new_genome(f,random.Random(41))
            r=fem_sweep(f,g,1.25)
            self.assertGreater(r['load_cases']['press_center']['mean_down_mm'],0)
            self.assertLess(r['force_equilibrium_max'],1e-7)
            self.assertLess(r['moment_equilibrium_max'],1e-7)
            self.assertEqual(len(r['load_cases']),8)
    def test_offcenter_produces_different_moment_and_displacement(self):
        g=new_genome('crown',random.Random(41));m=voxel_mesh('crown',g,FEMConfig(pitch_mm=1.25))
        fem=HexElasticSolver(m,young_MPa=g['material_E']);center=fem.solve();offset=fem.solve(offset=(1.4,0.))
        self.assertGreater(np.linalg.norm(np.asarray(offset['moment_reaction_Nmm'])-center['moment_reaction_Nmm']),.02)
        self.assertLess(offset['moment_equilibrium_relative'],1e-6)
    def test_deterministic_surface_matches_fe_displacements(self):
        g=new_genome('quadrant',random.Random(41));m=voxel_mesh('quadrant',g,FEMConfig(pitch_mm=1.25))
        fem=HexElasticSolver(m,young_MPa=g['material_E']);r=fem.solve();v=_serialize_mesh_fields(m,r)
        self.assertTrue(np.allclose(np.asarray(v['displacement_mm']),np.round(r['displacement'][np.unique(m.surface_faces)],7)))
        self.assertEqual(len(v['faces'])*3,len(m.surface_faces)*3)
    def test_invalid_unsupported_topology(self):
        g=new_genome('crown',random.Random(3));g['height']=25
        with self.assertRaises(InvalidGeometry):voxel_mesh('crown',g)

if __name__=='__main__':unittest.main()
