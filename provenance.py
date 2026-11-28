"""Shared numerical source identity for current NeuroSkin experiments."""
from hashlib import sha256
from pathlib import Path


SOURCE_SCHEMA = 'neuroskin.numerical_source.v1'
NUMERICAL_SOURCES = (
    'advanced.py', 'archetype_geometry.py', 'audit_combine.py', 'audit_scheduler.py',
    'beam_fem.py', 'electromechanics.py', 'electronics_budget.py',
    'electronics_evolution.py', 'engine.py', 'evaluation_v30.py', 'evolution_continuation.py',
    'finalist_selection.py', 'full_evaluation.py', 'geometry_fixes.py',
    'gpu_sparse_fem.py', 'hybrid_geometry.py', 'hybrid_library.py',
    'laminate_fem.py', 'laminate_shell.py', 'manual_evaluation.py',
    'matrixfree_fem.py', 'membrane_tile.py', 'neuroskin_multiscale.py',
    'neuroskin_v30/material_regions.py', 'neuroskin_v30/mesh.py',
    'neuroskin_v30/nonlinear_fem.py', 'nonlinear_skin_tile.py', 'optimization.py',
    'orientation_study.py', 'physical_fem.py', 'piezoelectric.py', 'population_pareto.py',
    'provenance.py', 'pvdf_array.py', 'pvdf_physics.py', 'readout_gain.py',
    'recovery_sim.py', 'reference_fem.py', 'relaxed_membrane.py', 'search_space.py',
    'seed_library.py', 'selection_refinement.py', 'sensor_fusion.py',
    'sensor_metrics.py', 'spatial_validation.py', 'symmetry_geometry.py',
    'tile_optimization.py', 'validation_contract.py', 'validation_design.py',
    'validation_protocol_v30.json',
)


def numerical_source_hash(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    digest = sha256(SOURCE_SCHEMA.encode('ascii') + b'\0')
    for name in sorted(NUMERICAL_SOURCES):
        digest.update(name.encode('utf-8') + b'\0' + (root / name).read_bytes() + b'\0')
    return digest.hexdigest()
