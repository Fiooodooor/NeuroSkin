"""Deterministic, explicit second-stage *surrogate* audit for NeuroSkin candidates.

This module does not claim to solve contact, hyperelastic FEA or electrostatics.
It provides a common, reproducible exhaustive screening protocol for finalists.
Physical quantities are proxies unless the external measurement/FEM evidence exists.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from advanced import structural_struts, curve_stiffness
from electromechanics import examine, CASES
from spatial_validation import spatial_pressure_test
from optimization import PRESETS

AUDIT_VERSION='3.0-alpha-d31-rank5-screen'
PRESSURE_FORCES_N=(.025,.10,.40)
FREQUENCIES_HZ=(2.,25.,150.)
NUISANCE_STRAINS=(-.05,.05)
NOISE=np.array([.001]*4+[.0003]*2+[.002],float)


def electric_vector(response):
    e=response['electrical']
    return np.array(e['pressure_delta_pF']+e['lateral_delta_pF']+[e['hall_torsion_delta_mT']],float)


def condition_metrics(family,g):
    """Local identification of Fx,Fy,Fz and contact x,y from 7 *assumed* readouts.

    Vectors are whitened by assumed noise; input dimensions are normalized by
    reference scales (0.1 N for force, 3 mm for location). This assesses local
    numerical identifiability, not force accuracy in hardware.
    """
    ref=np.array([.015,-.01,-.1,.6,-.4],float)
    step=np.array([.003,.003,.003,.15,.15],float)
    J=np.zeros((7,5))
    for i in range(5):
        up=ref.copy();down=ref.copy();up[i]+=step[i];down[i]-=step[i]
        def f(x):return electric_vector(examine(family,g,'normal',force=x[:3],offset=tuple(x[3:])))
        J[:,i]=(f(up)-f(down))/(2*step[i])
    M=J*np.array([.1,.1,.1,3.,3.])[None,:]/NOISE[:,None]
    sv=np.linalg.svd(M,compute_uv=False)
    rank=int(np.sum(sv>max(sv[0],1e-12)*1e-6))
    return {'rank_5_unknowns':rank,'smin_whitened':float(sv[-1]),
            'condition_whitened':float(sv[0]/max(sv[-1],1e-12)),
            'singular_values_whitened':[float(x) for x in sv],
            'assumption':'Independent synthetic capacitive/Hall readouts, no calibration; measured hardware may have lower effective rank.'}


def manufacturability(family,g):
    """Compute geometric warning flags, not manufacturing certification."""
    paths=structural_struts(family,g)
    radii=[];arc_lengths=[];curvatures=[];extrema=[]
    for pts,r,kind in paths:
        radii.append(float(r));segs=np.diff(pts,axis=0)
        arc_lengths.append(float(np.linalg.norm(segs,axis=1).sum()))
        for s,t in zip(segs[:-1],segs[1:]):
            c=np.linalg.norm(np.cross(s,t))/max(np.linalg.norm(s)*np.linalg.norm(t),1e-12)
            curvatures.append(float(c))
        extrema.append((float(np.max(np.abs(pts[:,:2]))),float(pts[:,2].min()),float(pts[:,2].max())))
    minimum_diameter=2*min(radii)
    longest_slender=max(L/(2*r) for L,r in zip(arc_lengths,radii))
    max_span=max(x[0] for x in extrema)
    flags=[]
    if minimum_diameter<.6:flags.append('thin_feature_below_0.6_mm')
    if longest_slender>35:flags.append('long_slender_members')
    if max_span>10:flags.append('overhang_outside_nominal_20_mm_cell')
    if max((x[2] for x in extrema)) > 8.5:flags.append('excess_height')
    if len(paths)>45:flags.append('too_many_members')
    return {'member_count':len(paths),'minimum_member_diameter_mm':round(minimum_diameter,4),
            'longest_slenderness_ratio':round(longest_slender,3),
            'max_lateral_extent_mm':round(max_span,3),
            'max_turn_sine':round(max(curvatures,default=0),5),
            'flags':flags,'passed':not flags}


def force_recovery(family,g):
    """Separate deterministic train/test contacts; ridge fit of [Fx,Fy,Fz].

    Not a demonstration of inversion of real sensor response. Position is NOT
    supplied to the estimator; mixed offsets test contact-position confounding.
    """
    rng=np.random.default_rng(47221)
    def dataset(n):
        X=[];Y=[];positions=[]
        for _ in range(n):
            fx,fy=rng.uniform(-.045,.045,size=2)
            fz=-rng.uniform(.02,.2)
            x,y=rng.uniform(-2.5,2.5,size=2)
            raw=electric_vector(examine(family,g,'normal',force=[fx,fy,fz],offset=(x,y)))
            X.append(raw/NOISE);Y.append([fx,fy,fz]);positions.append([x,y])
        return np.array(X),np.array(Y),np.array(positions)
    train,ytrain,_=dataset(70);test,ytest,coords=dataset(30)
    # Robust standardization, ridge on *train* only; no train/test leakage.
    mu=train.mean(axis=0);sd=np.maximum(train.std(axis=0),1e-6)
    A=(train-mu)/sd;T=(test-mu)/sd
    C=np.c_[np.ones(len(A)),A];D=np.c_[np.ones(len(T)),T]
    ridge=np.eye(C.shape[1])*.5;ridge[0,0]=0
    beta=np.linalg.solve(C.T@C+ridge,C.T@ytrain)
    predicted=D@beta
    error=np.sqrt(np.mean((predicted-ytest)**2,axis=0))
    # Basic indicator only. Spatial offset is a nuisance variable; model has no explicit location channels.
    return {'holdout_rmse_N':[round(float(v),6) for v in error],
            'holdout_mean_rmse_N':round(float(error.mean()),6),
            'train_count':len(train),'holdout_count':len(test),
            'training':'Ridge on synthetic signals; fixed seed, independently generated positions, no real-world generalization claim'}


def audit_candidate(family,g,objective='balanced',grid_size=5):
    if objective not in PRESETS:raise ValueError('Unknown objective')
    if grid_size not in (3,5,7):raise ValueError('Invalid audit grid')
    from optimization import evaluate
    quick,original,_=evaluate(family,g,objective,False,3)
    geom=manufacturability(family,g)
    spatial={}
    for f in PRESSURE_FORCES_N:
        spatial[str(f)]=spatial_pressure_test(family,g,force_n=f,grid_size=grid_size)
    cases={}
    signals=[]
    for name in CASES:
        r=examine(family,g,name,frequency_hz=25)
        e=r['electrical'];u=r['mechanics']
        vector=electric_vector(r)
        signals.append(vector)
        cases[name]={
            'pressure_delta_pF':[float(v) for v in e['pressure_delta_pF']],
            'lateral_delta_pF':[float(v) for v in e['lateral_delta_pF']],
            'hall_delta_mT':float(e['hall_torsion_delta_mT']),
            'piezo_peak_V':float(r['piezoelectric']['peak_V']),
            'piezo_strain_proxy':float(r['piezoelectric'].get('strain_proxy',0)),
            'u_mm':[float(v) for v in u['displacement_mm']],
            'rotation_rad':[float(v) for v in u['rotation_rad']],
            'signal_snr_assumed':round(float(np.linalg.norm(vector/NOISE)),4)}
    frequency={}
    for freq in FREQUENCIES_HZ:
        r=examine(family,g,'normal',frequency_hz=freq)
        p=r['piezoelectric']
        frequency[str(freq)]={'peak_V':float(p['peak_V']),
                              'dynamic_snr_proxy':float(p['dynamic_snr_proxy']),
                              'local_strain_proxy':float(p['strain_proxy'])}
    # Mechanical unload/recovery is a calibrated-parameter PLACEHOLDER, not a
    # solved time-dependent viscoelastic solid. It nonetheless affects promotion.
    from recovery_sim import recovery_for_candidate
    unload=recovery_for_candidate(family,g)
    # Explicitly preserve individual tests, not merely their weighted averages.
    observability=condition_metrics(family,g)
    from symmetry_geometry import symmetry_report
    symmetry=symmetry_report(family,g)
    recovery=force_recovery(family,g)
    from selection_refinement import spatial_operating_summary, enforce_score_band
    summary=spatial_operating_summary(spatial)
    # The 25 mN test is a sensitivity diagnostic. Using the minimum over ALL
    # force levels for the operating-band KPI made a 10/13 passing 0.1 N scan
    # appear to have 0% coverage. This distinction is now explicit.
    min_coverage=summary['operating_worst_coverage']
    min_snr=summary['operating_min_snr_assumed']
    margin_quality=summary['operating_mean_margin_quality']
    strain=max(abs(cases[n]['piezo_strain_proxy']) for n in cases)
    # Hard engineering screening, not physical certification.
    feasible=bool(summary['screen_feasible'] and geom['passed'] and
                  observability['rank_5_unknowns']==5 and
                  strain<=.08 and np.isfinite(quick) and unload['strain_screen_passed'])
    signal_component=min(1.,max(0.,min_snr)/8.)
    low_force_component=min(1.,max(0.,summary['low_force_min_snr_assumed'])/3.)
    recovery_component=math.exp(-recovery['holdout_mean_rmse_N']/.04)
    conditioning_component=1./(1.+math.log10(max(observability['condition_whitened'],1.)))
    dynamic_component=math.tanh(max(0.,frequency['25.0']['dynamic_snr_proxy'])/12.)
    utility=100*(.17*np.clip(quick/100,0,1)+.20*min_coverage+.13*margin_quality+
                 .12*signal_component+.16*recovery_component+.10*conditioning_component+
                 .08*dynamic_component+.04*low_force_component)
    utility=.92*utility+.08*unload['recovery_score_0_100_assumed']
    if objective=='electronics':utility=.80*utility+.20*original['fitness_readout']
    if not feasible:
        utility=min(49.99,utility*.5*(.40+.60*margin_quality))
    rejection_reasons=list(summary['failing_conditions'])
    if not geom['passed']:rejection_reasons.extend(f'manufacturing_{f}' for f in geom['flags'])
    if observability['rank_5_unknowns']<5:rejection_reasons.append('underidentified_force_and_contact')
    if strain>.08:rejection_reasons.append('piezo_strain_proxy_excessive')
    if not unload['strain_screen_passed']:rejection_reasons.append('unloading_strain_limit')
    rejection_reasons=sorted(set(rejection_reasons))
    audit={'audit_version':AUDIT_VERSION,'family':family,'objective':objective,
           'quick_fitness':float(quick),'audit_score':round(float(utility),5),
           'feasible':feasible,
           'decision_basis':{'fitness_0_100':float(quick),'coverage_min':min_coverage,
                             'coverage_min_operating_0p1_0p4_N':min_coverage,
                             'coverage_low_force_0p025_N':summary['low_force_coverage'],
                             'assumed_signal_snr_min':float(min_snr),
                             'operating_mean_point_quality':margin_quality,
                             'screening_failure_reasons':rejection_reasons,
                             'force_holdout_rmse_N':recovery['holdout_mean_rmse_N'],
                             'condition_number':observability['condition_whitened'],
                             'piezo_strain_max_proxy':strain,
                             'recovery_5s_residual_fraction_assumed':unload['residual_fraction_after_5s'],
                             'recovery_strain_screen_passed':unload['strain_screen_passed'],
                             'manufacturing_flags':geom['flags']},
           'pressure_spatial':spatial,'spatial_operating_summary':summary,'screening_failure_reasons':rejection_reasons,
           'load_cases':cases,'piezo_frequency_sweep':frequency,'unloading_recovery':unload,
           'observability':observability,'symmetry':symmetry,'force_reconstruction':recovery,'manufacturability':geom,
           'screening_metrics':original,
           'limitations':['6-DOF beam proxy; no hyperelasticity or real contact FEM',
                           'synthetic electrical response and assumed noise (not measured)',
                           'STL is an assembly visualization, not a printable watertight union',
                           'strain and manufacturing thresholds are tentative design assumptions',
                           'Unloading recovery uses an assumed standard-linear-solid compliance, not viscoelastic FEM or experimental calibration']}
    if objective=='electronics':
        audit['decision_basis']['readout_score_assumed']=original['fitness_readout']
        audit['decision_basis']['readout_worst_peak_to_span']=original['readout_worst_peak_to_span']
    return enforce_score_band(audit)


def promote(incumbent, finalists):
    """Incumbent can only be replaced by a fully audited finalist.

    Prefer fully feasible designs; then audit score, then maintain incumbent
    at ties (up to 1e-8). No screening-score-only replacement.
    """
    pool=[x for x in ([incumbent] if incumbent is not None else [])+list(finalists) if x]
    if not pool:return None,{'reason':'no_finalist'}
    for x in pool:
        if not x.get('audit'):raise ValueError('Promotion requires completed audit for every candidate')
    reports=[x['audit'].get('validation_v30') for x in pool]
    if any(reports):
        # Never compare legacy fitness to a newly validated report. An older
        # incumbent remains in place until explicitly revalidated.
        if not all(reports):
            if incumbent is not None:
                return incumbent,{'reason':'incompatible_legacy_validation_protocol',
                                  'previous':incumbent['id'],'selected':incumbent['id'],
                                  'replaced':False,'requires_revalidation':True}
            raise ValueError('Partial Top-3 validation: a finalist lacks a report')
        from validation_contract import ValidationReport, candidate_comparable
        for report in reports:ValidationReport.model_validate(report)
        anchor=reports[0]
        if any(not candidate_comparable(anchor,x)[0] for x in reports[1:]):
            if incumbent is not None:
                return incumbent,{'reason':'incomparable_fidelity_or_protocol',
                                  'previous':incumbent['id'],'selected':incumbent['id'],
                                  'replaced':False,'requires_revalidation':True}
            raise ValueError('Top-3 validation protocol or fidelity differs')
    def rank(x):return (int(bool(x['audit']['feasible']) and
                            (not reports[0] or x['audit']['validation_v30']['pass_current_tier'])),
                        float(x['audit']['audit_score']))
    candidate=max(pool,key=rank)
    previous=incumbent['id'] if incumbent else None
    if incumbent is not None and rank(candidate)<=rank(incumbent):candidate=incumbent
    validated=bool(candidate['audit'].get('validation_v30',{}).get('pass_current_tier'))
    return candidate,{'previous':previous,'selected':candidate['id'],
                      'replaced':previous is not None and candidate['id']!=previous,
                      'validated_T0':validated,
                      'status':'T0_synthetic_screen_pass' if validated else 'provisional_not_validated',
                      'rule':'same fidelity and protocol → T0 screen → audit score; incumbent retained on ties'}
