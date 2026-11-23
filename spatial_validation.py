"""Spatial vertical-load screening and transparent conservative plausibility gates.

Not FEA, not nonlinear contact: 6-DOF rigid plate + elastic rods with assumed
basal capacitors. Grid points are restricted to a specified contact disk.
All units are mm, N, pF, radians. A gate PASS is NOT experimental validation.
"""
from __future__ import annotations
import math
import numpy as np
from electromechanics import examine

DEFAULTS = dict(force_n=0.1, grid_size=5, coverage_fraction=0.85,
                snr_threshold=3.0, displacement_limit_mm=2.0,
                tilt_limit_rad=0.35, lateral_limit_mm=4.0,
                max_negative_reaction_fraction=0.25)

def grid_points(radius,grid_size=5):
    if grid_size not in (3,5,7):
        raise ValueError('grid_size must be 3, 5, or 7')
    if not np.isfinite(radius) or radius<=0:
        raise ValueError('radius must be positive')
    points=[]
    for y in np.linspace(-radius,radius,grid_size):
        for x in np.linspace(-radius,radius,grid_size):
            if x*x+y*y <= radius*radius+1e-10:
                points.append((float(x),float(y)))
    # includes center for odd grids
    return points

def spatial_pressure_test(family,genome,force_n=0.1,grid_size=5,coverage_fraction=.85,
                          snr_threshold=3.,displacement_limit_mm=2.,
                          tilt_limit_rad=.35,lateral_limit_mm=4.,
                          max_negative_reaction_fraction=.25):
    if force_n<=0 or not math.isfinite(force_n):
        raise ValueError('force_n must be positive')
    if not 0<coverage_fraction<=1:
        raise ValueError('coverage_fraction out of range')
    radius=float(genome['pad_radius'])*coverage_fraction
    points=grid_points(radius,grid_size)
    rows=[]
    failures=[]
    for x,y in points:
        r=examine(family,genome,'normal',force=[0,0,-force_n],offset=(x,y))
        el=r['electrical'];me=r['mechanics']
        sig=np.array(el['pressure_delta_pF'],dtype=float)
        noise=float(el['noise_assumptions']['pressure_rms_pF'])
        f=np.asarray(me['foot_reactions_N'],float)[:,2]
        u=np.array(me['displacement_mm'],float);angle=np.array(me['rotation_rad'],float)
        snr=float(np.linalg.norm(sig)/noise) if noise>0 else 0.
        # A capacitive channel cannot reliably represent a tensile *contact* reaction
        # unless bonded; surface test flags large negative support components.
        neg=float(np.maximum(f,0).sum()/(np.abs(f).sum()+1e-12))
        tilt=float(np.linalg.norm(angle[:2]))
        lateral=float(np.linalg.norm(u[:2]))
        vertical=float(-u[2])
        dielectric_gap=float(genome.get('dielectric_gap_mm', .45))
        compression=np.asarray(el.get('pressure_dielectric_motion_mm', []), dtype=float)
        bottom_out=bool(len(compression) and np.max(compression)>dielectric_gap*.76)
        passed=bool(np.isfinite([*sig,*u,*angle,neg]).all() and
                    snr>=snr_threshold and 0<vertical<=displacement_limit_mm and
                    tilt<=tilt_limit_rad and lateral<=lateral_limit_mm and
                    neg<=max_negative_reaction_fraction and not bottom_out)
        # Continuous progress metric prevents a zero-coverage plateau from
        # giving all infeasible genotypes the same reproductive advantage.
        signal_quality=float(np.clip(snr/max(snr_threshold, 1e-12), 0., 1.))
        vertical_quality=float(min(1., displacement_limit_mm/max(vertical, 1.e-9))) if vertical>0 else 0.
        tilt_quality=float(min(1.,tilt_limit_rad/max(tilt,1.e-9)))
        lateral_quality=float(min(1.,lateral_limit_mm/max(lateral,1.e-9)))
        reaction_quality=float(min(1.,max_negative_reaction_fraction/max(neg,1.e-9)))
        point_quality=(.40*signal_quality+.30*vertical_quality+.15*tilt_quality+
                       .10*lateral_quality+.05*reaction_quality)
        if vertical<=0:point_quality*=.1
        if bottom_out:point_quality*=.5
        if not np.isfinite(point_quality):point_quality=0.
        flags=[]
        if not np.isfinite([*sig,*u,*angle]).all(): flags.append('nonfinite')
        if snr<snr_threshold: flags.append('weak_pressure_signal')
        if vertical<=0: flags.append('wrong_vertical_deflection')
        if vertical>displacement_limit_mm: flags.append('excessive_vertical_deflection')
        if tilt>tilt_limit_rad: flags.append('excessive_tilt')
        if lateral>lateral_limit_mm: flags.append('excessive_lateral_motion')
        if neg>max_negative_reaction_fraction: flags.append('unilateral_contact_risk')
        if bottom_out: flags.append('capacitor_bottom_out_risk')
        rows.append({'x_mm':round(x,5),'y_mm':round(y,5),'signal_norm_pF':round(float(np.linalg.norm(sig)),7),
                     'signal_sum_pF':round(float(sig.sum()),7),'snr_proxy':round(snr,4),
                     'vertical_deflection_mm':round(vertical,6),'lateral_mm':round(lateral,6),
                     'tilt_rad':round(tilt,6),'negative_reaction_fraction':round(neg,5),
                     'pressure_channels_pF':sig.round(7).tolist(), 'passed':passed,'flags':flags,
                     'point_quality':round(float(point_quality),6),'signal_quality':round(signal_quality,6)})
        if flags:failures.extend(flags)
    snrs=[r['snr_proxy'] for r in rows]
    passed_count=sum(r['passed'] for r in rows)
    unique=sorted(set(failures))
    return {'status':'PASS' if passed_count==len(rows) else 'FAIL',
            'total_points':len(rows),'passing_points':passed_count,
            'coverage_fraction':round(passed_count/len(rows),4),
            'mean_point_quality':round(float(np.mean([r['point_quality'] for r in rows])),6),
            'min_point_quality':round(float(min(r['point_quality'] for r in rows)),6),
            'test_radius_mm':round(radius,4),'applied_vertical_force_N':force_n,
            'min_snr_proxy':round(min(snrs),4), 'median_snr_proxy':round(float(np.median(snrs)),4),
            'max_vertical_deflection_mm':round(max(r['vertical_deflection_mm'] for r in rows),5),
            'max_lateral_mm':round(max(r['lateral_mm'] for r in rows),5),
            'max_tilt_rad':round(max(r['tilt_rad'] for r in rows),6),
            'rms_tilt_rad':round(float(np.sqrt(np.mean([r['tilt_rad']**2 for r in rows]))),6),
            'failure_reasons':unique,'points':rows,
            'assumptions':{'model':'linear rigid-pad/rod surrogate; fixed-bonded mechanical feet, unilateral electrical contact warning',
                           'electrode':'assumed parallel plate, electrode gap compression derived from basal force',
                           'noise':'assumed RMS noise, not measured','pass_meaning':'plausibility screening only; never a validated physical result'},
            'thresholds':{'snr':snr_threshold,'max_vertical_mm':displacement_limit_mm,
                          'max_tilt_rad':tilt_limit_rad,'max_lateral_mm':lateral_limit_mm,
                          'max_negative_reaction_fraction':max_negative_reaction_fraction}}

def cheap_gate(family,genome,grid_size=3):
    """Small spatial screen used in evolution; full 5x5/7x7 available on demand."""
    s=spatial_pressure_test(family,genome,grid_size=grid_size)
    return {k:v for k,v in s.items() if k!='points'}
