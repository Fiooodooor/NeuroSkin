## v1.8 correction: bonded PVDF stiffness now modeled

**This overrides historical v1.4/v1.7 text below.** HEX8 uses an energy-equivalent embedded PVDF membrane stiffness with approximate adhesive shear-transfer; beam FEM uses a composite-section axial and bending approximation. Films are not separately resolved as 3D solids or shells. The substrate stress map does not include resolved PVDF stress, adhesive peel stress or debonding. Both models are small-strain and uncalibrated; refer to [RELEASE_NOTES_v18.md](RELEASE_NOTES_v18.md) for validation status.

# NeuroSkin Evolution Lab 1.3 — High-resolution mechanical FEM

## Practical change

**Default FEM backend in the GUI and CLI is now explicit SOLID HEX8**. The older 1.25 mm voxel mesh can be replaced by **0.3125 mm (4× linear resolution)** or **0.15625 mm (8× linear resolution)**. These reductions can increase the number of volumetric elements by up to 64× and 512× for a fixed 3D domain, and dramatically increase compute/memory requirements. The GUI also offers optional **3D Euler–Bernoulli space-frame beam FEM** for quick, small-strain, member-level mechanics. **A 0.15625 mm beam discretization is NOT the same as a 0.15625 mm volumetric HEX8 solid mesh.** Select the solver explicitly.

### Install

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements.txt  # recommended for fine HEX8
python server.py --cores 8 --open --port 8765
```

The optional Numba accelerator is strongly recommended for the matrix-free iterative 3D HEX8 solver. Without Numba, very fine meshes over 5,000 elements return a clear installation error rather than silently taking hours. Existing direct sparse HEX8 cases remain compatible without Numba.

### Manual 4× / 8× solid simulation

```bash
python fem_cli.py --backend hex8 --family quadrant --seed 42 --pitch 0.3125 --force 0.1 --out solid_4x
python fem_cli.py --backend hex8 --family quadrant --seed 42 --pitch 0.15625 --force 0.1 --cg-maxiter 5000 --cg-timeout 180 --out solid_8x
python mesh_study.py --family quadrant --seed 42 --pitches 1.25,0.625,0.3125,0.15625 --out comparison
```

The 8× run can take many seconds or minutes; high-resolution studies are best run on selected finalists, not on every candidate in every evolutionary generation. Fine-pitch solid Top-3 audits are serialized to protect RAM; the fast population screen still honors `--cores`.

### Timed evolution: same FEM in Basic and Advanced

```bash
python evolve_cli.py --seconds 120 --cores 8 --population 96 --mode all --fem --fem-backend hex8 --fem-pitch 0.3125 --gate --out runs_v05
# For faster, less detailed member mechanics, select --fem-backend beam.
```

The GUI starts in Basic with 0.3125 mm volumetric HEX8 selected. Advanced exposes backend and pitch independently. Individual selected models can be re-evaluated at 0.15625 mm solid HEX8 in the FEM panel. Saved experiments remain readable, and the engine code fingerprint changes to prevent unqualified comparison with old results.

### Mechanical method and limitations

- Curved, tapered flexures are now generated as a **continuous watertight tube per member**, not a chain of overlapping thick cylinders; the same segment-dependent radius enters the quick mechanics proxy and the HEX8 voxelization.
- Curved-member rasterization is restricted to local bounding boxes. The FEM contact patch first expands adaptively, then uses the nearest connected cluster of valid top nodes if necessary. The contact loading method remains a **prescribed nodal force**, not resolved unilateral contact.
- Solid HEX8 uses 8-node linear elements with 2×2×2 Gauss integration. A sparse direct solver handles small meshes. Larger meshes use **Numba-accelerated matrix-free CG** with a 3×3 block-Jacobi preconditioner, a convergence criterion, iteration and wall-time limits, and a conservative memory budget.
- High-resolution requests can fail with a specific diagnostic if the grid is disconnected, under-resolved, exceeds memory limits, or the iterative solver does not converge. This is preferable to returning a fabricated result.
- The full volumetric displacements, strain and stress can be exported to NPZ/VTK. For very large models the GUI may sample the surface triangles for responsive display; sampling is flagged in its response. **FE results are not interpolated from the six-DOF surrogate**.
- **More elements do not by themselves establish 4–8× better numerical accuracy.** Voxel discretization changes the effective member geometry, particularly when the coarse grid inflates a thin strut. A resolution/convergence study is mandatory. Thin curved members are still only ~2–3 voxels wide at 0.15625 mm; local stress concentrations need even finer or unstructured adaptive meshes.
- Both backends are linear small-strain mechanics. Large deflections, buckling, self-contact, hyperelastic elastomer behavior and fully coupled piezoelectricity remain OUT OF SCOPE. If max principal strain is several percent or more, treat the results as a preliminary screen.

### Reproducible example (Quadrant, seed 42, 0.1 N normal)

| Pitch | HEX8 cells | Mean downward motion | Elapsed wall time |
|---:|---:|---:|---:|
| 1.25 mm | 125 | 0.05281 mm | 0.01 s |
| 0.625 mm | 384 | 0.28541 mm | 0.02 s |
| 0.3125 mm | 2,668 | 0.76640 mm | 0.41 s |
| 0.15625 mm | 19,345 | 0.87654 mm | 27.81 s |

The difference between the last two is still about **12.6% relative to the 0.15625 mm result**. Therefore this specific design is **NOT mesh converged**. Moreover, the computed displacement is a significant fraction of the cell height, so linearity may be a poor physical approximation. This is a crucial negative result of the study, not evidence of an already accurate sensor.

Artifacts: `example_mesh_study/study.csv`, `study.json`, `study.png`. Run `python -m pytest -q tests` for regression coverage; the extra 8× HEX8 test is enabled with `NEUROSKIN_SLOW_TESTS=1`.

---

**Update 1.3:** See [FINE_MESH_RELEASE.md](FINE_MESH_RELEASE.md) for fine 3D beam FE, optional 4×/8× solid HEX8 and their distinct limits. The document below describes the legacy 1.2 HEX8 backend.

# NeuroSkin Evolution Lab 1.2 — genuine 3D linear solid FEM

## What changed

Version 1.1 optimized a **reduced 6-DOF beam surrogate**, which could not predict a physical displacement field. Version 1.2 adds an independently assembled **3-dimensional, linear, isotropic elastic HEX8 continuum finite-element solver** (`physical_fem.py`) and uses it as a second-stage filter during evolution. This is genuine sparse FEM, `K u = f`, not an animation of the surrogate.

This **does not** make the overall program a certified physical simulation. It uses small-strain linear elasticity, a voxelized approximation of the CAD family centerlines and radius, assumed material constants, idealized fixed bases and applied loads, and synthetic electrical transduction.

## Run the application

```bash
python -m pip install -r requirements.txt
python server.py --cores 8 --open --port 8765
```

Open `http://127.0.0.1:8765`. A **Run real 3D FEM for Top-3 finalists** checkbox is on by default. Both Basic and Advanced run the **same core solver**; Advanced exposes an extra resolution setting.

