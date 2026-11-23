# NeuroSkin Evolution Lab v1.3 — high-resolution finite-element mechanics

## Added

- Explicit `Solid 3D HEX8` and `3D space-frame beam FEM` selector in both Advanced evolution controls and individual FEM inspection. **Solid 3D HEX8 is the default**. The selected backend is persisted in evolution configuration.
- Four- and eight-fold linear mesh refinement relative to legacy 1.25 mm: selectable **0.3125 mm** and **0.15625 mm**; manual FEM also accepts 0.125 mm (experimental). Fine solid voxelization (x, y, z) is fundamentally different from simply splitting a beam centerline into shorter segments.
- Memory-bounded matrix-free HEX8, Numba-accelerated element assembly actions, 3×3 block-Jacobi preconditioned CG, configurable iteration/time/resource budgets, explicit failure messages.
- Faster local-bounding-box rasterization of curved, tapered members; optional boundary surface construction and browser visualization sampling for very large models.
- `mesh_study.py` for reproducible grid-resolution diagnostics and CSV/JSON/PNG output.
- Controlled taper and thinner struts. Each displayed flexure is now a continuous closed tube instead of a chain of overlapping cylinders; local radii also drive the FEM voxelization and reduced-order mechanical proxy.
- Improved contact-patch handling for archived and coarse models; radius expansion and nearest-node fallback are reported with the results.
- Optional high-resolution dependencies: `requirements.txt` (historically a separate high-resolution file, merged in v1.7).

## Verified

- Full regression suite (before explicit backend selector): 74 passed, 1 optional slow test skipped, 39.79 s.
- Post-integration selected suite: 22 passed, 1 skipped, including pipeline, FEM, high-res and space-frame checks.
- API TestClient on a saved archived genome: successful 0.3125 mm solid HEX8 and 0.15625 mm beam solves.
- Actual standalone **0.15625 mm SOLID HEX8** run: 19,345 elements, matrix-free CG converged after ~1,922 iterations. See `example_mesh_study`.
- JavaScript inline blocks: checked with Node `--check`.

## Important limitations

- Both FEM backends implement small-strain linear elasticity, not nonlinear silicone, contact, buckling, fatigue or coupled piezoelectric FEM.
- The example mesh study is **NOT converged**: 0.3125 versus 0.15625 mm deflections differ by roughly 12.6%; coarse grid thickened the thin members. An extremely fine mesh changes the effective geometry and may still not resolve local stress reliably.
- Fine meshes are computationally costly; `--cores` accelerates candidate screening but ultrafine volumetric Top-3 audits are serialized for memory safety. A run might exceed its requested evolution wall-time while finishing an expensive audit.
- No claim of guaranteed improved sensor performance or manufacturability. Consider 3D tetrahedral adaptive meshing and nonlinear hyperelastic FEM for design qualification.
