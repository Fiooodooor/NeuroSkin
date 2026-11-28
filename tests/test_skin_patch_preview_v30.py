from copy import deepcopy
import random

import pytest
from fastapi.testclient import TestClient

from skin_patch_preview import patch_layout, geometry_template, attach_skin_previews


def template():
    return {'genome_hash': 'same', 'bounds_mm': [[-9., -9., 0.], [9., 9., 6.]]}


def design(n=3, id='layout'):
    return {'id': id, 'size': n, 'side_mm': n*20., 'pitch_mm': 20.,
            'substrate_thickness_mm': 4., 'membrane_thickness_mm': .5,
            'receptor': {'id': 'example', 'genome_hash': 'same'}}


@pytest.mark.parametrize('n', [3, 5, 7])
def test_exact_grid_placements_and_geometry_identity(n):
    layout = patch_layout(design(n), template())
    assert layout['sensor_count'] == n*n
    assert len({tuple(p['position_mm']) for p in layout['placements']}) == n*n
    assert layout['placements'][0]['position_mm'] == [10., 10., 0.]
    assert layout['placements'][-1]['position_mm'] == [n*20.-10., n*20.-10., 0.]
    assert layout['minimum_xy_clearance_mm'] == 2.
    assert layout['membrane_z_mm'] == 6.
    assert layout['nominal_geometry_only'] and not layout['hardware_qualified']
    assert layout['genome_hash'] == template()['genome_hash']


def test_geometry_mismatch_and_invalid_spacing_are_rejected():
    stale = template()
    stale['genome_hash'] = 'different'
    with pytest.raises(ValueError, match='match'):
        patch_layout(design(), stale)
    crowded = design()
    crowded.update(pitch_mm=10., side_mm=30.)
    with pytest.raises(ValueError, match='fit'):
        patch_layout(crowded, template())
    bad = design()
    bad['side_mm'] = 1.
    with pytest.raises(ValueError, match='dimensions'):
        patch_layout(bad, template())


def test_preview_preference_never_compares_fidelity_scores(monkeypatch):
    import skin_patch_preview
    monkeypatch.setattr(skin_patch_preview, 'geometry_template', lambda *args: template())
    screen = [{**design(n, 'screen-'+str(n)), 'fidelity': 'screen', 'diagnostic_screen_pass': True,
               'utility_cost': .1} for n in (3, 5, 7)]
    refined = [{**design(3, 'refined-3'), 'fidelity': 'refined', 'diagnostic_screen_pass': True,
                'utility_cost': 10.}]
    result = {'screening': screen, 'refined': refined}
    original = deepcopy(screen)
    attach_skin_previews(result, {'example': ({}, {})})
    assert result['recommended_skin_patches'] == {'3': 'refined:refined-3', '5': 'screen:screen-5', '7': 'screen:screen-7'}
    assert result['screening'] == original


def test_surface_template_is_actual_genome_and_bounded_lod(monkeypatch):
    from advanced import new_genome
    from validation_contract import digest
    import skin_patch_preview
    genome = new_genome('quadrant', random.Random(42))
    candidate = {'id': 'current', 'family': 'quadrant'}
    original = deepcopy(genome)
    surface = geometry_template(candidate, genome)
    assert surface['genome_hash'] == digest({'family': 'quadrant', 'genome': genome})
    assert surface['rendering'] == 'surface_mesh'
    assert {'base', 'flexure', 'contact', 'piezo'} <= {c['part'] for c in surface['components']}
    monkeypatch.setattr(skin_patch_preview, 'MAX_TEMPLATE_FACES', 1)
    reduced = geometry_template(candidate, genome)
    assert reduced['rendering'] == 'structural_centerlines'
    assert reduced['centerlines_mm'] and not reduced['components']
    assert genome == original


@pytest.mark.parametrize('n,side', [(3, 80.), (7, 160.)])
def test_actual_optimization_supplies_matching_skin_geometry(n, side):
    from server import app
    req = {'selection': 'hybrid', 'index': 'h01_serpentine_quadrant', 'include_library': False,
           'sizes': [n], 'patch_side_mm': side, 'tensions': [.3], 'substrate_depths_mm': [4.],
           'finalists': 1, 'compute_workers': 1}
    with TestClient(app) as client:
        response = client.post('/api/v30/tile/optimize', json=req)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['skin_patches'], result['skin_preview_errors']
        layout = next(p for p in result['skin_patches'] if p['key'] == result['recommended_skin_patches'][str(n)])
        model = result['skin_templates'][layout['receptor_id']]
        assert layout['sensor_count'] == n*n
        assert model['genome_hash'] == layout['genome_hash']
        assert layout['side_mm'] == side
        refined = [row for row in result['refined'] if not row.get('failed')]
        assert layout['fidelity'] == ('refined' if refined else 'screen')
        if not refined:
            assert result['refined'][0]['failed'] and result['refined'][0]['error']
        assert result['diagnostic_context']['path'] == 'tile/optimize'
