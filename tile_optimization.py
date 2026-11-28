"""Bounded multiscale design search over a fixed physical skin footprint.

T0 synthetic reaction sensing, not calibrated readout. Screening uses linear
Q1 plus a local substrate compression approximation; finalists are recomputed
with nonlinear membrane and full 3D substrate compliance. Scores from the two
fidelities are never mixed. The selected receptor is not mutated in place.
"""
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from itertools import product
import math
import numpy as np
from scipy.optimize import nnls
from membrane_tile import MembraneTile
from nonlinear_skin_tile import Substrate3D
from relaxed_membrane import RelaxedSkinTile
from manual_evaluation import manual_worker_initializer

OBJECTIVES=('force_rmse_N','position_mae_mm','power_mW','maximum_receptor_compression_mm')
# Exact physical coordinates expressed as fractions of the common patch.
# Center-grid calibration uses different positions. Both single and multi-contact.
SCENARIOS=(((.31,.37,.1),),((.63,.43,.4),),((.47,.69,.2),),
           ((.32,.62,.1),(.67,.34,.2)))


def receptor_descriptor(candidate,genome):
    from advanced import curve_stiffness,structural_struts
    from electromechanics import examine
    from electronics_budget import budget_for_response
    from validation_contract import digest
    family=candidate['family'];g=genome
    K=curve_stiffness(family,g,E=float(g.get('material_E',1.)))
    compliance=float(np.linalg.solve(K,[0.,0.,1.,0.,0.,0.])[2])
    if not math.isfinite(compliance) or compliance<=0:raise ValueError('Invalid receptor stiffness')
    # Conservative axis-aligned envelope of actual paths, pad and standard base.
    half=max(9.3,float(g['pad_radius'])+.4+max(abs(float(g.get('pad_offset_x',0.))),abs(float(g.get('pad_offset_y',0.)))))
    for points,radius,_ in structural_struts(family,g):
        half=max(half,float(np.abs(np.asarray(points)[:,:2]).max())+float(radius))
    b=budget_for_response(examine(family,g,'normal',force=[0.,0.,-.4]))
    return {'id':str(candidate['id']),'family':family,'genome_hash':digest({'family':family,'genome':g}),
            'kz_N_mm':1/compliance,'envelope_mm':2*half,
            'power_per_taxel_mW':b['power_estimated_mW'],'channels_per_taxel':b['channel_count'],
            'bytes_per_taxel_s':b['link_throughput_bytes_s'],'readout_capacity':bool(b['adc_capacity_pass'] and b['link_capacity_pass']),
            'pvdf_saturated_outputs_assumed':b['pvdf_saturated_outputs_assumed']}


def designs(receptors,side,sizes,tensions,depths,young,membrane_E,membrane_t,noise,seed):
    if not np.isfinite([side,young,membrane_E,membrane_t,noise,*tensions,*depths]).all() or min(side,young,membrane_E,membrane_t,*tensions,*depths)<=0 or noise<0:
        raise ValueError('Invalid patch parameters')
    out=[];excluded=[]
    for i,(r,n,T,h) in enumerate(product(receptors,sorted(set(sizes)),sorted(set(tensions)),sorted(set(depths)))):
        pitch=side/n
        if pitch<r['envelope_mm']+1.:
            excluded.append({'receptor_id':r['id'],'size':n,'pitch_mm':pitch,'reason':'conservative envelope + 1 mm clearance'})
            continue
        out.append({'id':f'design-{i:03d}','receptor':r,'size':n,'pitch_mm':pitch,'side_mm':side,
                    'pretension_N_mm':T,'substrate_thickness_mm':h,'substrate_young_MPa':young,
                    'membrane_young_MPa':membrane_E,'membrane_thickness_mm':membrane_t,
                    'noise_N':noise,'seed':seed})
    if not out:raise ValueError('No receptor fits the requested patch; increase side length or reduce density')
    return out,excluded


