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

## Revision 13 — feasible-first population Pareto reproduction
- [x] Deterministic non-dominated sorting across all valid fast-screen candidates using the four common geometry/electrical/robustness/PVDF proxy objectives. Duplicate objective vectors receive identical ranks and finite crowding scores. Infeasible candidates retain scalar refinement gradient but cannot dominate eligible ones; numerical failures rank last.
- [x] Pareto order drives parent tournaments and elitism. Known audit failure status is reused for matching genomes. QD archive uses constraint class and scalar within-niche quality (never cross-generation relative Pareto rank); failed exact clones invalidate their old archive entry. The GUI and stage decisions expose the common screening front.
- Three standalone ranking tests passed locally; additional QD integration test and existing search regressions scheduled in CI. Full local application regression remains pending.
- D015: Top-3 finalist nomination remains highest fast fitness and identical full audit; the incumbent cannot be replaced by screening Pareto rank. This change is generation-wide proxy Pareto selection, not full-population measured or Monte Carlo Pareto optimization. No physical qualification is inferred; T3 remains optional.

## Revision 14 — cache-aware Pareto finalist nomination
- [x] Allocate up to three distinct full audits: strongest eligible scalar leader, then new eligible Pareto-ranked alternatives. Reuse known failures before nomination and retain explicit fallback to fresh near-misses. If the population collapses to fewer distinct genomes, report the actual count rather than crash or duplicate candidates.
- [x] Archive nomination reasons and restrict the audited T0 Pareto report to fully feasible, passing candidates. The full audit and champion-promotion rule are unchanged.
- Four focused local nomination tests passed; application CI pending. D016: supersedes D015's scalar-only nomination; this is compute allocation, not a relaxation of physical qualification.

## Revision 15 — matched sensor-fusion ablation
- [x] Separate T0 diagnostic comparing seven legacy static channels, actual intermediate-stage outputs, and signed wired PVDF RC amplitude. Shared samples, group splits and noise realization; validation-only decoder selection. DC correctly yields zero PVDF signal. Explicit ideal centered 3.3 V clipping and saturation fraction. API /api/v30/fusion and Multiscale Lab UI; one concurrent fusion request per process.
- Two standalone fusion tests passed locally, plus four nomination tests. A local H01 smoke test using the available alpha.4 mechanics snapshot gave 225 samples, two stage outputs and one wired PVDF output: static/combined force RMSE 0.04775/0.04442 N; position MAE 2.382/2.388 mm; 40% assumed PVDF saturation. Not an exact current-HEAD benchmark or hardware measurement. Integration API test added to Windows CI.
- D017: do not reward additional channels automatically. The dynamic amplitude is a quasi-static surrogate evaluated at a known frequency, not an actual dynamic waveform/inertial response. Keep it outside promotion until independent evidence and a calibrated electronics model exist. T3 remains optional.

## Revision 16 — feedback capacitance refinement
- [x] Sensor-fusion report now sweeps existing 20–220 pF feedback bounds, holding tau fixed and reporting the corresponding ideal feedback resistance. Select gain by training/validation clipping first and validation-normalized decoder error second. Outer test targets and clipping are not used in selection. No genome mutation or fitness change.
- Two additional focused gain tests passed (eight local nomination/fusion/gain tests in total). Local H01 alpha.4 smoke benchmark selected 220 pF versus nominal 72.20181 pF, reducing held-out clipping 40% to 20% and force RMSE 0.04442 to 0.04225 N. Position MAE 2.399 mm. At fixed tau 5.84364 s the ideal Rf is 26.562 Gohm: not a validated practical circuit. Full current-HEAD CI pending.
- D018: do not expand gene bounds or automatically promote a gain setting that still clips. An ideal gain sweep does not replace circuit noise, amplifier stability, parasitics or bandwidth analysis. Previous local API smoke test passed with router, lab and API-test blob hashes matching the fusion commit.

## Revision 17 — single-page workspace and context safety
- [x] Compact four-tab Basic and eight-tab Advanced workspace; reuse existing controls, grouped settings, persistent actions and shared live/archive candidate context. Responsive layout, keyboard tab navigation, Plotly resize on panel activation.
- [x] Embed existing Multiscale Lab without leaving the main page. Independent contact/tile/fusion tabs, retained iframe state, explicit candidate rebind, candidate and live-run identity checks; standalone /v30 retained.
- [x] Discard stale FEM, spatial, mesh and response results on selection changes, reset stale inspectors and forward PVDF overrides to spatial endpoint. Archive editing remains disabled; no independent concurrent engine is implied.
- Local Chromium isolated DOM smoke passed Basic/Advanced tabs, seed selection, candidate-bound lab URL and 390px no-overflow. Plotly and HTTP transport were stubbed in that test due Chromium navigation policy; full-browser test is still needed. Python imports and JS syntax passed. D019: keep one controller; switch between live and archived experiment contexts, not fabricated multi-engine sessions.

