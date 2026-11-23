"""NeuroSkin 1.9.1: feasibility-first evolution and sensing refinements.

No score in this suite is claimed to be a measured hardware result.
"""
import random
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from advanced import new_genome, structural_struts, engine_provenance, audit_job
from electromechanics import examine
from full_evaluation import audit_candidate
from optimization import evaluate
from pvdf_array import choose_film_members, _cached_member_selection
from selection_refinement import (spatial_operating_summary, enforce_score_band,
                                  guided_child, INFEASIBLE_SCORE_CEILING)
from spatial_validation import spatial_pressure_test


class RefinementPolicyTests(unittest.TestCase):
    def test_low_force_diagnostic_is_not_worst_operating_coverage(self):
        def reading(coverage, snr, tilt, quality):
            return dict(coverage_fraction=coverage, min_snr_proxy=snr, max_tilt_rad=tilt,
                        mean_point_quality=quality, failure_reasons=[])
        r = spatial_operating_summary({
            '0.025': reading(0.0, 1.2, .04, .5),
            '0.1': reading(.8, 3.3, .12, .92),
            '0.4': reading(1.0, 4.1, .25, 1.0),
        })
        self.assertEqual(r['low_force_coverage'], 0.0)
        self.assertEqual(r['operating_worst_coverage'], .8)
        self.assertTrue(r['screen_feasible'])

    def test_postmix_infeasible_score_is_always_below_feasible(self):
        failed = enforce_score_band({'feasible':False, 'audit_score':92.3})
        passed = enforce_score_band({'feasible':True, 'audit_score':33.3})
        self.assertLessEqual(failed['audit_score'],INFEASIBLE_SCORE_CEILING)
        self.assertGreaterEqual(passed['audit_score'],50.)
        self.assertLess(failed['audit_score'],passed['audit_score'])
        less_bad=enforce_score_band({'feasible':False,'audit_score':80.})
        worse=enforce_score_band({'feasible':False,'audit_score':40.})
        self.assertGreater(less_bad['audit_score'],worse['audit_score'])
        self.assertLess(less_bad['audit_score'],50.)

    def test_electrode_area_gap_and_compliance_affect_synthetic_snr(self):
        g = new_genome('quadrant', random.Random(19))
        g.update(topology='orthogonal', asymmetry=0., pad_offset_x=0.,pad_offset_y=0.,
                 wave_amp=0.,strut_gradient=0.,piezo_count=4)
        weak = dict(g, electrode_area_mm2=4.0, dielectric_gap_mm=.6, mount_compliance_mm_N=.11)
        strong = dict(g, electrode_area_mm2=9.5, dielectric_gap_mm=.25, mount_compliance_mm_N=.43)
        s0 = spatial_pressure_test('quadrant', weak, grid_size=3)
        s1 = spatial_pressure_test('quadrant', strong, grid_size=3)
        self.assertGreater(s1['min_snr_proxy'],s0['min_snr_proxy'])
        self.assertGreaterEqual(s1['coverage_fraction'],s0['coverage_fraction'])
        self.assertAlmostEqual(examine('quadrant',weak,'normal')['electrical']['noise_assumptions']['pressure_rms_pF'],
                               examine('quadrant',strong,'normal')['electrical']['noise_assumptions']['pressure_rms_pF'])

    def test_refinement_genes_bounded_and_old_genomes_readable(self):
        rng=random.Random(998)
        for family in ('quadrant','crown','chiral'):
            for _ in range(20):
                g = new_genome(family,rng)
                self.assertTrue(4.0 <= g['electrode_area_mm2'] <= 9.5)
                self.assertTrue(.25 <= g['dielectric_gap_mm'] <= .65)
                self.assertTrue(.10 <= g['mount_compliance_mm_N'] <= .48)
            legacy = dict(g)
            for k in ('electrode_area_mm2','dielectric_gap_mm','dielectric_epsilon_r', 'mount_compliance_mm_N'):
                legacy.pop(k)
            self.assertTrue(spatial_pressure_test(family,legacy,grid_size=3)['points'])

    def test_targeted_guidance_moves_sensible_parameters(self):
        rng=random.Random(18)
        g=new_genome('quadrant',rng)
        g.update(pad_offset_x=.7,pad_offset_y=-.6,asymmetry=.45,piezo_count=3,
                 dielectric_gap_mm=.49,electrode_area_mm2=5.0)
        info={'spatial_gate':{'failure_reasons':['weak_pressure_signal','excessive_tilt']}}
        child=guided_child('quadrant',g,info,random.Random(3))
        self.assertLessEqual(child['dielectric_gap_mm'],.65)
        self.assertGreaterEqual(child['electrode_area_mm2'],4.)
        self.assertIn(child['piezo_count'],(1,2,3,4))
        self.assertLessEqual(abs(child['pad_offset_x']),.8)

    def test_partial_margins_provide_gradient_on_failed_screen(self):
        g=new_genome('quadrant',random.Random(52))
        g.update(topology='orthogonal',asymmetry=0.,pad_offset_x=0.,pad_offset_y=0.,wave_amp=0.,strut_gradient=0.)
        weak=dict(g,electrode_area_mm2=4.,dielectric_gap_mm=.6,mount_compliance_mm_N=.1)
        middle=dict(g,electrode_area_mm2=8.,dielectric_gap_mm=.28,mount_compliance_mm_N=.27)
        a,ma,_=evaluate('quadrant',weak,'balanced',True,3)
        b,mb,_=evaluate('quadrant',middle,'balanced',True,3)
        self.assertLess(a,15.)
        self.assertLess(b,15.)
        self.assertGreater(b,a)
        self.assertIn('spatial_continuous_quality',mb)

    def test_cached_layout_is_stable(self):
        g=new_genome('crown',random.Random(14))
        paths=structural_struts('crown',g)
        first=choose_film_members(paths,g)
        before=_cached_member_selection.cache_info().hits
        for _ in range(8):
            self.assertEqual(choose_film_members(paths,g),first)
        self.assertGreaterEqual(_cached_member_selection.cache_info().hits,before+8)
        old=dict(g);old.pop('piezo_count',None)
        self.assertEqual(len(choose_film_members(paths,old)),1)

    def test_full_audit_score_band_and_explicit_force_summary(self):
        g=new_genome('quadrant',random.Random(33))
        audit=audit_candidate('quadrant',g,grid_size=3)
        self.assertIn('spatial_operating_summary',audit)
        self.assertIn('screening_failure_reasons',audit)
        self.assertIn('score_band',audit)
        self.assertEqual(audit['score_band']=='feasible',audit['feasible'])
        self.assertGreaterEqual(audit['audit_score'],50.) if audit['feasible'] else self.assertLess(audit['audit_score'],50.)

    def test_fem_final_stage_keeps_feasibility_band(self):
        g=new_genome('quadrant',random.Random(44))
        audit=audit_job(('quadrant',g,'balanced',3,True,1.25,'hex8'))
        self.assertIn('fem',audit)
        self.assertIn('audit_policy_version',audit)
        self.assertLess(audit['audit_score'],50.) if not audit['feasible'] else self.assertGreaterEqual(audit['audit_score'],50.)
        if 'laminate_shell' in audit:
            self.assertIn('laminate_shell_score',audit['decision_basis'])

    def test_shell_score_is_independent_of_manual_visual_inspection_load(self):
        from physical_fem import fem_sweep
        g=new_genome('quadrant',random.Random(31))
        a=fem_sweep('quadrant',g,pitch_mm=1.25,include_fields=True,backend='hex8',
                    inspector_case='press_center',inspector_force_N=.1)
        b=fem_sweep('quadrant',g,pitch_mm=1.25,include_fields=True,backend='hex8',
                    inspector_case='press_offset',inspector_force_N=.3,inspector_offset=(1.,0.))
        self.assertAlmostEqual(a['laminate_shell']['shell_score'],b['laminate_shell']['shell_score'])
        self.assertAlmostEqual(a['fem_score'],b['fem_score'])
        self.assertIsNotNone(b['laminate_shell_inspection'])
        self.assertNotEqual(a['laminate_shell_inspection']['max_eq_stress_MPa'],
                            b['laminate_shell_inspection']['max_eq_stress_MPa'])

    def test_gui_has_operating_coverage_and_failure_reasons(self):
        html=(Path(__file__).parents[1]/'static'/'index.html').read_text(encoding='utf8')
        self.assertIn('0.1 N coverage',html)
        self.assertIn('0.4 N coverage',html)
        self.assertIn('screening_failure_reasons',html)
        self.assertIn('Final laminate shell',html)
        self.assertIn('Evaluate All',html)

    def test_provenance_changes_after_policy_update(self):
        provenance=engine_provenance()
        self.assertEqual(provenance['release'],'1.9.1')
        self.assertEqual(len(provenance['sha256']),64)


if __name__=='__main__':
    unittest.main()