Select any model from the gallery, expand **Actual 3D FEM: stress, strain and deformed mesh** under the existing concept viewer, select a load case, and press **Compute real FEM**. The second Plotly view shows the *same HEX8 surface nodes used in the solve*, shifted by the **computed** displacements. Choose von Mises stress, maximum principal strain, or displacement magnitude. The visual scale affects only the display.

Test cases supported for individual visual inspection: central downward load, offset downward load, X/Y shear with normal preload, Z torsion with preload. The Top-3 FEM audit runs eight cases (five downward contact positions, two shears and torsion).

To run timed evolution headlessly:

```bash
python evolve_cli.py --cores 8 --seconds 120 --population 64 --mode all --fem --fem-pitch 1.25 --gate --grid 3 --audit-grid 5 --out runs_v05
```

To reproduce a mechanical model independently, from its saved genome:

```bash
python fem_cli.py --family quadrant --genome candidate_genome.json --force 0.1 --pitch 1.0 --convergence --out fem_results
```

Without `--genome`, `fem_cli.py` generates a seeded procedural candidate (`--seed 42`). Output files: `deformed_solid_FEM.vtk` (actual volume cells, original coordinates and solved displacement), `fields.npz` (full nodal and cell fields), `FEM_report.json` (forces, reactions, displacement, convergence diagnostic and assumptions). Open VTK in ParaView and use its Warp By Vector filter for 3D deformation.

## Evolution hierarchy

1. All members undergo the original fast reduced-order mechanical/electrical proxy screening.
2. **Three geometrically distinct highest-scoring finalists** undergo an identical, physical HEX8 FEM load protocol and the original synthetic electrical audit.
3. Every finalist is ranked using a combined `audit_score = 0.4 * old_score + 0.6 * FEM_score` with feasibility prioritized and failure assigned zero, with all assumptions explicit. This is an **engineering heuristic**, not a calibrated quality score.
4. The **previous FEM-audited incumbent** is carried into the same comparison and only replaced if the new finalist wins the audited comparison. The incumbent's genome is injected into the next population, while FEM signals from audited finalists change their parent-selection priority.
5. The FEM results, solver build hash and promotion reasons are saved in each stage under `runs_v05/<id>/stages/` and remain inspectable later in the Saved experiments GUI.

