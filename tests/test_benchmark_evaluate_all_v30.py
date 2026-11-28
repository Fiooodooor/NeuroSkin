from copy import deepcopy
import pytest
from benchmark_evaluate_all import numerical_signature,compare


def sample():
    cases={str(i):dict(energy_Nmm=.2,mean_down_mm=.01,max_abs_principal_strain=.02,
                       force_equilibrium_relative=1e-7,moment_equilibrium_relative=1e-7) for i in range(8)}
    return dict(candidate_id='seed-test',family='crown',audit=dict(feasible=True,audit_score=70),
                validation_v30=dict(protocol_hash='test',pass_current_tier=True),
                fem=dict(fem_backend='hex8',fem_linear_solver='matrix_free',mesh_pitch_mm=.3125,
                         nodes=200,elements=100,feasible_linear=True,geometry_fidelity_pass=True,
                         pressure_valid=True,fem_score=70,load_cases=cases))


def test_reject_failed_and_changed_qualification():
    a=sample();s=numerical_signature(a)
    b=deepcopy(a);b['fem']['load_cases']['0']['energy_Nmm']+=1e-9
    assert compare(s,numerical_signature(b))
    b['fem']['feasible_linear']=False
    assert not compare(s,numerical_signature(b))
    b['fem']=None
    with pytest.raises(ValueError):numerical_signature(b)


def test_reject_changed_mesh_or_response():
    a=sample();s=numerical_signature(a)
    a['fem']['nodes']+=1
    assert not compare(s,numerical_signature(a))
    a=sample();a['fem']['load_cases']['0']['energy_Nmm']*=2
    assert not compare(s,numerical_signature(a))
