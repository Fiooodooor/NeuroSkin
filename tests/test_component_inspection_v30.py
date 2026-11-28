import random
import numpy as np
import pytest
from advanced import detail_mesh, webmesh, new_genome, structural_struts
from hybrid_library import ranked, genome_for
from pvdf_array import choose_film_members


@pytest.mark.parametrize('hybrid',[False,True])
def test_component_spans_and_film_identity(hybrid):
    if hybrid:
        spec=ranked()[0];family=spec.upper_family;g=genome_for(spec)
    else:
        family='quadrant';g=new_genome(family,random.Random(42));g['hybrid_id']='none'
    data=webmesh(family,g,10)
    nodes=data['component_tree']['nodes']
    assert len({n['id'] for n in nodes})==len(nodes)
    original=detail_mesh(family,g,10)
    for c in data['components']:
        spans=[n for n in nodes if n['part']==c['part']]
        assert sum(n['face_count'] for n in spans)==len(c['faces'])
        assert sum(n['vertex_count'] for n in spans)==len(c['vertices'])
        np.testing.assert_array_equal(c['faces'],original[c['part']].faces)
        np.testing.assert_allclose(c['vertices'],original[c['part']].vertices,atol=.00051)
        for n in spans:
            faces=np.asarray(c['faces'][n['face_start']:n['face_start']+n['face_count']])
            assert faces.min()>=n['vertex_start'] and faces.max()<n['vertex_start']+n['vertex_count']
    paths=structural_struts(family,g);selected=choose_film_members(paths,g)
    members={n['id']:n for n in nodes if n['part']=='flexure'}
    assert len(members)==len(paths)
    for n in nodes:
        if n['part']=='piezo':
            assert selected[n['film_index']]==n['member_index']
            assert members[n['bonded_to']]['stage']==n['stage']
    if hybrid:assert {'upper','lower','interface'}<={n['stage'] for n in nodes}
