"""Stable, physically anchored visual representation of a PVDF ribbon.

This is render geometry, not a finite element shell or a manufactured patch.
The strip follows a chosen curved strut, with stable radial normals, width
limited by the support radius, and a finite thickness. It replaces the old
single arbitrary rigid, diagonally-rotated rectangle.
"""
from __future__ import annotations
import numpy as np
import trimesh

def _unit(v):
    length=float(np.linalg.norm(v))
    return np.asarray(v,dtype=float)/max(length,1e-12)

def pvdf_ribbon(points, member_radius, position=.5, length_mm=4., width_mm=2.5, thickness_mm=.028):
    pts=np.asarray(points,dtype=float)
    if len(pts)<2 or not np.isfinite(pts).all() or member_radius<=0:raise ValueError('Invalid support path')
    d=np.linalg.norm(np.diff(pts,axis=0),axis=1)
    arclength=np.r_[0.,np.cumsum(d)]
    total=float(arclength[-1])
    if total<1e-4:raise ValueError('Degenerate support path')
    mid=np.clip(position,.04,.96)*total
    span=max(.35,min(float(length_mm),total*.82))
    low=max(0.07*total,mid-span/2)
    high=min(.93*total,mid+span/2)
    if high-low<.2:high=min(.96*total,low+.2)
    # Dense resampling and a local moving frame; no uncontrolled roll angle.
    s=np.linspace(low,high,max(7,int((high-low)/.24)+1))
    center=np.column_stack([np.interp(s,arclength,pts[:,k]) for k in range(3)])
    tangents=np.gradient(center,axis=0)
    thick=max(.025,float(thickness_mm))
    width=min(max(.18,float(width_mm)),max(.22,1.45*member_radius))
    verts=[];prev_normal=None
    for c,t in zip(center,tangents):
        tangent=_unit(t)
        radial=np.array([c[0],c[1],0.],float)
        radial-=np.dot(radial,tangent)*tangent
        if np.linalg.norm(radial)<1e-6:
            radial=np.cross(tangent,[0,0,1.])
        if np.linalg.norm(radial)<1e-6:
            radial=np.array([1.,0.,0.])
        normal=_unit(radial)
        if prev_normal is not None and np.dot(prev_normal,normal)<0:normal=-normal
        across=_unit(np.cross(tangent,normal))
        normal=_unit(np.cross(across,tangent))
        prev_normal=normal
        # Thin strip is on the external surface of its support rather than
        # suspended through its middle. Four corners of each cross-section.
        base=c+normal*(member_radius+.012+thick*.5)
        a=base+across*(width/2)
        b=base-across*(width/2)
        verts.extend([a+normal*thick/2,b+normal*thick/2,
                      a-normal*thick/2,b-normal*thick/2])
    faces=[]
    for i in range(len(center)-1):
        a=4*i;b=4*(i+1)
        for j,k in ((0,1),(1,3),(3,2),(2,0)):
            faces.extend([(a+j,a+k,b+k),(a+j,b+k,b+j)])
    faces.extend([(0,2,1),(1,2,3)])
    e=4*(len(center)-1)
    faces.extend([(e,e+1,e+2),(e+1,e+3,e+2)])
    mesh=trimesh.Trimesh(vertices=np.asarray(verts),faces=np.asarray(faces),process=False)
    # winding correctness not material to Plotly, but exporter expects a closed mesh.
    return mesh
