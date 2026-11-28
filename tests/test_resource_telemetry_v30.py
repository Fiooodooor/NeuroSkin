import pytest
from resource_telemetry import cpu_equivalents,ProcessTreeSampler
from hardware_profile import _parse_gpu_line


def test_matched_process_time_not_reservation():
    old={(1,1.):10.,(2,2.):5.,(3,3.):10.}
    new={(1,1.):11.,(2,2.):8.,(3,4.):99.}
    assert cpu_equivalents(old,new,2.)==2.
    assert cpu_equivalents(old,new,0.) is None


def test_missing_gpu_memory_does_not_crash():
    assert _parse_gpu_line('NVIDIA Quadro P1000, N/A, N/A, 538.0, 6.1') is None


def test_sampler_first_observation():
    r=ProcessTreeSampler().snapshot()
    if not r['available']:pytest.skip(r['reason'])
    assert r['process_count']>=1 and r['rss_sum_mib']>0
    assert r['logical_cpu_equivalents_lower_estimate'] is None
