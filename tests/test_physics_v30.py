import random
import numpy as np
import pytest
from advanced import new_genome
from electromechanics import raw_mechanics
from pvdf_physics import charge_pc, capacitance_pf
from piezoelectric import transduction
from laminate_fem import effective_film_properties
from laminate_shell import resolve_laminate_shell
from physical_fem import voxel_mesh, FEMConfig


def test_d31_broad_face_signed_charge_and_capacitance():
    p = dict(effective_width_mm=2., effective_span_mm=4., film_thickness_mm=.028, pvdf_E_MPa=2000.)
    assert charge_pc(p,.001) == pytest.approx(-368.)
    assert charge_pc(p,-.001) == pytest.approx(368.)
    assert charge_pc(dict(p,film_thickness_mm=.056),.001) == charge_pc(p,.001)
    assert capacitance_pf(dict(p,film_thickness_mm=.056)) == pytest.approx(capacitance_pf(p)/2)


def test_active_area_mass_and_legacy_mode():
    g = new_genome('quadrant',random.Random(7));g['hybrid_id']='none'
    m = raw_mechanics('quadrant',g)
    p = transduction('quadrant',g,m)
    q = transduction('quadrant',dict(g,piezo_mode=1),m)
    assert p['charge_pC'] == q['charge_pC']
    assert not q['d33_supported']
    assert sum(c['film_mass_g'] for c in p['channels']) == pytest.approx(p['total_pvdf_mass_g_estimate'])
    for c in p['channels']:
        assert c['charge_pC'] == pytest.approx(-23*c['pvdf_E_MPa_assumed']*c['strain_proxy']*c['active_electrode_area_mm2'])
        assert c['film_mass_g'] == pytest.approx(c['active_electrode_area_mm2']*g['piezo_thickness_um']/1000*.00178)


def test_undeformed_shell_has_zero_strain_energy_and_charge():
    g = new_genome('quadrant',random.Random(7));g['hybrid_id']='none'
    mesh = voxel_mesh('quadrant',g,FEMConfig(pitch_mm=1.25))
    shell = resolve_laminate_shell(mesh,'quadrant',g,np.zeros_like(mesh.nodes))
    for film in shell['per_film']:
        assert film['estimated_charge_pC'] == pytest.approx(0.,abs=1e-12)
        assert film['shell_energy_Nmm'] == pytest.approx(0.,abs=1e-12)
        assert film['top_fiber_strain_max_abs'] == pytest.approx(0.,abs=1e-12)


def test_single_stage_force_balance():
    for family in ('crown','chiral','quadrant'):
        g=new_genome(family,random.Random(19));g['hybrid_id']='none'
        m=raw_mechanics(family,g,force=[.02,-.01,-.1])
        np.testing.assert_allclose(np.sum(m['foot_reactions_N'],axis=0),m['applied_force_N'],atol=1e-7)
