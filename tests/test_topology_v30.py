import random
from advanced import FAMILIES, new_genome, jump, cross, INTEGER_GENES
from hybrid_library import ranked,genome_for


def test_topology_jump_changes_effective_architecture_and_valid_labels():
    rng=random.Random(741)
    for family in FAMILIES:
        g=new_genome(family,rng)
        for _ in range(100):
            child=jump(family,g,rng,'topology')
            assert (child['hybrid_id'],child['topology'])!=(g['hybrid_id'],g['topology'])
            assert (child['hybrid_id']!='none')==(child['topology']=='hybrid')
            g=child


def test_no_orphan_hybrid_and_integer_crossover():
    rng=random.Random(51)
    for family in FAMILIES:
        for _ in range(50):
            a,b=new_genome(family,rng),new_genome(family,rng)
            for g in (a,b,cross(family,a,b,rng)):
                assert (g['hybrid_id']!='none')==(g['topology']=='hybrid')
                assert all(isinstance(g[k],int) for k in INTEGER_GENES if k in g)
