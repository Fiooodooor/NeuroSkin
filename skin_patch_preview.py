"""Nominal skin assemblies bound to computed tile designs, never solved fields."""
import math
import numpy as np

MAX_TEMPLATE_FACES = 16000


def geometry_template(candidate, genome):
    from advanced import detail_mesh, structural_struts
    from validation_contract import digest
    groups = detail_mesh(candidate['family'], genome, quality=5)
    bounds = np.array([mesh.bounds for mesh in groups.values()])
    low, high = bounds[:, 0].min(axis=0), bounds[:, 1].max(axis=0)
    if not np.isfinite(bounds).all() or np.any(high <= low):
        raise ValueError('Invalid receptor preview bounds')
    face_count = sum(len(mesh.faces) for mesh in groups.values())
    surfaces = face_count <= MAX_TEMPLATE_FACES
    return {
        'candidate_id': str(candidate['id']), 'family': candidate['family'],
        'genome_hash': digest({'family': candidate['family'], 'genome': genome}),
        'bounds_mm': [low.tolist(), high.tolist()],
        'rendering': 'surface_mesh' if surfaces else 'structural_centerlines',
        'components': [{'part': part, 'vertices': np.round(mesh.vertices, 4).tolist(),
                        'faces': mesh.faces.tolist()} for part, mesh in groups.items()] if surfaces else [],
        'centerlines_mm': [] if surfaces else [np.round(points, 4).tolist()
                                             for points, _, _ in structural_struts(candidate['family'], genome)],
        'source_faces': face_count,
        'note': 'Actual generated conceptual geometry; nominal placement, no local FEM deformation or CAD qualification.',
    }


def patch_layout(design, template):
    n = design['size']
    pitch, side = float(design['pitch_mm']), float(design['side_mm'])
    depth = float(design['substrate_thickness_mm'])
    thickness = float(design['membrane_thickness_mm'])
    if type(n) is not int or n not in (3, 5, 7, 8):
        raise ValueError('Unsupported skin patch grid')
    if not all(math.isfinite(v) and v > 0 for v in (pitch, side, depth, thickness)) or not math.isclose(n*pitch, side):
        raise ValueError('Invalid skin patch dimensions')
    if template['genome_hash'] != design['receptor']['genome_hash']:
        raise ValueError('Receptor geometry does not match the computed design')
    low, high = np.asarray(template['bounds_mm'], float)
    clearance = float(min(pitch-(high[0]-low[0]), pitch-(high[1]-low[1])))
    if clearance < 0 or any(low[i] < -pitch/2-1e-8 or high[i] > pitch/2+1e-8 for i in (0, 1)):
        raise ValueError('Generated receptors do not fit the computed pitch')
    return {
        'schema': 'neuroskin.skin_patch_preview.v1', 'design_id': design['id'],
        'receptor_id': design['receptor']['id'], 'genome_hash': template['genome_hash'],
        'size': n, 'sensor_count': n*n, 'side_mm': side, 'pitch_mm': pitch,
        'substrate_depth_mm': depth, 'membrane_thickness_mm': thickness,
        'membrane_z_mm': float(high[2]-low[2]), 'minimum_xy_clearance_mm': clearance,
        'placements': [{'id': f'r{row+1}-c{col+1}', 'row': row, 'column': col,
                        'position_mm': [(col+.5)*pitch, (row+.5)*pitch, float(-low[2])]}
                       for row in range(n) for col in range(n)],
        'nominal_geometry_only': True, 'hardware_qualified': False,
    }


def attach_skin_previews(result, receptor_models):
    """Attach geometry once, placements per result, and same-fidelity choices."""
    rows = [row for key in ('screening', 'refined') for row in result[key] if not row.get('failed')]
    templates, errors = {}, []
    for receptor_id in sorted({row['receptor']['id'] for row in rows}):
        try:
            candidate, genome = receptor_models[receptor_id]
            templates[receptor_id] = geometry_template(candidate, genome)
        except (ValueError, KeyError, RuntimeError, MemoryError) as exc:
            errors.append({'receptor_id': receptor_id, 'reason': str(exc)})
    previews = []
    for row in rows:
        template = templates.get(row['receptor']['id'])
        if template is None:
            continue
        try:
            layout = patch_layout(row, template)
        except (ValueError, KeyError) as exc:
            errors.append({'design_id': row['id'], 'reason': str(exc)})
            continue
        previews.append({**layout, 'key': row['fidelity']+':'+row['id'], 'fidelity': row['fidelity'],
                         'diagnostic_screen_pass': row['diagnostic_screen_pass'],
                         'utility_cost': row['utility_cost']})
    recommended = {}
    for n in sorted({p['size'] for p in previews}):
        same_grid = [p for p in previews if p['size'] == n]
        refined = [p for p in same_grid if p['fidelity'] == 'refined']
        pool = refined or same_grid
        best = min(pool, key=lambda p: (not p['diagnostic_screen_pass'], p['utility_cost'], p['key']))
        recommended[str(n)] = best['key']
    result['skin_templates'] = templates
    result['skin_patches'] = previews
    result['skin_preview_errors'] = errors
    result['recommended_skin_patches'] = recommended
    result['skin_selection_policy'] = 'Per grid: refined results if available, otherwise screening; feasibility then existing utility within that fidelity. Best computed candidate, not a global optimum.'
    return result
