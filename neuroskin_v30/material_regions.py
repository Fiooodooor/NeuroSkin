"""Explicit bonded material IDs for verification boxes and voxel receptor regions."""
import numpy as np


def layered_box_ids(mesh):
    z=mesh.nodes[mesh.tets,2].mean(axis=1)
    return (z>(mesh.nodes[:,2].min()+mesh.nodes[:,2].max())/2).astype(int)


def receptor_plate_ids(mesh,genome):
    """Reuse the actual voxel plate occupancy predicates; plate wins overlaps."""
    c=.5*(mesh.nodes[mesh.elements[:,0]]+mesh.nodes[mesh.elements[:,6]])
    x,y,z=c.T;h=mesh.pitch_mm;H=float(genome['height'])
    pad=float(genome.get('pad_radius',3.2))+.4
    hybrid=genome.get('hybrid_id','none') not in ('none',None,'')
    # Base geometry has different shapes for quadrant; at z<=.85 the
    # contiguous voxel union is treated as plate material only where base
    # geometry is actually present. Infer quadrant via caller-provided family.
    family=genome.get('_material_family')
    if family=='quadrant' and not hybrid:
        r=float(genome['radius'])*.77
        base=np.zeros(len(c),bool)
        for sx in (-1,1):
            for sy in (-1,1):base|=(np.abs(x-sx*r)<=1.65)&(np.abs(y-sy*r)<=1.65)
    else:base=x*x+y*y<=9.3**2
    plate=base&(z<=.85)
    plate|=(z>=H-max(.65,h*.75))&(z<=H+max(.45,h*.45))&((x-float(genome.get('pad_offset_x',0.)))**2+(y-float(genome.get('pad_offset_y',0.)))**2<=pad**2)
    if hybrid:
        from hybrid_geometry import mid_height,mid_radius
        plate|=(np.abs(z-mid_height(genome))<=max(float(genome.get('hybrid_plate_thickness',.65))*.5,h*.55))&(x*x+y*y<=mid_radius(genome)**2)
    if not np.any(plate) or np.all(plate):raise ValueError('Voxel pitch does not resolve both material regions')
    return np.repeat(plate.astype(int),6)


def surface_topology(mesh,material_ids):
    t=mesh.tets
    faces=np.concatenate([t[:,[1,2,3]],t[:,[0,3,2]],t[:,[0,1,3]],t[:,[0,2,1]]])
    _,inv,counts=np.unique(np.sort(faces,axis=1),axis=0,return_inverse=True,return_counts=True)
    mask=counts[inv]==1
    outer=faces[mask];owners=np.tile(np.arange(len(t)),4)[mask]
    used,remap=np.unique(outer.ravel(),return_inverse=True)
    return used,{'vertices_mm':mesh.nodes[used].tolist(),'faces':remap.reshape(-1,3).tolist(),
                 'face_material_ids':np.asarray(material_ids)[owners].tolist()}
