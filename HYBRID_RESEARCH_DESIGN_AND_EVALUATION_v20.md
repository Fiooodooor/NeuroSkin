# NeuroSkin 2.0 — Ten stacked, mechanically connected hybrid sensor architectures

## Scope and validity

All 10 structures are new *parametric engineering hypotheses* that use the same bottom mounting disk,
a connected intermediate plate, an upper contact plate and separate upper/lower flexible members.
Their shapes are **not reproductions of exact paper CAD** and are not claims of patent novelty.
The 0–100 catalogue rank is a transparent engineering PRIOR, entirely separate from calculated FEM and sensor scores.
The current HEX8 uses small-strain linear elasticity and voxelized members; full contact, damage, buckling and real electrostatics are absent.

## Ten scoring criteria (0–10 each, maximum 100)

1. **Normal pressure response (normal)** — 10 means more favorable for robotic skin; for complexity/risk scores higher means cheaper/safer.
2. **Shear-force separation (shear)** — 10 means more favorable for robotic skin; for complexity/risk scores higher means cheaper/safer.
3. **Off-center touch localization (position)** — 10 means more favorable for robotic skin; for complexity/risk scores higher means cheaper/safer.
4. **PVDF dynamic observability (dynamic)** — 10 means more favorable for robotic skin; for complexity/risk scores higher means cheaper/safer.
5. **Mode independence / observability (modes)** — 10 means more favorable for robotic skin; for complexity/risk scores higher means cheaper/safer.
6. **Reversible deformation (recovery)** — 10 means more favorable for robotic skin; for complexity/risk scores higher means cheaper/safer.
7. **Fatigue risk (higher is safer) (fatigue)** — 10 means more favorable for robotic skin; for complexity/risk scores higher means cheaper/safer.
8. **Fabrication feasibility (fabrication)** — 10 means more favorable for robotic skin; for complexity/risk scores higher means cheaper/safer.
9. **Readout cost / complexity (higher is simpler) (electronics)** — 10 means more favorable for robotic skin; for complexity/risk scores higher means cheaper/safer.
10. **Numerical tractability (numerical)** — 10 means more favorable for robotic skin; for complexity/risk scores higher means cheaper/safer.

## Ranking: engineering prior versus the initial synthetic/FEM audit

| Rank | Architecture | Upper | Lower | Prior /100 | Actual initial audit /100 | Coarse FEM /100 | Audited feasible? |
|---:|---|---|---|---:|---:|---:|---|
| 1 | S-Bridge / Differential Quadrant | quadrant/serpentine | quadrant/orthogonal | 84 | 81.58 | 89.80 | yes |
| 2 | Catenary Arch / Radial Trellis | crown/arched | crown/woven | 81 | 34.98 | 82.65 | NO |
| 3 | Rigid-Island Upper / Compliant Crown | quadrant/orthogonal | crown/radial | 81 | 35.66 | 87.61 | NO |
| 4 | Graded Crown / Kirigami Hinge | crown/arched | quadrant/kirigami | 80 | 35.13 | 88.81 | NO |
| 5 | Counter-Helix / Quadrant | chiral/counter | quadrant/orthogonal | 78 | 35.66 | 87.24 | NO |
| 6 | Helical Active / Dome Reference | chiral/helical | crown/arched | 78 | 35.13 | 86.21 | NO |
| 7 | Mirrored S-Pairs / Counter-Braids | quadrant/serpentine | chiral/braided | 76 | 32.32 | 85.00 | NO |
| 8 | Kirigami Hinge / Helical Reference | quadrant/kirigami | chiral/counter | 76 | 30.06 | 79.97 | NO |
| 9 | Auxetic Re-entrant / Chiral Torsion | quadrant/auxetic | chiral/helical | 75 | 28.72 | 73.55 | NO |
| 10 | Opposed Helix / Balanced Helix | chiral/helical | chiral/counter | 73 | 84.89 | 85.91 | yes |

**Critical distinction:** 2/10 starting seeds pass the complete v2.0 **assumed numerical screening**, with their seeded thicknesses and at 1.25-mm HEX8 pitch.
The remaining eight fail at least one screen. Passing the synthetic gate does not mean laboratory-validated sensitivity, stress convergence or print readiness.
All ten did achieve a connected HEX8 solve under pressure; those calculations are **not mesh-converged**.

