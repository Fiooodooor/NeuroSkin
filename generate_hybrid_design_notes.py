from __future__ import annotations
from pathlib import Path
import csv
import json
from hybrid_library import ranked,CRITERIA

ENGINEERING_STEPS={
'h01_serpentine_quadrant':[
'Need: reduce tilt dependence when normal pressure is moved across the pad.',
'Upper: four mirrored S-shaped flexures; tune bend amplitude and PVDF strain transfer.',
'Lower: four quadrant reference members tied through the middle plate; keep moderate lateral stiffness.',
'Readout: 2 upper and 2 lower PVDF strips plus separate capacitive reference channels.',
'Validation focus: off-center contact map, shear cross-coupling, two-stage displacement split and hinge fatigue.'
],
'h04_arched_trellis':[
'Need: improve normal-force spatial uniformity with controlled total travel.',
'Upper: smooth catenary-like crown ribs to distribute contact pressure.',
'Lower: radial woven/trellis members to stabilize the interface with redundant paths.',
'Readout: two dynamic PVDF elements per stage and four quasi-static electrodes.',
'Validation focus: high feature count, local stress at trellis junctions, voxel-inflation and fabrication.'
],
'h07_rigid_island':[
'Need: find robust contact position estimates while limiting sensing-layer strain.',
'Upper: comparatively stiff four-arm island/cross geometry; contact plate remains the main rigid island.',
'Lower: compliant radial crown provides the major force-responsive displacement.',
'Readout: lower static capacitance, upper differential PVDF for impact/contact gradients.',
'Validation focus: force bypass around the sensing stage and whether upper PVDF has meaningful dynamic strain.'
],
'h02_crown_kirigami':[
'Need: combine high normal compliance with substrate-strain rejection.',
'Upper: graded arches with a smooth profile and deliberately limited thickness.',
'Lower: kirigami-inspired four-arm flexures (NOT literal open cutouts in current CAD).',
'Readout: upper common-mode PVDF, lower differential PVDF and lower-layer capacitance.',
'Validation focus: fatigue at hinge-like regions, pressure response under 5% substrate stretch.'
],
'h03_counterhelix_quadrant':[
'Need: distinguish normal contact from torsional disturbance.',
'Upper: counter-helix/chiral paths with phase-controlled twisting.',
'Lower: orthogonal quadrant flexures act as non-chiral directional reference.',
'Readout: upper torsional PVDF differential channels plus lower normal-force capacitance.',
'Validation focus: compression-to-twist leakage and X/Y force identifiability.'
],
'h08_helix_crown':[
'Need: separate short impact events from slowly varying touch.',
'Upper: helical stage concentrates dynamic bending at the PVDF surface.',
'Lower: crown stage provides comparatively smooth normal-force transfer.',
'Readout: upper PVDF high-pass channels and lower static capacitive channels.',
'Validation focus: 2/25/150 Hz response, elastomer viscoelastic attenuation and contact creep.'
],
'h06_mirror_braid':[
'Need: obtain independent directional signatures while rejecting global robot motion.',
'Upper: mirrored S-bends for X/Y response.',
'Lower: braided chiral paths for global torsion and reference deformation.',
'Readout: independently measured films in both stages; no irreversible summation before acquisition.',
'Validation focus: condition number of response matrix and adhesive fatigue at twist extrema.'
],
'h09_kirigami_helix':[
'Need: tolerate substrate stretch while preserving tactile sensitivity.',
'Upper: kirigami-inspired compliant bends, currently represented by connected tubes.',
'Lower: counter-helical stabilizer and twist reference.',
'Readout: opposing PVDF pairs plus an independent lower-stage capacitive gap.',
'Validation focus: 5% axial stretch, cyclic strain and hinge safety; actual slit topology requires future shell CAD.'
],
'h05_auxtwist':[
'Need: mechanical amplification of directional loads at small normal forces.',
'Upper: re-entrant auxetic-inspired arm trajectories (negative Poisson ratio NOT established).',
'Lower: chiral torsional stage with separate electrodes.',
'Readout: PVDF X/Y differential and capacitance common mode.',
'Validation focus: verify negative Poisson behavior experimentally, buckling, FEM mesh convergence and hysteresis.'
],
'h10_dual_chiral':[
'Need: use opposite compression-to-twist signs as mechanical information channels.',
'Upper: positive-pitch helix; lower: negative-pitch counter-helix (handedness regression tested).',
'Shared plate: mechanically couples two stages in series, with no top-to-base bypass.',
'Readout: 3 PVDF sensors per stage, independent before optional digitally signed combination.',
'Validation focus: cancellation under pure Fz, torsion cross-talk and chirality manufacturing tolerance.'
]}

