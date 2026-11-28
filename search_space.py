"""Authoritative, validated search scopes and geometry-aware mutation operators.

All scopes are used by GUI, server, CLI and evolutionary operators. This prevents
hybrid libraries from existing only as generation-zero showcase specimens.
No mutation is accepted on the basis of a heuristic alone; the normal screening
and identical Top-3 audit remain the source of evolutionary selection.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import random
from typing import Mapping

from engine import FAMILIES, LIMITS
from hybrid_library import SPECS, BY_ID, genome_for

HYBRID_IDS = tuple(s.id for s in SPECS) + ('procedural',)
SEARCH_STRATEGIES = ('adaptive', 'explore', 'precision')


def mode_options():
    options = [
        {'id': 'all', 'label': 'Everything · single + all 10 hybrids'},
        {'id': 'single:all', 'label': 'All single-stage geometries'},
        {'id': 'hybrid:all', 'label': 'All curated + procedural hybrids'},
        {'id': 'procedural:all', 'label': 'Procedural two-stage combinations · all families'},
    ]
    for family in FAMILIES:
        options.extend((
            {'id': family, 'label': f'{family.title()} · single + matching hybrids'},
            {'id': f'single:{family}', 'label': f'{family.title()} · single-stage only'},
            {'id': f'hybrid:{family}', 'label': f'{family.title()} · matching hybrid stages'},
            {'id': f'procedural:{family}', 'label': f'Procedural hybrid · {family.title()} upper stage'},
        ))
    options.extend({'id': 'hybrid:' + spec.id,
                    'label': f'Hybrid only · {spec.name}'} for spec in SPECS)
    return options

MODES = tuple(entry['id'] for entry in mode_options())


PROCEDURAL_TOPOLOGIES = {
    'crown': ('radial','arched','woven','branching','spiral'),
    'chiral': ('helical','counter','braided','staggered','double_helix'),
    'quadrant': ('orthogonal','serpentine','diagonal','crossed','kirigami','auxetic'),
}


def make_procedural_genome(family: str, rng: random.Random):
    if family not in FAMILIES:raise ValueError('Unknown upper-stage family')
    from advanced import new_genome
    g=new_genome(family,rng)
    lower=rng.choice(FAMILIES)
    g.update(hybrid_id='procedural',topology='hybrid',
             hybrid_upper_family=family,hybrid_lower_family=lower,
             hybrid_upper_topology=rng.choice(PROCEDURAL_TOPOLOGIES[family]),
             hybrid_lower_topology=rng.choice(PROCEDURAL_TOPOLOGIES[lower]),
             hybrid_opposed_chirality=rng.choice((0,1)),
             hybrid_phase=round(rng.uniform(-math.pi,math.pi),5),
             height=max(6.2,float(g['height'])))
    g['pad_offset_x']=0.;g['pad_offset_y']=0.
    return g


@dataclass(frozen=True)
class SearchScope:
    mode: str
    families: tuple[str, ...]
    allow_single: bool
    hybrid_ids: tuple[str, ...]

    @classmethod
    def parse(cls, mode: str) -> 'SearchScope':
        if mode not in MODES:
            raise ValueError(f'Unknown search scope: {mode}; available: {", ".join(MODES)}')
        if mode == 'all':
            return cls(mode, tuple(FAMILIES), True, HYBRID_IDS)
        if mode == 'single:all':
            return cls(mode, tuple(FAMILIES), True, ())
        if mode == 'hybrid:all':
            return cls(mode, tuple(FAMILIES), False, HYBRID_IDS)
        if mode in FAMILIES:
            return cls(mode, (mode,), True, tuple(s.id for s in SPECS if s.upper_family == mode))
        category, _, token = mode.partition(':')
        if category == 'single':
            return cls(mode, (token,), True, ())
        if category == 'hybrid' and token in FAMILIES:
            return cls(mode, (token,), False, tuple(s.id for s in SPECS if s.upper_family == token) + ('procedural',))
        if category == 'procedural' and token in ('all', *FAMILIES):
            return cls(mode, tuple(FAMILIES) if token=='all' else (token,), False, ('procedural',))
        if category == 'hybrid' and token in BY_ID:
            return cls(mode, (BY_ID[token].upper_family,), False, (token,))
        raise ValueError('Unreachable search scope')

    def accepts(self, family: str, genome: Mapping) -> bool:
        if family not in self.families:
            return False
        hybrid = genome.get('hybrid_id', 'none')
        if hybrid in ('none', '', None):
            return self.allow_single and genome.get('topology') != 'hybrid'
        if hybrid == 'procedural':
            low = genome.get('hybrid_lower_family')
            return (hybrid in self.hybrid_ids and genome.get('topology')=='hybrid'
                    and genome.get('hybrid_upper_family')==family
                    and low in FAMILIES
                    and genome.get('hybrid_upper_topology') in PROCEDURAL_TOPOLOGIES[family]
                    and genome.get('hybrid_lower_topology') in PROCEDURAL_TOPOLOGIES.get(low,()))
        return (hybrid in self.hybrid_ids and BY_ID[hybrid].upper_family == family
                and genome.get('topology') == 'hybrid')

    def choose_family(self, rng: random.Random) -> str:
        if not self.allow_single and self.hybrid_ids:
            # Sample architectures, not upper-stage families; avoids family-count bias.
            selected=rng.choice(self.hybrid_ids)
            return rng.choice(self.families) if selected=='procedural' else BY_ID[selected].upper_family
        return rng.choice(self.families)

    def generate(self, rng: random.Random, *, architecture_id: str | None = None):
        from advanced import new_genome
        if architecture_id is not None:
            if architecture_id not in self.hybrid_ids:
                raise ValueError('Architecture is outside selected search scope')
            if architecture_id=='procedural':
                f=self.choose_family(rng)
                return f, make_procedural_genome(f,rng)
            spec = BY_ID[architecture_id]
            return spec.upper_family, genome_for(spec, rng)
        if not self.allow_single:
            chosen=rng.choice(self.hybrid_ids)
            if chosen=='procedural':
                fam=rng.choice(self.families)
                return fam,make_procedural_genome(fam,rng)
            spec=BY_ID[chosen]
            return spec.upper_family, genome_for(spec, rng)
        family = self.choose_family(rng)
        if self.hybrid_ids and rng.random() < 0.40:
            choices = [x for x in self.hybrid_ids if x=='procedural' or BY_ID[x].upper_family == family]
            if choices:
                chosen=rng.choice(choices)
                if chosen=='procedural':return family,make_procedural_genome(family,rng)
                spec = BY_ID[chosen]
                return family, genome_for(spec, rng)
        g = new_genome(family, rng)
        return family, self.repair(family, g, rng)

    def repair(self, family: str, genome: dict, rng: random.Random | None = None) -> dict:
        """Preserve existing numeric genes while enforcing the selected architecture.

        Random replacement of a forbidden hybrid is only permitted for hybrid-only
        scopes; single-only scopes always remove it. Legacy family scopes retain
        their historical behavior, with invalid cross-family hybrids repaired.
        """
        rng = rng or random.Random(0)
        if family not in self.families:
            raise ValueError('Genome family outside selected search scope')
        g = dict(genome)
        hybrid = g.get('hybrid_id', 'none')
        choices = [s for s in self.hybrid_ids if s=='procedural' or BY_ID[s].upper_family == family]
        if not self.allow_single:
            if not choices:
                raise ValueError('No hybrid architecture belongs to selected family')
            if hybrid not in choices:
                hybrid = rng.choice(choices)
        elif hybrid not in choices:
            hybrid = 'none'
        g['hybrid_id'] = hybrid
        if hybrid == 'procedural':
            if 'hybrid_upper_topology' not in g or 'hybrid_lower_topology' not in g:
                replacement=make_procedural_genome(family,rng)
                for key in ('hybrid_upper_topology','hybrid_lower_topology','hybrid_lower_family','hybrid_opposed_chirality'):
                    g[key]=replacement[key]
            g['hybrid_upper_family']=family
            if g.get('hybrid_lower_family') not in FAMILIES:
                g['hybrid_lower_family']=rng.choice(FAMILIES)
            if g.get('hybrid_upper_topology') not in PROCEDURAL_TOPOLOGIES[family]:
                g['hybrid_upper_topology']=rng.choice(PROCEDURAL_TOPOLOGIES[family])
            if g.get('hybrid_lower_topology') not in PROCEDURAL_TOPOLOGIES[g['hybrid_lower_family']]:
                g['hybrid_lower_topology']=rng.choice(PROCEDURAL_TOPOLOGIES[g['hybrid_lower_family']])
        if hybrid != 'none':
            g['topology'] = 'hybrid'
            g['height'] = max(6.2, float(g['height']))
        elif g.get('topology') == 'hybrid':
            from advanced import KINDS
            choices_kind = [k for k in KINDS[family] if k not in ('hybrid',)]
            g['topology'] = rng.choice(choices_kind)
        # A hybrid phase is a genuine relative angle, separate from helix handedness.
        if 'hybrid_phase' in g:
            g['hybrid_phase'] = float(max(-math.pi, min(math.pi, g['hybrid_phase'])))
        return g


def procedural_topology_mutation(family: str, genome: dict, rng: random.Random) -> dict:
    """Deliberate macro-change of one procedural-stage topology or lower family.

    Called from the global/topology operator only, never from a repair operation
    or a precision refinement step. Search-scope validation follows afterwards.
    """
    if genome.get('hybrid_id') != 'procedural':
        return dict(genome)
    g = dict(genome)
    k = rng.choice(('hybrid_lower_family', 'hybrid_upper_topology',
                    'hybrid_lower_topology', 'hybrid_opposed_chirality'))
    if k == 'hybrid_lower_family':
        g[k] = rng.choice(FAMILIES)
        g['hybrid_lower_topology'] = rng.choice(PROCEDURAL_TOPOLOGIES[g[k]])
    elif k == 'hybrid_upper_topology':
        g[k] = rng.choice(PROCEDURAL_TOPOLOGIES[family])
    elif k == 'hybrid_lower_topology':
        g[k] = rng.choice(PROCEDURAL_TOPOLOGIES[g['hybrid_lower_family']])
    else:
        g[k] = 1 - int(g.get(k, 0))
    return g


def local_refinement(family: str, genome: dict, rng: random.Random, *, precision: float = 0.8, stagnation: int = 0) -> dict:
    """Small bounded mutation around an elite, preserving architecture and topology.

    Precision near 1 reduces the trust-region step; stagnation broadens it.
    The mutation changes 1-4 coordinates in normalized range and is evaluated
    with exactly the same objective and feasibility gate as other offspring.
    """
    from advanced import PARAM_EXTRA, INTEGER_GENES, _snap_piezo_count
    if not 0.0 <= precision <= 1.0:
        raise ValueError('precision must be 0..1')
    bounds = {**LIMITS[family], **PARAM_EXTRA[family]}
    g = dict(genome)
    protected = {'morph_seed', 'hybrid_sensor_mode', 'piezo_mode', 'piezo_wiring',
                 'piezo_count', 'ribs', 'tier_count', 'branch_factor'}
    keys = [k for k in bounds if k in g and k not in protected and k not in INTEGER_GENES]
    if not keys:
        return g
    step = (0.075 - 0.061 * precision) * (1.8 if stagnation >= 10 else 1.0)
    n = min(len(keys), rng.randint(1, 4))
    for key in rng.sample(keys, n):
        lo, hi = bounds[key]
        value = float(g[key])
        # Reflect at the bounds to avoid accumulating mass on hard limits.
        candidate = value + rng.gauss(0, step * (hi - lo))
        for _ in range(3):
            if candidate < lo:
                candidate = lo + (lo - candidate)
            if candidate > hi:
                candidate = hi - (candidate - hi)
        g[key] = round(max(lo, min(hi, candidate)), 6)
    return _snap_piezo_count(g, family)


def niche_key(family: str, genome: dict, metrics: dict | None = None):
    """MAP-Elites-lite bin: structure, stage ratio, alignment and touch sensitivity.

    A *coarse* cell structure maintains separate elites across mechanisms and
    response bands without storing an unbounded nearest-neighbor archive.
    """
    hybrid = genome.get('hybrid_id') or 'none'
    if hybrid=='procedural':
        topo = 'procedural/'+str(genome.get('hybrid_lower_family'))+'/'+str(genome.get('hybrid_upper_topology'))+'/'+str(genome.get('hybrid_lower_topology'))
    else:
        topo = hybrid if hybrid != 'none' else str(genome.get('topology', 'unknown'))
    angle = abs(float(genome.get('hybrid_phase', 0.0)))
    phase_bin = min(3, int(angle / (math.pi + 1e-9) * 4)) if hybrid != 'none' else 0
    split = float(genome.get('hybrid_split', 0.5))
    split_bin = 0 if split < 0.45 else 2 if split > 0.55 else 1
    if metrics:
        # Prefer robust synthetic phenotype over hardcoded architecture only.
        coverage = metrics.get('spatial_gate', {}).get('coverage_fraction')
        coverage_bin = min(3, max(0, int(float(coverage) * 4))) if coverage is not None else 0
    else:
        coverage_bin = 0
    return family, topo, phase_bin, split_bin, coverage_bin


class EliteArchive:
    """Bounded QD archive, quality-aware within each niche."""
    def __init__(self, max_size=256):
        self.items: dict[tuple, dict] = {}
        self.max_size = max_size
    def insert(self, candidate: dict):
        key = niche_key(candidate['family'], candidate['genome'], candidate.get('metrics'))
        old = self.items.get(key)
        if old is None or candidate['selection'] > old['selection']:
            self.items[key] = candidate
        if len(self.items) > self.max_size:
            worst = min(self.items, key=lambda k: self.items[k]['selection'])
            del self.items[worst]
    def sample(self, rng: random.Random, *, family: str | None = None):
        choices = [c for c in self.items.values() if family is None or c['family'] == family]
        return rng.choice(choices) if choices else None
    def __len__(self):
        return len(self.items)