## Mesh refinement warning for the two numerical leaders

| Model | Centre deflection, 1.25 mm [mm] | Centre deflection, 0.625 mm [mm] | Fine/coarse ratio | Shell screen at 0.625 mm |
|---|---:|---:|---:|---|
| S-Bridge / Differential Quadrant | 0.16896 | 0.35224 | 2.08 | **FAIL** |
| Opposed Helix / Balanced Helix | 0.01629 | 0.08530 | 5.24 | Pass |

Both linear HEX8 solutions satisfy force/moment equilibrium, but **neither is mesh-converged**. The coarser mesh artificially thickens thin members, in particular all 22 chiral members in the double-helix model at 1.25 mm pitch. In the h01 refined check the reduced ribbon-shell stress/strain screen fails. Lower mesh pitch alone is not sufficient to fix large-strain, adhesive or contact assumptions. Run `hybrid_mesh_check.py` and pursue fitted tet/shell meshing and actual material testing before claiming physical accuracy.

## Architecture-by-architecture development steps (observable design decisions, not private reasoning)

### 1. S-Bridge / Differential Quadrant — 84/100 prior
**CAD:** `h01_serpentine_quadrant`; `quadrant/serpentine` over `quadrant/orthogonal`.
**Literature motivation:** https://www.nature.com/articles/s41563-026-02508-7
**Role:** Compliant upper S-bends measure touch; lower orthogonal quadrant provides directional reference

Design/test sequence:
1. Need: reduce tilt dependence when normal pressure is moved across the pad.
2. Upper: four mirrored S-shaped flexures; tune bend amplitude and PVDF strain transfer.
3. Lower: four quadrant reference members tied through the middle plate; keep moderate lateral stiffness.
4. Readout: 2 upper and 2 lower PVDF strips plus separate capacitive reference channels.
5. Validation focus: off-center contact map, shear cross-coupling, two-stage displacement split and hinge fatigue.
Initial computed check: upper `0.06398` mm, lower `0.00654` mm at 0.1 N; lower share `9.3%`; coarse HEX8 score `89.80`. **Full gate: PASS (assumed numerical screen)**.

### 2. Catenary Arch / Radial Trellis — 81/100 prior
**CAD:** `h04_arched_trellis`; `crown/arched` over `crown/woven`.
**Literature motivation:** https://www.jos.ac.cn/article/doi/10.1088/1674-4926/24080006
**Role:** High upper compliance with lower redundant bracing

Design/test sequence:
1. Need: improve normal-force spatial uniformity with controlled total travel.
2. Upper: smooth catenary-like crown ribs to distribute contact pressure.
3. Lower: radial woven/trellis members to stabilize the interface with redundant paths.
4. Readout: two dynamic PVDF elements per stage and four quasi-static electrodes.
5. Validation focus: high feature count, local stress at trellis junctions, voxel-inflation and fabrication.
Initial computed check: upper `0.00668` mm, lower `0.00057` mm at 0.1 N; lower share `7.9%`; coarse HEX8 score `82.65`. **Full gate: FAIL**.

### 3. Rigid-Island Upper / Compliant Crown — 81/100 prior
**CAD:** `h07_rigid_island`; `quadrant/orthogonal` over `crown/radial`.
**Literature motivation:** https://www.sciencedirect.com/science/article/pii/S1385894726085177
**Role:** Stiff upper surface localizes force, lower flexible crown transmits common pressure

Design/test sequence:
1. Need: find robust contact position estimates while limiting sensing-layer strain.
2. Upper: comparatively stiff four-arm island/cross geometry; contact plate remains the main rigid island.
3. Lower: compliant radial crown provides the major force-responsive displacement.
4. Readout: lower static capacitance, upper differential PVDF for impact/contact gradients.
5. Validation focus: force bypass around the sensing stage and whether upper PVDF has meaningful dynamic strain.
Initial computed check: upper `0.02458` mm, lower `0.00260` mm at 0.1 N; lower share `9.6%`; coarse HEX8 score `87.61`. **Full gate: FAIL**.

