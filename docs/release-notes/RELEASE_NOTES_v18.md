# NeuroSkin Evolution Lab v1.8 — bonded-PVDF mechanics and unified inspection

## Required changes

**One action: Evaluate All.** It updates three inspectors in the main user flow:

1. Mechanical FEM: stress, strain, solved deformation for the selected case and force.
2. Load-case + predicted electrical response, including dynamic PVDF.
3. Spatial downward-pressure screening.

**Top-3 panel relocated.** It appears *inside* the Selected geometry panel, **below the interactive 3D viewer and above the Mechanical FEM panel**, while the evolutionary process runs. Finalist cards show bonded PVDF inclusion. The old independent FEM and pressure action buttons have been removed. The Basic/Advanced switch does not change the underlying audit protocol.

## Mechanical model: PVDF + adhesive

The old warning `FEM currently ignores film and adhesive stiffness` is replaced. The new model does **not** merely move the graphic:

- Each film is mapped to a chosen mechanical strut through a short set of stations along its centreline.
- A thin-film membrane contributes an additional positive-semidefinite stiffness matrix `K_film` to the substrate FEM system: `(K_substrate + K_film) u = f`.
- The assumed adhesive transmits strain using a finite shear-lag compliance. Its thickness, shear modulus and bonded area change the effective film axial modulus.
- The reported elastic response now includes PVDF/adhesive effects in the **HEX8** equilibrium solve and in the quicker **beam** and **6-DOF** mechanical approximations. They have different physical fidelity.
- Finalist reports include `pvdf_stiffness_included`, `pvdf_film_count`, `pvdf_adhesive_model`, strain and energy contribution, estimated charge, and estimated mass.
- A fast composite model runs for **all individuals**. An identical full mechanical audit with these films runs for the **top three individuals of each generation**, if the already-default-enabled FEM toggle remains checked; those results influence parent selection and incumbent promotion.
- Pre-v1.8 archives are preserved, but their historical scores must **not** be compared directly with newly computed scores. A film override is applied only in a fresh analysis.

The model is **not** coupled piezoelectric field FEM, fully resolved adhesive/film solid or shell FEM, or a calibrated model of peel, debonding, hyperelasticity, plasticity and fatigue. HEX8's displayed von Mises stress is for the **substrate**; PVDF film forces and energy are reported separately. The uncertainty of assumed moduli and shear-lag coefficients is not captured by the single score.

## Physical assumptions and core equations

Film properties are defined by genotypic variables `piezo_E_MPa`, `piezo_thickness_um`, `piezo_width_mm`, `piezo_span_mm`, `piezo_adhesive_G_MPa`, `piezo_adhesive_thickness_um`, and `piezo_bond_fraction`. Archived genomes without them receive documented defaults.

- Equivalent axial film force stiffness: `E A / L` reduced by a bounded, approximate adhesive shear-transfer coefficient.
- HEX8: segments of the film are mapped to nearby real substrate FE nodes; each contributes an energy term `0.5 * k * (weighted axial extension)^2`. This produces a symmetric positive-semidefinite added stiffness.
- Beam FEM: the member uses an effective axial and flexural stiffness in the bonded-film region, rather than a true layered shell.
- Fast screening: the same film dimensions and adhesive assumptions affect equivalent-rod compliance and predicted PVDF transduction.

A real PVDF laminate must be calibrated with the actual manufacturer's material data, electrodes, adhesive, substrate, temperature and frequency. The adhesive model is a **reduced-order approximation**.

## Additional bug fixes

- Fixed crossover's blending of two independent random coefficients: it could exceed genetic parameter bounds (e.g., adhesive bond fraction > 1). The corrected interpolation uses one coefficient and its complement.
- Fixed a report-field naming mismatch for maximum PVDF strain that broke the full HEX8 sweep.
- Fixed the manual FEM API: it previously created `HexElasticSolver` without passing the candidate's genome, silently omitting bonded-film reinforcement.
- Unified Evaluate All uses the requested FEM case, force, and offset **for the displayed deformation** without changing the standardized load cases used to rank all candidates.
- Removed a JavaScript event handler referencing an absent standalone FEM button.
- The `pvdf_stiffness_included` flag is visible in both the manual FEM response and the full audit.

## Verification performed in this release

- `59 passed, 1 skipped` in a focused Python test run, plus 23 geometry subtests.
- Dedicated tests compare bonded and unbonded HEX8 solutions, verify positive-semidefinite reinforcement, response to film/adhesive parameters, legacy single-film genomes, 6-DOF screening, beam mechanics and API fields.
- A **3-generation/36-evaluation** CLI smoke test completed with linear HEX8 audit for Top-3 in each generation. The 3 saved finalists of generation 3 each had actual coupled laminate results.
- `node --check` passed for the GUI's JavaScript.
- Browser rendering, NVIDIA CUDA, Windows 11 worker scheduling and material experiments were not executable in this Linux environment; a Windows-machine validation is still required.

## Install / run

```powershell
python -m pip install -r requirements.txt
python server.py --cores auto --open --port 8765
```

For a short, practical first evolution on HP Z840, keep the Top-3 FEM checkbox enabled and start with coarse 1.25 mm solid HEX8; only refine selected champions to 0.3125 or 0.15625 mm after a mesh-convergence study. Many ultrafine audits can consume substantial CPU time and RAM.
