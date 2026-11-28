# NeuroSkin 3.0 — release gates (revision 2)
Baseline: user-uploaded GitHub main at ae9c0104a351441231b265259284a9fb113c461c (VERSION 2.2.0, 268 tracked files). Active development branch: develop/v3-integrated. Previous develop/v3 is preserved. Alpha 2 changes must be integrated and tested against this baseline before release.
- [ ] R01 Verify uploaded v2.2 sources and integrate remaining alpha changes; manifest, provenance, Windows/Linux installation, historical scores explicitly historical.
- [ ] R02 Physics: electrode-area PVDF, charge signs, mass/capacitance consistency, force and moment equilibrium, no undisclosed mesh inflation. Analytic/regression tests.
- [ ] R03 Symmetry: geometry orbits C1/C2/C3/C4/C6/C8 and Dn, preserve orbits in mutations; separate per-stage material/electrode symmetry. Use normalized stiffness residual and field/channel permutations; Cn chirality allowed.
- [ ] R04 Stack: independently parameterized 1–3 stages, physical interface and sensors, transformed wrench and stiffness, energy balance, geometry and FEM. Compare matched height, channel and power budgets.
- [ ] R05 Evolution: feasible-first Pareto across whole population, robust common scenarios, failed trials counted, separate evidence tiers, reproducible search space.
- [ ] R06 Nonlinear FEM: conforming multi-material CAD mesh, contact, convergence, penalty sensitivity, nearly incompressible material checks, resource limits. Reference-box tests alone insufficient.
- [ ] R07 Electronics: actual channel topology, d31 integration, static capacitive and dynamic PVDF, optional Hall, noise/covariance and readout saturation; traceable AFE/CDC parameters; BOM and PCB reference design.
- [ ] R08 Intelligence: grouped holdout, nested tuning, rank 5 plus noise-scaled conditioning, force and position errors, no leakage; separate measured and synthetic.
- [ ] R09 Tile: 3x3/5x5/8x8, membrane and electrical coupling, edge loads, multiple contacts, reconstruction, FE verification. T0 spring-network reference first.
- [ ] R10 Macro skin: curved substrate, strains, segmentation, bus bandwidth, synchronization and calibration.
- [ ] R11 Optional T3: measured CSV, provenance, calibration, uncertainty, independent specimens/sessions and review; no data means NOT_PERFORMED, never release/evolution blocker, never auto-certified.
- [ ] R12 Release: Evolve/Pause/Stop/Evaluate All/export/archive and async GUI race tests; Linux/Windows CI, benchmark logs, docs, versioned release. No hardware claims without evidence.

## Verified partial milestones
- [x] T0 1–3 stage series wrench transport and energy balance reference.
- [x] T0 normalized stiffness symmetry reference (polar/axial vectors).
- [x] T0 finite tile spring-network equilibrium reference.
- [x] Six focused tests pass locally (Python 3.13).
- [x] Actual two-stage wrench transport in advanced.py and electromechanics.py, with tests across all ten reference hybrids; 22 focused local tests passed, five heavier FEM/API cases deselected, 30 subtests passed.
These milestones do not complete R03/R04/R09. Do not confuse software release with T1/T2/T3 qualification of individual candidates.

## Decision log
- D001: share reference math before coupling it to procedural geometry; do not score reference tile as real skin.
- D002: T3 is optional; numerical T2 requires independent numerical verification, not physical measurements. Hardware-calibrated claims remain separate.
- D003: corrected physics changes historical fitness; re-evaluation required.
- D004: direct Git from working container remains blocked by DNS. The user uploaded v2.2 to main; new development now uses that commit. Keep main unchanged until tests and release gates are complete.
- D005: transfer corrected source files directly, not the historical migration script; that script targets the original pristine v2.2 and must not be rerun on partially integrated revisions.

## Revision 3 — physics corrections
- [x] Shared signed broad-face d31 charge and active-area capacitance/mass across analytical, embedded membrane, shell and beam models. Legacy d33 request explicitly unsupported.
- [x] Zero-reference shell curvature and corrected quadrature; single-stage reaction matrices match stiffness assembly.
- [x] Rank-five full audit gate; voxel inflation and force imbalance disqualify linear FEM screening. GUI displays coefficient and FEM results.
- Local regression: 79 passed, 45 subtests passed. These are engineering tests, not hardware evidence.
- D006: older h01/h10 reference tests assumed coarse inflated meshes could pass. The new tests assert geometry rejection and retain equilibrium checks; do not lower this gate to recover old scores. A conforming mesh is still required. Historical score comparisons invalidated by source hashes.

## Revision 4 — constrained symmetry and consistent stage channels
- [x] C2/C3/C4/C6/C8 and D2/D3/D4/D6/D8 selectable search modes with exact rotational centerline orbits, all primary legs instrumented, centered pads, repaired mutations, and T0 stiffness diagnostics in full audit.
- [x] Exact mapping of globally selected films into each stage stiffness; per-stage imbalance; fixed footprint-to-channel mapping; upper-stage films no longer directly receive imposed ground strain.
- [x] New evolved genomes normalize d33 to d31; archives remain readable.
- Local regression: 81 tests and 83 subtests passed (scope, symmetry, validation, hybrid, API, PVDF and pipeline).
- D007: constrained modes deliberately limited to single-stage primary-flexure topologies; arbitrary web/archetype and stacked orbit constraints, fully meshed symmetry, and wiring equivariance remain open. Constrained Cn may have higher rotational symmetry than requested; Dn uses radial-planar flexures, and chiral families remain Cn-only. Default all-mode remains unconstrained. Do not equate exact centerlines with FEM field symmetry.

## Revision 5 — integrated nonlinear and multiscale diagnostics
- [x] Strict face-connected, positive-volume TET4 mesh, homogeneous compressible Neo-Hookean material and analytic consistent tangent; rigid-mode checks; planar frictionless penalty contact and elastic unloading. 11 focused tests passed.
- [x] Existing candidate selection (including archives and preview overrides) connected to bounded nonlinear voxel subdivision and tile APIs; GUI Multiscale lab link, heatmaps and request error handling.
- [x] T0 tile contact load distribution preserving total force and first moments; reaction transfer matrix and nonnegative grid reconstruction under declared synthetic noise.
- [x] 22 focused tests passed, including nonlinear candidate and API tests; JavaScript syntax checked. New tests added to existing Windows CI job (remote execution pending).
- D008: voxel-derived nonlinear candidate results are DIAGNOSTIC_ONLY and T2_qualified=false, irrespective of numerical convergence. Inflated geometry requires explicit diagnostic opt-in. Limit: 250 HEX8 / 1500 TET4 per request; one concurrent nonlinear request per server process. This does not replace CAD-conforming multimaterial FEM or integrate nonlinear fitness.
- D009: tile inverse uses direct reaction sensing and the same assumed scalar transfer model. It is not electrical sensing, independent decoder validation, physical membrane, or identification of the number of contacts.

## Revision 6 — evolution regression correction
- [x] Topology jumps select a distinct effective architecture, not an overwritten label. No new orphan hybrid labels; categorical and integer genes are not interpolated during crossover.
- 29 focused tests and 41 subtests passed (2 long lifecycle cases deselected). Full-suite qualification remains pending.
- D010: a hybrid-to-hybrid transition may legitimately retain the topology label 'hybrid'; tests now compare architecture identity as well. Scope repair may still constrain the result in a single-architecture mode.
