from concurrent.futures import ThreadPoolExecutor
import threading
import pytest
import manual_evaluation as m


def test_budget_respects_cpu_ram_gpu():
    p=m.plan_manual(40,100000,True,'hex8',.3125,'cpu',True)
    assert p.surrogate_processes==3 and p.fem_case_workers==8
    assert p.surrogate_processes+p.fem_case_workers+p.matvec_workers<=40 and p.matvec_workers>0
    assert m.plan_manual(40,100000,True,'hex8',.3125,'gpu',True).fem_case_workers==1
    assert m.plan_manual(40,None,True,'hex8',.3125,'cpu',True).surrogate_processes==0
    assert m.plan_manual(1,100000,True,'hex8',.3125,'cpu',True).fem_case_workers==1
    assert m.plan_manual(40,1000,True,'hex8',.3125,'cpu',True).surrogate_processes==0


def test_parallel_dag_overlaps_and_returns_input_results(monkeypatch):
    entered=threading.Event();release=threading.Event();updates=[]
    def surrogate(name,*args):
        if name=='audit':
            entered.set();assert release.wait(5)
        return name
    monkeypatch.setattr(m,'surrogate_stage',surrogate)
    def fem(phase):
        assert entered.wait(5);phase({'phase':'test_case'});release.set();return 'fem'
    p=m.plan_manual(8,100000,True,'hex8',.3125,'cpu',True)
    r=m.run_manual('crown',{},dict(hybrid=True,fem_enabled=True),p,fem,updates.append,executor_factory=ThreadPoolExecutor)
    assert [r[k] for k in ('audit','validation','orientation','fem')]==['audit','validation','orientation','fem']
    assert all(v['state']=='completed' for v in r['telemetry']['stages'].values())
    assert any(v['stages']['fem']['state']=='running' for v in updates)


@pytest.mark.parametrize('fem,status,convergence',[(None,'not_run',False),({'feasible_linear':False},'fail',False),({'feasible_linear':True},'not_run',False),({'feasible_linear':True,'mesh_convergence_verified':True},'pass',True)])
def test_fem_evidence_attach_preserves_t0(fem,status,convergence):
    r={'evidence':{'solver':'six_dof_composite_surrogate'},'tests':[{'id':'continuum_fem','status':'not_run'},{'id':'mesh_convergence','status':'not_run'}],'metrics':{},'pass_current_tier':True}
    out=m.attach_fem_evidence(r,fem)
    assert out['tests'][0]['status']==status and out['evidence']['mesh_convergence_verified']==convergence and out['pass_current_tier']


def test_spawn_parallel_and_serial_same_numerical_decision():
    from hybrid_library import ranked,genome_for
    spec=ranked()[0];g=genome_for(spec)
    opts=dict(hybrid=True,fem_enabled=False,objective='balanced',audit_grid=3,candidate_id='spawn-test',inspector_force=.1)
    serial=m.run_manual(spec.upper_family,g,opts,m.plan_manual(1,20000,False,'hex8',1.25,'cpu',True),lambda:None,lambda x:None)
    parallel=m.run_manual(spec.upper_family,g,opts,m.plan_manual(3,20000,False,'hex8',1.25,'cpu',True),lambda:None,lambda x:None)
    assert parallel['telemetry']['plan']['surrogate_processes']==2
    assert parallel['audit']['audit_score']==serial['audit']['audit_score']
    assert parallel['validation']['tests']==serial['validation']['tests']
    assert parallel['validation']['metrics']==serial['validation']['metrics']
    assert parallel['orientation']==serial['orientation']
