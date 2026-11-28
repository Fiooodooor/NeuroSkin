from finalist_selection import genome_key, nominate
from population_pareto import OBJECTIVES


def candidate(id, score, metrics=(1,1,1,1), feasible=True, gene=None):
    return {'id':id,'family':'quadrant','genome':{'gene':id if gene is None else gene},'fitness':score,'selection':score,'metrics':{**dict(zip(OBJECTIVES,metrics)),'spatial_feasible':feasible}}


def test_known_failures_cannot_starve_new_candidates():
    a,b,c,d,e=[candidate(str(i),100-i) for i in range(5)]
    cache={(*genome_key(x),'settings'):{'feasible':False} for x in (a,b)}
    top,reasons=nominate([a,b,c,d,e],cache,('settings',),True)
    assert {x['id'] for x in top}=={'2','3','4'}
    assert a['known_audit_feasible'] is False
    assert len(reasons)==3


def test_cached_leader_and_two_new_tradeoffs():
    a=candidate('a',100,(8,8,8,8)); b=candidate('b',99);c=candidate('c',98)
    d=candidate('d',40,(10,1,1,1));e=candidate('e',39,(1,10,1,1))
    cache={(*genome_key(x),):{'feasible':True} for x in (a,b,c)}
    top,reasons=nominate([a,b,c,d,e],cache,(),True)
    assert top[0] is a and {x['id'] for x in top[1:]}=={'d','e'}
    assert reasons['d']=='new_eligible_pareto'


def test_duplicates_and_short_population():
    a=candidate('a',50,gene=1);b=candidate('b',50,gene=1);c=candidate('c',40,gene=2)
    top,reasons=nominate([a,b,c],{},(),True)
    assert len(top)==2 and len({genome_key(x) for x in top})==2
    assert top==nominate([c,b,a],{},(),True)[0]


def test_infeasible_fallback_prefers_fresh_and_valid_numerics():
    a=candidate('a',14,feasible=False);b=candidate('b',12,feasible=False);c=candidate('c',10,feasible=False);d=candidate('d',100,(float('nan'),1,1,1))
    cache={genome_key(a):{'feasible':False}}
    top,_=nominate([a,b,c,d],cache,(),True)
    assert [x['id'] for x in top]==['b','c','a']
