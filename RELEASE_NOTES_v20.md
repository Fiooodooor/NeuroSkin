# NeuroSkin 2.0 — Two-stage mixed-morphology sensor cells

## Major features

- Ten ranked research-inspired concrete hybrids with ten objective priors each and documented assumptions.
- Upper sensing flexures and lower reference flexures share a **real intermediate plate** in one HEX8 3D solid.
- A typed `hybrid_id` gene selects among ten actual stage combinations, including a handedness-checked double-chiral design.
- Additional evolvable stage genes: `hybrid_split`, `hybrid_upper_scale`, `hybrid_lower_scale`, `hybrid_phase`, `hybrid_plate_thickness`, `hybrid_sensor_mode`.
- Composite 6DOF fast stiffness uses **series compliance**, rather than treating both stages as parallel struts.
- FEM computes upper/lower 3D displacements for 8 load cases, stage-compression fraction, mechanical response matrix and condition number.
- PVDF sensors are distributed across the upper and lower stages, and the dynamic surrogate uses each stage’s individual kinematics. A critical bug was corrected: reduced-order foot reaction and strain-transfer calculations now share the **same PVDF-reinforced member matrices** as the global series stiffness, restoring exact normal-force equilibrium in all 10 seeds.
- The Top-3 audit includes FEM, bonded-film mechanics, PVDF ribbon shell, per-stage participation and feasible-first promotion.
- The single `Evaluate All` action continues to update FEM, electrical and spatial pressure inspectors, plus laminate stage metrics.
- Gallery shows all ten concepts with direct 3D previews; conceptual STL and JSON genomes are in `hybrid_validation_v20`. Two reference seeds (h01 thickness 0.95 mm, h10 thickness 0.58 mm) now pass the **assumed full gate** at coarse mesh, rather than relaxing thresholds.

## Acceptance tests run for this release

- 10/10 curated models generated connected HEX8 geometry and a pressure solution with force equilibrium.
- Focused hybrid + FEM + archive + laminate tests pass, including ten force-balance subtests and two tuned reference seeds. Run `python -m pytest -q tests/test_hybrid_v20.py` for the latest exact count.
- CLI smoke evolution with 2 workers, 3 seconds, 24 initial population, and active HEX8 Top-3 full audits: **2 generations and 48 evaluations; status completed**.
- The full legacy suite progressed past 80 tests but exceeded a 240-second execution budget; do not treat this as a verified full-suite pass.
- Old score generation remains versioned; the v2.0 source fingerprint includes both new modules.

## Scientific limitations

The computed FEM does not establish actual sensing accuracy. The 3D solid is voxelized and may substantially over-thicken members at coarse pitch. Upper/lower stages have identical assumed substrate elastic modulus; bonded PVDF adds a reduced embedded reinforcement. Caps, midplate, and struts are modeled as contiguous elastomer, not distinct manufactured bonded bodies. The electronic transfer/noise, recovery material constants and shell strain limits remain assumed. Read `HYBRID_RESEARCH_DESIGN_AND_EVALUATION_v20.md` for details and verified literature references.

## Final refinement and mesh-sensitivity findings

- Fixed a force-equilibrium bug in the fast hybrid model: upper/lower member reaction calculations now use the same PVDF-reinforced stiffness matrices as the series solve.
- Fixed upper-stage rotation being applied twice (once through morphology phase and again through a world-frame rotation). The physical mesh and reduced 6-DOF stiffness now share one orientation transform.
- Fixed a relative moment-balance calculation that divided roundoff in a zero-moment load case by `1e-10 Nmm`, falsely failing some refined HEX8 meshes. The denominator now uses a force×characteristic-length scale.
- Tuned h01 and h10 reference thicknesses while keeping the original screens. They pass the **coarse** 1.25-mm full audit, but this is a screening demonstration, NOT a proof of convergence.
- A 0.625-mm check changes central displacement from 0.16896→0.35224 mm (h01) and 0.01629→0.08530 mm (h10). Neither result is converged; h01 fails the reduced PVDF shell screen at 0.625 mm. See `hybrid_mesh_check_v20/check.csv`.
- All ten architectures remain mechanically connected in one solid HEX8; they have separate upper/lower PVDF readouts and a rigid-interface 6DOF *surrogate* distinct from the connected-solid solve.
