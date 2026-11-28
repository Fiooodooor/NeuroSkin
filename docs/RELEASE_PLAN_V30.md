# NeuroSkin 3.0 — release gates (revision 1)
Baseline: v2.2 archive + integrated 3.0-alpha.2 working copy; GitHub main is 1.9.1. Do not merge until the complete baseline has been imported.
- [ ] R01 Import exact v2.2 sources and alpha changes; manifest, provenance, Windows/Linux installation, historical scores explicitly historical.
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
These milestones do not complete R03/R04/R09. Do not confuse software release with T1/T2/T3 qualification of individual candidates.

## Decision log
- D001: share reference math before coupling it to procedural geometry; do not score reference tile as real skin.
- D002: T3 is optional; numerical T2 requires independent numerical verification, not physical measurements. Hardware-calibrated claims remain separate.
- D003: corrected physics changes historical fitness; re-evaluation required.
- D004: direct Git from working container is blocked by DNS. Connector commits can store text, but full source snapshot is not yet synced. Keep main unchanged; no release tag until baseline and gates are complete.
