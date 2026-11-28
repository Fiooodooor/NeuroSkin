"""Read-only, bounded and path-safe access to persisted NeuroSkin runs.

Archive files are data, never executable code. The archive schema intentionally
uses the existing results.json format; old v1.0 runs remain readable.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

RUN_ID = re.compile(r'^[A-Za-z0-9_-]{1,48}$')
MAX_STATE_BYTES = 100 * 1024 * 1024

class ArchiveError(ValueError):
    pass

class ArchiveStore:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, run_id: str) -> Path:
        if not RUN_ID.fullmatch(run_id):
            raise ArchiveError('Invalid run identifier')
        path = (self.root / run_id).resolve()
        if path.parent != self.root:
            raise ArchiveError('Invalid run directory')
        return path

    def resolve_file(self, run_id: str, relative_name: str, max_bytes: int = MAX_STATE_BYTES) -> Path:
        relative = Path(relative_name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ArchiveError('Invalid archive file path')
        folder = self.path(run_id)
        target = folder / relative
        resolved = target.resolve()
        if not resolved.is_relative_to(folder) or target.is_symlink():
            raise ArchiveError('Archive file escapes its run directory or is a symbolic link')
        if not resolved.is_file():
            raise FileNotFoundError(relative_name)
        if resolved.stat().st_size > max_bytes:
            raise ArchiveError('Archive file exceeds size limit')
        return resolved

    def load(self, run_id: str) -> dict[str, Any]:
        filename = self.resolve_file(run_id, 'results.json')
        if not filename.is_file():
            raise FileNotFoundError(run_id)
        if filename.stat().st_size > MAX_STATE_BYTES:
            raise ArchiveError('Archive exceeds size limit')
        with filename.open('r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict) or data.get('id') != run_id:
            raise ArchiveError('Archive ID does not match directory')
        if not isinstance(data.get('history'), list):
            raise ArchiveError('Invalid archive: history is missing')
        return data

    def list_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        results = []
        if not (1 <= limit <= 500):
            raise ArchiveError('Limit out of range')
        for path in self.root.iterdir():
            if not path.is_dir() or not RUN_ID.fullmatch(path.name) or path.is_symlink():
                continue
            f = path / 'results.json'
            if not f.is_file():
                continue
            try:
                state = self.load(path.name)
                incumbent = state.get('audited_champion') or state.get('best') or {}
                audit = incumbent.get('audit') or {}
                results.append({
                    'id':path.name,
                    'status':state.get('status', 'unknown'),
                    'generation':int(state.get('generation') or 0),
                    'evaluated':int(state.get('evaluated') or 0),
                    'seconds':round(float(state.get('elapsed') or 0), 2),
                    'seed':state.get('seed'),
                    'objective':state.get('objective'),
                    'family':incumbent.get('family'),
                    'champion_id':incumbent.get('id'),
                    'audit_score':audit.get('audit_score'),
                    'fitness':incumbent.get('fitness'),
                    'modified_utc':f.stat().st_mtime,
                })
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
                # Partial writes or old/unrecognized archives must never break the GUI.
                continue
        results.sort(key=lambda r:r['modified_utc'], reverse=True)
        return results[:limit]

    @staticmethod
    def lookup(state: dict[str, Any], kind: str, index: str | int, family: str = 'crown'):
        if kind == 'best':
            return state.get('best') or state.get('audited_champion')
        if kind == 'family':
            return (state.get('champions') or {}).get(family)
        if kind == 'gallery':
            try:
                idx = int(index)
                gallery = state.get('gallery') or []
                return gallery[idx] if 0 <= idx < len(gallery) else None
            except (ValueError, TypeError):
                return None
        if kind == 'id':
            values = ([state.get('best'), state.get('audited_champion')]
                      + list((state.get('champions') or {}).values())
                      + list(state.get('gallery') or [])
                      + list(state.get('audit_top3') or []))
            return next((c for c in values if c and str(c.get('id')) == str(index)), None)
        return None

    def list_stages(self, run_id: str, limit: int = 5000) -> list[dict[str, Any]]:
        folder = self.path(run_id) / 'stages'
        if not folder.resolve().is_relative_to(self.path(run_id)):
            raise ArchiveError('Stage directory escapes its run directory')
        if not folder.exists():
            return []
        if not (1 <= limit <= 10000):
            raise ArchiveError('Stage limit out of range')
        result=[]
        for path in sorted(folder.glob('stage_*.json'))[-limit:]:
            if not re.fullmatch(r'stage_\d{6}\.json',path.name) or path.is_symlink():
                continue
            try:
                path = self.resolve_file(run_id, 'stages/' + path.name, 16*1024*1024)
                with path.open(encoding='utf-8') as f:record=json.load(f)
                c=record.get('champion') or {}
                result.append({'generation':record['generation'],
                               'elapsed':record.get('elapsed'),
                               'champion_id':c.get('id'),
                               'score':(c.get('audit') or {}).get('audit_score'),
                               'feasible':(c.get('audit') or {}).get('feasible')})
            except (OSError,ValueError,KeyError,TypeError):
                continue
        return result

    def load_stage(self, run_id: str, generation: int) -> dict[str, Any]:
        if not (1 <= generation <= 999999):
            raise ArchiveError('Generation outside supported range')
        path=self.resolve_file(run_id, f'stages/stage_{generation:06d}.json', 16*1024*1024)
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f'Stage {generation} not found')
        if path.stat().st_size > 16*1024*1024:
            raise ArchiveError('Stage exceeds safe size')
        with path.open(encoding='utf-8') as f:record=json.load(f)
        if not isinstance(record,dict) or record.get('run_id')!=run_id or record.get('generation')!=generation:
            raise ArchiveError('Stage content does not match identifier')
        return record
