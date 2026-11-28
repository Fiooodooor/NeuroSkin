"""Apply physics corrections to a pristine NeuroSkin 2.2 tree.

Usage: python tools/upgrade_v22_physics.py /path/to/neuroskin_evolution_lab_v22
Exact-anchor checks reject incompatible revisions before writing.
"""
from pathlib import Path
import sys


def upgrade(root):
    root = Path(root)
    if (root / 'VERSION').read_text().strip() != '2.2.0':
        raise ValueError('Expected NeuroSkin 2.2.0 source')
    edits = {}
    def change(file, before, after):
        s = edits.get(file, (root / file).read_text(encoding='utf-8'))
        if s.count(before) != 1:
            raise ValueError(f'Unexpected anchor in {file}: {before[:80]}')
        edits[file] = s.replace(before, after, 1)
    change('piezoelectric.py', '''        axial_force=stress*bond['effective_width_mm']*thickness
        dcoeff=D33_PC_PER_N if int(genome.get('piezo_mode',0))==1 else D31_PC_PER_N
        charge=dcoeff*axial_force
        capacitance=EPS0_PF_MM*EPSR*width*length/max(thickness,.001)''', '''        # Electrodes are on the broad faces: axial stress drives d31, not d33.
        # The legacy d33 flag is retained for archive compatibility, not simulated.
        active_area=bond['effective_width_mm']*bond['effective_span_mm']
        charge=D31_PC_PER_N*stress*active_area
        capacitance=EPS0_PF_MM*EPSR*active_area/bond['film_thickness_mm']''')
    change('piezoelectric.py', "'arc_length_mm':float(arc),'film_length_mm':min(length,arc*.82),", "'arc_length_mm':float(arc),'film_length_mm':bond['effective_span_mm'],\n            'active_electrode_area_mm2':active_area,'film_mass_g':bond['film_mass_g'],")
    change('piezoelectric.py', "'d_coefficient_pC_per_N_assumed':float(D33_PC_PER_N if int(genome.get('piezo_mode',0)) else D31_PC_PER_N),", "'d_coefficient_pC_per_N_assumed':D31_PC_PER_N,\n      'requested_piezo_mode':int(genome.get('piezo_mode',0)),\n      'transduction_mode':'d31_uniaxial_broad_face',\n      'd33_supported':False,")
    change('piezoelectric.py', "'total_pvdf_mass_g_estimate':count*width*min(length,4.0)*thickness*.00178,", "'total_pvdf_mass_g_estimate':float(sum(c['film_mass_g'] for c in channels)),")
    change('piezoelectric.py', 'PVDF multi-channel d31/d33 + RC highpass', 'PVDF multi-channel d31 + RC highpass')
    change('laminate_fem.py', '            charge=D31_PC_N*ffilm', "            charge=D31_PC_N*p['pvdf_E_MPa']*p['shear_lag_transfer']*avg*p['effective_width_mm']*p['effective_span_mm']")
    change('laminate_shell.py', '        curvature = _curvature_from_polyline(deformed)', '        curvature = _curvature_from_polyline(deformed) - _curvature_from_polyline(surf_pts)\n        membrane_station *= props[\'shear_lag_transfer\']')
    change('laminate_shell.py', '        ds_station = np.r_[seg_und[0], 0.5 * (seg_und[:-1] + seg_und[1:]), seg_und[-1]]', '        ds_station = np.r_[0.5*seg_und[0], 0.5 * (seg_und[:-1] + seg_und[1:]), 0.5*seg_und[-1]]\n        ds_station *= span / ds_station.sum()')
    change('laminate_shell.py', "        est_charge = float(-23.0 * props['pvdf_E_MPa'] * props['effective_width_mm'] * tf * membrane_station.mean())", "        est_charge = float(-23.0 * props['pvdf_E_MPa'] * props['effective_width_mm'] * np.dot(membrane_station, ds_station))")
    change('advanced.py', '''  compliances=[np.linalg.inv(K) for _,K in stages]
  C=compliances[0]+compliances[1]''', '''  from hybrid_geometry import mid_height
  T=np.eye(6);T[:3,3:]=-skew(np.array([0.,0.,p['height']-mid_height(p)]))
  C=T@np.linalg.inv(stages[0][1])@T.T+np.linalg.inv(stages[1][1])''')
    change('electromechanics.py', ''' if abs(strain)>0:
  for pts,kl,B in members:
   a=pts[0]
   moved=np.array([a[0]*strain,0.,0.])
   load+=B.T@kl@moved
 u_lower=np.linalg.solve(K['lower'],load)
 u_upper=np.linalg.solve(K['upper'],load)
 total=u_lower+u_upper''', ''' T=np.eye(6);T[:3,3:]=-skew(np.array([0.,0.,genome['height']-mid_height(genome)]))
 lower_load=T.T@load
 if abs(strain)>0:
  for pts,kl,B in members:
   a=pts[0]
   moved=np.array([a[0]*strain,0.,0.])
   lower_load+=B.T@kl@moved
 u_lower=np.linalg.solve(K['lower'],lower_load)
 u_upper=np.linalg.solve(K['upper'],load)
 total=T@u_lower+u_upper''')
    change('electromechanics.py', "np.linalg.inv(np.linalg.inv(K['lower'])+np.linalg.inv(K['upper'])).tolist()", "np.linalg.inv(T@np.linalg.inv(K['lower'])@T.T+np.linalg.inv(K['upper'])).tolist()")
    change('electromechanics.py', "'model':'two_rigid_stage_6DOF_series_proxy'", "'stage_loads_N_Nmm':{'lower':(T.T@load).tolist(),'upper':load.tolist()},\n         'model':'two_rigid_stage_6DOF_transported_series_proxy'")
    change('static/index.html', 'pie.d_coefficient_pC_per_N)', "(pie.d_coefficient_pC_per_N_assumed??pie.d_coefficient_pC_per_N??'n/a'))")
    change('static/index.html', " renderSolvedFEM();$('femStatus').textContent=", " renderSolvedFEM();$('femMetrics').textContent=JSON.stringify({backend:fm.fem_backend,mesh_pitch_mm:fm.mesh_pitch_mm,inflated_features:fm.inflated_features,feasible_linear:fm.feasible_linear,force_equilibrium_max:fm.force_equilibrium_max,moment_equilibrium_max:fm.moment_equilibrium_max},null,2);$('femStatus').textContent=")
    change('full_evaluation.py', "observability['rank_5_unknowns']>=3", "observability['rank_5_unknowns']==5")
    change('full_evaluation.py', "observability['rank_5_unknowns']<3", "observability['rank_5_unknowns']<5")
    change('physical_fem.py', 'valid=bool(pressure_valid and extrema<.12 and mesh.voxels>80 and max(v[\'moment_equilibrium_relative\'] for v in results.values())<1e-4)', 'valid=bool(pressure_valid and extrema<.12 and mesh.voxels>80 and mesh.inflated_features==0 and max(v[\'force_equilibrium_relative\'] for v in results.values())<1e-4 and max(v[\'moment_equilibrium_relative\'] for v in results.values())<1e-4)')
    change('evaluation_v30.py', "ENGINE_SIGNATURE = 'neuroskin-v2.2-validated-surrogate-20261128'", "ENGINE_SIGNATURE = 'neuroskin-v3-physics-corrections-1'")
    change('evaluation_v30.py', "'evaluation_v30.py','laminate_fem.py','physical_fem.py')", "'evaluation_v30.py','laminate_fem.py','physical_fem.py','laminate_shell.py','piezoelectric.py','hybrid_geometry.py','pvdf_array.py')")
    change('evaluation_v30.py', "reason='No physically measured calibration data supplied'", "reason='Optional T3: no physically measured calibration data supplied; does not block software release or evolution'")
    for file, s in edits.items():
        (root / file).write_text(s, encoding='utf-8')
    return sorted(edits)


if __name__ == '__main__':
    print('\n'.join(upgrade(sys.argv[1])))
