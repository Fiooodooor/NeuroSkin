"""Deterministic three-finalist nomination with audit-cache awareness.

All nominated designs still receive the same full audit. This only allocates
compute slots; it does not change validation gates or champion promotion.
"""
from population_pareto import constraint_class, parent_key, rank_population


def genome_key(candidate):
    return candidate['family'], tuple(sorted(candidate['genome'].items()))


def nominate(candidates, audits, settings, physical_gate, count=3):
    """One scalar leader, one unexplored Pareto design, one further contender.

    Known failed audits are fallback only. Numerical screen failures are last.
    If enough distinct unaudited eligible designs exist, reserve two slots for
    them. If fewer distinct genomes exist, return the actual count rather than
    fabricate duplicates. Input candidates are annotated with known feasibility.
    """
    if count < 1:
        raise ValueError('Positive finalist count required')
    unique = {}
    for c in candidates:
        key = genome_key(c)
        known = audits.get((*key, *settings))
        c.pop('known_audit_feasible', None)
        if known is not None:
            c['known_audit_feasible'] = bool(known['feasible'])
        old = unique.get(key)
        if old is None or (c['fitness'], c['id']) > (old['fitness'], old['id']):
            unique[key] = c
    pool = list(unique.values())
    rank_population(pool, physical_gate)
    selected, reasons = [], {}
    def take(choices, order, reason):
        if choices and len(selected) < count:
            c = max(choices, key=order)
            selected.append(c)
            reasons[c['id']] = reason
            pool.remove(c)
    def cls(c):
        return constraint_class(c, physical_gate)
    def fresh(c):
        return (*genome_key(c), *settings) not in audits
    def viable(c):
        return cls(c) == 0
    def scalar(c):
        return (c['fitness'], c['id'])
    def diverse(c):
        return (*parent_key(c), c.get('novelty', 0.), c['id'])
    take([c for c in pool if viable(c)], scalar, 'eligible_scalar_leader')
    # Prefer new candidates over repeat audits. A passed cached leader may
    # compete, but cannot occupy all audit slots when unexplored alternatives exist.
    while len(selected) < count and any(viable(c) and fresh(c) for c in pool):
        take([c for c in pool if viable(c) and fresh(c)], diverse, 'new_eligible_pareto')
    while len(selected) < count and pool:
        best_class = min(cls(c) for c in pool)
        group = [c for c in pool if cls(c) == best_class]
        # Within the infeasible class, try new near-misses before known failures.
        take([c for c in group if fresh(c)] or group, diverse, 'fallback_constraint_class_'+str(best_class))
    return selected, reasons
