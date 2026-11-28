import numpy as np
import pytest

from membrane_tile import MembraneTile
from neuroskin_multiscale import tile_response
from neuroskin_v30.integration import TileInput, TileOptimizeInput
from nonlinear_skin_tile import Substrate3D
from relaxed_membrane import RelaxedSkinTile
from tile_optimization import designs


def test_seven_grid_contract_and_scalar_balance():
    request = TileInput(size=7, contacts=[{'x_mm': 60, 'y_mm': 60, 'force_N': .1}])
    assert request.size == 7
    assert TileOptimizeInput().sizes == [3, 5, 7]
    assert TileInput(size=8, contacts=request.contacts).size == 8
    with pytest.raises(ValueError):
        TileInput(size=4, contacts=request.contacts)
    k = np.full((7, 7), .4)
    loads = np.zeros_like(k)
    loads[3, 3] = .1
    assert tile_response(k, .2, loads)['force_balance_error_N'] < 1e-12


def test_seven_grid_membrane_and_compliant_substrate():
    k = np.full((7, 7), .4)
    linear = MembraneTile(k, 20., .3).solve([(60., 60., .1)])
    assert linear['reaction_N'].shape == (7, 7)
    assert linear['force_balance_error_N'] < 1e-9
    substrate = Substrate3D(7, 20., 4., 1.)
    model = RelaxedSkinTile(k, 20., .3, 2., .5, substrate=substrate)
    result = model.solve([(60., 60., .1)])
    assert result['reaction_N'].shape == (7, 7)
    assert result['force_balance_error_N'] < 1e-8
    assert result['substrate']['mesh']['nodes'] == 29*29*3


def test_design_search_keeps_seven_when_footprint_fits():
    receptor = dict(id='example', envelope_mm=19.)
    rows, rejected = designs([receptor], 160., [3, 5, 7], [.3], [4.], 1., 2., .5, .001, 42)
    assert [r['size'] for r in rows] == [3, 5, 7]
    assert not rejected
    rows, rejected = designs([receptor], 120., [3, 7], [.3], [4.], 1., 2., .5, .001, 42)
    assert [r['size'] for r in rows] == [3]
    assert rejected[0]['size'] == 7
