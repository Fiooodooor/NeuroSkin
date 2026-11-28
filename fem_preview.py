"""Display-only standard load cases, with shared mesh and bounded surface payload.

Never use sampled fields for qualification or extrema. All metrics are
computed on the original FE solution. No additional FEM solve is required.
"""
import numpy as np

PREVIEW_CASES = ('press_center','press_x_plus','shear_x','torsion_z')
MAX_TRIANGLES = 20_000
FIELD_KEYS = ('displacement_mm','stress_vm_MPa','principal_strain')


def pack_previews(fields, load_cases, boundary_results=None):
    """Deduplicate identical reference topology across standard load cases."""
    first=fields[PREVIEW_CASES[0]]
    vertices=np.asarray(first['vertices_mm'],float)
    faces=np.asarray(first['faces'],dtype=np.int64)
    if vertices.ndim!=2 or vertices.shape[1]!=3 or not len(vertices) or not np.isfinite(vertices).all():
        raise ValueError('Invalid preview vertices')
    if faces.ndim!=2 or faces.shape[1]!=3 or not len(faces) or faces.min()<0 or faces.max()>=len(vertices):
        raise ValueError('Invalid preview triangles')
    count=len(faces)
    step=max(1,(count+MAX_TRIANGLES-1)//MAX_TRIANGLES)
    used,inv=np.unique(faces[::step].ravel(),return_inverse=True)
    cases={}
    for name in PREVIEW_CASES:
        f=fields[name]
        if not np.array_equal(vertices,np.asarray(f['vertices_mm'])) or not np.array_equal(faces,np.asarray(f['faces'])):
            raise ValueError('Standard FEM previews must share reference topology')
        case={}
        for key in FIELD_KEYS:
            values=np.asarray(f[key],float)
            shape=(len(vertices),3) if key=='displacement_mm' else (len(vertices),)
            if values.shape!=shape or not np.isfinite(values).all():raise ValueError('Invalid preview field: '+key)
            case[key]=values[used].tolist()
        m=load_cases[name]
        case['load']={k:m[k] for k in ('load_force_N','offset_mm','torque_z_Nmm') if k in m}
        case['metrics']={k:m[k] for k in ('max_displacement_mm','max_von_mises_MPa','max_abs_principal_strain','force_equilibrium_relative','moment_equilibrium_relative') if k in m}
        if boundary_results is not None:
            extra=boundary_results[name]
            for k in ('boundary_vectors','boundary_error'):
                if k in extra:case[k]=extra[k]
        cases[name]=case
    source=int(first.get('source_surface_triangles',count))
    return {'schema':1,'vertices_mm':vertices[used].tolist(),'faces':inv.reshape(-1,3).tolist(),
            'cases':cases,'case_order':list(PREVIEW_CASES),'source_surface_triangles':source,
            'display_surface_triangles':len(faces[::step]),'display_downsampled':len(faces[::step])<source,
            'note':'Display-only sampled FE fields; qualification and extrema use full original solutions.'}
