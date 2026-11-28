from copy import deepcopy
import json
import random
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from advanced import EvolutionEngine, new_genome
from archive_store import ArchiveStore
from evolution_continuation import load_source, initialize, save_population
from search_space import SearchScope
from server import Start


def source_run(tmp_path, *, checkpoint=False):
    store = ArchiveStore(tmp_path/'runs')
    scope = SearchScope.parse('single:all')
    genome = scope.repair('quadrant', new_genome('quadrant', random.Random(32)), random.Random(32))
    candidate = {'id': 'old-12', 'family': 'quadrant', 'genome': genome,
                 'generation': 12, 'fitness': 98., 'audit': {'feasible': True, 'audit_score': 97.}}
    settings = Start(mode='single:all', seconds=3, population=12, seed=32, cores=1, audit_grid=3,
                     fem_enabled=False, exploration=.25).model_dump()
    state = EvolutionEngine.empty(None)
    state.update(id='parent', status='completed', generation=40, duration=3., seed=32, run_settings=settings,
                 best=candidate, audited_champion=candidate, gallery=[candidate], provenance={'sha256': 'historical'})
    folder = store.path('parent');folder.mkdir()
    (folder/'results.json').write_text(json.dumps(state), encoding='utf-8')
    stage = {'run_id': 'parent', 'generation': 25, 'champion': candidate, 'top3': [candidate], 'run_settings': settings}
    (folder/'stages').mkdir()
    (folder/'stages/stage_000025.json').write_text(json.dumps(stage), encoding='utf-8')
    if checkpoint:
        population = [('quadrant', scope.repair('quadrant', new_genome('quadrant', random.Random(i)), random.Random(i))) for i in range(12)]
        save_population(store.root, 'parent', 40, population, random.Random(99), settings, state['provenance'])
    return store, candidate, settings


@pytest.mark.parametrize('checkpoint', [False, True])
def test_saved_elites_and_population_are_not_mutated(tmp_path, checkpoint):
    store, best, settings = source_run(tmp_path, checkpoint=checkpoint)
    before = {str(p): p.read_bytes() for p in store.root.rglob('*.json')}
    source = load_source(store, 'parent', None, Start().model_dump())
    assert source['metadata']['parent_generation'] == 40
    assert source['metadata']['source_kind'] == ('population_checkpoint' if checkpoint else 'saved_elites')
    pop, lineage = initialize(source, SearchScope.parse('single:all'), 12, random.Random(32), settings)
    assert len(pop) == 12 and pop[0] == ('quadrant', best['genome'])
    assert all(SearchScope.parse('single:all').accepts(f, g) for f, g in pop)
    assert lineage['random_state_restored'] is checkpoint
    pop[0][1]['height'] = -1
    assert {str(p): p.read_bytes() for p in store.root.rglob('*.json')} == before
    assert load_source(store, 'parent', 25, Start().model_dump())['metadata']['parent_generation'] == 25


def test_legacy_missing_controls_are_explicit_and_incompatible_scope_fails(tmp_path):
    store, _, settings = source_run(tmp_path)
    path = store.path('parent')/'results.json'
    state = json.loads(path.read_text(encoding='utf-8'));state.pop('run_settings')
    path.write_text(json.dumps(state), encoding='utf-8')
    source = load_source(store, 'parent', None, Start().model_dump())
    assert any('population' in warning and 'exploration' in warning for warning in source['metadata']['warnings'])
    with pytest.raises(ValueError, match='compatible scope'):
        initialize(source, SearchScope.parse('chiral'), 12, random.Random(32), settings)


def test_checkpoint_corruption_is_rejected(tmp_path):
    store, _, _ = source_run(tmp_path, checkpoint=True)
    path = store.path('parent')/'stages/population_000040.json'
    checkpoint = json.loads(path.read_text(encoding='utf-8'))
    checkpoint['next_population'][0]['genome']['height'] += 1
    path.write_text(json.dumps(checkpoint), encoding='utf-8')
    with pytest.raises(ValueError, match='checksum'):
        load_source(store, 'parent', None, Start().model_dump())


