"""Memory-controlled matrix-free 3-D HEX8 elasticity operator.

Uses the SAME gauss-integrated element stiffness as the assembled sparse solver.
No global stiffness matrix is constructed.  `numba` is an optional performance
accelerator; large fine grids require it for practical computation.
"""
from __future__ import annotations
import time
import threading
import numpy as np
from scipy.sparse.linalg import LinearOperator, cg
try:
    from numba import njit
except ImportError:
    njit = None


def _element_matvec_py(edof, ke, x, ndofs):
    out=np.zeros(ndofs, dtype=np.float64)
    for row in edof:
        np.add.at(out, row, ke@x[row])
    return out


def _element_diag_py(edof, diag_ke, ndofs):
    out=np.zeros(ndofs, dtype=np.float64)
    np.add.at(out, edof.ravel(), np.tile(diag_ke, len(edof)))
    return out

if njit:
    @njit(cache=True,nogil=True)
    def _element_matvec_fast(edof, ke, x, ndofs):
        out=np.zeros(ndofs, dtype=np.float64)
        for e in range(edof.shape[0]):
            for i in range(24):
                val=0.0
                for j in range(24):
                    val+=ke[i,j]*x[edof[e,j]]
                out[edof[e,i]]+=val
        return out

    @njit(cache=True)
    def _element_blocks_fast(edof, ke, n_nodes):
        blocks=np.zeros((n_nodes,3,3),dtype=np.float64)
        for e in range(edof.shape[0]):
            for a in range(8):
                node=edof[e,3*a]//3
                for i in range(3):
                    for j in range(3):
                        blocks[node,i,j]+=ke[3*a+i,3*a+j]
        return blocks

    @njit(cache=True)
    def _element_diag_fast(edof, diag_ke, ndofs):
        out=np.zeros(ndofs, dtype=np.float64)
        for e in range(edof.shape[0]):
            for i in range(24):
                out[edof[e,i]]+=diag_ke[i]
        return out
else:
    _element_matvec_fast=None
    _element_diag_fast=None
    _element_blocks_fast=None


class MatrixFreeElasticity:
    def __init__(self, edof, ke, free, ndofs, *, maxiter=5000, rtol=5e-5, timeout_s=180.0, extra_stiffness=None):
        self.edof=np.ascontiguousarray(edof,dtype=np.int32)
        self.ke=np.ascontiguousarray(ke,dtype=np.float64)
        self.free=np.asarray(free,dtype=np.int32)
        self.ndofs=int(ndofs)
        self.maxiter=int(maxiter)
        self.rtol=float(rtol)
        self.timeout_s=float(timeout_s)
        self.extra_stiffness=extra_stiffness
        self.accelerated=njit is not None
        if not self.accelerated and len(self.edof)>5_000:
            raise RuntimeError('High-resolution matrix-free FEM requires optional numba; install with pip install numba')
        if self.accelerated:
            self.diag=_element_diag_fast(self.edof,np.diag(self.ke),self.ndofs)
        else:
            self.diag=_element_diag_py(self.edof,np.diag(self.ke),self.ndofs)
        if self.extra_stiffness is not None:
            self.diag += np.asarray(self.extra_stiffness.diagonal(),float)
        diagonal=self.diag[self.free]
        if np.any(diagonal <= 0) or not np.all(np.isfinite(diagonal)):
            raise RuntimeError('Matrix-free FEM: invalid diagonal, disconnected or unstable structure')
        self.invdiag=1/diagonal
        n=len(self.free)
        self.A=LinearOperator((n,n),matvec=self._free_matvec,dtype=np.float64)
        self.block_inv=None
        if self.accelerated and self.extra_stiffness is None:
            blocks=_element_blocks_fast(self.edof,self.ke,self.ndofs//3)
            try:
                self.block_inv=np.linalg.inv(blocks)
            except np.linalg.LinAlgError:
                self.block_inv=None
        self.M=LinearOperator((n,n),matvec=self._precondition,dtype=np.float64)
        self._diagnostics=threading.local()

    @property
    def last_iterations(self):
        return getattr(self._diagnostics,"iterations",0)

    @property
    def last_relative_residual(self):
        return getattr(self._diagnostics,"residual",None)

    def warmup(self):
        """Compile the shared read-only kernel before concurrent RHS solves."""
        self._global_matvec(np.zeros(self.ndofs,dtype=np.float64))

    def _precondition(self,v):
        if self.block_inv is None:
            return self.invdiag*v
        full=np.zeros(self.ndofs,dtype=np.float64)
        full[self.free]=v
        out=np.einsum('nij,nj->ni',self.block_inv,full.reshape(-1,3),optimize=True).reshape(-1)
        return out[self.free]

    def _global_matvec(self,x):
        base=(_element_matvec_fast(self.edof,self.ke,np.asarray(x,dtype=np.float64),self.ndofs) if self.accelerated
              else _element_matvec_py(self.edof,self.ke,np.asarray(x,dtype=np.float64),self.ndofs))
        if self.extra_stiffness is not None:
            base += self.extra_stiffness@x
        return base

    def _free_matvec(self,free_vec):
        x=np.zeros(self.ndofs)
        x[self.free]=free_vec
        return self._global_matvec(x)[self.free]

    def multiply(self,x):
        return self._global_matvec(np.asarray(x,dtype=np.float64))

    def solve(self,load):
        rhs=np.asarray(load,dtype=np.float64)[self.free]
        self._diagnostics.iterations=0
        self._diagnostics.residual=None
        started=time.monotonic()
        def tick(_):
            self._diagnostics.iterations+=1
            if time.monotonic()-started>self.timeout_s:
                raise RuntimeError(f'Matrix-free CG timed out after {self.timeout_s:g} seconds ({self.last_iterations} iterations). Use a coarser pitch, increase timeout, or improve preconditioning.')
        x,info=cg(self.A,rhs,M=self.M,rtol=self.rtol,atol=0.0,maxiter=self.maxiter,callback=tick)
        if not np.all(np.isfinite(x)):
            raise RuntimeError('Matrix-free iterative FEM returned a non-finite displacement')
        u=np.zeros(self.ndofs)
        u[self.free]=x
        residual=np.linalg.norm(self.multiply(u)[self.free]-rhs)/max(np.linalg.norm(rhs),1e-12)
        self._diagnostics.residual=float(residual)
        if info != 0 or residual > max(self.rtol*5,1e-4):
            raise RuntimeError(f'Matrix-free CG did not converge: info={info}, iterations={self.last_iterations}, residual={residual:.3g}. Increase maxiter, use a coarser pitch or a stronger preconditioner.')
        return u
