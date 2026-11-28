"""2.1 acceptance: actual run-mode scope, mutation locality and hybrid rotation.

Does not claim empirical force accuracy or nonlinear contact validation.
"""
import random
import math
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient
from hybrid_library import BY_ID, genome_for
from search_space import (SearchScope, MODES, SEARCH_STRATEGIES,
                          local_refinement, EliteArchive, niche_key)
from orientation_study import scan_rotations
from advanced import EvolutionEngine, structural_struts, curve_stiffness, jump


class SearchScopeTests(unittest.TestCase):
    def test_every_declared_scope_generates_only_legal_genomes(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                scope = SearchScope.parse(mode)
                rng = random.Random(123)
                for _ in range(9):
                    family, genome = scope.generate(rng)
                    self.assertTrue(scope.accepts(family, genome))
                    child = jump(family, genome, rng, 'topology')
                    fixed = scope.repair(family, child, rng)
                    self.assertTrue(scope.accepts(family, fixed))
                    self.assertNotEqual(fixed['topology'] == 'hybrid', fixed['hybrid_id'] == 'none')

    def test_exact_hybrid_scope_does_not_drift(self):
        spec = BY_ID['h10_dual_chiral']
        scope = SearchScope.parse('hybrid:' + spec.id)
        rng = random.Random(111)
        for _ in range(30):
            family, genome = scope.generate(rng)
            self.assertEqual(family, spec.upper_family)
            self.assertEqual(genome['hybrid_id'], spec.id)
            child = scope.repair(family, jump(family, genome, rng, 'wide'), rng)
            self.assertEqual(child['hybrid_id'], spec.id)
            self.assertEqual(child['topology'], 'hybrid')

    def test_single_only_scope_removes_hybrid_even_when_mutation_adds_one(self):
        scope = SearchScope.parse('single:all')
        rng = random.Random(42)
        spec = BY_ID['h01_serpentine_quadrant']
        genome = genome_for(spec)
        fixed = scope.repair(spec.upper_family, genome, rng)
        self.assertEqual(fixed['hybrid_id'], 'none')
        self.assertNotEqual(fixed['topology'], 'hybrid')

    def test_bounded_precision_is_reproducible_and_distinct(self):
        g = genome_for(BY_ID['h01_serpentine_quadrant'])
        a = local_refinement('quadrant', g, random.Random(6), precision=.90)
        b = local_refinement('quadrant', g, random.Random(6), precision=.90)
        c = local_refinement('quadrant', g, random.Random(6), precision=.15)
        self.assertEqual(a, b)
        self.assertEqual(a['hybrid_id'], g['hybrid_id'])
        self.assertEqual(a['topology'], 'hybrid')
        self.assertNotEqual(a, c)
        from advanced import PARAM_EXTRA
        from engine import LIMITS
        for name, value in a.items():
            if name in PARAM_EXTRA['quadrant'] or name in LIMITS['quadrant']:
                low, high = (LIMITS['quadrant'] | PARAM_EXTRA['quadrant'])[name]
                self.assertGreaterEqual(value, low)
                self.assertLessEqual(value, high)

    def test_procedural_generates_multiple_cross_family_combinations(self):
        from physical_fem import voxel_mesh, FEMConfig, HexElasticSolver
        from advanced import cross
        scope = SearchScope.parse('procedural:all')
        rng = random.Random(18)
        combos = set()
        samples = []
        for _ in range(80):
            family, genome = scope.generate(rng)
            self.assertTrue(scope.accepts(family, genome))
            combos.add((family, genome['hybrid_lower_family']))
            if len(samples) < 5:
                samples.append((family, genome))
        self.assertGreaterEqual(len(combos), 7)
        for family, genome in samples:
            with self.subTest(top=family, bottom=genome['hybrid_lower_family']):
                solid = voxel_mesh(family, genome, FEMConfig(pitch_mm=1.25))
                result = HexElasticSolver(solid, float(genome['material_E']), family=family, genome=genome).solve()
                self.assertGreater(result['mean_down_mm'], 0.)
                self.assertLess(result['force_equilibrium_relative'], 1e-4)
        _, a = samples[0]
        _, b = samples[-1]
        if samples[0][0] == samples[-1][0]:
            child = cross(samples[0][0], a, b, rng)
            fixed = scope.repair(samples[0][0], child, rng)
            self.assertTrue(scope.accepts(samples[0][0], fixed))

    def test_archive_keeps_best_per_niche(self):
        qd = EliteArchive(max_size=3)
        g = genome_for(BY_ID['h01_serpentine_quadrant'])
        for score in (8.0, 12.0, 4.0):
            qd.insert({'family': 'quadrant', 'genome': g, 'selection': score, 'metrics': {}})
        self.assertEqual(len(qd), 1)
        self.assertEqual(qd.sample(random.Random(1))['selection'], 12.0)


class RotationTests(unittest.TestCase):
    def test_angular_phase_rotates_upper_legs_not_lower_and_not_handedness(self):
        from hybrid_geometry import mid_height, stage_descriptors
        spec = BY_ID['h10_dual_chiral']
        g = genome_for(spec)
        a = dict(g, hybrid_phase=0.0)
        b = dict(g, hybrid_phase=math.pi/4)
        lines_a = structural_struts(spec.upper_family, a)
        lines_b = structural_struts(spec.upper_family, b)
        mid = mid_height(a)
        lower = [i for i, (pts, _, _) in enumerate(lines_a) if pts[0, 2] < mid - .25]
        upper = [i for i, (pts, _, _) in enumerate(lines_a) if pts[0, 2] >= mid - .25]
        self.assertTrue(lower and upper)
        np.testing.assert_allclose(lines_a[lower[0]][0], lines_b[lower[0]][0])
        self.assertFalse(np.allclose(lines_a[upper[0]][0], lines_b[upper[0]][0]))
        stages_a = list(stage_descriptors(spec.upper_family, a))
        stages_b = list(stage_descriptors(spec.upper_family, b))
        self.assertEqual(np.sign(stages_a[0][2]['twist']), np.sign(stages_b[0][2]['twist']))
        self.assertEqual(np.sign(stages_a[1][2]['twist']), np.sign(stages_b[1][2]['twist']))

    def test_rotation_sweep_is_reproducible_and_does_not_modify_source(self):
        spec = BY_ID['h01_serpentine_quadrant']
        genome = genome_for(spec)
        original = dict(genome)
        report = scan_rotations(spec.upper_family, genome, grid=3)
        self.assertEqual(genome, original)
        self.assertEqual(len(report['rows']), 5)
        self.assertIn(report['best_screened_angle_deg'], (0.0,22.5,45.0,67.5,90.0))
        self.assertTrue(any('min_snr_assumed' in r for r in report['rows']))

    def test_api_exposes_all_search_modes_and_orientation(self):
        import server
        client = TestClient(server.app)
        resp = client.get('/api/search_spaces')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual({x['id'] for x in resp.json()['modes']}, set(MODES))
        self.assertEqual({x['id'] for x in resp.json()['strategies']}, set(SEARCH_STRATEGIES))
        html = (Path(__file__).parents[1] / 'static' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('id="searchStrategy"', html)
        self.assertIn('id="searchPrecision"', html)
        self.assertIn('refreshSearchScopes()', html)
        self.assertIn('orientation_study', html)

    def test_live_exact_hybrid_evolution_preserves_scope(self):
        # Smoke test with a short run and no expensive solid FEM. Dedicated
        # identical Top-3 audit still runs, and archives must finalize cleanly.
        from tempfile import TemporaryDirectory
        spec = BY_ID['h01_serpentine_quadrant']
        with TemporaryDirectory() as d:
            e = EvolutionEngine(Path(d))
            e.start('hybrid:' + spec.id, 3., seed=201, population=12,
                    exploration=.8, physical_gate=False, gate_grid=3,
                    cores=1, audit_grid=3, fem=False,
                    search_strategy='precision', search_precision=.9)
            e.thread.join(timeout=55)
            state = e.snapshot()
            self.assertEqual(state['status'], 'completed', state['error'])
            self.assertGreaterEqual(state['generation'], 1)
            self.assertEqual(state['search_strategy'], 'precision')
            self.assertGreaterEqual(state['qd_archive_size'], 1)
            for c in state['gallery']:
                self.assertEqual(c['genome']['hybrid_id'], spec.id)


if __name__ == '__main__':
    unittest.main()