## Revision 18 — compact results, pinned context and browser regression (alpha.5)
- [x] Basic short option labels, visible effective compute/FEM summary; Advanced retains all controls and collapsible raw engineering reports. Manual FEM inspection settings distinguished from evolutionary Top-3 settings.
- [x] Multiscale summary cards and matched sensor-fusion comparison table, feedback diagnostic, retained lab results across tabs, no rebind while a lab request is running.
- [x] Guard selection identity at server and browser boundaries, reject stale live experiment/candidate IDs with HTTP 409, resolve current finalists before gallery checkpoint, keep archived data read-only. Discard out-of-order results on selection or settings change.
- Local focused API/archive tests: 13 passed; lifecycle tests: 5 passed on available local mechanics snapshot. Isolated Chromium DOM smoke passed tab/mode transitions, mobile width and tile/box rendering with real TestClient results. Full browser navigation blocked in local environment; add opt-in real Uvicorn/Chromium regression to Windows CI. Full latest-tree CI pending.
- Previous gain CI: 127 passed, 1 failed, 44 subtests; failure was the lifecycle test's 22-second deadline, not a numerical assertion. Extend test deadline to 120 seconds and always shut down the worker; retain completion, generation and audit assertions. No measured performance improvement claimed.
- D020: identity safety is not concurrent independent engine support; T3 remains optional.

## Revision 19 — bounded inspection sessions and context-switch regression
- [x] Retain up to three candidate-bound Multiscale sessions with explicit switching/closing; no silent result eviction or rebinding of the previous frame. Context includes archive generation and PVDF overrides. Busy active session cannot be switched/closed. Origin and source window checked for each frame message.
- [x] Sticky desktop command bar and tabs, compact mobile layout, clear empty-design call to action. Fix native select input/change race which reset experiment and lab context selection before change handlers.
- Isolated Chromium DOM regression: four/eight Basic/Advanced tabs, two seed sessions, switching both directions, explicit close and 390px viewport without overflow; no JavaScript errors. Uses controlled API/Plotly transport, not real embedded browsing. Extend real-browser test to verify retained tile results across archive session switching. Latest exact-head CI remains pending.
- D021: three retained in-page inspection sessions only, not separate evolutionary engines; data retained for current browser page lifetime. No backend physics or qualification changes; T3 optional.

## Revision 20 — provenance-aware diagnostic report comparison and local snapshots
- [x] All Multiscale endpoints attach normalized experiment settings, candidate identity and genome hash, cached source fingerprint and runtime versions. Group only identical diagnostic comparison keys; do not rank across different experiment conditions or solver versions.
- [x] Advanced Multiscale comparison panel receives successful reports from the verified frame, retains the latest successful report per session and analysis type, compares matching groups, explicitly saves up to 12 reports / 512000 JSON characters in browser local storage and exports JSON. No automatic replay, no engine restore or hardware qualification. Local storage is scoped to the browser origin.
- [x] Local Node storage tests passed, 9 focused Python API/context tests passed (one expensive candidate diagnostic deselected), isolated Chromium DOM with real TestClient tile result and controlled message transport passed report capture, save, three-session limit and archive switching, 390 px layout and no page errors. Local snapshot does not constitute a complete latest-HEAD regression; actual browser/Windows CI pending. Added backend, Node and browser regression coverage.
- D022: persistence is explicit report snapshots rather than automatic restart of stale candidates or computation. Same settings key permits synthetic diagnostic comparison only; candidate-specific geometry and PVDF are recorded separately. T3 optional.

## Revision 21 — explicit next-run workstation presets
- [x] Advanced Overview presets persist up to six named configurations including CPU budget, population, search and FEM settings, and physical gate. Validate every field against the loaded catalogue and hardware limit before changing any control. Save/apply/delete are blocked during a live run or archive inspection. Seed deliberately excluded; no automatic start or replay.
- [x] Node tests for storage, limits, atomic invalid-input rejection and missing options passed; isolated Chromium DOM test confirmed preset save/apply, report save, archive switching, no horizontal overflow at 390 px and no page errors. Full Chromium reload persistence added to CI; latest HEAD CI pending. Revision 19 exact-commit Windows/Chromium CI passed.
- D023: profiles are explicit next-run settings stored per browser origin, not hardware-independent automatic defaults. Do not silently clamp a preset or overwrite the active experiment. No change to solver/validation criteria; T3 optional.