root=Path(__file__).parent
comparison=json.loads((root/'hybrid_validation_v20'/'comparison.json').read_text())['results']
by_id={r['id']:r for r in comparison}
sp=ranked()
lines=[
'# NeuroSkin 2.0 — Ten stacked, mechanically connected hybrid sensor architectures',
'',
'## Scope and validity',
'',
'All 10 structures are new *parametric engineering hypotheses* that use the same bottom mounting disk,',
'a connected intermediate plate, an upper contact plate and separate upper/lower flexible members.',
'Their shapes are **not reproductions of exact paper CAD** and are not claims of patent novelty.',
'The 0–100 catalogue rank is a transparent engineering PRIOR, entirely separate from calculated FEM and sensor scores.',
'The current HEX8 uses small-strain linear elasticity and voxelized members; full contact, damage, buckling and real electrostatics are absent.',
'',
'## Ten scoring criteria (0–10 each, maximum 100)',
'',
]+[f'{i}. **{title} ({key})** — 10 means more favorable for robotic skin; for complexity/risk scores higher means cheaper/safer.' for i,(key,title) in enumerate(CRITERIA,1)]+['',
'## Ranking: engineering prior versus the initial synthetic/FEM audit',
'',
'| Rank | Architecture | Upper | Lower | Prior /100 | Actual initial audit /100 | Coarse FEM /100 | Audited feasible? |',
'|---:|---|---|---|---:|---:|---:|---|',
]
for i,s in enumerate(sp,1):
 r=by_id[s.id]
 lines.append(f'| {i} | {s.name} | {s.upper_family}/{s.upper_topology} | {s.lower_family}/{s.lower_topology} | {sum(s.scores)} | {r["audit_score_100"]:.2f} | {r["fem_score_100"]:.2f} | {"yes" if r["audit_feasible"] else "NO"} |')
lines+=['',
f'**Critical distinction:** {sum(bool(r["audit_feasible"]) for r in comparison)}/10 starting seeds pass the complete v2.0 **assumed numerical screening**, with their seeded thicknesses and at 1.25-mm HEX8 pitch.',
'The remaining eight fail at least one screen. Passing the synthetic gate does not mean laboratory-validated sensitivity, stress convergence or print readiness.',
'All ten did achieve a connected HEX8 solve under pressure; those calculations are **not mesh-converged**.',
'',
'## Architecture-by-architecture development steps (observable design decisions, not private reasoning)',
'']
for i,s in enumerate(sp,1):
 r=by_id[s.id]
 lines += [f'### {i}. {s.name} — {sum(s.scores)}/100 prior',
          f'**CAD:** `{s.id}`; `{s.upper_family}/{s.upper_topology}` over `{s.lower_family}/{s.lower_topology}`.',
          f'**Literature motivation:** {s.evidence_url}',
          f'**Role:** {s.role}',
          '','Design/test sequence:']
 lines += [f'{j}. {part}' for j,part in enumerate(ENGINEERING_STEPS[s.id],1)]
 lines += [f'Initial computed check: upper `{r["hybrid_upper_compression_mm"]:.5f}` mm, lower `{r["hybrid_lower_compression_mm"]:.5f}` mm at 0.1 N; lower share `{r["hybrid_lower_share"]:.1%}`; coarse HEX8 score `{r["fem_score_100"]:.2f}`. **Full gate: {"PASS (assumed numerical screen)" if r["audit_feasible"] else "FAIL"}**.','']
