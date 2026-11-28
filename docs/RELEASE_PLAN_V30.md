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

## Revision 7 — full regression follow-up
- Initial full suite (before topology fix): 203 passed, 3 failed, 1 skipped, 106 subtests passed. The topology regression is repaired in revision 6.
- D011: provenance reads the exact VERSION instead of hard-coding the release. The old refinement fixture's middle candidate now passes the corrected physical screen; use two explicitly single-stage candidates that actually fail the unchanged weak-pressure criterion to test the gradient. Scores 6.1000 and 6.5880, both below 15. No qualification threshold was relaxed.
- 16 focused tests passed, 2 lifecycle cases deselected; rerun of full suite required.

## Revision 8 — candidate readout accounting and report comparability
- [x] Logical wired PVDF and intermediate-stage output counts drive packet size, power, scan capacity and ADC noise estimates. Signed wiring maps film output and capacitance to readout channels. Saturation is explicitly reported for the modeled excitation, not used as a physical circuit qualification.
- [x] Same-tier report comparison now requires identical solver source hash and random seed as well as protocol/noise/fidelity. Missing solver provenance requires revalidation. Expanded source hash includes electronics, contract and full audit.
- 17 targeted tests passed (readout and validation). Real component selection, CDC/AFE circuit simulation, static/dynamic decoder fusion and hardware evidence remain open. No real BOM price or measured noise implied.

## Revision 9 — single development branch
Canonical development branch: `develop/v3`. Consolidate the full v2.2-derived integrated tree, previous develop/v3 history and the current main license in a non-force merge. Previous integrated branch remains historical; do not develop there. Original snapshot importer/status are historical only. T3 remains optional.

## Revision 10 — resource-aware parallel audits (3.0.0-alpha.4)
- [x] Remove the fixed <0.4 mm serial-audit switch. Bound candidate-process and HEX8 case concurrency by CPU budget and available RAM. Preserve all eight standardized load cases, ordering and numerical gates.
- [x] Shared matrix-free operator with GIL-free Numba matvec and per-thread CG diagnostics; lock shared SuperLU solves, allow concurrent field recovery. GPU and beam remain serial within a candidate.
- [x] Live outstanding/cached/completed audit counters and elapsed time; Windows spawn ceiling of 61 processes; no orphan queued audit jobs on stop. Root VERSION and GUI identify alpha.4.
- [x] 31 focused tests passed locally, including spawned workers, serial/parallel numerical equivalence, lifecycle, refinement and readout. CI updated. Run `python benchmark_audits.py --cores 1,16,24,32,40 --pitch .3125 --grid 5` on the target workstation.
- D012: memory reservations are estimates, not hard RSS caps. Unknown RAM or small budgets restrict concurrency; a single solver retains its existing memory guard. SuperLU factorization and solve are serial and only field recovery overlaps; max eight independent case workers per candidate. NUMA and actual speedup on dual Xeon/P1000 remain unmeasured. No change in audit protocol or evidence tier.

## Revision 11 — matrix-free preconditioning and performance evidence
- [x] Include embedded PVDF laminate in exact nodal 3x3 block-Jacobi CG preconditioner; enforce positive definiteness and invert free principal subblocks for partially fixed nodes. Fallback to scalar diagonal if block factorization fails.
- [x] Solver and scheduling provenance; report solver setup time, load-case wall time, direct factor nonzeros and CG preconditioner in audit/benchmark.
- Local regression: 41 passed, 1 opt-in 8x case skipped, 3 subtests passed. Local H01 0.3125 mm mesh: 17,232 HEX8, 24,699 nodes. Forced matrix-free center load: scalar Jacobi 1,359 iterations, 7.19 s; nodal block 1,082 iterations, 6.57 s (single runs, not a statistically established speedup). Both force equilibrium errors below 1e-4; displacements ~0.55081236 mm. Direct COLAMD setup ~8.4–9.5 s, single solve ~0.105 s, 73,262,927 factor nonzeros. MMD_AT_PLUS_A setup ~17.9 s, 96,408,972 nonzeros: rejected. Geometric ordering ~7.3 s on one example: insufficient evidence to change default. Eight of ten reference hybrids use direct solver at this pitch. Retain COLAMD and the solver-selection threshold.
- D013: optimize completed audits/time, not CPU percentage alone. Direct sparse factorization remains serial per finalist and may limit sustained utilization; future optional parallel factorization must demonstrate equivalence and benchmark improvement. No workstation-specific speedup or hardware qualification claimed.

## Revision 12 — independent shear and bounded nonlinear decoding
- [x] Protocol shear levels independently excite Fx and Fy, rather than coupling them. Nine signed axis combinations in the default protocol and 25 in dense mode. Static-only fast response path avoids unused PVDF computation.
- [x] Validation-group selection of ridge/RBF models with fixed dimensionless target scales, train-only feature transforms and bounded 32-center RBF, then refit on train+validation and untouched test. Explicit split fractions and assumed no-contact diagnostic.
- [x] Common random Monte Carlo scenarios even when genes differ; numerical failures counted as zero signal and explicitly fail the completion gate. One-sided exact binomial upper bound, not hardware reliability. Rank-five local observability required for new protocol reports. Dense/sample count settings fingerprint prevents incompatible promotion comparisons.
- Three standalone numerical design tests passed locally; additional integration tests added to Windows CI, remote result pending. Full current application regression not yet run locally.
- D014: the static decoder still uses seven assumed capacitance/Hall channels, not dynamic PVDF or stage-channel fusion. Absolute contact radii remain candidate dependent; unsupported physical axes and T3 remain explicit. New protocol scores must not be compared with earlier scores. Do not equate synthetic held-out prediction with independent physical accuracy.
