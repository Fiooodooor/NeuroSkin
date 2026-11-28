import pytest
from electronics_evolution import score_budgets
from population_pareto import rank_population,OBJECTIVES


def budget(peak,power=5,capacity=True):
    return dict(pvdf_output_peak_V_assumed=peak,pvdf_peak_headroom_V_assumed=1.65,
                adc_total_rms_noise_V_assumed=.001,power_estimated_mW=power,
                adc_capacity_pass=capacity,link_capacity_pass=True,channel_count=8)


def test_clipping_and_capacity_penalized_not_rewarded():
    good=score_budgets([budget([1.5])])
    clipped=score_budgets([budget([3.])])
    assert good['fitness_readout']>clipped['fitness_readout']
    assert clipped['readout_clipped_case_fraction_assumed']==1
    assert score_budgets([budget([1.5],power=10)])['fitness_readout']<good['fitness_readout']
    assert score_budgets([budget([1.5],capacity=False)])['fitness_readout']==0
    assert score_budgets([budget([0.])])['fitness_readout']<good['fitness_readout']


def test_readout_is_fifth_objective_only_for_new_preset():
    def item(id,s):
        return dict(id=id,fitness=50,metrics={**dict.fromkeys(OBJECTIVES,50),'fitness_preset':'electronics','fitness_readout':s})
    a,b=item('a',90),item('b',10)
    assert rank_population([a,b],False)==['a']
    del a['metrics']['fitness_readout']
    assert rank_population([a,b],False)==['b']


def test_real_candidate_electronics_preset():
    from hybrid_library import ranked,genome_for
    from optimization import evaluate
    spec=ranked()[0];g=genome_for(spec)
    a,metrics,_=evaluate(spec.upper_family,g,'electronics')
    assert a>=0,metrics.get('error')
    assert 0<=metrics['fitness_readout']<=100 and metrics['readout_case_count']==6
    assert metrics['readout_channel_count']>=8
    b,old,_=evaluate(spec.upper_family,g,'balanced')
    assert b>=0 and 'fitness_readout' not in old
