# NeuroSkin 1.3 — refined mechanical FEM

This release adds a **fine discretization of real structural mechanics**, with an explicit choice of backend. The two backends have **different physical assumptions** and must never be conflated.

## Backends and discretization

| Backend | Numerical elements | Field solved | Pitch | Intended use |
|---|---|---|---|---|
| `beam` | 3D Euler-Bernoulli frame (6 DOF/node), rigid-pad coupling, fixed bases | 3D translations, rotations, beam stress estimates | 0.15625–0.3125 mm recommended | Thin, curved members and rapid evolutionary audits |
| `hex8` | 3D continuum 8-node voxel HEX8 (3 DOF/node) | 3D displacements and strain/stress in occupied solid voxels | 0.3125 mm demonstrated; 0.15625 mm experimental/expensive | Volumetric check and mesh sensitivity |
| `auto` | Beam when pitch <0.7 mm; HEX8 otherwise | Depends on backend | .25 mm default | Responsive GUI / Top-3 evolution |

**4× / 8×** means pitch `1.25 / 4 = 0.3125 mm` and `1.25 / 8 = 0.15625 mm`.

For a fixed 3D volume, dividing the pitch by 8 can increase element counts up to approximately 512×. The **beam** backend subdivides only member centrelines: that does not provide 8× resolution through the cross-section and cannot recover solid stress concentrations. The **solid** backend can build the smaller voxels and uses a matrix-free CG solver (optional Numba acceleration) when the model is large, subject to time, RAM and numerical convergence limitations. **Do not confuse generated mesh with converged solution**.

## GUI usage

Start `python server.py --cores 8 --open --port 8765` and open **Mechanical FEM** under the model view. Select **FEM solver** and **Mesh pitch** independently, then press **Compute real FEM**.

Default GUI + evolutionary Top-3 use `.25 mm` space-frame FEM. Choose `.3125` (4×), `.15625` (8×). Force `Solid HEX8` for an expensive volumetric run. The archived genotypes are backwards-compatible and are remeshed by the current geometry backend; compare provenance hashes before comparing old and new fitness.

## CLI recipes

Fast 8× beam FE and finer convergence comparison:

```bash
python fem_cli.py --backend beam --family crown --seed 41 \
  --pitch 0.15625 --force 0.02 --convergence --out fine_beam
```

Real 4× solid FE. Install optional Numba for the memory-saving matrix-free CG:

```bash
pip install -r requirements.txt
python fem_cli.py --backend hex8 --family crown --seed 41 \
  --pitch 0.3125 --force 0.02 --out solid_4x
```

8× solid mesh is an experimental heavy mode. In this development environment mesh generation completed, but an 8× solid solve did **not** finish within the tool time limit. It is **not validated** and may need substantially more RAM, better preconditioning or a tetrahedral/adaptive mesh. Avoid using 32 concurrent very-large solid solves without explicit memory management.

Use 8× beam FEM for candidate generation and preliminary ranking; use more accurate independent FE (solid FEM with convergence) and experiments before manufacturing.

## Contact fallback

The old `Contact patch only has 0 nodes` failure is repaired for coarse HEX8: the solver tries a wider radius and then the nearest connected top-node cluster. It reports `contact_patch_mode`, `loaded_nodes` and `contact_patch_radius_used_mm`. Fine beam FEM imposes normal/shear/torsion at a rigid top-pad master (no artificial nodal contact patch), so the 0-node issue cannot arise. Neither backend models unilateral contact, friction or local pressure distribution.

## Scope/limits

- Small-strain, small-rotation linear elasticity. Large deformation is **not** physical: beam audit marks candidates with displacement/height >15% or high stress-derived strain as non-feasible. Nonlinear silicone, self-contact, buckling, viscoelasticity, fatigue and embedded PVDF effects remain future tasks.
- Beam stresses from linear beam theory are not continuum von Mises stress maxima at junctions.
- The fast evolutionary surrogate still ranks the whole population. The three finalists undergo FEM and synthetic sensor validation. Electrical sensing is not a coupled field solve.
- Smooth tapered 3D tube visualization is still conceptual CAD assembled from parts, not fabrication-qualified.
- Number of CPU workers (`--cores`) refers to parallel candidate-level screening. It does not guarantee that a single factorization uses all cores.

## Demonstrated tests

- Three prototype families were solved with beam elements at **0.15625 mm** pitch.
- A representative crown solid model at **0.3125 mm** had **14,880 HEX8 cells and 21,648 nodes** and was solved with matrix-free CG under 0.02 N, reaching approximately `0.08017 mm` mean vertical deflection and relative equilibrium residual approximately `9.8e-5` (example, not a convergence proof).
- An 8× solid crown mesh contained **109,795 HEX8 cells / 136,067 nodes**; the solve exceeded the available time limit. These numbers show that the fine mesh can be built, *not* that it has converged.
- Unit tests cover Euler-Bernoulli closed-form cantilever compliance, force and moment balance, 8× FE, compatibility with older candidate paths, off-centre contact recovery and GUI mesh-field serialization.

## Relevant tools

SciPy iterative `cg`/`LinearOperator`: https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.cg.html

Gmsh curvature-aware size fields and adaptive sizing: https://gmsh.info/doc/texinfo/

scikit-fem 3-D elasticity: https://scikit-fem.readthedocs.io/en/stable/
