import random
import numpy as np
import pytest
from advanced import structural_struts, curve_stiffness, jump, _single_stage_struts
from hybrid_geometry import stage_models
from hybrid_library import ranked, genome_for
from pvdf_array import choose_film_members, layout_metrics
from search_space import SearchScope
from symmetry_geometry import TARGETS, symmetry_report
from piezoelectric import transduction
from electromechanics import raw_mechanics


@pytest.mark.parametrize('target',TARGETS)
def test_constrained_scope_preserves_orbits_and_stiffness(target):
    rng=random.Random(44)
    scope=SearchScope.parse('symmetry:'+target)
    for family in scope.families:
        g=scope.repair(family,scope.generate(rng)[1] if len(scope.families)==1 else __import__('advanced').new_genome(family,rng),rng)
        for _ in range(3):
            assert scope.accepts(family,g)
            paths=structural_struts(family,g)
            assert len(paths)==g['piezo_count']
            report=symmetry_report(family,g)
            assert report['stiffness_residual'][target]<1e-10
            assert report['central_lateral_mm']<1e-10
            assert report['central_tilt_rad']<1e-10
            assert report['film_layout']['normalized_imbalance']<1e-10
            # Match every rotated path to another actual path, not only K.
            a=2*np.pi/int(target[1:]);c,s=np.cos(a),np.sin(a)
            q=np.array([[c,s,0],[-s,c,0],[0,0,1]])
            for p,r,tag in paths:
                assert any(np.allclose(p@q,x,atol=1e-10) and r==rr and tag==tt for x,rr,tt in paths)
            g=scope.repair(family,jump(family,g,rng,'wide'),rng)


def test_stage_film_indices_match_global_layout_for_all_hybrids():
    for spec in ranked():
        g=genome_for(spec)
        for n in (1,2,3,4,6,8):
            h=dict(g,piezo_count=n)
            global_paths=structural_struts(spec.upper_family,h)
            expected=set(choose_film_members(global_paths,h))
            actual=set();offset=0
            for _,f,sg,_ in stage_models(spec.upper_family,h):
                actual.update(offset+i for i in sg['_film_indices'])
                assert sg['piezo_count']==len(sg['_film_indices'])
                offset+=len(_single_stage_struts(f,sg))
            assert actual==expected and len(actual)==n


def test_odd_stack_sensor_imbalance_cannot_cancel_across_levels():
    spec=ranked()[0];g=dict(genome_for(spec),piezo_count=3)
    layout=layout_metrics(structural_struts(spec.upper_family,g),g)
    assert layout['per_stage']['upper']['film_count']==2
    assert layout['per_stage']['lower']['film_count']==1
    assert layout['normalized_imbalance']>=layout['per_stage']['lower']['normalized_imbalance']


def test_upper_pvdf_not_directly_strained_by_ground_movement():
    spec=ranked()[0];g=genome_for(spec)
    result=transduction(spec.upper_family,g,raw_mechanics(spec.upper_family,g,'stretch_x'))
    assert all(abs(c['charge_pC'])<1e-12 for c in result['channels'] if c['stage']=='upper')
