"""Acceptance tests: two 3D stages must be physically connected and evaluated in series."""
import random
import unittest
from pathlib import Path
import numpy as np
from fastapi.testclient import TestClient

from hybrid_library import ranked, genome_for, library_json
from hybrid_geometry import mid_height
from advanced import structural_struts, curve_stiffness, detail_mesh, _single_stage_curve_stiffness
from physical_fem import voxel_mesh, FEMConfig, HexElasticSolver, fem_sweep, InvalidGeometry
from pvdf_array import choose_film_members
from piezoelectric import response
from electromechanics import raw_mechanics
from server import app


class HybridLibraryTests(unittest.TestCase):
    def test_catalogue_ranks_ten_by_transparent_ten_metric_prior(self):
        designs=ranked()
        self.assertEqual(len(designs),10)
        self.assertEqual(len({x.id for x in designs}),10)
        self.assertTrue(all(len(d.scores)==10 and all(0<=v<=10 for v in d.scores) for d in designs))
        self.assertEqual([sum(x.scores) for x in designs],sorted([sum(x.scores) for x in designs],reverse=True))
        self.assertEqual(len(library_json()['criteria']),10)

    def test_opposed_chirality_is_real_not_just_a_label(self):
        from hybrid_library import BY_ID
        from hybrid_geometry import stage_descriptors
        spec=BY_ID['h10_dual_chiral']
        g=genome_for(spec)
        stages=list(stage_descriptors(spec.upper_family,g))
        self.assertLess(stages[0][2]['twist'],0.)
        self.assertGreater(stages[1][2]['twist'],0.)

    def test_geometry_and_mechanical_loadpath_for_every_architecture(self):
        for spec in ranked():
            with self.subTest(spec=spec.id):
                g=genome_for(spec)
                mid=mid_height(g)
                paths=structural_struts(spec.upper_family,g)
                self.assertGreaterEqual(len(paths),8)
                self.assertTrue(any(p[0,2]<mid-.25 for p,r,tag in paths))
                self.assertTrue(any(p[0,2]>=mid-.25 for p,r,tag in paths))
                self.assertTrue(all(np.all(np.isfinite(p)) for p,_,_ in paths))
                body=detail_mesh(spec.upper_family,g,quality=10)
                self.assertIn('inner',body)
                self.assertIn('piezo',body)
                mesh=voxel_mesh(spec.upper_family,g,FEMConfig(pitch_mm=1.25))
                self.assertGreater(mesh.voxels,80)
                solution=HexElasticSolver(mesh,float(g['material_E']),family=spec.upper_family,genome=g).solve()
                self.assertGreater(solution['mean_down_mm'],0)
                self.assertLess(solution['force_equilibrium_relative'],1e-4)

    def test_series_stiffness_and_stage_specific_pvdf_channels(self):
        from hybrid_geometry import stage_stiffnesses
        for spec in ranked():
            with self.subTest(spec=spec.id):
                g=genome_for(spec)
                stages=stage_stiffnesses(spec.upper_family,g,_single_stage_curve_stiffness)
                # Independent work-conjugate transport: top force induces
                # a lever-arm moment at the intermediate plate.
                h=g['height']-mid_height(g)
                T=np.eye(6); T[0,4]=h; T[1,3]=-h
                reference=np.linalg.inv(T@np.linalg.inv(stages[0][1])@T.T+np.linalg.inv(stages[1][1]))
                actual=curve_stiffness(spec.upper_family,g)
                np.testing.assert_allclose(actual,reference,rtol=1e-9,atol=1e-9)
                chosen=choose_film_members(structural_struts(spec.upper_family,g),g)
                self.assertEqual(len(chosen),g['piezo_count'])
                mechanics=raw_mechanics(spec.upper_family,g,'normal')
                self.assertIn('stage_displacements_mm',mechanics)
                pvdf=response(spec.upper_family,g,mechanics)
                labels=[c['stage'] for c in pvdf['channels']]
                self.assertIn('upper',labels)
                self.assertIn('lower',labels)

    def test_stacked_wrench_transport_and_substrate_motion(self):
        for spec in ranked():
            with self.subTest(spec=spec.id):
                g=genome_for(spec)
                m=raw_mechanics(spec.upper_family,g,'shear_x')
                top=np.asarray(m['stage_loads_N_Nmm']['upper'])
                low=np.asarray(m['stage_loads_N_Nmm']['lower'])
                np.testing.assert_allclose(low[:3],top[:3],atol=1e-12)
                self.assertAlmostEqual(low[4]-top[4],.03*(g['height']-mid_height(g)),places=12)
                u=np.r_[m['displacement_mm'],m['rotation_rad']]
                np.testing.assert_allclose(curve_stiffness(spec.upper_family,g)@u,top,atol=1e-9)
                stretch=raw_mechanics(spec.upper_family,g,'stretch_x')
                np.testing.assert_allclose(stretch['stage_displacements_mm']['upper'],0.,atol=1e-12)
                np.testing.assert_allclose(stretch['stage_rotations_rad']['upper'],0.,atol=1e-12)

    def test_upper_rotation_and_stage_scale_are_not_inert_genes(self):
        spec=ranked()[0];g=genome_for(spec)
        a=dict(g,hybrid_phase=0.,hybrid_upper_scale=.65)
        b=dict(g,hybrid_phase=.70,hybrid_upper_scale=1.2)
        path_a=structural_struts(spec.upper_family,a)
        path_b=structural_struts(spec.upper_family,b)
        # Upper-stage surface has rotated, while lower stage remains anchored.
        upper_index=next(i for i, (p,r,tag) in enumerate(path_a) if p[0,2]>mid_height(a)-.25)
        self.assertFalse(np.allclose(path_a[upper_index][0][0,:2],path_b[upper_index][0][0,:2]))
        self.assertFalse(np.allclose(curve_stiffness(spec.upper_family,a),curve_stiffness(spec.upper_family,b)))

    def test_fast_hybrid_reactions_obey_global_force_equilibrium(self):
        # Prevent mixing PVDF-reinforced stiffness with unreinforced reaction terms.
        for spec in ranked():
            with self.subTest(spec=spec.id):
                from electromechanics import raw_mechanics
                g=genome_for(spec)
                mechanics=raw_mechanics(spec.upper_family,g,'normal')
                reactions=np.asarray(mechanics['foot_reactions_N'])
                total=float(reactions[:,2].sum())
                self.assertAlmostEqual(total,-0.1,places=7)
                np.testing.assert_allclose(np.asarray(mechanics['K_N_per_mm_proxy']),
                                           curve_stiffness(spec.upper_family,g),
                                           rtol=1e-9,atol=1e-9)

    def test_tuned_reference_hybrids_pass_identical_complete_audit(self):
        from hybrid_library import BY_ID
        from advanced import audit_job
        for code in ('h01_serpentine_quadrant','h10_dual_chiral'):
            with self.subTest(hybrid=code):
                spec=BY_ID[code]
                genome=genome_for(spec)
                self.assertGreater(genome['thickness'],0.5)
                audit=audit_job((spec.upper_family,genome,'balanced',3,True,1.25,'hex8'))
                self.assertTrue(audit['feasible'],str(audit['decision_basis']))
                self.assertTrue(audit['fem']['feasible_linear'])
                self.assertTrue(audit['laminate_shell']['feasible_shell_screen'])

    def test_electrical_wiring_mode_changes_available_information(self):
        from electromechanics import examine
        spec=ranked()[0];g=genome_for(spec)
        independent=examine(spec.upper_family,dict(g,hybrid_sensor_mode=0),'normal')['electrical']['hybrid_stage_channels']
        aggregate=examine(spec.upper_family,dict(g,hybrid_sensor_mode=2),'normal')['electrical']['hybrid_stage_channels']
        self.assertEqual(independent['readout_mode'],'independent')
        self.assertEqual(len(independent['readout_vector_pF_assumed']),2)
        self.assertEqual(aggregate['readout_mode'],'common_only')
        self.assertEqual(len(aggregate['readout_vector_pF_assumed']),1)

    def test_full_fem_reports_two_stage_loads_and_shell(self):
        spec=ranked()[0];g=genome_for(spec)
        r=fem_sweep(spec.upper_family,g,pitch_mm=1.25,backend='hex8',include_fields=True)
        self.assertTrue(r['feasible_linear'])
        d=r['hybrid_stages']
        self.assertGreater(d['lower_compression_mm'],0)
        self.assertGreater(d['upper_compression_mm'],0)
        self.assertLess(d['continuity_error_mm'],1e-8)
        self.assertEqual(d['stage_response_rank_max3'],3)
        self.assertEqual(len(d['stage_displacements_by_load']),8)
        self.assertTrue(r['laminate_shell'] and not r['laminate_shell'].get('failed'))

    def test_refined_mesh_central_load_has_physically_scaled_moment_balance(self):
        # For centered -Fz theoretical net moment is zero; do not divide
        # machine precision residual by a near-zero reference moment.
        from hybrid_library import BY_ID
        spec=BY_ID['h10_dual_chiral'];g=genome_for(spec)
        report=fem_sweep(spec.upper_family,g,pitch_mm=.625,backend='hex8')
        self.assertTrue(report['feasible_linear'])
        self.assertLess(report['moment_equilibrium_max'],1e-7)
        self.assertGreater(report['elements'],2000)

    def test_beam_backend_cannot_silently_ignore_intermediate_plate(self):
        spec=ranked()[0];g=genome_for(spec)
        with self.assertRaises(InvalidGeometry):
            fem_sweep(spec.upper_family,g,pitch_mm=0.5,backend='beam')

    def test_api_and_browser_controls(self):
        client=TestClient(app)
        r=client.get('/api/hybrid_library')
        self.assertEqual(r.status_code,200)
        self.assertEqual(len(r.json()['architectures']),10)
        spec=ranked()[0]
        cand=client.get('/api/hybrids/'+spec.id)
        self.assertEqual(cand.status_code,200)
        self.assertEqual(cand.json()['genome']['hybrid_id'],spec.id)
        audit=client.post('/api/evaluate_all',json={
            'selection':'hybrid','index':spec.id,'family':spec.upper_family,
            'audit_grid':3,'fem_enabled':True,'fem_backend':'hex8',
            'fem_pitch_mm':1.25,'fem_inspection_case':'press_center',
            'fem_inspection_force_n':0.1,'fem_inspection_offset_x':0.0,'fem_inspection_offset_y':0.0,
        })
        self.assertEqual(audit.status_code,200,audit.text[:300])
        self.assertIn('hybrid_stages',audit.json()['audit'])
        html=(Path(__file__).parents[1]/'static'/'index.html').read_text(encoding='utf8')
        self.assertIn('id="hybridLibrary"',html)
        self.assertIn("loadHybridLibrary()",html)
        self.assertIn('Final laminate shell',html)
