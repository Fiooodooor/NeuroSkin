import json
from population_pareto import OBJECTIVES,rank_population,parent_key,archive_key


def item(id,values,score=50,ok=True,**kw):
    return dict(id=id,metrics={**dict(zip(OBJECTIVES,values)),'spatial_feasible':ok},fitness=score,selection=score,**kw)


def test_tradeoffs_domination_and_feasibility_first():
    a=item('a',[9,1,7,5]);b=item('b',[1,9,7,5]);c=item('c',[1,1,1,1],90)
    bad=item('bad',[99]*4,100,False);failed=item('failed',[99]*4,100,known_audit_feasible=False)
    invalid=item('invalid',[float('nan')]*4,100)
    pop=[a,b,c,bad,failed,invalid]
    assert rank_population(pop,True)==['a','b']
    assert c['pareto']['rank']==1
    assert sorted(pop,key=parent_key,reverse=True)[-1] is invalid
    assert parent_key(a)>parent_key(c)>parent_key(bad)
    assert archive_key(a)>archive_key(failed)
    json.dumps([x['pareto'] for x in pop],allow_nan=False)


def test_clones_same_rank_and_crowding_and_order_independent():
    a=item('a',[3,1,2,2]);b=item('b',[1,3,2,2]);clone=item('clone',[3,1,2,2]);c=item('c',[2,2,2,2])
    pop=[a,b,clone,c];rank_population(pop,False)
    first={x['id']:x['pareto'].copy() for x in pop}
    rank_population(pop[::-1],False)
    assert first=={x['id']:x['pareto'] for x in pop}
    assert a['pareto']==clone['pareto']
    assert c['pareto']['rank']==0


def test_failed_candidates_keep_continuous_search_gradient():
    a=item('a',[1]*4,3,False);b=item('b',[1]*4,12,False)
    assert rank_population([a,b],True)==[]
    assert parent_key(b)>parent_key(a)
    assert rank_population([a,b],False)==['a','b']


def test_archive_reclassifies_known_failed_clone_and_prefers_eligible():
    import random
    from search_space import EliteArchive
    q=EliteArchive()
    a=item('a',[1]*4,90,family='quadrant',genome={'topology':'orthogonal'})
    rank_population([a],True);q.insert(a)
    bad=item('bad',[1]*4,90,family='quadrant',genome={'topology':'orthogonal'},known_audit_feasible=False)
    rank_population([bad],True);q.insert(bad)
    assert q.sample(random.Random(1))['id']=='bad'
    b=item('b',[1]*4,20,family='quadrant',genome={'topology':'serpentine'})
    rank_population([b],True);q.insert(b)
    assert all(q.sample(random.Random(i))['id']=='b' for i in range(10))
