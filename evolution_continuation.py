"""Branch evolution from saved genomes; historical scores are never inherited."""
from copy import deepcopy
import json
import os

from validation_contract import digest

SETTINGS = ('mode', 'seconds', 'seed', 'population', 'exploration', 'objective',
            'physical_gate', 'gate_grid', 'cores', 'audit_grid', 'fem_enabled',
            'fem_pitch_mm', 'fem_backend', 'search_strategy', 'search_precision')


def _object(value, label):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(label+' must be a JSON object')
    return value


def _list(value, label):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(label+' must be a JSON array')
    return value


def load_source(store, run_id, generation, defaults):
    saved = store.load(run_id)
    stage = store.load_stage(run_id, generation) if generation is not None else None
    boundary = stage['generation'] if stage is not None else saved['generation']
    if type(boundary) is not int or not 0 <= boundary < 999999:
        raise ValueError('Source generation must be 0..999998')
    settings = dict(defaults)
    recorded = {**saved, 'seconds': saved.get('duration', defaults['seconds']),
                **_object(saved.get('run_settings'), 'Run settings'),
                **_object((stage or {}).get('run_settings'), 'Stage settings')}
    missing = [key for key in SETTINGS if recorded.get(key) is None]
    settings.update({key: recorded[key] for key in SETTINGS if recorded.get(key) is not None})
    warnings = []
    if missing:
        warnings.append('Old archive did not record '+', '.join(missing)+'. Defaults loaded; review before starting.')
    champion = (stage.get('champion') if stage is not None else saved.get('audited_champion') or saved.get('best'))
    champion = _object(champion, 'Saved champion')
    elites = ([champion] + (_list(stage.get('top3'), 'Stage finalists') if stage is not None else
              _list(saved.get('audit_top3'), 'Run finalists') + list(_object(saved.get('champions'), 'Family champions').values())
              + _list(saved.get('gallery'), 'Saved gallery')))
    checkpoint = None
    if boundary:
        try:
            path = store.resolve_file(run_id, f'stages/population_{boundary:06d}.json', 16*1024*1024)
        except FileNotFoundError:
            pass
        else:
            checkpoint = json.loads(path.read_text(encoding='utf-8'))
            if (not isinstance(checkpoint, dict) or checkpoint.get('schema') != 1
                    or checkpoint.get('run_id') != run_id or checkpoint.get('generation') != boundary
                    or not isinstance(checkpoint.get('next_population'), list)
                    or not 1 <= len(checkpoint['next_population']) <= 256):
                raise ValueError('Invalid population checkpoint identity or size')
            body = {key: value for key, value in checkpoint.items() if key != 'sha256'}
            if checkpoint.get('sha256') != digest(body):
                raise ValueError('Population checkpoint checksum mismatch')
    seeds = []
    if champion:
        seeds.append(champion)
    if checkpoint:
        seeds.extend(checkpoint['next_population'])
    seeds.extend(c for c in elites if c)
    unique = {}
    for candidate in seeds:
        candidate = _object(candidate, 'Saved candidate')
        if not isinstance(candidate.get('genome'), dict) or not isinstance(candidate.get('family'), str):
            raise ValueError('Saved source contains an invalid genome')
        key = digest({'family': candidate['family'], 'genome': candidate['genome']})
        unique.setdefault(key, {'family': candidate['family'], 'genome': deepcopy(candidate['genome'])})
    if not unique:
        raise ValueError('Saved source contains no candidate geometries')
    metadata = {'parent_run_id': run_id, 'parent_generation': boundary,
                'source_kind': 'population_checkpoint' if checkpoint else 'saved_elites',
                'source_candidate_id': (champion or {}).get('id'),
                'source_candidate_generation': champion.get('generation'),
                'source_genome_hash': digest({'family': champion['family'], 'genome': champion['genome']}) if champion else None,
                'source_score': _object(champion.get('audit'), 'Champion audit').get('audit_score'),
                'source_provenance': saved.get('provenance'),
                'seed_count': len(unique), 'settings': settings, 'warnings': warnings,
                'policy': 'New branch; fresh scoring and audits. Population/PRNG can be restored; novelty, QD and audit caches restart. Not exact process replay.'}
    metadata['source_digest'] = digest({'metadata': metadata, 'seeds': list(unique.values()),
                                        'checkpoint': checkpoint})
    return {'metadata': metadata, 'seeds': list(unique.values()),
            'rng_state': checkpoint.get('rng_state') if checkpoint else None}


def compatible_seeds(source, scope):
    from advanced import KINDS
    return [c for c in source['seeds'] if c['family'] in KINDS
                and c['genome'].get('topology') in KINDS[c['family']] and scope.accepts(c['family'], c['genome'])]


def random_state(value):
    """Validate JSON PRNG data without executing serialized Python objects."""
    import random
    def tuples(item):
        return tuple(tuples(v) for v in item) if isinstance(item, list) else item
    try:
        state = tuples(value)
        random.Random(0).setstate(state)
        return state
    except (TypeError, ValueError, OverflowError, IndexError) as exc:
        raise ValueError('Invalid saved random-generator state') from exc


def plan(source, scope, population, settings):
    eligible = compatible_seeds(source, scope)
    if not eligible:
        raise ValueError('No saved geometry fits the selected search scope; choose a compatible scope')
    restored = (source.get('rng_state') is not None and settings['seed'] is not None
                and settings['seed'] == source['metadata']['settings'].get('seed'))
    if restored:
        random_state(source['rng_state'])
    hashes = [digest(c) for c in eligible]
    lineage = {key: deepcopy(value) for key, value in source['metadata'].items() if key != 'settings'}
    lineage.update(eligible_seed_count=len(eligible), excluded_seed_count=len(source['seeds'])-len(eligible),
                   inherited_count=min(population, len(eligible)), random_state_restored=restored,
                   source_champion_eligible=source['metadata'].get('source_genome_hash') in hashes,
                   initial_audit_genome_hash=hashes[0], initial_audit_family=eligible[0]['family'],
                   settings_changes={key: {'from': source['metadata']['settings'].get(key), 'to': value}
                                     for key, value in settings.items() if value != source['metadata']['settings'].get(key)})
    return lineage


def initialize(source, scope, population, rng, settings):
    """Keep original compatible elites unchanged, then make diverse offspring."""
    from search_space import local_refinement
    lineage = plan(source, scope, population, settings)
    eligible = compatible_seeds(source, scope)
    if lineage['random_state_restored']:
        rng.setstate(random_state(source['rng_state']))
    pop = [(c['family'], deepcopy(c['genome'])) for c in eligible[:population]]
    while len(pop) < population:
        if rng.random() < .75:
            parent = rng.choice(eligible)
            family = parent['family']
            genome = local_refinement(family, parent['genome'], rng, precision=settings['search_precision'])
            pop.append((family, scope.repair(family, genome, rng)))
        else:
            pop.append(scope.generate(rng))
    return pop, lineage


def save_population(folder, run_id, generation, population, rng, settings, provenance):
    directory = folder/run_id/'stages'
    directory.mkdir(parents=True, exist_ok=True)
    document = {'schema': 1, 'run_id': run_id, 'generation': generation,
                'next_population': [{'family': f, 'genome': g} for f, g in population],
                'rng_state': rng.getstate(), 'run_settings': settings, 'provenance': provenance}
    document['sha256'] = digest(document)
    path = directory/f'population_{generation:06d}.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(document, allow_nan=False), encoding='utf-8')
    os.replace(temporary, path)
