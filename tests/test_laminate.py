"""Regression for PVDF/adhesive stiffness and single-action GUI integration.

Low-resolution acceptance tests only. Does not assert physically calibrated moduli,
nonlinear behavior, or a convergence-certified FEM solution.
"""
import random
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from fastapi.testclient import TestClient

from advanced import new_genome, proxy, jump, cross, audit_job
from beam_fem import BeamFEM, beam_sweep
from physical_fem import FEMConfig, HexElasticSolver, voxel_mesh


class LaminateMechanics(unittest.TestCase):
    def g(self, family='quadrant', seed=33):
        return new_genome(family, random.Random(seed))

    def test_positive_semidefinite_films_and_improved_compliance(self):
        for family in ('crown','chiral','quadrant'):
            with self.subTest(family=family):
                g = self.g(family)
                mesh = voxel_mesh(family, g, FEMConfig(pitch_mm=1.25))
                bare = HexElasticSolver(mesh, young_MPa=g['material_E'], include_laminate=False)
                bond = HexElasticSolver(mesh, young_MPa=g['material_E'], family=family, genome=g)
                x = np.random.default_rng(42).standard_normal(3*len(mesh.nodes))
                self.assertGreaterEqual(float(x@(bond.laminate.stiffness@x)), -1e-10)
                r0 = bare.solve(force=(0.,0.,-.1))
                r1 = bond.solve(force=(0.,0.,-.1))
                self.assertTrue(r1['pvdf_stiffness_included'])
                self.assertGreater(r1['laminate_energy_Nmm'], 0.)
                self.assertLessEqual(r1['energy_Nmm'], r0['energy_Nmm']*(1.+1e-9))
                self.assertLess(r1['force_equilibrium_relative'], 1e-6)
                self.assertGreaterEqual(len(r1['pvdf_laminate_response']['per_film']),2)

    def test_fast_evolution_is_sensitive_to_film_and_bond_properties(self):
        g=self.g()
        weak=dict(g, piezo_E_MPa=1200., piezo_adhesive_G_MPa=.15,
                  piezo_adhesive_thickness_um=130.,piezo_bond_fraction=.5)
        strong=dict(g, piezo_E_MPa=4000.,piezo_adhesive_G_MPa=5.,
                    piezo_adhesive_thickness_um=20.,piezo_bond_fraction=1.)
        _,a,_=proxy('quadrant',weak)
        _,b,_=proxy('quadrant',strong)
        self.assertGreater(a['compress_disp_0p1N_mm_proxy'], b['compress_disp_0p1N_mm_proxy'])

    def test_beam_film_strain_and_top3_audit(self):
        g=self.g()
        fem=BeamFEM('quadrant',g,pitch_mm=.75)
        b=fem.solve(force=(0.,0.,-.1))
        self.assertTrue(b['pvdf_stiffness_included'])
        self.assertEqual(b['pvdf_laminate_response']['film_count'],g['piezo_count'])
        self.assertLess(b['force_equilibrium_relative'],1e-6)
        outcome=beam_sweep('quadrant',g,pitch_mm=.75)
        self.assertTrue(outcome['pvdf_stiffness_included'])
        self.assertEqual(outcome['pvdf_film_count'],g['piezo_count'])
        audit=audit_job(('quadrant',g,'balanced',3,True,1.25,'hex8'))
        self.assertTrue(audit['fem']['pvdf_stiffness_included'])
        self.assertEqual(audit['decision_basis']['pvdf_film_count'],g['piezo_count'])

    def test_archived_legacy_genome_keeps_single_film(self):
        g=self.g();g.pop('piezo_count',None)
        for k in ('piezo_E_MPa','piezo_adhesive_G_MPa','piezo_adhesive_thickness_um','piezo_bond_fraction'):
            g.pop(k,None)
        mesh=voxel_mesh('quadrant',g,FEMConfig(pitch_mm=1.25))
        solver=HexElasticSolver(mesh,young_MPa=g['material_E'],family='quadrant',genome=g)
        self.assertEqual(solver.laminate.film_count,1)
        self.assertTrue(solver.solve()['pvdf_stiffness_included'])

    def test_crossover_stays_in_material_ranges(self):
        rng=random.Random(18)
        a=new_genome('quadrant',rng);b=new_genome('quadrant',rng)
        for _ in range(100):
            a=cross('quadrant',a,b,rng)
            self.assertLessEqual(a['piezo_bond_fraction'],1.)
            self.assertGreaterEqual(a['piezo_bond_fraction'],.5)


class UnifiedGui(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(Path(__file__).parents[1]/'static'/'index.html').read_text(encoding='utf8')

    def test_audit_panel_in_geometry_before_mechanical_fem(self):
        s=self.html
        self.assertLess(s.index('Selected geometry · interactive 3D'),s.index('Top-3 full audit · current generation'))
        self.assertLess(s.index('Top-3 full audit · current generation'),s.index('Mechanical FEM: deformed mesh'))
        self.assertEqual(s.count('id="top3Pipeline"'),1)

    def test_one_primary_evaluate_all_button(self):
        s=self.html
        self.assertEqual(s.count('id="evaluateAll"'),1)
        for old in ('id="femRun"','id="runspatial"','id="runcheck"'):
            self.assertNotIn(old,s)
        self.assertIn('await runCharacterization()',s)
        self.assertIn('await runSpatial()',s)
        self.assertIn('renderSolvedFEM()',s)

    def test_evaluate_all_updates_selected_fem_case_and_audit(self):
        import server
        g=new_genome('quadrant',random.Random(24))
        candidate={'id':'audit-v18','family':'quadrant','genome':g}
        with patch('server.select_candidate',return_value=candidate):
            client=TestClient(server.app)
            response=client.post('/api/evaluate_all',json={
                 'selection':'best','family':'quadrant','audit_grid':3,
                 'fem_enabled':True,'fem_backend':'beam','fem_pitch_mm':.75,
                 'fem_inspection_case':'press_offset','fem_inspection_force_n':.2,
                 'fem_inspection_offset_x':1.,'fem_inspection_offset_y':0.})
            self.assertEqual(response.status_code,200,response.text[:350])
            obj=response.json();fem=obj['fem']
            self.assertEqual(fem['inspection_case'],'press_offset')
            self.assertEqual(fem['pvdf_film_count'],g['piezo_count'])
            self.assertTrue(fem['pvdf_stiffness_included'])
            self.assertTrue(fem['fields']['vertices_mm'])
            self.assertAlmostEqual(fem['inspection_metrics']['load_force_N'][2],-.2)
            self.assertIn('unloading_recovery',obj['audit'])

    def test_manual_api_includes_bonded_film_mechanics(self):
        import server
        g=new_genome('quadrant',random.Random(42))
        candidate={'id':'test-v18','family':'quadrant','genome':g}
        with patch('server.select_candidate',return_value=candidate):
            c=TestClient(server.app)
            resp=c.post('/api/fem/simulate',json={'selection':'best','family':'quadrant',
                         'pitch_mm':1.25,'case':'press_center','compute_device':'cpu'})
            self.assertEqual(resp.status_code,200,resp.text[:350])
            result=resp.json()
            self.assertTrue(result['pvdf_stiffness_included'])
            self.assertEqual(result['pvdf_response']['film_count'],g['piezo_count'])
            self.assertGreater(len(result['mesh']['vertices_mm']),0)

if __name__=='__main__':
    unittest.main()
