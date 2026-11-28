import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from archive_store import ArchiveStore, ArchiveError


def test_numerical_identity_includes_all_declared_sources(tmp_path):
    from provenance import NUMERICAL_SOURCES, numerical_source_hash
    from advanced import engine_provenance
    from evaluation_v30 import solver_source_hash
    assert {'physical_fem.py', 'engine.py', 'gpu_sparse_fem.py', 'relaxed_membrane.py'} <= set(NUMERICAL_SOURCES)
    for name in NUMERICAL_SOURCES:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'original')
    baseline = numerical_source_hash(tmp_path)
    for name in NUMERICAL_SOURCES:
        p = tmp_path / name
        p.write_bytes(b'changed')
        assert numerical_source_hash(tmp_path) != baseline, name
        p.write_bytes(b'original')
    assert engine_provenance()['sha256'] == solver_source_hash()


def test_collection_does_not_launch_smoke_engine(monkeypatch):
    import advanced
    monkeypatch.setattr(advanced.EvolutionEngine, 'start', lambda *a, **kw: pytest.fail('Import started evolution'))
    import smoke_test
    importlib.reload(smoke_test)


def test_curated_single_stage_seeds_never_inherit_random_hybrids():
    import random
    from seed_library import SEEDS, seed_genome
    for seed in SEEDS:
        for number in (42, 123, 10007):
            for mutate in (False, True):
                genome = seed_genome(seed, random.Random(number), mutate=mutate)
                assert genome['hybrid_id'] == 'none', (seed.id, number)
                assert genome['topology'] == seed.id


def test_expired_budget_does_not_admit_second_generation(tmp_path, monkeypatch):
    import advanced
    now = [0.0]
    audits = []
    monkeypatch.setattr(advanced, 'time', SimpleNamespace(monotonic=lambda: now[0], sleep=lambda seconds: None))
    def audit(job):
        audits.append(job)
        now[0] = 10.0
        return {'audit_score': 1.0, 'feasible': False}
    monkeypatch.setattr(advanced, 'audit_job', audit)
    engine = advanced.EvolutionEngine(tmp_path)
    try:
        engine.start('quadrant', 3, 42, 12, audit_grid=3, fem=False)
        engine.thread.join(timeout=30)
        state = engine.snapshot()
        assert state['status'] == 'completed', state.get('error')
        assert state['generation'] == 1
        assert state['evaluated'] == 12
        assert len(audits) <= 3
        assert ArchiveStore(tmp_path).load(state['id'])['status'] == 'completed'
    finally:
        assert engine.shutdown(5)


@pytest.fixture
def archives(tmp_path, monkeypatch):
    import server
    store = ArchiveStore(tmp_path / 'runs')
    monkeypatch.setattr(server, 'ARCHIVES', store)
    def save(run_id):
        report = {'schema_version': 'neuroskin.validation_report.v1', 'candidate_id': 'c',
                  'family': 'quadrant', 'protocol_hash': 'protocol', 'genome_hash': 'genome',
                  'tier': 'T0', 'source': 'synthetic_surrogate',
                  'evidence': {'solver': 'surrogate', 'solver_hash': 'solver', 'material_hash': 'material',
                               'seed': 0, 'noise_provenance': 'assumed', 'evaluation_settings_hash': 'settings'},
                  'tests': [{'id': key, 'status': 'pass', 'source': 'synthetic_surrogate'} for key in
                            ('contact_load', 'no_contact', 'independent_holdout', 'sensor_covariance',
                             'geometry_screen', 'observability', 'robustness_completion')], 'metrics': {}}
        champion = {'id': 'c', 'family': 'quadrant', 'audit': {'audit_score': 20, 'validation_v30': report}}
        state = {'id': run_id, 'history': [], 'best': champion, 'audited_champion': champion,
                 'objective': 'balanced', 'audit_grid': 3, 'fem_enabled': False,
                 'fem_backend': 'hex8', 'fem_pitch_mm': .625, 'provenance': {'sha256': 'source'}}
        folder = store.path(run_id)
        folder.mkdir()
        (folder / 'results.json').write_text(json.dumps(state), encoding='utf-8')
        return state
    return store, save, TestClient(server.app, raise_server_exceptions=False)


@pytest.mark.parametrize('field,value', [('solver_hash', 'other'), ('seed', 2), ('evaluation_settings_hash', 'other')])
def test_archive_comparison_rejects_different_experiments(archives, field, value):
    store, save, client = archives
    save('left')
    state = save('right')
    assert client.get('/api/archives/compare?left=left&right=right').json()['comparable']
    state['best']['audit']['validation_v30']['evidence'][field] = value
    (store.path('right') / 'results.json').write_text(json.dumps(state), encoding='utf-8')
    result = client.get('/api/archives/compare?left=left&right=right').json()
    assert not result['comparable']
    assert result['score_delta_right_minus_left'] is None


def test_final_and_selected_stage_audits_and_expected_export_errors(archives):
    store, save, client = archives
    state = save('saved')
    assert client.get('/api/archives/saved/audit').status_code == 200
    stages = store.path('saved') / 'stages'
    stages.mkdir()
    champion = {'id': 'stage-candidate', 'audit': {'audit_score': 3}}
    (stages / 'stage_000001.json').write_text(json.dumps({'run_id': 'saved', 'generation': 1,
                                                       'champion': champion, 'decision': {}}), encoding='utf-8')
    response = client.get('/api/archives/saved/audit?generation=1')
    assert response.status_code == 200
    assert response.json()['champion']['id'] == 'stage-candidate'
    for kind in ('json', 'csv', 'genome', 'stl'):
        assert client.get('/api/export/' + kind + '?run_id=missing').status_code == 404
        assert client.get('/api/export/' + kind, params={'run_id': '../outside'}).status_code == 422
    assert client.get('/api/archives/saved/download').status_code == 200


def test_archive_refuses_external_file_and_stage_links(tmp_path):
    store = ArchiveStore(tmp_path / 'runs')
    folder = store.path('linked')
    folder.mkdir()
    outside = tmp_path / 'outside.json'
    outside.write_text('{"id":"linked","history":[]}', encoding='utf-8')
    try:
        (folder / 'results.json').symlink_to(outside)
    except OSError:
        pytest.skip('Host does not permit symbolic links')
    with pytest.raises(ArchiveError):
        store.load('linked')
    other = store.path('staged')
    other.mkdir()
    (other / 'stages').symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ArchiveError):
        store.list_stages('staged')
