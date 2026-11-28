import numpy as np
import pytest
from fem_preview import PREVIEW_CASES,pack_previews


def test_shared_preview_topology_and_case_identity(monkeypatch):
    import fem_preview
    monkeypatch.setattr(fem_preview,'MAX_TRIANGLES',1)
    fields={name:{'vertices_mm':[[0,0,0],[1,0,0],[0,1,0],[1,1,0]],
                  'faces':[[0,1,2],[1,2,3]],'displacement_mm':[[0,0,i]]*4,
                  'stress_vm_MPa':[i]*4,'principal_strain':[i/10]*4}
            for i,name in enumerate(PREVIEW_CASES)}
    metrics={name:{'max_displacement_mm':i,'load_force_N':[0,0,-.1]} for i,name in enumerate(PREVIEW_CASES)}
    out=pack_previews(fields,metrics)
    assert out['case_order']==list(PREVIEW_CASES)
    assert out['display_downsampled'] and out['display_surface_triangles']==1
    assert len(out['vertices_mm'])==3
    for i,name in enumerate(PREVIEW_CASES):
        assert out['cases'][name]['displacement_mm']==[[0,0,i]]*3
        assert out['cases'][name]['metrics']['max_displacement_mm']==i
    fields['shear_x']['vertices_mm'][0]=[1,2,3]
    with pytest.raises(ValueError,match='share reference'):pack_previews(fields,metrics)


@pytest.mark.parametrize('backend',['hex8','beam'])
def test_fem_preview_fields_reuse_standard_cases_without_changing_score(backend):
    from advanced import new_genome
    from physical_fem import fem_sweep
    import random
    g=new_genome('quadrant',random.Random(42));g['hybrid_id']='none'
    a=fem_sweep('quadrant',g,pitch_mm=1.25,backend=backend)
    b=fem_sweep('quadrant',g,pitch_mm=1.25,backend=backend,include_fields=True,include_previews=True)
    assert 'preview_fields' not in a
    assert a['fem_score']==pytest.approx(b['fem_score'],abs=1e-7)
    assert a['feasible_linear']==b['feasible_linear']
    p=b['preview_fields'];assert p['case_order']==list(PREVIEW_CASES)
    for name in PREVIEW_CASES:
        c=p['cases'][name]
        assert len(c['displacement_mm'])==len(p['vertices_mm'])
        assert c['metrics']['max_displacement_mm']==b['load_cases'][name]['max_displacement_mm']
        vectors=c['boundary_vectors']
        np.testing.assert_allclose(vectors['applied']['force_N'],b['load_cases'][name]['load_force_N'],atol=1e-10)
        np.testing.assert_allclose(vectors['reaction']['force_N'],b['load_cases'][name]['force_reaction_N'],atol=1e-10)
        assert np.linalg.norm(vectors['force_balance_N'])<1e-4
        assert np.linalg.norm(vectors['moment_balance_Nmm'])<1e-3
        assert 'boundary_vectors' not in b['load_cases'][name]
        if backend=='hex8':
            assert vectors['substrate_sections']
            assert all(s['area_mm2']>0 for s in vectors['substrate_sections'])
        else:assert 'substrate_sections' not in vectors
    assert not np.allclose(p['cases']['press_center']['displacement_mm'],p['cases']['shear_x']['displacement_mm'])


def test_optional_preview_serialization_failure_does_not_change_fem_result(monkeypatch):
    from advanced import new_genome
    import physical_fem as pf
    import random
    g=new_genome('quadrant',random.Random(42));g['hybrid_id']='none'
    baseline=pf.fem_sweep('quadrant',g,pitch_mm=1.25,backend='hex8')
    def fail(*args,**kwargs):
        raise ValueError('Injected preview packing failure')
    monkeypatch.setattr(pf,'pack_previews',fail)
    out=pf.fem_sweep('quadrant',g,pitch_mm=1.25,backend='hex8',include_previews=True)
    assert 'preview_fields' not in out
    assert 'Injected preview packing failure' in out['preview_error']
    assert baseline['fem_score']==out['fem_score']
    assert baseline['feasible_linear']==out['feasible_linear']