### 4. Graded Crown / Kirigami Hinge — 80/100 prior
**CAD:** `h02_crown_kirigami`; `crown/arched` over `quadrant/kirigami`.
**Literature motivation:** https://advanced.onlinelibrary.wiley.com/doi/10.1002/adsr.202400012
**Role:** Top progressive arches distribute contact; lower hinge network isolates substrate strain

Design/test sequence:
1. Need: combine high normal compliance with substrate-strain rejection.
2. Upper: graded arches with a smooth profile and deliberately limited thickness.
3. Lower: kirigami-inspired four-arm flexures (NOT literal open cutouts in current CAD).
4. Readout: upper common-mode PVDF, lower differential PVDF and lower-layer capacitance.
5. Validation focus: fatigue at hinge-like regions, pressure response under 5% substrate stretch.
Initial computed check: upper `0.00778` mm, lower `0.00175` mm at 0.1 N; lower share `18.4%`; coarse HEX8 score `88.81`. **Full gate: FAIL**.

### 5. Counter-Helix / Quadrant — 78/100 prior
**CAD:** `h03_counterhelix_quadrant`; `chiral/counter` over `quadrant/orthogonal`.
**Literature motivation:** https://advanced.onlinelibrary.wiley.com/doi/10.1002/adem.202401613
**Role:** Upper counter-helix transduces dynamic torque; lower balanced quadrant distinguishes shear

Design/test sequence:
1. Need: distinguish normal contact from torsional disturbance.
2. Upper: counter-helix/chiral paths with phase-controlled twisting.
3. Lower: orthogonal quadrant flexures act as non-chiral directional reference.
4. Readout: upper torsional PVDF differential channels plus lower normal-force capacitance.
5. Validation focus: compression-to-twist leakage and X/Y force identifiability.
Initial computed check: upper `0.00511` mm, lower `0.00224` mm at 0.1 N; lower share `30.5%`; coarse HEX8 score `87.24`. **Full gate: FAIL**.

### 6. Helical Active / Dome Reference — 78/100 prior
**CAD:** `h08_helix_crown`; `chiral/helical` over `crown/arched`.
**Literature motivation:** https://www.sciencedirect.com/science/article/pii/S1359836823006443
**Role:** Upper helical PVDF acts as a dynamic receptor; lower dome acts as static force reference

Design/test sequence:
1. Need: separate short impact events from slowly varying touch.
2. Upper: helical stage concentrates dynamic bending at the PVDF surface.
3. Lower: crown stage provides comparatively smooth normal-force transfer.
4. Readout: upper PVDF high-pass channels and lower static capacitive channels.
5. Validation focus: 2/25/150 Hz response, elastomer viscoelastic attenuation and contact creep.
Initial computed check: upper `0.00372` mm, lower `0.00116` mm at 0.1 N; lower share `23.7%`; coarse HEX8 score `86.21`. **Full gate: FAIL**.

### 7. Mirrored S-Pairs / Counter-Braids — 76/100 prior
**CAD:** `h06_mirror_braid`; `quadrant/serpentine` over `chiral/braided`.
**Literature motivation:** https://www.sciencedirect.com/science/article/pii/S1385894725080283
**Role:** Mirrored upper paths give X/Y differential channels; lower braids provide common-mode filtering

Design/test sequence:
1. Need: obtain independent directional signatures while rejecting global robot motion.
2. Upper: mirrored S-bends for X/Y response.
3. Lower: braided chiral paths for global torsion and reference deformation.
4. Readout: independently measured films in both stages; no irreversible summation before acquisition.
5. Validation focus: condition number of response matrix and adhesive fatigue at twist extrema.
Initial computed check: upper `0.01942` mm, lower `0.00144` mm at 0.1 N; lower share `6.9%`; coarse HEX8 score `85.00`. **Full gate: FAIL**.

### 8. Kirigami Hinge / Helical Reference — 76/100 prior
**CAD:** `h09_kirigami_helix`; `quadrant/kirigami` over `chiral/counter`.
**Literature motivation:** https://advanced.onlinelibrary.wiley.com/doi/10.1002/adsr.202400012
**Role:** Upper thin hinges decouple substrate stretch, lower counter-helix offers torsional comparison

