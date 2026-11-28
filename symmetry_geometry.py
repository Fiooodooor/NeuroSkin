"""T0 symmetry-constrained primary-flexure orbits and diagnostic reports.

This constrains sampled centerlines and radii, not manufactured geometry,
CAD/HEX8 mesh symmetry, wiring topology, or coupled multiphysics fields.
"""
from __future__ import annotations
import math
import numpy as np
from neuroskin_multiscale import symmetry_error

ORDERS = (2, 3, 4, 6, 8)
TARGETS = tuple(f'{group}{n}' for group in ('C', 'D') for n in ORDERS)


def parse_target(target):
    if target == 'C1':
        return 1, False
    if target not in TARGETS:
        raise ValueError(f'Unsupported symmetry target {target}')
    return int(target[1:]), target[0] == 'D'


def legal_counts(family, target):
    order, mirror = parse_target(target)
    if family == 'quadrant':
        return (4,) if 4 % order == 0 else ()
    if mirror and family == 'chiral':
        return ()  # Preserve chirality as a distinct research design class.
    return tuple(n for n in (4, 6, 8) if n % order == 0 and (n >= 5 or family == 'chiral'))


def legal_topologies(family, target):
    _, mirror = parse_target(target)
    if mirror:
        return ('radial',) if family == 'crown' else ('orthogonal',) if family == 'quadrant' else ()
    return {'crown': ('radial','spiral','arched'), 'chiral': ('helical','counter'),
            'quadrant': ('orthogonal','serpentine','diagonal')}[family]


def repair_symmetry(family, genome, target, rng):
    g = dict(genome)
    counts = legal_counts(family, target)
    kinds = legal_topologies(family, target)
    if not counts or not kinds:
        raise ValueError('Symmetry class incompatible with family')
    n = 4 if family == 'quadrant' else int(g.get('ribs',counts[0]))
    if n not in counts:
        n = rng.choice(counts)
    if family != 'quadrant':g['ribs'] = n
    g.update(symmetry_target=target,hybrid_id='none',branch_factor=0,
             pad_offset_x=0.,pad_offset_y=0.,piezo_count=n,piezo_wiring=0,piezo_mode=0)
    if g.get('topology') not in kinds:g['topology'] = rng.choice(kinds)
    return g


def accepts_symmetry(family, g, target):
    n = 4 if family == 'quadrant' else int(g.get('ribs',0))
    return (g.get('symmetry_target') == target and n in legal_counts(family,target)
            and g.get('topology') in legal_topologies(family,target)
            and g.get('hybrid_id','none') == 'none' and g.get('branch_factor',0) == 0
            and g.get('pad_offset_x',0.) == g.get('pad_offset_y',0.) == 0.
            and g.get('piezo_count') == n and g.get('piezo_wiring') == 0)


def constrain_paths(family, genome, paths):
    target = genome.get('symmetry_target','C1')
    if target == 'C1':return paths
    if not accepts_symmetry(family,genome,target):raise ValueError('Invalid symmetry-constrained genome')
    order, mirror = parse_target(target)
    n = len(paths)
    if n not in legal_counts(family,target) or any(tag!='leg' for _,_,tag in paths):
        raise ValueError('Constrained orbit must contain only primary flexures')
    seed,radius,tag = paths[0]
    seed = np.asarray(seed,float).copy()
    phi = math.atan2(seed[0,1],seed[0,0])
    if mirror:
        radial = np.array([math.cos(phi),math.sin(phi)])
        seed[:,:2] = (seed[:,:2] @ radial)[:,None]*radial[None,:]
    result=[]
    for i in range(n):
        a=2*math.pi*i/n
        c,s=math.cos(a),math.sin(a)
        q=seed.copy();q[:,:2]=q[:,:2]@np.array([[c,s],[-s,c]])
        result.append((q,radius,tag))
    return result


def symmetry_report(family, genome):
    from advanced import structural_struts, curve_stiffness, _single_stage_curve_stiffness
    from pvdf_array import layout_metrics
    k = curve_stiffness(family,genome,E=genome.get('material_E',1.))
    length = max(float(genome['radius']),.1)
    errors = {target:symmetry_error(k,int(target[1:]),length,mirror=target[0]=='D') for target in TARGETS}
    response = np.linalg.solve(k,np.array([0.,0.,-.1,0.,0.,0.]))
    stages={}
    if genome.get('hybrid_id','none') not in ('none',None,''):
        from hybrid_geometry import stage_stiffnesses
        for name, sk in stage_stiffnesses(family,genome,_single_stage_curve_stiffness):
            stages[name]={target:symmetry_error(sk,int(target[1:]),length,mirror=target[0]=='D') for target in TARGETS}
    return {'target':genome.get('symmetry_target','C1'),'source':'T0_linear_stiffness_proxy',
            'stiffness_residual':errors,'stage_stiffness_residual':stages,
            'central_lateral_mm':float(np.linalg.norm(response[:2])),
            'central_tilt_rad':float(np.linalg.norm(response[3:5])),
            'central_twist_rad':float(response[5]),
            'film_layout':layout_metrics(structural_struts(family,genome),genome),
            'limitations':'Centerline and stiffness symmetry only; Dn residual uses global X reflection; FEM field and wiring equivalence not certified.'}
