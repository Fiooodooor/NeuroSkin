"""Regression and fail-closed acceptance checks for versioned validation."""
from __future__ import annotations

from copy import deepcopy
import csv
import json
from pathlib import Path
import random
import tempfile

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from advanced import new_genome, audit_job
from sensor_metrics import grouped_position_split, decoder_holdout, pareto_front
from validation_contract import (
    load_protocol, digest, candidate_comparable, ValidationReport,
    TestResult, Evidence,
)
from evaluation_v30 import evaluate_protocol, robust_screen
from measured_import import load_measured_csv, EXPECTED


def genome():
    return new_genome('quadrant', random.Random(42))


def test_contract_is_versioned_and_hash_stable():
    p=load_protocol()
    assert p.schema_version=='neuroskin.validation_protocol.v0.1'
    assert digest(p.model_dump()) == digest(load_protocol().model_dump())
    bad=p.model_dump();bad['dataset_splits']['test_fraction']=.4
    from validation_contract import Protocol
    with pytest.raises(ValidationError):Protocol.model_validate(bad)


def test_fail_closed_missing_and_invalid_report():
    seed=Evidence(solver='surrogate',solver_hash='a'*64,material_hash='b'*64,
                  seed=42,noise_provenance='assumed')
    def reqtests():
        return [TestResult(id=k,status='pass',source='synthetic_surrogate') for k in
                ('contact_load','no_contact','independent_holdout','sensor_covariance','geometry_screen')]
    valid=ValidationReport(candidate_id='x',family='quadrant',protocol_hash='p'*64,
         genome_hash='g'*64,evidence=seed,tier='T0',source='synthetic_surrogate',
         tests=reqtests(),metrics={},pass_current_tier=True,eligible_for_same_tier_promotion=True)
    assert valid.pass_current_tier
    with pytest.raises(ValidationError):ValidationReport.model_validate({**valid.model_dump(),
        'tests':[t.model_dump() for t in reqtests()[:-1]]})
    failed=valid.model_dump();failed['tests'][0]['status']='fail'
    with pytest.raises(ValidationError):ValidationReport.model_validate(failed)
    invalid=valid.model_dump();invalid['tier']='T3'
    with pytest.raises(ValidationError):ValidationReport.model_validate(invalid)
    invalid=valid.model_dump();invalid['tier']='T1'
    with pytest.raises(ValidationError):ValidationReport.model_validate(invalid)