Design/test sequence:
1. Need: tolerate substrate stretch while preserving tactile sensitivity.
2. Upper: kirigami-inspired compliant bends, currently represented by connected tubes.
3. Lower: counter-helical stabilizer and twist reference.
4. Readout: opposing PVDF pairs plus an independent lower-stage capacitive gap.
5. Validation focus: 5% axial stretch, cyclic strain and hinge safety; actual slit topology requires future shell CAD.
Initial computed check: upper `0.03405` mm, lower `0.00108` mm at 0.1 N; lower share `3.1%`; coarse HEX8 score `79.97`. **Full gate: FAIL**.

### 9. Auxetic Re-entrant / Chiral Torsion — 75/100 prior
**CAD:** `h05_auxtwist`; `quadrant/auxetic` over `chiral/helical`.
**Literature motivation:** https://www.sciencedirect.com/science/article/pii/S2211285524008747
**Role:** Upper re-entrant deformation amplifies lateral gradients; lower chiral stage responds to torsion

Design/test sequence:
1. Need: mechanical amplification of directional loads at small normal forces.
2. Upper: re-entrant auxetic-inspired arm trajectories (negative Poisson ratio NOT established).
3. Lower: chiral torsional stage with separate electrodes.
4. Readout: PVDF X/Y differential and capacitance common mode.
5. Validation focus: verify negative Poisson behavior experimentally, buckling, FEM mesh convergence and hysteresis.
Initial computed check: upper `0.02150` mm, lower `0.00138` mm at 0.1 N; lower share `6.0%`; coarse HEX8 score `73.55`. **Full gate: FAIL**.

### 10. Opposed Helix / Balanced Helix — 73/100 prior
**CAD:** `h10_dual_chiral`; `chiral/helical` over `chiral/counter`.
**Literature motivation:** https://www.sciencedirect.com/science/article/pii/S0264127525010494
**Role:** Two stages have opposed chirality and different stiffness for signed torque discrimination

Design/test sequence:
1. Need: use opposite compression-to-twist signs as mechanical information channels.
2. Upper: positive-pitch helix; lower: negative-pitch counter-helix (handedness regression tested).
3. Shared plate: mechanically couples two stages in series, with no top-to-base bypass.
4. Readout: 3 PVDF sensors per stage, independent before optional digitally signed combination.
5. Validation focus: cancellation under pure Fz, torsion cross-talk and chirality manufacturing tolerance.
Initial computed check: upper `0.00430` mm, lower `0.00103` mm at 0.1 N; lower share `19.3%`; coarse HEX8 score `85.91`. **Full gate: PASS (assumed numerical screen)**.

## Exact software integration (v2.0)

1. `hybrid_library.py`: 10 explicit variants, scored with the same 10 criteria; API exposes rationale, research URL, gene presets.
2. `hybrid_geometry.py`: two *different* source topologies, each built in local coordinates and joined by one mechanically continuous middle plate at `hybrid_split × height`.
3. `advanced.py`: 6 new evolvable stage genes (`hybrid_split`, `hybrid_upper_scale`, `hybrid_lower_scale`, `hybrid_phase`, `hybrid_plate_thickness`, `hybrid_sensor_mode`) and a categorical `hybrid_id`. Local mutation, restart, crossover and generation-zero seeding now support them.
4. `advanced.curve_stiffness`: use **series compliance** `K_total⁻¹ = K_upper⁻¹ + K_lower⁻¹`, NOT `K_upper + K_lower`, for the fast stage. This is a rigid-plate 6-DOF approximation.
5. `physical_fem.voxel_mesh`: explicit bottom disk + intermediate plate + top pad and both stage rib sets in ONE face-connected solid mesh.
6. `pvdf_array.py`: distribute PVDF channels across the upper AND lower stage; default two independent films per stage.
7. `electromechanics.py` + `piezoelectric.py`: stage-separated mechanical displacements, bottom-only support reactions and independent film readouts. Capacitive transfer remains an assumed analytical function.
8. `physical_fem.fem_sweep`: eight standardized linear-HEX8 load cases, per-stage 3D displacement, three-mode mechanical response signature, strain, stress and equilibrium checks; bonded PVDF/adhesive reinforcement and final shell postprocessing are preserved.
9. `advanced.audit_job`: three best finalists receive the same FEM, spatial, dynamic, inverse reconstruction, manufacturing and recovery protocols. A previous incumbent stays unless a fully audited finalist is superior according to feasible-first promotion.
10. `server.py` + `static/index.html`: `/api/hybrid_library`, `/api/hybrids/{id}` and a Basic/Advanced-visible hybrid gallery; click Preview, then the existing single `Evaluate All` action.

