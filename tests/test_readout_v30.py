from dataclasses import replace
from copy import deepcopy
import pytest
from electronics_budget import ElectronicsAssumptions,estimate_budget,budget_for_response
from validation_contract import candidate_comparable
from hybrid_library import ranked,genome_for
from electromechanics import examine


def test_packet_and_adc_budget_scale_with_channel_count():
    a=ElectronicsAssumptions(channels=8)
    r=estimate_budget(a)
    assert r['packet_bytes']==18 and r['link_throughput_bytes_s']==9000
    assert r['adc_capacity_pass']
    assert not estimate_budget(replace(a,channels=64))['adc_capacity_pass']
    assert estimate_budget(replace(a,channels=64,parallel_adcs=8))['adc_capacity_pass']
    with pytest.raises(ValueError):estimate_budget(replace(a,transmission_bytes_per_sample=16))
    with pytest.raises(ValueError):estimate_budget(replace(a,mcu_duty_cycle=1.1))
    with pytest.raises(ValueError):estimate_budget(replace(a,afe_power_mW_per_channel=float('nan')))


def test_candidate_wiring_and_stage_channels_change_budget():
    s=ranked()[0];g=genome_for(s)
    g.update(piezo_count=4,piezo_wiring=0,hybrid_sensor_mode=0)
    r=budget_for_response(examine(s.upper_family,g))
    assert r['channel_count']==13 and r['pvdf_output_count']==4 and r['stage_output_count']==2
    g.update(piezo_wiring=1,hybrid_sensor_mode=2)
    b=budget_for_response(examine(s.upper_family,g))
    assert b['channel_count']==9 and b['pvdf_output_count']==1 and b['stage_output_count']==1
    assert b['link_throughput_bytes_s']<r['link_throughput_bytes_s']
    assert b['pvdf_capacitance_per_output_pF_assumed'][0]==pytest.approx(sum(r['pvdf_capacitance_per_output_pF_assumed']))


def test_comparability_requires_same_solver_and_seed():
    a={'protocol_hash':'a','tier':'T0','evidence':{'solver_hash':'b','seed':42,'noise_provenance':'assumed','mesh_convergence_verified':False}}
    assert candidate_comparable(a,deepcopy(a))[0]
    for field in ('solver_hash','seed'):
        b=deepcopy(a);b['evidence'][field]='different'
        assert candidate_comparable(a,b)==(False,'different_'+field)
    b=deepcopy(a);del b['evidence']['solver_hash']
    assert candidate_comparable(a,b)==(False,'missing_solver_hash')