## Revision 22 — standardized four-case FEM preview payload
- Add opt-in display fields for centered normal pressure, +X offset pressure, X shear with preload and Z torsion with preload, using the existing standardized eight solves for HEX8 and beam. Shared reference topology, 20,000 display triangles maximum per case; full-mesh metrics and existing custom inspector preserved. No additional solve for the four standard views; no preview fields in stored audit summaries. GUI wiring follows in the next commit. Numerical/Node regression added; CI pending.
- D024: choose four complementary mechanical modes rather than four arbitrary pressure cases. The standard preview loads do not follow the custom inspector controls. Sampling is visualization only, not a basis for qualification. T3 optional.

## Revision 23 — shared geometry docks and four-case FEM grid
- Advanced Results/FEM/Signals reuse the actual Overview geometry DOM and its controls; Basic retains its compact Results. Multiscale has a separate bounded, cached, guarded undeformed preview of the pinned inspection session rather than the live selection. Plotly resources released when the session preview or FEM grid is hidden.
- Four collapsible FEM cards in responsive 2x2 grid with identical spatial bounds, field range, visual scale and actual standardized force/offset/moment labels. Existing custom inspector remains separately collapsible. Changing settings labels old fields stale; changing candidate clears them. No qualification change. Added real-browser regression assertions for tab docking and pinned archive geometry; full current-head tests pending.
- D025: preserve original Basic minimalism and do not duplicate stateful controls. Multiscale pinned view is conceptual undeformed geometry, not a solved nonlinear contact field. Standard grids show sampled fields and full FE extrema separately. T3 optional.

## Revision 24 — FEM preview refinement and actual browser regression
- Add shared displayed-scale legend, reset-all camera control, full-width expansion of each standard FEM card and lazy disposal of detailed custom/laminate WebGL plots outside FEM. Fix count-only PVDF preview/export queries sending a null wiring parameter, and retain archive generation zero in mesh/export requests.
- Added real FastAPI/Chromium Evaluate All test for all four load fields, shared color limits, audit payload stripping, expansion, resource disposal and count-only preview override. Exact-head browser CI pending.
- Local verification: all three tests in test_fem_previews_v30.py pass against available Alpha 2 mechanics with the same preview integration edits; the packer and test Git hashes match the committed files. Node shared-scale regression passed; frontend renderer hash matches Git. Previous full revision 21 CI passed. This is not a full latest-HEAD regression or GPU performance measurement.
- D026: display sampling may omit local extrema; label range as displayed and retain full solved extrema in case captions. No change to numerical qualification or T3.

## Revision 25 — keep display failures outside the FEM qualification boundary
- Optional four-case packing errors are reported separately without changing numerical score or feasible flag; exclude display-only errors from audit summaries. Clear preview resources on closing the FEM details panel as well as leaving the tab. Add injected-failure regression. Exact-head tests pending.
- D027: the optional preview serialization stage is not a physical validity gate. This does not suppress actual solver, geometry or equilibrium failures. T3 optional.

## Revision 26 — embedded dark canvas and workspace initialization fix
- Fix user-reported white iframe canvas: set explicit dark root/body/iframe backgrounds and dark native controls; flow-root isolates margin collapse; natural body height with 180 px floor rather than 500 px. Regression asserts actual embedded root/body colors and height on two sub-tabs. Prevent stale HTML caching with revalidation.
- Browser CI on b1d80e6: 136 backend tests / 44 subtests passed; browser failed due to temporary missing FEM workspace method. CI on 27f22d4: workspace tabs not initialized; FEM grid was queried using document.getElementById after its parent had been detached during tab construction. Resolve directly from retained FEM element. Optional-call new workspace hooks for mixed cached scripts. Current full CI pending; do not treat as a qualified release.

## Revision 27 — shared heavy-compute admission, first scheduler boundary
- Introduce process-local atomic admission across API evolution start, manual Evaluate All, linear FEM, nonlinear contact and fusion. Evolution owns the slot until the actual controller thread exits (including pause/stop cleanup). Conflicts return HTTP 409 rather than starting another unbudgeted solve. Lightweight mesh, characterization and tile diagnostics remain available.
- `/api/compute/status` and Advanced command-bar telemetry expose active manual request, live evolution ownership, elapsed time and available CPU/RAM; history bounded to 16 manual requests. Request completion is not numerical qualification. Fix standalone auto FEM choosing beam for two-stage hybrids.
- Five local isolated tests passed (thread race, failure cleanup, history, typed FastAPI schema and 409); actual application endpoint regression included in Windows CI. No queue, no RAM hard cap, no GPU allocation, no cross-process enforcement or independent evolution instances yet. Conservative admission policy is a deliberate first step; T3 optional.