## Evaluation protocol, decision thresholds and convergence

- **Stage 0:** validate a non-empty middle plate and a face-connected lower-to-upper load path; archive random seed, genome and provenance.
- **Stage 1:** fast all-individual screening: 0.1 N distributed vertical contact, SNR ≥ 3 using assumed noise, finite downward deflection, bounded tilt ≤ 0.35 rad, no capacitive gap bottom-out, plus shear/nuisance tests.
- **Stage 2:** three finalist audits each generation: 0.025 / 0.1 / 0.4 N pressure maps, X/Y force, torsion, off-centre loads, PVDF at 2 / 25 / 150 Hz, 5-variable synthetic observability, synthetic holdout inversion, fatigue/manufacturing flags and SLS-inspired unloading screen.
- **Stage 3:** connected HEX8 3D solid with eight force/moment cases; upper and lower displacements measured at distinct height surfaces; compare lower participation ratio and mechanical mode rank.
- **Stage 4:** bonded PVDF reinforcement and final reduced PVDF ribbon-shell computation; penalize exceeding assumed film-strain/shear thresholds.
- **Stage 5:** meshes at 1.25 / 0.625 / 0.3125 / 0.15625 mm (progressively as resource limits permit). Do not accept quantitative stress/deflection results unless key observables converge under an explicit acceptance tolerance (initial target 5–10%, not universally guaranteed).
- **Stage 6:** qualify prototypes with real silicone/TPU and PVDF; calibrate hysteresis, SNR, force cross-coupling, recovery and 10k/100k strain-cycle durability; repeat patent/FTO assessment with a patent attorney.

When the optimizer rejects a design, its feasible-first score remains below the feasible band. A high *FEM-only* score never makes a failed synthetic-electrical contact gate disappear.

## Example commands

```powershell
python server.py --cores auto --open --port 8765
python benchmark_hybrids.py --pitch 1.25 --grid 3 --out hybrid_validation_v20
python benchmark_hybrids.py --pitch 0.625 --grid 5 --out hybrid_finer
python -m pytest -q tests/test_hybrid_v20.py
```

## References and patent context

- Multiscale miniaturized 3D force sensors (Nature Materials 2026): https://doi.org/10.1038/s41563-026-02508-7
- Layered 3D force decoding (Chemical Engineering Journal): https://www.sciencedirect.com/science/article/pii/S1385894725080283
- Kirigami hinges for stretchable tactile arrays (Advanced Sensor Research): https://doi.org/10.1002/adsr.202400012
- Chiral compression/twist topology (Advanced Engineering Materials): https://doi.org/10.1002/adem.202401613
- 3D metamaterial super-chirality and achirality (Materials & Design): https://www.sciencedirect.com/science/article/pii/S0264127525010494
- Layered anisotropic force decoupling (Chemical Engineering Journal 2026): https://www.sciencedirect.com/science/article/pii/S1385894726085177
- Auxetic kirigami sensing: https://www.sciencedirect.com/science/article/pii/S2211285524008747
- Patent US20240044729A1 (contact force/lateral strain): https://patents.google.com/patent/US20240044729A1/en
- Patent US20240410770A1 (multilayer robotic skin): https://patents.google.com/patent/US20240410770A1/en
- Patent US11898924B2 (differential shear capacitance): https://patents.google.com/patent/US11898924B2/en

Patent publication does not establish actual infringement or freedom to operate. The proposed composite arrangement is not claimed to be novel or patentable without a claim-level search and jurisdiction-specific analysis.
