"""Reduced laminate-shell post-processing for bonded PVDF ribbons.

This module is intentionally explicit about scope: it is a *final-stage* shell-like
post-process run after the substrate mechanics solve. It does not replace the 3D
HEX8 substrate or a fully coupled film+adhesive shell/solid contact formulation.
Instead it reconstructs a thin ribbon shell kinematics on each selected PVDF film
support using the solved substrate displacement field.

Outputs:
- shell membrane strain and curvature along each film
- top/bottom fiber strain and approximate axial stress
- interfacial shear proxy from the shear-lag transmission factor
- a lightweight 3D ribbon mesh for browser visualization
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from scipy.spatial import cKDTree
from advanced import structural_struts, _profile_radius
from laminate_fem import material_parameters, effective_film_properties, film_stations
from pvdf_array import choose_film_members

POISSON_PVDF = 0.29
DENSITY_PVDF_G_MM3 = 0.00178


def _nearest4(tree: cKDTree, nodes: np.ndarray, xyz: np.ndarray, pitch_mm: float):
    dist, ids = tree.query(np.asarray(xyz, float), k=min(4, len(nodes)))
    ids = np.atleast_1d(ids).astype(np.int32)
    ds = np.atleast_1d(dist).astype(float)
    if ds.min() > max(2.8 * pitch_mm, 1.0):
        raise ValueError(f"Laminate shell mapping too far from substrate ({ds.min():.3g} mm)")
    if ds[0] < 1e-7:
        weights = np.eye(1, len(ids), 0).ravel()
    else:
        inv = 1.0 / np.maximum(ds, 1e-6) ** 2
        weights = inv / inv.sum()
    return ids, weights


def _station_frames(centerline: np.ndarray):
    n = len(centerline)
    tangents = np.zeros((n, 3), float)
    for i in range(n):
        if i == 0:
            d = centerline[1] - centerline[0]
        elif i == n - 1:
            d = centerline[-1] - centerline[-2]
        else:
            d = centerline[i + 1] - centerline[i - 1]
        tangents[i] = d / max(np.linalg.norm(d), 1e-12)
    normals = np.zeros((n, 3), float)
    binormals = np.zeros((n, 3), float)
    prev_n = None
    for i, (p, t) in enumerate(zip(centerline, tangents)):
        radial = np.array([p[0], p[1], 0.0], float)
        radial -= radial.dot(t) * t
        if np.linalg.norm(radial) < 1e-8:
            radial = np.cross(t, np.array([0.0, 0.0, 1.0]))
        if np.linalg.norm(radial) < 1e-8:
            radial = np.array([1.0, 0.0, 0.0])
        nvec = radial / max(np.linalg.norm(radial), 1e-12)
        if prev_n is not None and np.dot(prev_n, nvec) < 0:
            nvec = -nvec
        bvec = np.cross(t, nvec)
        bvec /= max(np.linalg.norm(bvec), 1e-12)
        normals[i] = nvec
        binormals[i] = bvec
        prev_n = nvec
    return tangents, normals, binormals


def _curvature_from_polyline(points: np.ndarray):
    n = len(points)
    if n < 3:
        return np.zeros(n, float)
    tangents, *_ = _station_frames(points)
    curvature = np.zeros(n, float)
    for i in range(1, n - 1):
        ds = 0.5 * (np.linalg.norm(points[i] - points[i - 1]) + np.linalg.norm(points[i + 1] - points[i]))
        dt = tangents[i + 1] - tangents[i - 1]
        curvature[i] = np.linalg.norm(dt) / max(2.0 * ds, 1e-9)
    curvature[0] = curvature[1]
    curvature[-1] = curvature[-2]
    return curvature


def _build_ribbon_mesh(centerline: np.ndarray, deformed_centerline: np.ndarray, width_mm: float, displacement: np.ndarray, field: np.ndarray):
    _, _, binormals = _station_frames(centerline)
    n = len(centerline)
    if n < 2:
        return {'vertices_mm': [], 'faces': [], 'displacement_mm': [], 'field': []}
    half = width_mm * 0.5
    verts = []
    disp = []
    field_v = []
    for i in range(n):
        for sign in (-1.0, 1.0):
            base = centerline[i] + sign * half * binormals[i]
            verts.append(base)
            disp.append(displacement[i])
            field_v.append(float(field[i]))
    faces = []
    for i in range(n - 1):
        a = 2 * i
        b = a + 1
        c = a + 2
        d = a + 3
        faces.append([a, c, b])
        faces.append([b, c, d])
    return {
        'vertices_mm': np.round(np.asarray(verts), 6).tolist(),
        'faces': faces,
        'displacement_mm': np.round(np.asarray(disp), 8).tolist(),
        'field': np.round(np.asarray(field_v), 8).tolist(),
    }


@dataclass
class ShellFilmSummary:
    film_index: int
    member_index: int
    span_mm: float
    width_mm: float
    thickness_mm: float
    membrane_strain_mean: float
    membrane_strain_max_abs: float
    curvature_max_1_mm: float
    top_fiber_strain_max_abs: float
    top_stress_MPa_max_abs: float
    eq_stress_MPa_max_abs: float
    interfacial_shear_MPa_max_abs: float
    shell_energy_Nmm: float
    estimated_charge_pC: float
    mesh: dict


def resolve_laminate_shell(mesh, family: str, genome: dict, displacement) -> dict | None:
    """Resolve a reduced thin-ribbon laminate shell on top of solved substrate motion.

    The shell inherits kinematics from the substrate FEM solution and computes a
    thin-shell stress/strain estimate for each PVDF ribbon. It is a post-process,
    not a coupled shell-solid solve.
    """
    U = np.asarray(displacement, float)
    if U.ndim == 1:
        if U.size != 3 * len(mesh.nodes):
            raise ValueError('Laminate shell displacement has invalid size')
        U = U.reshape(-1, 3)
    if U.shape != (len(mesh.nodes), 3):
        raise ValueError('Laminate shell displacement shape mismatch')
    paths = structural_struts(family, genome)
    chosen = choose_film_members(paths, genome)
    if not chosen:
        return None
    tree = cKDTree(mesh.nodes)
    nu = POISSON_PVDF
    per_film = []
    shell_meshes = []
    total_energy = 0.0
    total_charge = 0.0
    stress_max = 0.0
    shear_max = 0.0
    top_strain_max = 0.0
    shell_feasible = True
    warnings = []
    for film_idx, member_index in enumerate(chosen):
        pts, r, tag = paths[int(member_index)]
        radius = float(np.mean([_profile_radius(r, u, genome, tag) for u in (0.3, 0.5, 0.7)]))
        surf_pts, span = film_stations(pts, genome, radius, mesh.pitch_mm)
        props = effective_film_properties(genome, span, radius)
        station_disp = []
        mapped = []
        for xyz in surf_pts:
            ids, w = _nearest4(tree, mesh.nodes, xyz, mesh.pitch_mm)
            mapped.append((ids, w))
            station_disp.append(w @ U[ids])
        station_disp = np.asarray(station_disp, float)
        deformed = surf_pts + station_disp
        seg_und = np.linalg.norm(np.diff(surf_pts, axis=0), axis=1)
        seg_def = np.linalg.norm(np.diff(deformed, axis=0), axis=1)
        membrane = (seg_def - seg_und) / np.maximum(seg_und, 1e-9)
        membrane_station = np.r_[membrane[0], 0.5 * (membrane[:-1] + membrane[1:]), membrane[-1]]
        curvature = _curvature_from_polyline(deformed)
        tf = props['film_thickness_mm']
        top_strain = membrane_station + 0.5 * tf * curvature
        bottom_strain = membrane_station - 0.5 * tf * curvature
        Ex = props['pvdf_E_MPa'] / max(1.0 - nu ** 2, 1e-9)
        sx_top = Ex * top_strain
        sx_bottom = Ex * bottom_strain
        transfer = props['shear_lag_transfer']
        shear = np.abs(props['pvdf_E_MPa'] * props['film_thickness_mm'] * (1.0 - transfer) * membrane_station / max(props['adhesive_thickness_mm'], 1e-6))
        eq = np.sqrt(np.maximum(0.0, sx_top ** 2 + 3.0 * shear ** 2))
        ds_station = np.r_[seg_und[0], 0.5 * (seg_und[:-1] + seg_und[1:]), seg_und[-1]]
        A11 = props['pvdf_E_MPa'] * tf * props['effective_width_mm']
        D11 = props['pvdf_E_MPa'] * (tf ** 3) * props['effective_width_mm'] / 12.0
        shell_energy = float(0.5 * np.sum((A11 * membrane_station ** 2 + D11 * curvature ** 2) * ds_station))
        est_charge = float(-23.0 * props['pvdf_E_MPa'] * props['effective_width_mm'] * tf * membrane_station.mean())
        field = eq
        ribbon_mesh = _build_ribbon_mesh(surf_pts, deformed, props['effective_width_mm'], station_disp, field)
        film = ShellFilmSummary(
            film_index=int(film_idx),
            member_index=int(member_index),
            span_mm=float(span),
            width_mm=float(props['effective_width_mm']),
            thickness_mm=float(tf),
            membrane_strain_mean=float(np.mean(membrane_station)),
            membrane_strain_max_abs=float(np.max(np.abs(membrane_station))),
            curvature_max_1_mm=float(np.max(np.abs(curvature))),
            top_fiber_strain_max_abs=float(np.max(np.abs(np.r_[top_strain, bottom_strain]))),
            top_stress_MPa_max_abs=float(np.max(np.abs(np.r_[sx_top, sx_bottom]))),
            eq_stress_MPa_max_abs=float(np.max(eq)),
            interfacial_shear_MPa_max_abs=float(np.max(shear)),
            shell_energy_Nmm=shell_energy,
            estimated_charge_pC=est_charge,
            mesh=ribbon_mesh,
        )
        d = film.__dict__.copy()
        per_film.append(d)
        shell_meshes.append({
            'film_index': int(film_idx),
            'member_index': int(member_index),
            'name': f'PVDF film {film_idx + 1}',
            **ribbon_mesh,
        })
        total_energy += shell_energy
        total_charge += est_charge
        stress_max = max(stress_max, d['eq_stress_MPa_max_abs'])
        shear_max = max(shear_max, d['interfacial_shear_MPa_max_abs'])
        top_strain_max = max(top_strain_max, d['top_fiber_strain_max_abs'])
        if d['top_fiber_strain_max_abs'] > 0.025:
            shell_feasible = False
            warnings.append(f"film {film_idx + 1}: top fiber strain {d['top_fiber_strain_max_abs']:.4f} exceeds 2.5% screen")
        if d['interfacial_shear_MPa_max_abs'] > 12.0:
            shell_feasible = False
            warnings.append(f"film {film_idx + 1}: interfacial shear {d['interfacial_shear_MPa_max_abs']:.2f} MPa exceeds screen")
    score = 100.0 * math.exp(-max(0.0, top_strain_max - 0.006) * 35.0) * math.exp(-max(0.0, shear_max - 3.0) * 0.35)
    score = max(0.0, min(100.0, float(score)))
    return {
        'model': 'reduced_ribbon_shell_postprocess',
        'coupling': 'postprocessed_from_substrate_displacement',
        'film_count': len(per_film),
        'poisson_ratio_assumed': nu,
        'total_shell_energy_Nmm': float(total_energy),
        'total_estimated_charge_pC': float(total_charge),
        'max_eq_stress_MPa': float(stress_max),
        'max_interfacial_shear_MPa': float(shear_max),
        'max_top_fiber_strain_abs': float(top_strain_max),
        'shell_score': round(score, 5),
        'feasible_shell_screen': bool(shell_feasible),
        'warnings': warnings,
        'per_film': per_film,
        'graphics': {
            'mode': 'ribbon_mesh3d',
            'field_name': 'eq_stress_MPa',
            'deformation_embedded': True,
            'films': shell_meshes,
            'note': 'Reduced ribbon-shell visualization for PVDF strips; geometry follows the solved substrate displacement field.'
        },
        'limitations': [
            'Post-processed thin-ribbon shell, not a fully coupled shell-solid contact solve',
            'Adhesive enters via reduced shear-lag transfer and an interfacial shear proxy',
            'No peel, delamination, electrode layers, nonlinear material law or electric-field feedback',
        ],
    }
