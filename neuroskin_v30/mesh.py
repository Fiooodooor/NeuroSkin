"""Validated linear tetrahedral geometry (coordinates mm, volume mm³).

No mesh repair is performed implicitly: negative, singular and mixed-volume
cells are rejected. This avoids silently masking an invalid CAD→FEM pipeline.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np

class MeshError(ValueError):
    """Invalid FE geometry or unsupported element topology."""

@dataclass(frozen=True)
class TetMesh:
    nodes: np.ndarray
    tets: np.ndarray
    min_volume_mm3: float = 1e-12

    def __post_init__(self):
        x = np.asarray(self.nodes, dtype=float)
        raw = np.asarray(self.tets)
        if raw.dtype.kind not in 'iu':
            raise MeshError('tetrahedral connectivity must use integer indices')
        t = raw.astype(np.int64,copy=False)
        if not np.isfinite(self.min_volume_mm3) or self.min_volume_mm3 <= 0:
            raise MeshError('minimum cell volume must be positive finite')
        if x.ndim != 2 or x.shape[1] != 3 or len(x) < 4:
            raise MeshError("nodes must be [n,3] with at least four nodes")
        if t.ndim != 2 or t.shape[1] != 4 or len(t) == 0:
            raise MeshError("tets must be a nonempty [m,4] array")
        if not np.all(np.isfinite(x)) or np.any(t < 0) or np.any(t >= len(x)):
            raise MeshError("nonfinite node coordinates or invalid indices")
        if np.any(np.sort(t,axis=1)[:,1:] == np.sort(t,axis=1)[:,:-1]):
            raise MeshError("tetrahedron contains duplicate node")
        if len(np.unique(t)) != len(x):
            raise MeshError("orphan nodes in FEM mesh: delete unused vertices before solving")
        canonical_cells = np.sort(t,axis=1)
        if len(np.unique(canonical_cells,axis=0))!=len(t):
            raise MeshError('duplicate tetrahedra')
        # A floating disconnected component makes a fixed-base, single-body
        # equilibrium ill-posed. Separate nonbonded bodies require a true
        # multi-body contact solver, which this module explicitly is not.
        # Require face-connected cells, not merely shared vertices or edges.
        faces = np.sort(np.concatenate([t[:,[0,1,2]],t[:,[0,1,3]],t[:,[0,2,3]],t[:,[1,2,3]]]),axis=1)
        owners = np.tile(np.arange(len(t)),4)
        _,inv,counts=np.unique(faces,axis=0,return_inverse=True,return_counts=True)
        if np.any(counts>2):raise MeshError('nonmanifold tetrahedral face')
        parent=np.arange(len(t),dtype=np.int64)
        def find(a):
            while parent[a]!=a:
                parent[a]=parent[parent[a]];a=parent[a]
            return int(a)
        ordered=np.argsort(inv); paired=np.flatnonzero(counts==2)
        offsets=np.r_[0,np.cumsum(counts)]
        for face in paired:
            a,b=owners[ordered[offsets[face]:offsets[face]+2]]
            parent[find(int(a))]=find(int(b))
        if len({find(i) for i in range(len(t))})!=1:
            raise MeshError('disconnected tetrahedral components: face connectivity required')
        edges = x[t[:,1:]] - x[t[:,0,None]]
        six_vol = np.linalg.det(edges)
        if not np.all(np.isfinite(six_vol)) or np.any(six_vol <= 6*self.min_volume_mm3):
            raise MeshError("singular, inverted, or near-zero-volume tetrahedra")
        object.__setattr__(self, 'nodes', x.copy())
        object.__setattr__(self, 'tets', t.copy())
        self.nodes.setflags(write=False)
        self.tets.setflags(write=False)

    @property
    def volume_mm3(self) -> float:
        d = self.nodes[self.tets[:,1:]] - self.nodes[self.tets[:,0,None]]
        return float(np.linalg.det(d).sum()/6.)

    def metrics(self) -> dict:
        d = self.nodes[self.tets[:,1:]] - self.nodes[self.tets[:,0,None]]
        v = np.linalg.det(d)/6.
        edge_pairs=((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
        lengths=np.stack([np.linalg.norm(self.nodes[self.tets[:,a]]-self.nodes[self.tets[:,b]],axis=1)
                          for a,b in edge_pairs],axis=1)
        return {'nodes':int(len(self.nodes)),'tetrahedra':int(len(self.tets)),
                'volume_mm3':self.volume_mm3,'min_cell_volume_mm3':float(v.min()),
                'min_edge_mm':float(lengths.min()),'max_edge_mm':float(lengths.max()),
                'edge_ratio_max':float(np.max(lengths.max(axis=1)/lengths.min(axis=1)))}


def box_mesh(nx:int=1,ny:int=1,nz:int=1,lengths_mm=(1.,1.,1.)) -> TetMesh:
    """Structured hexahedral grid split into six positively oriented TET4/cell.

    Only for verification geometries; real receptor CAD requires conforming
    Gmsh tetrahedra and independent mesh convergence evidence.
    """
    sizes=(nx,ny,nz)
    if any(not isinstance(n,int) or isinstance(n,bool) or n<1 or n>100 for n in sizes):
        raise MeshError("subdivisions must be integer in 1..100")
    if len(lengths_mm)!=3 or any(not np.isfinite(a) or a<=0 for a in lengths_mm):
        raise MeshError("positive box dimensions required")
    xx,yy,zz=[np.linspace(0,float(L),n+1) for n,L in zip(sizes,lengths_mm)]
    nodes=np.array([(x,y,z) for z in zz for y in yy for x in xx],float)
    def idx(i,j,k): return i+(nx+1)*(j+(ny+1)*k)
    pattern=((0,1,2,6),(0,2,3,6),(0,3,7,6),(0,7,4,6),(0,4,5,6),(0,5,1,6))
    out=[]
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                c=(idx(i,j,k),idx(i+1,j,k),idx(i+1,j+1,k),idx(i,j+1,k),
                   idx(i,j,k+1),idx(i+1,j,k+1),idx(i+1,j+1,k+1),idx(i,j+1,k+1))
                out.extend([[c[a] for a in tet] for tet in pattern])
    return TetMesh(nodes,np.array(out,dtype=np.int64))


def read_tetra_mesh(path: str | Path, *, length_unit: str='mm') -> TetMesh:
    """Import exclusively TET4 from meshio-supported formats (e.g. .msh).

    Hard reject mixed tet4/tet10 and other volume element families, rather
    than silently losing volume or using the wrong scale.
    """
    if length_unit not in ('mm','m'):
        raise MeshError('length_unit must be explicitly mm or m')
    try:
        import meshio
    except ImportError as exc:
        raise RuntimeError('meshio is required to import Gmsh volume meshes') from exc
    m=meshio.read(str(path))
    tet_blocks=[np.asarray(b.data) for b in m.cells if b.type=='tetra']
    unsupported=[b.type for b in m.cells if b.type!='tetra' and not b.type.startswith(('vertex','line','triangle','quad'))]
    if unsupported:
        raise MeshError(f'Unsupported volume cells: {unsupported}; generate TET4 only')
    if not tet_blocks:
        raise MeshError('No linear tetrahedra found')
    x=np.asarray(m.points,dtype=float)[:,:3].copy()*(1000. if length_unit=='m' else 1.)
    return TetMesh(x,np.concatenate(tet_blocks,axis=0))


def hex8_to_tet4(nodes, cells):
    """Split structured HEX8 in NeuroSkin CORNERS order, without moving nodes.

    This is still a voxel staircase geometry, not a conforming CAD mesh.
    """
    cells=np.asarray(cells)
    if cells.ndim!=2 or cells.shape[1]!=8 or cells.dtype.kind not in 'iu':
        raise MeshError('expected integer HEX8 connectivity')
    pattern=np.array(((0,1,2,6),(0,2,3,6),(0,3,7,6),(0,7,4,6),(0,4,5,6),(0,5,1,6)))
    return TetMesh(nodes,cells[:,pattern].reshape(-1,4))
