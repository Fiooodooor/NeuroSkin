"""Persistent, run-final champions. Screening and per-generation saves never enroll."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
import tempfile

from archive_store import RUN_ID, MAX_STATE_BYTES
from validation_contract import digest


class UserBests:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id):
        if not RUN_ID.fullmatch(run_id):
            raise ValueError('Invalid user-best run identifier')
        path = self.root / (run_id + '.json')
        if path.is_symlink() or path.resolve().parent != self.root:
            raise ValueError('User-best file escapes its library')
        return path

    def capture(self, state):
        if state.get('status') not in ('completed', 'stopped'):
            return None
        candidate = state.get('audited_champion') or state.get('best') or {}
        score = (candidate.get('audit') or {}).get('audit_score')
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 90 < score <= 100:
            return None
        path = self._path(state['id'])
        # A run has one immutable library slot, including repeated terminal saves.
        if path.exists():
            return self.get(state['id'])
        entry = {
            'schema': 1, 'category': 'user_bests', 'id': 'user-best-' + state['id'],
            'run_id': state['id'], 'run_status': state['status'],
            'saved_at': datetime.now(timezone.utc).isoformat(),
            'score': score, 'score_type': 'full_audit_score',
            'candidate': deepcopy(candidate),
            'genome_hash': digest({'family': candidate['family'], 'genome': candidate['genome']}),
            'run_context': {key: deepcopy(state.get(key)) for key in (
                'seed', 'mode', 'objective', 'generation', 'provenance',
                'physical_gate', 'gate_grid', 'audit_grid', 'fem_enabled', 'fem_pitch_mm', 'fem_backend',
                'lineage', 'run_settings', 'population', 'exploration')},
        }
        payload = json.dumps(entry, indent=2, allow_nan=False)
        if len(payload.encode('utf-8')) > MAX_STATE_BYTES:
            raise ValueError('User-best entry exceeds size limit')
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.root, suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return entry

    def get(self, run_id):
        path = self._path(run_id)
        if path.stat().st_size > MAX_STATE_BYTES:
            raise ValueError('User-best entry exceeds size limit')
        entry = json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(entry, dict) or entry.get('schema') != 1 or entry.get('run_id') != run_id
                or entry.get('category') != 'user_bests' or entry.get('id') != 'user-best-' + run_id):
            raise ValueError('Invalid user-best entry')
        candidate = entry['candidate']
        score = entry.get('score')
        if (isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score)
                or not 90 < score <= 100 or score != candidate['audit'].get('audit_score')
                or entry.get('run_status') not in ('completed', 'stopped')):
            raise ValueError('Invalid user-best final score or run status')
        if entry['genome_hash'] != digest({'family': candidate['family'], 'genome': candidate['genome']}):
            raise ValueError('User-best geometry identity mismatch')
        return entry

    def list_entries(self):
        entries = []
        paths = sorted((p for p in self.root.glob('*.json') if not p.is_symlink()),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        for path in paths:
            try:
                entry = self.get(path.stem)
                candidate = entry['candidate']
                summary = {key: entry[key] for key in (
                    'id', 'run_id', 'run_status', 'saved_at', 'score', 'score_type', 'genome_hash', 'run_context')}
                summary.update(family=candidate['family'], candidate_id=candidate['id'],
                               generation=candidate.get('generation'), topology=candidate['genome'].get('topology'),
                               feasible=bool(candidate['audit'].get('feasible')))
                entries.append(summary)
            except (OSError, ValueError, KeyError, TypeError):
                logging.getLogger(__name__).warning('Skipping unreadable user-best entry %s', path.name)
        return entries

    def candidate(self, run_id):
        entry = self.get(run_id)
        candidate = deepcopy(entry['candidate'])
        candidate.update(id=entry['id'], origin='user_bests', source_run_id=run_id,
                         source_candidate_id=candidate['id'], library_genome_hash=entry['genome_hash'])
        return candidate
