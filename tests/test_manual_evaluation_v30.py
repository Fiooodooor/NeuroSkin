from concurrent.futures import ThreadPoolExecutor
import threading
import pytest
import manual_evaluation as m


def test_budget_respects_cpu_ram_gpu():
    p=m.plan_manual(40,100000,True,'hex8',.3125,'cpu',True)
    assert p.surrogate_processes==3 and p.fem_case_workers==8
    assert p.surrogate_processes+p.fem_case_workers<=40
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
    def fem():
        assert entered.wait(5);release.set();return 'fem'
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