lines += [
'## Exact software integration (v2.0)',
'',
'1. `hybrid_library.py`: 10 explicit variants, scored with the same 10 criteria; API exposes rationale, research URL, gene presets.',
'2. `hybrid_geometry.py`: two *different* source topologies, each built in local coordinates and joined by one mechanically continuous middle plate at `hybrid_split × height`.',
'3. `advanced.py`: 6 new evolvable stage genes (`hybrid_split`, `hybrid_upper_scale`, `hybrid_lower_scale`, `hybrid_phase`, `hybrid_plate_thickness`, `hybrid_sensor_mode`) and a categorical `hybrid_id`. Local mutation, restart, crossover and generation-zero seeding now support them.',
'4. `advanced.curve_stiffness`: use **series compliance** `K_total⁻¹ = K_upper⁻¹ + K_lower⁻¹`, NOT `K_upper + K_lower`, for the fast stage. This is a rigid-plate 6-DOF approximation.',
'5. `physical_fem.voxel_mesh`: explicit bottom disk + intermediate plate + top pad and both stage rib sets in ONE face-connected solid mesh.',
'6. `pvdf_array.py`: distribute PVDF channels across the upper AND lower stage; default two independent films per stage.',
'7. `electromechanics.py` + `piezoelectric.py`: stage-separated mechanical displacements, bottom-only support reactions and independent film readouts. Capacitive transfer remains an assumed analytical function.',
'8. `physical_fem.fem_sweep`: eight standardized linear-HEX8 load cases, per-stage 3D displacement, three-mode mechanical response signature, strain, stress and equilibrium checks; bonded PVDF/adhesive reinforcement and final shell postprocessing are preserved.',
'9. `advanced.audit_job`: three best finalists receive the same FEM, spatial, dynamic, inverse reconstruction, manufacturing and recovery protocols. A previous incumbent stays unless a fully audited finalist is superior according to feasible-first promotion.',
'10. `server.py` + `static/index.html`: `/api/hybrid_library`, `/api/hybrids/{id}` and a Basic/Advanced-visible hybrid gallery; click Preview, then the existing single `Evaluate All` action.',
'',
'## Evaluation protocol, decision thresholds and convergence',
'',
'- **Stage 0:** validate a non-empty middle plate and a face-connected lower-to-upper load path; archive random seed, genome and provenance.',
'- **Stage 1:** fast all-individual screening: 0.1 N distributed vertical contact, SNR ≥ 3 using assumed noise, finite downward deflection, bounded tilt ≤ 0.35 rad, no capacitive gap bottom-out, plus shear/nuisance tests.',
'- **Stage 2:** three finalist audits each generation: 0.025 / 0.1 / 0.4 N pressure maps, X/Y force, torsion, off-centre loads, PVDF at 2 / 25 / 150 Hz, 5-variable synthetic observability, synthetic holdout inversion, fatigue/manufacturing flags and SLS-inspired unloading screen.',
'- **Stage 3:** connected HEX8 3D solid with eight force/moment cases; upper and lower displacements measured at distinct height surfaces; compare lower participation ratio and mechanical mode rank.',
'- **Stage 4:** bonded PVDF reinforcement and final reduced PVDF ribbon-shell computation; penalize exceeding assumed film-strain/shear thresholds.',
'- **Stage 5:** meshes at 1.25 / 0.625 / 0.3125 / 0.15625 mm (progressively as resource limits permit). Do not accept quantitative stress/deflection results unless key observables converge under an explicit acceptance tolerance (initial target 5–10%, not universally guaranteed).',
'- **Stage 6:** qualify prototypes with real silicone/TPU and PVDF; calibrate hysteresis, SNR, force cross-coupling, recovery and 10k/100k strain-cycle durability; repeat patent/FTO assessment with a patent attorney.',
'',
'When the optimizer rejects a design, its feasible-first score remains below the feasible band. A high *FEM-only* score never makes a failed synthetic-electrical contact gate disappear.',
'',
'## Example commands',
'',
'```powershell',
'python server.py --cores auto --open --port 8765',
'python benchmark_hybrids.py --pitch 1.25 --grid 3 --out hybrid_validation_v20',
'python benchmark_hybrids.py --pitch 0.625 --grid 5 --out hybrid_finer',
'python -m pytest -q tests/test_hybrid_v20.py',
'```',
'',
'## References and patent context',
'',
'- Multiscale miniaturized 3D force sensors (Nature Materials 2026): https://doi.org/10.1038/s41563-026-02508-7',
'- Layered 3D force decoding (Chemical Engineering Journal): https://www.sciencedirect.com/science/article/pii/S1385894725080283',
'- Kirigami hinges for stretchable tactile arrays (Advanced Sensor Research): https://doi.org/10.1002/adsr.202400012',
'- Chiral compression/twist topology (Advanced Engineering Materials): https://doi.org/10.1002/adem.202401613',
'- 3D metamaterial super-chirality and achirality (Materials & Design): https://www.sciencedirect.com/science/article/pii/S0264127525010494',
'- Layered anisotropic force decoupling (Chemical Engineering Journal 2026): https://www.sciencedirect.com/science/article/pii/S1385894726085177',
'- Auxetic kirigami sensing: https://www.sciencedirect.com/science/article/pii/S2211285524008747',
'- Patent US20240044729A1 (contact force/lateral strain): https://patents.google.com/patent/US20240044729A1/en',
'- Patent US20240410770A1 (multilayer robotic skin): https://patents.google.com/patent/US20240410770A1/en',
'- Patent US11898924B2 (differential shear capacitance): https://patents.google.com/patent/US11898924B2/en',
'',
'Patent publication does not establish actual infringement or freedom to operate. The proposed composite arrangement is not claimed to be novel or patentable without a claim-level search and jurisdiction-specific analysis.',
]
(root/'HYBRID_RESEARCH_DESIGN_AND_EVALUATION_v20.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
with (root/'HYBRID_PRIOR_SCORES_v20.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f)
 w.writerow(['rank','id','name','upper_family','upper_topology','lower_family','lower_topology']+[key for key,_ in CRITERIA]+['prior_score_100','research_url'])
 for rank,s in enumerate(sp,1):w.writerow([rank,s.id,s.name,s.upper_family,s.upper_topology,s.lower_family,s.lower_topology,*s.scores,sum(s.scores),s.evidence_url])
print('design study and prior scoring generated')
