from copy import deepcopy
import json
import random
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from advanced import EvolutionEngine, new_genome
from user_bests import UserBests


def run_state(score=94., status='completed', run_id='run_123'):
    candidate = {'id': '1-2', 'family': 'quadrant', 'generation': 1, 'fitness': 99.,
                 'genome': new_genome('quadrant', random.Random(42)),
                 'metrics': {}, 'audit': {'audit_score': score, 'feasible': True}}
    return {'id': run_id, 'status': status, 'seed': 42, 'objective': 'balanced', 'generation': 3,
            'history': [], 'provenance': {'sha256': 'original-source'},
            'best': deepcopy(candidate), 'audited_champion': candidate}


@pytest.mark.parametrize('score', [90, 89.9, None, True, float('nan'), float('inf'), 101])
def test_strict_audit_threshold_never_uses_proxy_score(tmp_path, score):
    store = UserBests(tmp_path)
    assert store.capture(run_state(score)) is None
    assert store.list_entries() == []


@pytest.mark.parametrize('status', ['running', 'paused', 'finalizing', 'failed'])
def test_nonterminal_or_failed_saves_do_not_enroll(tmp_path, status):
    store = UserBests(tmp_path)
    assert store.capture(run_state(status=status)) is None
    assert store.list_entries() == []


def test_only_final_champion_is_immutable_and_survives_restart(tmp_path):
    engine = EvolutionEngine(tmp_path)
    state = run_state(90.0001, status='running')
    # Intermediate and finalizing archives are ordinary saves, never enrollment.
    for status in ('running', 'finalizing'):
        state['status'] = status
        engine._write_result(state)
        assert not engine.user_bests.list_entries()
    state.update(status='completed', best=run_state(99.)['best'])
    engine._write_result(state)
    path = tmp_path/'user_bests/run_123.json'
    original = path.read_bytes()
    # Retries do not create extra entries or replace the original final audit.
    state['audited_champion']['audit']['audit_score'] = 96.
    engine._write_result(state)
    restarted = EvolutionEngine(tmp_path)
    assert path.read_bytes() == original
    assert len(restarted.user_bests.list_entries()) == 1
    entry = restarted.user_bests.get('run_123')
    assert entry['score'] == 90.0001
    assert entry['candidate']['audit']['audit_score'] == 90.0001
    assert entry['run_context']['provenance']['sha256'] == 'original-source'
    candidate = restarted.user_bests.candidate('run_123')
    assert candidate['source_candidate_id'] == '1-2' and candidate['id'] == 'user-best-run_123'
    candidate['genome']['height'] = -1
    assert restarted.user_bests.candidate('run_123')['genome'] != candidate['genome']
    assert not list(path.parent.glob('*.tmp'))


@pytest.mark.parametrize('terminal', ['completed', 'stopped'])
def test_controller_enrolls_once_after_two_generations(tmp_path, monkeypatch, terminal):
    import advanced
    engine = EvolutionEngine(tmp_path)
    batches = []
    # Advance only the controller's clock; two generations do not depend on CPU speed.
    clock = {'now': 0.}
    monkeypatch.setattr(advanced, 'time', SimpleNamespace(monotonic=lambda: clock['now'], sleep=lambda _: None))

    def audits(pool, fn, jobs, plan, **kwargs):
        batches.append(len(jobs))
        return [{'audit_score': 95. if len(batches) == 1 else 92., 'feasible': True} for _ in jobs]

    monkeypatch.setattr(advanced, 'run_audit_batch', audits)
    original_stage = engine._save_stage
    committed = []

    def stage(generation, elapsed, finalists, champion, decision):
        original_stage(generation, elapsed, finalists, champion, decision)
        committed.append(generation)
        assert engine.user_bests.list_entries() == []
        if generation == 2:
            if terminal == 'stopped':
                engine.stop()
            else:
                clock['now'] = 4.

    monkeypatch.setattr(engine, '_save_stage', stage)
    try:
        engine.start('single:all', 3, 21, 12, .5, cores=1, audit_grid=3, fem=False)
        engine.thread.join(timeout=20)
        assert not engine.thread.is_alive()
        state = engine.snapshot()
        assert state['status'] == terminal, state.get('error')
        assert committed == [1, 2]
        entries = engine.user_bests.list_entries()
        assert len(entries) == 1
        stored = engine.user_bests.get(state['id'])
        assert stored['score'] == 95.
        assert stored['candidate'] == state['audited_champion']
        assert stored['candidate']['generation'] == 1  # Earlier best, not the last iteration.
    finally:
        engine.shutdown(timeout=5.)


def test_corrupt_entries_and_traversal_are_rejected(tmp_path):
    store = UserBests(tmp_path)
    store.capture(run_state())
    path = tmp_path/'run_123.json'
    entry = json.loads(path.read_text(encoding='utf-8'))
    entry['candidate']['genome']['height'] = -5
    path.write_text(json.dumps(entry), encoding='utf-8')
    with pytest.raises(ValueError, match='identity'):
        store.get('run_123')
    (tmp_path/'broken.json').write_text('{broken', encoding='utf-8')
    assert not store.list_entries()
    for invalid in ('../secret', '/root', '..', 'a/b'):
        with pytest.raises(ValueError):
            store.get(invalid)


def test_user_best_can_be_previewed_evaluated_and_exported_without_source_run(tmp_path, monkeypatch):
    import server
    store = UserBests(tmp_path)
    state = run_state()
    store.capture(state)
    monkeypatch.setattr(server.EVO, 'user_bests', store)
    with TestClient(server.app) as client:
        library = client.get('/api/user_bests').json()
        assert library['threshold_exclusive'] == 90 and len(library['entries']) == 1
        candidate = client.get('/api/user_bests/run_123').json()
        assert candidate['genome'] == state['audited_champion']['genome']
        params = {'selection': 'user_best', 'index': 'run_123', 'family': 'quadrant',
                  'expected_candidate_id': 'user-best-run_123'}
        response = client.get('/api/mesh', params={**{k: v for k, v in params.items() if k != 'selection'}, 'kind': 'user_best', 'quality': 5})
        assert response.status_code == 200, response.text
        assert response.json()['candidate']['id'] == 'user-best-run_123'
        exported = client.get('/api/export/genome', params=params)
        assert exported.status_code == 200 and exported.json() == candidate['genome']
        evaluated = client.post('/api/evaluate_all', json={**params, 'audit_grid': 3, 'fem_enabled': False})
        assert evaluated.status_code == 200, evaluated.text
        assert evaluated.json()['candidate_id'] == 'user-best-run_123'
        assert store.get('run_123')['score'] == 94.
        assert client.get('/api/user_bests/missing').status_code == 404