def test_groups_are_disjoint():
    groups=[str(i//4) for i in range(72)]
    indices=grouped_position_split(groups,seed=12)
    sets=[{groups[i] for i in ind} for ind in indices]
    assert len(sets)==3
    assert not (sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])
    assert sum(map(len,indices))==72


def test_decoder_is_train_only_and_deterministic():
    rng=np.random.default_rng(42)
    X=rng.normal(size=(80,7));Y=np.zeros((80,5))
    Y[:,:3]=X[:,:3]*.04;Y[:,3:5]=X[:,3:5]*.6
    groups=[i//8 for i in range(80)]
    a=decoder_holdout(X,Y,groups,seed=123)
    assert a==decoder_holdout(X,Y,groups,seed=123)
    assert a['train_count']+a['validation_count']+a['test_count']==80
    assert a['independent_test_groups']>0
    assert a['source']=='synthetic_surrogate'


def test_protocol_runs_with_unmodeled_axes_explicitly_unsupported():
    r=evaluate_protocol('quadrant',genome(),candidate_id='example',seed=111,
                        monte_carlo_samples=4)
    assert r['tier']=='T0'
    assert r['source']=='synthetic_surrogate'
    assert r['protocol_hash']==digest(load_protocol().model_dump())
    assert r==evaluate_protocol('quadrant',genome(),candidate_id='example',seed=111,
                                monte_carlo_samples=4)
    assert r['metrics']['decoder_holdout']['test_count']>0
    statuses={t['id']:t['status'] for t in r['tests']}
    assert statuses['nonlinear_contact']=='unsupported'
    assert statuses['temperature_variation']=='unsupported'
    assert statuses['indenter_variation']=='unsupported'
    assert statuses['mesh_convergence']=='not_run'
    assert not r['evidence']['mesh_convergence_verified']
    assert r['evidence']['noise_provenance']=='assumed'
    assert r['metrics']['readout_budget']['cost_status'].startswith('unknown')


def test_monte_carlo_has_explicit_uncertainties():
    a=robust_screen('quadrant',genome(),seed=13,samples=6)
    assert a==robust_screen('quadrant',genome(),seed=13,samples=6)
    assert a['assumed_snr_p10']<=a['assumed_snr_p50']<=a['assumed_snr_p90']
    assert 'temperature' in a['unsupported_axes']


def test_pareto_front_not_single_fitness():
    points=[{'a':1.,'b':9},{'a':2.,'b':8},{'a':3.,'b':7},{'a':2.,'b':10}]
    chosen=pareto_front(points,{'a':'min','b':'max'})
    assert points[1] not in chosen
    assert points[0] in chosen and points[3] in chosen


def test_no_cross_tier_score_comparison():
    a={'protocol_hash':'a','tier':'T0','evidence':{'noise_provenance':'assumed','mesh_convergence_verified':False}}
    b=deepcopy(a);b['tier']='T1'
    assert candidate_comparable(a,b)[0] is False
    b=deepcopy(a);b['protocol_hash']='different'
    assert candidate_comparable(a,b)[0] is False


def test_measured_csv_validated_and_not_automatically_certified():
    with tempfile.TemporaryDirectory() as d:
        f=Path(d)/'data.csv'
        with f.open('w',newline='',encoding='utf-8') as o:
            w=csv.writer(o);w.writerow(EXPECTED)
            for i in range(30):
                x=i%10;fy=.01;fx=0;fz=-.05-.01*(i%4)
                w.writerow(['session1',f'position_{x}','sphere',fx,fy,fz,float(x),float(x)/4,
                            fz*.1,fx*.2,fy*.2,float(x)*.1,fx,fy,0.])
        out=load_measured_csv(f)
        assert 'T3_NOT_GRANTED' in out['qualification']
        assert out['input_file_sha256']
        assert out['position_group_count']==10
        with pytest.raises(ValueError):
            f.write_text('foo,bar\n1,2',encoding='utf-8')
            load_measured_csv(f)


def test_top3_audit_records_common_protocol():
    g=genome()
    a=audit_job(('quadrant',g,'balanced',3,False,1.25,'hex8'))
    r=a['validation_v30']
    assert r['tier']=='T0'
    assert r['protocol_hash']==digest(load_protocol().model_dump())
    assert 'validation_force_rmse_N' in a['decision_basis']
    assert not a['feasible'] or r['pass_current_tier']


def test_api_protocol_and_evaluate_all_without_fem(monkeypatch):
    import server
    fake={'id':'v22-api','family':'quadrant','genome':genome()}
    monkeypatch.setattr(server,'select_candidate',lambda *args,**kwargs:fake)
    cli=TestClient(server.app)
    r=cli.get('/api/validation/protocol')
    assert r.status_code==200
    assert r.json()['sha256']==digest(load_protocol().model_dump())
    response=cli.post('/api/evaluate_all',json={'fem_enabled':False,'audit_grid':3})
    assert response.status_code==200,response.text[:500]
    data=response.json()
    assert data['validation_v30']['tier']=='T0'
    assert data['audit']['validation_v30']['protocol_hash']==data['validation_v30']['protocol_hash']


def test_gui_includes_validation_panel():
    html=Path(__file__).parents[1].joinpath('static/index.html').read_text(encoding='utf-8')
    assert 'id="validationLive"' in html
    assert 'id="validationMetrics"' in html
    assert 'id="validationStatus"' in html


def test_invalid_geometry_returns_explicit_failed_report():
    from evaluation_v30 import safe_evaluate_protocol
    bad=genome();bad['material_E']=-20
    report=safe_evaluate_protocol('quadrant',bad,candidate_id='invalid',seed=111,
                                  monte_carlo_samples=4)
    assert not report['eligible_for_same_tier_promotion']
    assert not report['pass_current_tier']
    assert report['tier']=='T0'
    assert all(t['status']=='fail' for t in report['tests'][:5])


def test_fem_merger_same_result_regardless_of_inspection_fields():
    from full_evaluation import audit_candidate
    from audit_combine import merge_fem_into_audit
    base=audit_candidate('quadrant',genome(),grid_size=3)
    fem={'feasible_linear':True,'fem_score':65.0,'pressure_valid':True,
         'pvdf_stiffness_included':True,'pvdf_film_count':4,
         'pvdf_fraction_of_total_energy':.03,
         'load_cases':{'press_center':{'mean_down_mm':.08}},
         'max_abs_principal_strain':.015,
         'laminate_shell':{'failed':False,'shell_score':70.0,'feasible_shell_screen':True,
                           'max_eq_stress_MPa':7.0,'max_interfacial_shear_MPa':.6,
                           'max_top_fiber_strain_abs':.015}}
    one=merge_fem_into_audit(deepcopy(base),deepcopy(fem),'quadrant',genome())
    fem_inspection=deepcopy(fem)
    fem_inspection['fields']={'only_for_visualization':True}
    two=merge_fem_into_audit(deepcopy(base),fem_inspection,'quadrant',genome(),include_fields=True)
    assert one['audit_score']==two['audit_score']
    assert one['feasible']==two['feasible']
    assert one['decision_basis']['laminate_shell_score']==two['decision_basis']['laminate_shell_score']