def evaluate_design(job):
    d,fidelity=job;n=d['size'];pitch=d['pitch_mm'];side=d['side_mm'];r=d['receptor']
    k=np.full((n,n),r['kz_N_mm'])
    if fidelity=='screen':
        # Local compliance E A/h only; ignores lateral constraint and coupling.
        local=d['substrate_thickness_mm']/(d['substrate_young_MPa']*(pitch/2)**2)
        m=MembraneTile(1/(1/k+local),pitch,d['pretension_N_mm'])
        actual=m
    else:
        sub=Substrate3D(n,pitch,d['substrate_thickness_mm'],d['substrate_young_MPa'])
        actual=RelaxedSkinTile(k,pitch,d['pretension_N_mm'],d['membrane_young_MPa'],d['membrane_thickness_mm'],substrate=sub)
    errors=[];positions=[];compressions=[];max_balance=0.;max_slope=0.;max_substrain=0.;condition=0.
    # Common noise seed for each scenario and grid size, independent of design.
    rng=np.random.default_rng(d['seed']+n)
    iy,ix=np.indices((n,n));centres=np.column_stack(((ix.ravel()+.5)*pitch,(iy.ravel()+.5)*pitch))
    for scenario in SCENARIOS:
        contacts=[(x*side-pitch/2,y*side-pitch/2,F) for x,y,F in scenario]
        # All predefined positions lie within even the 3x3 centre grid.
        a=actual.solve(contacts);reaction=np.asarray(a['reaction_N']).ravel()
        transfer=a['transfer']
        y=reaction+rng.normal(0,d['noise_N'],n*n)
        estimate,_=nnls(transfer,y)
        true_force=sum(F for _,_,F in scenario)
        true_pos=np.array([sum(x*side*F for x,_,F in scenario),sum(y*side*F for _,y,F in scenario)])/true_force
        # A non-detection incurs full patch diagonal error, never a free omission.
        estimated_pos=(estimate@centres/estimate.sum()) if estimate.sum()>1e-12 else None
        positions.append(float(np.linalg.norm(estimated_pos-true_pos)) if estimated_pos is not None else side*math.sqrt(2))
        errors.append(float(estimate.sum()-true_force))
        compressions.append(float(np.max(np.abs(reaction/k.ravel()))))
        max_balance=max(max_balance,a['force_balance_error_N'])
        if 'maximum_membrane_slope' in a:max_slope=max(max_slope,a['maximum_membrane_slope'])
        else:
            w=np.asarray(a['membrane_surface']['displacement_mm'])
            max_slope=max(max_slope,float(max(np.hypot(gx,gy).max() for gx in (np.diff(w,axis=1)[:-1],np.diff(w,axis=1)[1:]) for gy in (np.diff(w,axis=0)[:,:-1],np.diff(w,axis=0)[:,1:]))/(pitch/4)))
        if a.get('substrate'):max_substrain=max(max_substrain,a['substrate']['max_abs_principal_strain'])
        condition=max(condition,float(np.linalg.cond(transfer)))
    metrics={'force_rmse_N':float(np.sqrt(np.mean(np.square(errors)))),'position_mae_mm':float(np.mean(positions)),
             'power_mW':r['power_per_taxel_mW']*n*n,'maximum_receptor_compression_mm':max(compressions),
             'logical_channels':r['channels_per_taxel']*n*n,'aggregate_bytes_per_s_assumed':r['bytes_per_taxel_s']*n*n,
             'max_balance_error_N':max_balance,'max_membrane_slope':max_slope,
             'max_substrate_strain':max_substrain if fidelity=='refined' else None,'transfer_condition':condition}
    if not all(math.isfinite(v) for v in metrics.values() if v is not None):raise RuntimeError('Nonfinite tile metrics')
    passed=bool(max_balance<=1e-7 and max_slope<=(.1 if fidelity=='screen' else .5)
                and (fidelity=='screen' or max_substrain<=.03) and r['readout_capacity']
                and r['pvdf_saturated_outputs_assumed']==0)
    # Explicit engineering scalar for deterministic shortlist only; Pareto retained.
    utility=sum(metrics[k]/s for k,s in zip(OBJECTIVES,(.02,5.,100.,1.)))
    return {**d,'fidelity':fidelity,'metrics':metrics,'diagnostic_screen_pass':passed,'utility_cost':float(utility)}