## Revision 28 — compute activity history and regression compatibility
- Retain the previous Mechanical FEM heading prefix to preserve the legacy structural smoke test; the four-case grid remains unchanged. Prior revisions 24–25 failed the legacy heading assertion (135/136 other tests passed, respectively, and 44 subtests passed); browser phase was not reached. Add bounded activity history UI and monotonic conflict count, with explicit no-queue and no qualification claims. Five local scheduler tests re-run successfully; exact module/test hashes verified. Full latest CI pending.

## Revision 29 — component tree with exact conceptual primitive spans
- Preserve ordinary mesh export and expose individual generated component IDs, face/vertex spans, bounds, nominal flexure radius/length, stage identity and successful PVDF-to-member attachment. Stage assignment follows actual generator order. Missing ribbons are not fabricated. No FEM element ownership implied.
- Shared Advanced geometry and pinned Multiscale each have an interactive assembly tree, highlight selected faces on the existing plot, and optional reference centerlines. Main selection changes invalidate cached geometry; local highlight uses the accepted mesh payload. Reference centerlines are disabled on surrogate-deformed display. Add Python primitive span and Node highlight tests. Full current CI pending; revision 28 Windows backend and Chromium CI passed.
- D028: stable IDs are local to a candidate/geometry, not across genome mutations; sensor shapes remain conceptual proxies. T3 optional.

## Revision 30 — actual boundary wrench overlays in four standard FEM cases
- Collect applied nodal forces and fixed-node reactions directly from HEX8 residual and assembled loads; beam uses endpoint support forces and couples. Aggregate reference coordinates into bounded 4x4 XY bins, preserving total force and exact moment about global origin through free couples. Only requested preview cases get vectors; keep payload out of audit summaries. No extra solve.
- Four FEM cards share arrow scale and spatial bounds. Orange applied and cyan reaction arrows; hover exposes vector and free couple, captions expose applied moments and force residual. Reference coordinates and visual scale are explicit. Pure couples are numerical, not falsely shown as a force arrow. Geometry centerlines remain conceptual. Added equilibrium/aggregation, JS and actual browser checks. Full new CI pending.
- D029: boundary vectors + stress field + structural centerlines are not solved internal streamlines or local component stress attribution. No qualification change; T3 optional.

## Revision 31 — internal substrate traction and tree refinements
- Optional two horizontal HEX8 layer-center sections at nearest available thirds of loaded height; integrate signed center-recovered substrate traction sigma·(-ez) over occupied voxel areas. Explicit Voigt order and units. Bounded vector aggregation and shared scale; separate purple/pink toggle. Excludes embedded-film force and exact equilibrated section integration; beam section overlay unavailable. Applied arrows point toward their reference application point. No additional solve or score change.
- Preserve expanded component groups, show bounds, make explicit film selection reveal PVDF, clear stale pinned tree on closing last session. Add synthetic section sign/area regression and browser toggle test. Exact-head tests pending.
- D030: actual approximate internal substrate traction is a step beyond boundary vectors; do not call it exact force lines or component-level stress mapping. T3 optional.

## Revision 32 — connect component identity to per-film solved response
- Attach existing standardized FEM per-film reduced laminate metrics to each preview packet, with exact film+member ID matching. Component tree shows signed effective strain, estimated charge and laminate energy for four standard cases; no arbitrary stress-to-member attribution. No additional solve, no fitness change. Preserve stale settings warning; reference centerline toggle disabled on deformed geometry. Pinned Multiscale does not borrow live FEM evidence.
- Local revision 31 tests: three exact-blob force/section tests, two exact-blob component tests on patched Alpha 2 geometry and four exact-blob preview tests on patched Alpha 2 mechanics passed. New revision 32 film matching and real-browser checks added; full latest HEAD pending. Prior revision 28 Windows CI: 144 tests, 44 subtests and 2 browser tests passed.
- D031: signed charge is an assumed reduced-film output, not circuit voltage after wiring or hardware measurement. Local substrate attribution and calibrated readout remain open. T3 optional.

## Revision 33 — budgeted parallel Evaluate All DAG
- Independent surrogate audit, standardized validation and hybrid orientation use spawn process workers under a CPU/RAM estimate; FEM stays local and receives 1–8 case workers, with GPU case concurrency fixed to one. Explicit UI worker budget; unknown RAM conservative. Preserve existing qualification by attaching only FEM-dependent fields to independently produced T0 report. Status reports submitted/running/completed stages and allocation; no claim of OS utilization. Drain workers on exception. Tests for scheduling and evidence merge added; current CI pending. No new independent heavy jobs yet; process-local admission remains.
- D032: prioritize reducing manual wall time without changing mesh pitch, load protocol, T0 selection or optional T3. Sparse factorization and other phases can remain serial; no guaranteed speedup until workstation benchmark.