def test_real_branch_uses_generation_boundary_and_fresh_audits(tmp_path, monkeypatch):
    import advanced
    store, best, settings = source_run(tmp_path)
    source = load_source(store, 'parent', None, Start().model_dump())
    original = (store.path('parent')/'results.json').read_bytes()
    engine = EvolutionEngine(store.root)
    clock = {'now': 0.}
    monkeypatch.setattr(advanced, 'time', SimpleNamespace(monotonic=lambda: clock['now'], sleep=lambda _: None))
    seen = []
    original_evaluate = advanced.evaluate_job
    def evaluate(job):
        seen.append(deepcopy(job))
        return original_evaluate(job)
    monkeypatch.setattr(advanced, 'evaluate_job', evaluate)
    monkeypatch.setattr(advanced, 'run_audit_batch', lambda pool, fn, jobs, plan, **kw:
                        [{'audit_score': 20., 'feasible': False} for _ in jobs])
    stage = engine._save_stage
    def save(*args):
        stage(*args)
        clock['now'] = 4.
    monkeypatch.setattr(engine, '_save_stage', save)
    progress = []
    original_write = engine._write_result
    def write(state):
        original_write(state)
        if state['status'] == 'running':
            recovered = load_source(store, state['id'], None, Start().model_dump())
            progress.append(recovered['metadata'])
    monkeypatch.setattr(engine, '_write_result', write)
    try:
        engine.start('single:all', 3, 32, 12, .65, objective='touch', cores=1, audit_grid=3, fem=False,
                     continuation=source)
        engine.thread.join(timeout=30)
        result = engine.snapshot()
        assert result['status'] == 'completed', result.get('error')
        assert progress and progress[0]['parent_generation'] == 41
        assert progress[0]['source_kind'] == 'population_checkpoint'
        assert result['generation'] == 41 and result['branch_generation'] == 1
        assert result['best']['generation'] == 41 and result['best']['id'].startswith('41-')
        assert result['best']['audit']['audit_score'] == 20.  # No stale 97-point champion retained.
        assert seen[0][1] == best['genome'] and seen[0][2] == 'touch'
        assert result['lineage']['settings_changes']['objective'] == {'from': 'balanced', 'to': 'touch'}
        assert result['run_settings']['population'] == 12 and result['exploration'] == .65
        assert (store.path('parent')/'results.json').read_bytes() == original
        assert not engine.user_bests.list_entries()
        stage = store.load_stage(result['id'], 41)
        assert stage['champion']['generation'] == stage['generation'] == 41
        next_source = load_source(store, result['id'], None, Start().model_dump())
        assert next_source['metadata']['source_kind'] == 'population_checkpoint'
        assert next_source['metadata']['settings']['objective'] == 'touch'
    finally:
        assert engine.shutdown(timeout=5.)


def test_api_settings_merge_source_guard_and_admission(tmp_path, monkeypatch):
    import server
    store, _, _ = source_run(tmp_path)
    engine = EvolutionEngine(store.root)
    monkeypatch.setattr(server, 'EVO', engine);monkeypatch.setattr(server, 'ARCHIVES', store)
    calls = []
    def start(*args, **kwargs):
        calls.append((args, kwargs))
        return {'id': 'new_branch', 'status': 'running'}
    monkeypatch.setattr(engine, 'start', start)
    with TestClient(server.app) as client:
        metadata = client.get('/api/archives/parent/continuation?generation=25').json()
        assert metadata['parent_generation'] == 25
        assert client.post('/api/archives/parent/continue', json={'generation': 25, 'source_digest': '0'*64}).status_code == 409
        assert not calls
        response = client.post('/api/archives/parent/continue', json={'generation': 25,
            'source_digest': metadata['source_digest'], 'objective': 'electronics', 'seconds': 5})
        assert response.status_code == 200, response.text
        args, kwargs = calls[0]
        assert args[1:5] == (5., 32, 12, .25) and args[5] == 'electronics'
        assert kwargs['continuation']['metadata']['parent_generation'] == 25
        assert client.post('/api/archives/parent/continue', json={'population': 2}).status_code == 422
        engine.thread = SimpleNamespace(is_alive=lambda: True)
        assert client.post('/api/archives/parent/continue', json={}).status_code == 409
        engine.thread = None
        assert client.get('/api/archives/missing/continuation').status_code == 404


def test_part_functions_match_single_and_hybrid_roles():
    from advanced import webmesh
    from hybrid_library import ranked, genome_for
    quadrant = webmesh('quadrant', new_genome('quadrant', random.Random(42)), 6)['component_tree']['nodes']
    hub = next(n for n in quadrant if n['part'] == 'inner')
    assert hub['label'] == 'Conceptual hub' and 'no dedicated sensor' in hub['function']
    assert all('placeholder' in n['function'] for n in quadrant if n['part'] == 'sensor')
    spec = ranked()[0]
    hybrid = webmesh(spec.upper_family, genome_for(spec), 6)['component_tree']['nodes']
    plate = next(n for n in hybrid if n['part'] == 'inner')
    assert plate['stage'] == 'interface' and 'coupling plate' in plate['function']
