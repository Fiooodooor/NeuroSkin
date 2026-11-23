import random
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from advanced import new_genome, audit_job
from physical_fem import fem_sweep


class LaminateShellV19(unittest.TestCase):
    def test_hex8_fem_reports_final_laminate_shell(self):
        g = new_genome('quadrant', random.Random(7))
        fem = fem_sweep('quadrant', g, pitch_mm=1.25, include_fields=True, backend='hex8')
        self.assertIn('laminate_shell', fem)
        shell = fem['laminate_shell']
        self.assertIsInstance(shell, dict)
        self.assertFalse(shell.get('failed', False))
        self.assertEqual(shell['film_count'], g['piezo_count'])
        self.assertTrue(shell['graphics']['films'])
        self.assertGreaterEqual(shell['shell_score'], 0.0)
        self.assertLessEqual(shell['shell_score'], 100.0)

    def test_top3_audit_includes_shell_stage(self):
        g = new_genome('quadrant', random.Random(9))
        audit = audit_job(('quadrant', g, 'balanced', 3, True, 1.25, 'hex8'))
        self.assertIn('laminate_shell', audit)
        self.assertIn('laminate_shell_score', audit['decision_basis'])
        self.assertIn('laminate_shell_feasible', audit['decision_basis'])

    def test_evaluate_all_exposes_shell_summary_to_ui(self):
        import server
        g = new_genome('quadrant', random.Random(11))
        candidate = {'id': 'shell-v19', 'family': 'quadrant', 'genome': g}
        with patch('server.select_candidate', return_value=candidate):
            client = TestClient(server.app)
            response = client.post('/api/evaluate_all', json={
                'selection': 'best', 'family': 'quadrant', 'audit_grid': 3,
                'fem_enabled': True, 'fem_backend': 'hex8', 'fem_pitch_mm': 1.25,
                'fem_inspection_case': 'press_center', 'fem_inspection_force_n': .1,
                'fem_inspection_offset_x': 0., 'fem_inspection_offset_y': 0.})
            self.assertEqual(response.status_code, 200, response.text[:300])
            obj = response.json()
            self.assertIn('laminate_shell', obj['audit'])
            self.assertIn('laminate_shell', obj['fem'])
            self.assertTrue(obj['fem']['laminate_shell']['graphics']['films'])


class LaminateShellGuiV19(unittest.TestCase):
    def test_gui_mentions_shell_stage_and_view(self):
        from pathlib import Path
        html = (Path(__file__).parents[1] / 'static' / 'index.html').read_text(encoding='utf8')
        self.assertIn('Final laminate shell — resolved PVDF ribbons', html)
        self.assertIn('id="laminatePlot"', html)
        self.assertIn('renderLaminateShell()', html)