The interface is still **multi-fidelity**, not every candidate receives continuum FEM. Running full FEM on a 32-core machine for the entire population may be introduced separately after an appropriate mesh-quality/cost study.

## Mechanics: explicit model and equations

- Nodes: three translations each, no rigid-body dynamics, no beam proxy in this solver.
- Elements: eight-node regular solid HEX8 with `2x2x2` Gaussian integration.
- Constitutive model: isotropic, small-strain Hooke law: `sigma = lambda tr(epsilon) I + 2 mu epsilon`, `epsilon = (grad(u)+grad(u)^T)/2`.
- Supports: `ux=uy=uz=0` on all bottom mount nodes.
- Loads: force distributed over a circular region of top FE nodes; torsion by balanced tangential nodal forces.
- Solved fields: nodal displacement, cell strain tensor, cell stress tensor, von Mises stress, maximum principal strain, free residual, support reaction vectors, reaction moments and strain energy.
- Robustness: mesh component connectivity, non-empty contact region, stiffness invertibility, global force and moment balance are checked; invalid candidates receive `INVALID`, not invented FEM values.

## Critical limitations / limitations of this release

1. **Voxel thickness inflation**: when radius `< 1.15 * pitch`, a member is numerically thickened. This is made explicit in every FEM result. It may artificially stiffen the model. High fidelity requires lowering pitch until both member radius and interface geometry are resolved.
2. **Grid convergence is NOT guaranteed**. A test on one crown with pitch 1.25 and 1.0 mm produced deflections approximately 0.094 and 0.226 mm, respectively (**58% relative discrepancy**): the result **fails** a 10% convergence screen. `--convergence` is a *two-grid warning*, not a formal three-level mesh-convergence qualification.
3. **No nonlinear geometry or constitutive laws**. A high principal strain makes small-strain linearity questionable. At high strain the scores must not be used as real-life force calibration. True Ecoflex/TPU behavior needs at least a suitable hyperelastic law and measured parameters.
4. **No unilateral contact, buckling, self-contact, crack/fatigue, adhesion or friction**. Top force is distributed to nodes; the tool does not compute real contact pressure.
5. **No coupled PVDF, capacitance field or sensor-electronics FEM**. The optional capacitance estimate is based on FE-computed contact displacement and assumed parallel plates. PVDF remains a separate, assumed electrical model inherited from 1.1.
6. The visualization STL is an overlapping assembly; the **FE voxels are a separate meshed approximation of the same strut centerline/radius, not a direct tetrahedralization of that STL**. This is deliberate and documented.
7. The `FEM_score` is a heuristic comparing the real FE fields. A high score is not certification, detection accuracy or an experimental result.

## Verification and future milestones

The full 1.1 regression suite passes unchanged (58 tests). New solver tests cover:
- closed-form axial bar compliance (within 12% on a coarse 3D mesh);
- force and moment balance;
- response to vertical load for every structural family;
- noncentral loading moment response;
- exported mesh coordinates exactly matching solved FE nodal displacement;
- invalid geometry handling.

Next recommended milestone from Deep Research: **Gmsh + scikit-fem direct tetra mesh generation** of watertight solids, three-grid convergence analysis, then **FEBio/SfePy** for large deformation, contact and PVDF piezoelectrics. No such solver is represented as implemented in 1.2.

Research/docs: https://gmsh.info/doc/texinfo/ ; https://scikit-fem.readthedocs.io/en/stable/ ; https://febio.org/ ; https://sfepy.org/doc-devel/examples/multi_physics-piezo_elasticity.html ; https://www.nature.com/articles/s41528-026-00563-3 ; https://www.nature.com/articles/s41528-024-00310-6


### PVDF array symmetry in v1.4

The code now displays 2 or 4 PVDF ribbons distributed over primary beams and evaluates their dynamic electrical surrogate separately. **Neither HEX8 nor beam FEM includes bonded PVDF, electrodes, wiring, or adhesive as elastic material.** Balanced films reduce gross asymmetry of the intended assembly but do not establish mechanical balance in FEM. Do not use this solver to certify an assembled multimaterial sensor; a coupled composite model or calibrated equivalent section is required. Archived genomes without `piezo_count` retain their original one-sided film unless explicitly preview-overridden.