def safe_evaluate(job):
    try:return evaluate_design(job)
    except (ValueError,RuntimeError,ArithmeticError,np.linalg.LinAlgError,MemoryError) as exc:
        d,fidelity=job
        return {**d,'fidelity':fidelity,'failed':True,'error':str(exc),'diagnostic_screen_pass':False}


def pareto(rows):
    eligible=[r for r in rows if r.get('diagnostic_screen_pass') and not r.get('failed')]
    if len({r['fidelity'] for r in rows})>1:raise ValueError('Mixed tile fidelity')
    def dominates(a,b):
        x=[a['metrics'][k] for k in OBJECTIVES];y=[b['metrics'][k] for k in OBJECTIVES]
        return all(i<=j for i,j in zip(x,y)) and any(i<j for i,j in zip(x,y))
    return [r['id'] for r in eligible if not any(dominates(o,r) for o in eligible)]


def optimize(designs,excluded,finalists,workers=1,progress=lambda _:None):
    if not 1<=workers<=4 or not 1<=finalists<=3 or not 1<=len(designs)<=72:raise ValueError('Invalid bounded search budget')
    def batch(items,fidelity,pool):
        jobs=[(d,fidelity) for d in items]
        progress({'phase':f'{fidelity} 0/{len(jobs)}'})
        iterator=map(safe_evaluate,jobs) if pool is None else pool.map(safe_evaluate,jobs)
        rows=[]
        for r in iterator:
            rows.append(r);progress({'phase':f'{fidelity} {len(rows)}/{len(jobs)}'})
        return rows
    def run(pool):
        screen=batch(designs,'screen',pool);front=pareto(screen)
        valid=[r for r in screen if r.get('diagnostic_screen_pass')]
        # Prefer nondominated designs, but retain diagnostic near misses when
        # screen rejects everything; refinement may change that conclusion.
        ranked=sorted([r for r in screen if not r.get('failed')],key=lambda r:(not r['diagnostic_screen_pass'],r['id'] not in front,r['utility_cost'],r['id']))
        shortlist=ranked[:finalists]
        byid={d['id']:d for d in designs}
        refined=batch([byid[r['id']] for r in shortlist],'refined',pool)
        refined_front=pareto(refined)
        return {'tier':'T0','model':'bounded_multiscale_tile_search','objectives_minimize':list(OBJECTIVES),
                'screening':screen,'screening_pareto_ids':front,'shortlist_ids':[r['id'] for r in shortlist],
                'refined':refined,'refined_pareto_ids':refined_front,'excluded':excluded,
                'screening_pass_count':len(valid),'workers':workers,'scenario_fractions_and_forces':SCENARIOS,
                'limitations':['synthetic reaction sensing and center-point inverse; no hardware calibration',
                               'fixed patch and common physical contact positions; centroid only, not contact multiplicity',
                               'screen local substrate compliance; refined 3D linear substrate and nonlinear membrane with fixed-perimeter in-plane relaxation',
                               'same scenarios used for shortlist and refinement; not independent qualification',
                               'assumed per-taxel electronics; aggregate throughput reported, no shared-bus design',
                               'no automatic promotion of receptor, tile, or evidence tier']}
    if workers==1:return run(None)
    with ProcessPoolExecutor(max_workers=workers,mp_context=get_context('spawn'),initializer=manual_worker_initializer) as pool:return run(pool)
