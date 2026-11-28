# NeuroSkin Evolution Lab v2.2 — Validation Engine

This version adds a strict synthetic-validation protocol, independent position-group holdout,
uncertainty analysis, fail-closed audit, unified mechanical score merger, source/protocol
hashes, and a measurement CSV importer. **This is experimental software; current
simulations do not establish hardware sensor performance or nonlinear contact accuracy.**

- [Plan zadań i kryteria akceptacji](IMPLEMENTATION_PLAN.md)
- [Szczegóły wydania](RELEASE_NOTES_v22.md)
- [Protokół](validation_protocol_v30.json)

Windows 11 / Python 3.14 / HP Z840:

```powershell
python -m pip install -r requirements.txt
python -m pip check
python server.py --cores auto --open --port 8765
```

Testy zmienionych modułów:

```powershell
python -m pytest -q tests/test_validation.py tests/test_pipeline.py tests/test_archive_api.py
```

# NeuroSkin 2.1.1 — Windows shutdown hotfix

See [RELEASE_NOTES_v211_SHUTDOWN.md](RELEASE_NOTES_v211_SHUTDOWN.md) for Ctrl+C fixes and PowerShell launcher.

# NeuroSkin Evolution Lab v2.1 — Search Space & Orientation

The current release fixes the old Search space selector and adds explicit hybrid
scope control, procedural two-stage stage-pair generation, adaptive exploration,
local precision refinement, QD niches and upper/lower rotation scans. See
[RELEASE_NOTES_v21.md](RELEASE_NOTES_v21.md) for full usage and limitations.

# NeuroSkin Evolution Lab 2.0 — Two-stage hybrid sensing structures

**New release: ten connected double-stage architectures, research-based design catalogue, detailed STL concept models, and stage-resolved mechanical/electrical evaluation.**

The existing single-stage Crown, Chiral and Quadrant families remain supported.
The 10 new architectures are available at the top of the GUI under **Ten two-stage hybrid architectures**; use **Preview** then the existing **Evaluate All** button. All ten are also generation-zero genomes for mixed-family evolution. The final Top-3 audit uses connected HEX8 FEM when enabled.

## Windows 11 / HP Z840 installation

```powershell
python -m pip install -r requirements.txt
python -m pip check
python server.py --cores auto --open --port 8765
```

For a 3D mesh-sensitivity check of the two leading numerical seeds:

```powershell
python hybrid_mesh_check.py --pitches 1.25,0.625 --out hybrid_mesh_check_v20
```

**Warning:** the two current reference seeds are NOT mesh-converged. The 
1.25→0.625 mm displacement changes are large; h01 additionally fails a
PVDF laminate-shell screen at 0.625 mm. Never use the coarse 1.25 mm
passing score as material qualification.

For a reproducible baseline / STL catalogue:

```powershell
python benchmark_hybrids.py --pitch 1.25 --grid 3 --out hybrid_validation_v20
python hybrid_preview.py
python -m pytest -q tests/test_hybrid.py
```

All dependencies are listed in **one** `requirements.txt`, including CUDA 12 CuPy for Quadro P1000. The GPU remains optional for runtime FEM because your benchmark found CPU much faster for small problems. Defaults remain CPU-first.

## Important scientific caveats

- Every hybrid has a face-connected 3D HEX8 mesh including the middle plate and both stages, but the material model is linear elastic; the plate has the same nominal material as the flexures (its enhanced geometric stiffness is not a separate rigid material).
- The fast screening model assumes a rigid 6DOF middle interface with two stage compliances in series. It is **not equivalent** to the full HEX8 field. The original beam FEM cannot model the middle plate and explicitly rejects hybrid genomes.
- PVDF and adhesive use embedded stiffness and final reduced shell postprocessing, **not** full multilayer multiphysics FEM or experimental material calibration.
- The ten 0–100 engineering prior scores are subjective and reproducible. Two deliberately tuned reference genomes (h01 and h10) pass the *assumed synthetic + coarse HEX8 + laminate-shell* screen; eight starting seeds fail. Passing is not hardware validation or mesh convergence.
- Historical pre-2.0 fitness scores are **not comparable** with v2.0; reopen models and recompute them.

See [HYBRID_RESEARCH_DESIGN_AND_EVALUATION_v20.md](HYBRID_RESEARCH_DESIGN_AND_EVALUATION_v20.md) for 10 designs, the 10×10 ranking, literature, patents, load cases, testing steps and exact integration architecture.

## Release validation

The v2.0 acceptance suite checks 3D load-path connectivity, PVDF in both stages, series compliance, middle-plate displacement under force, standardized loads, laminate shell, GUI/API, and compatibility with old genomes. Some original long-running integration tests can exceed short CI timeouts; see release notes for exactly which tests completed.

---

# NeuroSkin Evolution Lab 1.9.1 — CURRENT RELEASE

**Windows 11 / Python 3.14 / Quadro P1000 installation:** `python -m pip install -r requirements.txt` then `python server.py --cores auto --open --port 8765`.

This refinement makes **feasible-first Top-3 selection** consistent after the complete FEM and laminate-shell audit, corrects the operating-band pressure diagnostics (0.1/0.4 N vs separate 25 mN diagnostic), adds sensor-gap/electrode-area/mount-compliance genetic parameters, and provides gradient-guided mutations rather than plateauing on hard failures. The single **Evaluate All** button continues to update all inspectors. Saved experiments remain accessible, but previous fitness values are historical and incomparable until recalculated.

Read [RELEASE_NOTES_v191.md](RELEASE_NOTES_v191.md) first for scientific limitations, test commands, complete change list and references. `refinement_benchmark.py` generates a reproducible initial-population report, and `render_refinement_preview.py` generates a spatial SNR comparison for an unchanged symmetric Quadrant mechanism under two electronic-design assumptions.

---

# NeuroSkin 1.9 — CURRENT RELEASE (read before historical notes)

## What changed in v1.9
- Added a **final laminate-shell post-processing stage** for resolved PVDF ribbon mechanics after the substrate FEM solve.
- Added UI support for a **final PVDF ribbon-shell graphic** and shell summary metrics in the Mechanical FEM area.
- Integrated the shell stage into **Evaluate All** and into the **Top-3 full audit** decision basis.
- Added preview artifact `LAMINATE_SHELL_PREVIEW_v19.png` plus a helper script to regenerate it.

- Full instructions and physical limitations: [RELEASE_NOTES_v18.md](RELEASE_NOTES_v18.md).
- One primary **Evaluate All** action updates actual mechanical FEM, load-case/electrical and spatial-pressure inspectors. The Top-3 audit panel is displayed under the 3D viewer, above mechanical FEM.
- **Mechanical PVDF + adhesive contributions are now approximated in the FE equation** (embedded membrane shear-lag for HEX8 and composite-rod approximation for beam). The same laminate parameters affect fast fitness and the complete Top-3 audit each generation when FEM is enabled.
- The older paragraphs below document how previous releases worked; statements saying PVDF stiffness is absent describe those **old versions**, not v1.8.
- Installation: `python -m pip install -r requirements.txt` then `python server.py --cores auto --open --port 8765`.

---

# NeuroSkin Evolution Lab v1.7 — one requirements file, CPU-first benchmark, Windows affinity fix

**Installation (Windows 11, Python 3.14, Quadro P1000):**

```powershell
python -m pip install -r requirements.txt
python -m pip check
python environment_doctor.py --gpu
python server.py --cores auto --open --port 8765
```

One `requirements.txt` contains **all** dependencies, including Numba, CuPy CUDA 12 `[ctk]`, Gmsh, scikit-fem, meshio and PyVista. Expect larger installation/downloads (VTK/CUDA). The installed CuPy 14.x and driver are preserved by pip if they satisfy the requirements. `launch_windows.bat` starts the app and no longer reinstalls packages. `install_windows.bat` performs installation and a dependency check once.

**Your verified baseline:** Quadro P1000 CC 6.1 / 4 GiB VRAM; CUDA12 CuPy CG smoke test passed. At 125 HEX8 elements, CPU 0.014618 s vs CUDA 21.964896 s cold. For this size, GPU is **~1502× slower in total wall time**, not a winning backend. GPU remains opt-in; CPU and Numba matrix-free HEX8 remain defaults for 4×/8× meshes.

**Hardware affinity correction:** Windows reports 88 host threads, but this process reports access to 44. With SMT2 the conservative accessible physical-core estimate is 22; auto worker recommendation is approximately 20 rather than the old 40. Actual NUMA/processor-group reach must be measured, not inferred solely from affinity counts. Use `python hardware_profile.py --json`, then benchmark 12/16/20/24/32 workers to establish the fastest configuration.

**Fairer benchmark:**

```powershell
python hardware_benchmark.py --family quadrant --pitch 1.25 --repeats 5 --warmup 2 --case normal --out gpu_vs_cpu_v17.json
python hardware_benchmark.py --family quadrant --pitch 1.25 --repeats 5 --warmup 2 --case offset --out gpu_offset_v17.json
```

It reports setup/first solve separately from warm repeated solves, plus whole-field numerical agreement. GPU is recommended only if the entire measured workflow is faster and displacement fields match. **Do not equate CUDA correctness with GPU acceleration.** Your `CUDA_PATH` warning is not necessarily fatal with the `[ctk]` wheel; the code filters only the specific toolkit-path warning during validated CUDA initialization, leaving genuine errors visible. Avoid inventing `CUDA_PATH` pointing to the driver directory.

**Scope unchanged:** all FEM models still use small-strain linear elasticity. Optional Gmsh/scikit-fem/PyVista packages are installed as requested, but the production simulation engine does not silently switch to those packages or claim nonlinear hyperelasticity. The current PVDF stiffness still is not incorporated into continuum mechanics. Scoring remains an engineering surrogate with Top-3 FEM checks, not measured tactile-sensor accuracy.

See [RELEASE_NOTES_v17.md](RELEASE_NOTES_v17.md), [WORKSTATION_HP_Z840.md](WORKSTATION_HP_Z840.md) and [RELEASE_NOTES_v16.md](RELEASE_NOTES_v16.md).

---

# NeuroSkin Evolution Lab v1.6

**NEW:** Read [`RELEASE_NOTES_v16.md`](RELEASE_NOTES_v16.md) for the 20 new geometries, 10×10 scoring, top-10 evolutionary seeding, 1–8 PVDF choices, basic/advanced GUI with **Evolve** and **Evaluate All**, and time-dependent recovery screening. The full 20-STL catalog is under [`seed_models_v16/`](seed_models_v16/); research references are documented in [`docs/SCIENTIFIC_SOURCES.md`](docs/SCIENTIFIC_SOURCES.md).

Start on Windows:

```powershell
python -m pip install -r requirements.txt
python server.py --cores auto --open --port 8765
```

The previous documentation is retained below for historical context; any stated version numbers or limitations below reflect earlier releases rather than v1.6.

---

**Current release: NeuroSkin 1.4.** See [RELEASE_NOTES_v14.md](RELEASE_NOTES_v14.md) for multi-film PVDF symmetry, archival preview upgrades and the *remaining* missing PVDF stiffness in FEM.

# NeuroSkin Evolution Lab v1.3 — fine-grid solid FEM and refined flexures

**Start here:**

```bash
python -m pip install -r requirements.txt
python server.py --cores 8 --open --port 8765
```

Open `http://127.0.0.1:8765`. Select the actual mechanical solver **Solid 3D HEX8** (default) and mesh pitch **0.3125 mm (4× finer)** or **0.15625 mm (8× finer)**. The optional **3D beam FEM** is useful for fast screening but does **not** refine the solid volume. Both GUI modes use the same selected solver and optimization settings. Current archives remain accessible in **Saved experiments**.

The old contact-patch failure is now handled by adaptive patch expansion and a nearest-top-node fallback; the action and effective patch radius are recorded for review. Legs are now thinner, geometrically tapered and rendered as continuous closed tubes, not overlapping cylinders. The taper affects both the quick mechanical screening and solid FEM voxelization.

For reproducing the full mesh resolution study:

```bash
python mesh_study.py --family quadrant --seed 42 --pitches 1.25,0.625,0.3125,0.15625 --out study
```

For separate full field export:

```bash
python fem_cli.py --backend hex8 --family quadrant --pitch 0.15625 --force 0.1 --cg-maxiter 5000 --cg-timeout 180 --out fem_8x
```

**Read `FEM_README.md` first** for material assumptions, iterative CG limits, voxel inflation, convergence, estimated memory and why 8× more elements per dimension does not mean 8× more accurate force predictions. The project is an experimental engineering tool, **not a production-validated nonlinear digital twin**.

---

# NeuroSkin Evolution Lab 1.0 — full Top-3 audit, Basic/Advanced UI and corrected 3D PVDF display

## Run interactive app

```bash
python -m pip install -r requirements.txt
python server.py --cores 4 --open --port 8765
```
Open http://127.0.0.1:8765. Select CPU workers in the left panel (server --cores sets the default). `launch.sh 4` also works on Linux/macOS. On Windows run `launch_windows.bat 4`.

## Headless evolution

```bash
python evolve_cli.py --cores 4 --seconds 120 --population 128 --mode all --gate --grid 3 --exploration 0.8 --out results
```

`--cores` creates *separate processes* using spawn rather than threads. Native BLAS parallelism is set to one thread per worker. The timed evolution runs until a complete generation finishes, so a generation already underway may exceed the selected duration slightly. Pause takes effect between generations. Stopping also finishes in-flight generation before cancellation. `--cores 1` runs sequentially. The OS/cgroup may still limit actual CPU share; 100% CPU utilization is **not** guaranteed. Large batch/pool and expensive spatial gate improve worker occupancy. Do not use more workers than the available CPU quota; memory usage scales with workers. CPU overutilization is not a useful objective by itself.

## Throughput test

```bash
python benchmark.py --cores 1,2,4 --population 96 --repeats 3 --gate
```

Benchmark includes worker startup overhead; best worker count depends on the workload. For very short runs multicore may be **slower** than sequential mode.

## What was added

- 3 mechanically anchored sensor families, now **10 topology labels each (30 combinations)**: crown, chiral and four-foot quadrant.
- Additional morphology parameters (23 genes per family; some family-specific parameters). Procedural branches are physically connected between base and touch pad, with deterministic seeded waves and smooth endpoints.
- Adjustable radius, height, beam thickness, number of ribs, curvature, taper, twist, offset, local waves, frequency, spatial phase, local radius gradient, variable modulus (assumption), extra load paths, and a deterministic procedural seed.
- Real multiprocessing with configurable process count, evaluations/sec on dashboard, headless CLI and benchmark.
- Physical plausibility gate still configurable for downward force over 3×3 / 5×5 / 7×7 *contact-disk* grids.
- Existing electrical screening, strain, bending, shear, torsion, off-center load, interactive 3D candidate selection, and JSON/CSV/STL export retained.

## Interpretation and limitations (critical)

**THIS IS NOT NONLINEAR FINITE ELEMENT ANALYSIS.** The optimizer evaluates an equivalent 6-DOF beam assembly with curved-rod arc-length approximations and synthetic, assumed capacitive/Hall readouts. It does not simulate nonlinear contact, viscoelasticity, actual stresses, fatigue, electrical parasitics, dielectric field distributions, motor EMI, or material manufacturing defects. Pad-offset and support assumptions are simplified. An exported STL is a conceptual overlapping set of primitives, **not** a watertight print-ready CAD assembly. Gene labels `auxetic`, `kirigami`, `origami` and `lattice` identify candidate inspirations and **do not establish** an effective negative Poisson ratio, folding mechanism, or topological class without verification.

Optimization fitness **0–100 is a weighted heuristic, not predictive accuracy**. Gate flags use assumed RMS noise and mechanical limits, not certified safety tests. Structural variation is deliberately bounded by basal anchor and pad constraints; randomly generated candidates have only plausible *connectivity*, not established mechanical viability. For physical design, validate candidates in FEBio/CalculiX/Abaqus with hyperelastic materials, nonlinear contact, mesh convergence, local electrode deformation and real calibration data.

## Relevant research and engineering rationale

- [Computational design of mechanical metamaterials (Nature Computational Science, 2024)](https://www.nature.com/articles/s43588-024-00672-x) — topology and AI inverse design; inspires exploration and screening pipeline.
- [Inverse design of highly deformable mechanical metamaterials (Advanced Science, 2025)](https://advanced.onlinelibrary.wiley.com/doi/full/10.1002/advs.202415935) — semi-random structural optimization and manufacturing-aware smoothing.
- [A Topology Optimization Framework for the Inverse Design of Nonlinear Mechanical Metamaterials (2026)](https://advanced.onlinelibrary.wiley.com/doi/full/10.1002/adem.202503183) — response-curve-driven design; motivates future nonlinear solver.
- [Designing recoverable architected metamaterials using Euler-derived parametric cellular topologies (2026)](https://www.sciencedirect.com/science/article/pii/S0020740326004856) — combinatorial topology exploration with mechanics.
- [Gibson–Ashby models and applicability limits review (2026)](https://www.mdpi.com/1996-1944/19/13/2711) — mechanical stiffness/relative density heuristics, not fabrication validation.

## Engineering next stage

Implement **multi-fidelity evolutionary optimization**: surrogate/beam screening → meshing and nonlinear hyperelastic FEM for elite/novel candidates → experimental compression/shear/strain testing → refit predictive model including manufacturing uncertainty. This is not yet part of the v0.8 application.

Run tests: `python -m unittest discover -s tests -v`.


## v0.9 — piezoelectricity + improved deformation preview

- **Evolution includes piezoelectric sensitivity**: 9 extra design parameters per genome (film length, width, thickness, position, strain transfer, orientation, feedback capacitance, RC leakage time, d31/d33 preference). They undergo the existing genetic mutation/crossover/cross-family transformation and affect selection fitness. The `dynamic` optimization preset allocates 50% to simulated PVDF dynamic response.
- PVDF mechanical-to-electrical transduction estimates local strain from the 6-DOF surrogate, then stress / charge using assumed PVDF elastic modulus and d31/d33. Piezo has a waveform at 25 Hz and charge-decay curve. The estimated response is *not* experimental sensitivity and is NOT calculated by a coupled electromechanical field solver.
- PVDF charge-amplifier high-pass attenuation is included; static force cannot be inferred reliably from indefinitely held charge. Motion (microvibrations, impacts, slip) is the intended piezo sensing domain.
- The visualizer now interpolates deformations by **nearest polyline arc length** for each flexure instead of using only global Z. The contact pad rotates as a rigid body, base remains anchored. This is a kinematic approximation, not elastic equilibrium or a deformation gradient from nonlinear FEM.
- Three usual optimization presets are reweighted to include piezo; new **dynamic** preset prioritizes dynamic event sensitivity.
- Use `python -m unittest discover -s tests -v` and optional `node tests/test_deformation.js`.

### Colleague review
No separate colleague analysis was supplied in the available conversation/files. `COLLEAGUE_REVIEW_TEMPLATE.md` explains how to contribute it and trace proposed changes to assumptions, code and tests. We do not attribute unsupported claims to a third party.

### Important limitations
- The morphology-to-PVDF strain transfer is a specified *surrogate assumption*, not stress/strain FEM. Tensile/compressive strain, shear and torsion responses cannot be trusted without calibration and nonlinear analysis.
- Piezoelectric static-force capability depends strongly on readout leakage and frequency. Pressure must still be read via capacitive/resistive channels.
- Current graphical 3D mesh uses overlapping conceptual primitives; neither it nor its deformed view is suitable for manufacturing qualification.
- Optimized PVDF d31/d33 mode selection is a wiring/poling design hypothesis; actual geometry and poling direction must match that mode.

### Scientific references
- Measurement Specialties / TE Connectivity, *Piezo Film Sensors Technical Manual*: https://cdn.sparkfun.com/assets/d/a/a/b/b/Piezo_Film_Sensors_Technical_Manual.pdf
- PCB Piezotronics, *Introduction to Piezoelectric Force Sensors*: https://www.pcb.com/resources/technical-information/introduction-to-force-sensors
- *Inverse Design of Highly Deformable Mechanical Metamaterial Based on Partitional Semi-Random Optimization* (2025): https://pmc.ncbi.nlm.nih.gov/articles/PMC12302590/
- *A Topology Optimization Framework for the Inverse Design of Nonlinear Mechanical Metamaterials* (2026): https://advanced.onlinelibrary.wiley.com/doi/full/10.1002/adem.202503183

### Latest implementation detail
The PVDF film visual component is anchored to the first structural flexure, oriented along its tangent and placed by the `piezo_position` gene. The reduced-order strain estimate projects the attachment displacement onto the strut chord and includes a small bending term; the PVDF film stiffness is **not** added back into the global 6-DOF stiffness matrix. This is therefore *one-way transduction*, not fully coupled electromechanical FEM. Multi-core execution uses separate worker processes; actual CPU utilization and wall-clock speed are workload dependent.

Verification performed in this build: 41 Python unit tests, JS deformation checks, static browser-code syntax validation, and a successful 2-worker, 3-second headless evolution with the spatial gate and dynamic objective (96 evaluations in that environment).


## v0.9.1 hotfix — Evolve returns `[object Object]`

- Frontend now renders FastAPI/Pydantic validation error arrays with field names.
- Fixed UI/server population mismatch: populations 192 and 256 are accepted.
- CPU worker validation reports explicit numbers and respects Linux affinity.
- Worker pool is capped by population size, errors include exception type, and full tracebacks appear in server terminal.
- Browser performs a CPU-count preflight before POST /api/start.
- Do not run two servers on port 8765 simultaneously. Restart the server and hard-refresh browser (Ctrl+Shift+R).

Potential platform-specific issues at 32 workers: Windows process spawn, memory pressure, missing dependencies in spawned processes. Start with `--cores 4` and increase to 8, 16, 32 while monitoring CPU/memory.

---

# NeuroSkin Evolution Lab 1.0 — staged evaluation and corrected PVDF visualization

## What changed in v1.0

- **Basic / Advanced switch**: starts in **Basic** for every browser session. Both modes invoke the **same** simulation, optimization, candidate audit, and selection code. Advanced exposes additional search, pressure-grid, and diagnostic controls. Changing view alone does not re-run or modify the model.
- **Top-3 audit every generation**: after fast screening, the three highest quick-fitness candidates receive the **identical full surrogate audit**. Audit includes normal-force contact grids at **0.025, 0.1 and 0.4 N**, all defined 3D load cases, PVDF response at **2, 25, 150 Hz**, geometric warnings, synthetic electrical SNR, local Jacobian/observability, and reconstruction error against an independent synthetic holdout set (**70 training + 30 test**).
- **Incumbent protection**: the previous audited best is retained unless a fully audited finalist outranks it (feasible designs first, audit score second). The previous best is not discarded simply because another design scores higher in the fast screening. All comparisons use the same audit settings within a run.
- **Exportable decision trail**: `champion_full_audit.json`, `audit_history.csv`, `stage_decisions.json`, `champion_CONCEPT_NOT_PRINT_READY.stl`, plus per-family visual concepts. Dashboard includes Top-3 cards with click-to-inspect, incumbent and last promotion decision, and a complete audit JSON download.
- **PVDF geometry fixed**: the old **flat, randomly angled gray rectangle** was a visual artifact of aligning a box with a single strut tangent. PVDF is now a **thin, gold, conformal ribbon** running along a curved supporting member, with deterministic, constrained local orientation. Its width is bounded by its supporting strut so it does not masquerade as a huge unsupported sheet. Use **PVDF layer** checkbox in the 3D header to show/hide it. Individual film geometry is a closed 3D ribbon, although the entire assembled model still has overlapping components.
- **Export completion race fixed**: status is `finalizing` during file export; `completed` is only emitted after outputs have been saved. This also fixes tempfile-related regressions in automation.
- **Regressions**: 49 Python tests, including geometry and full-pipeline tests.

## Example

```bash
python -m pip install -r requirements.txt
python server.py --cores 8 --open --port 8765
# From a second terminal, deterministic headless run:
python evolve_cli.py --cores 8 --seconds 120 --population 96 --mode all \
  --objective balanced --gate --grid 3 --audit-grid 5 --out runs_120s
python -m unittest discover -s tests -q
```

Full audits are **compute intensive**. A timed run can exceed the selected duration by the remainder of its in-flight generation and export operations. With 32 process workers, a population of 96 or 128 is usually a better starting point than 24, but CPU saturation is workload and hardware dependent. More processes do not guarantee a faster run.

### Interpretation of a 'full' audit

**Full refers to exhaustive coverage of the implemented *surrogate* tests, not high-fidelity verification.** No nonlinear FEM, dielectric field solver, fracture, durability, creep, contact friction, or physical calibration is performed. Contact-pad displacement is reduced to six degrees of freedom, electrical signals depend on assumed electrode/gap and noise parameters, and rank tests are local numerical measurements. A candidate can be called *feasible under screening assumptions*, **never 'physically validated' or 'production ready'**.

### Relevant research / patent checks

These sources motivate parameters and warn against treating structural design as automatically patentable:

- Nature Materials (2026), [Multiscale-structured miniaturized 3D force sensors](https://www.nature.com/articles/s41563-026-02508-7) — multimaterial geometric separation of normal/tangential force; motivates off-center contact, sensor cross-coupling, and minimum detectable force.
- Advanced Materials Technologies (2026), [Mechanical Decoupling of a Multiaxial Force Sensor via Multiple Sensing Mechanisms](https://advanced.onlinelibrary.wiley.com/doi/10.1002/admt.71078) — architectural decoupling; motivates separate observability/reconstruction audits.
- Chemical Engineering Journal (2026), [Geometry-mediated decoupling of multidimensional forces in flexible anisotropic tactile sensors](https://www.sciencedirect.com/science/article/abs/pii/S1385894726085177) — geometry and bending immunity; motivates substrate-strain nuisance tests.
- Patent application [WO2022056223A1](https://patents.google.com/patent/WO2022056223A1/en) — stretchable kirigami interconnects and multimodal electronic skins are prior art, not automatically novel.

These references do not constitute novelty or freedom-to-operate opinions. The code should not be used to justify patent claims or physical device specifications without independent verification.

---

# NeuroSkin Evolution Lab 1.2 — saved experiments and generation replay

## How to inspect the results after running and restarting the application

1. Run an evolution normally, wait until **completed**. The application writes
   `runs/<run_id>/results.json`, CSV history, champion STL and a `stages/`
   directory containing one atomic JSON for **each completed generation**.
2. Restart the application (`python server.py --cores 8 --open --port 8765`).
3. At the top of the GUI open **Saved experiments** → **Refresh** → select a run
   → **Open**. Its final audited champion, gallery, final Top-3, history and
   decisions are restored to the normal viewer. The archive is read-only.
4. Under **Generation** choose any stored generation and **Inspect stage**.
   Click one of the three finalist cards to pin that model in the 3D viewer.
5. In **Advanced**, run electrical load cases and the spatial downward-pressure
   scan against the actual saved genome, or export that specific model as STL.
6. Use **Download selected run ZIP** to export the saved result, audit history,
   conceptual STL and per-generation stage snapshots. **Return to live** to
   resume viewing ongoing evolution or start another experiment.

**Important:** a headless CLI run written to `runs_headless/` is NOT automatically
visible in the GUI, which uses `runs/` next to `server.py`. Run the CLI with
`--out runs` if you want to open its outputs in the GUI.

### Archived experiments and comparison

Advanced mode also provides **Compare this run with**. Scores are compared
only if objective, audit protocol and the recorded *exact source hash* match.
Older runs without a model hash can be opened but are intentionally marked
**not directly comparable**. A better relative surrogate score does not imply
better hardware performance.

### Improvements and bug fixes

- Archive management is path-safe, bounded, read-only, robust to incomplete JSON,
  and provides a persisted run ZIP without executing stored code.
- Every Top-3 stage is atomically written after the identical full surrogate audit.
  Existing `results.json` remains backward compatible with v1.0.
- Run state includes model source-code SHA-256, software release version and
  the surrogate-validation level, improving reproducibility and audit safety.
- Terminal completion is **only published after** the final archive has been
  atomically saved. This eliminates a race in tempfile-based regression tests.
- Three **distinct** genomes are chosen for Top-3 whenever the population
  contains at least three unique geometries. Duplicates do not waste audit slots.
- `archive_store.py` is independent of the evolutionary optimizer for safe
  inspection, and archived load-case evaluation uses the original stored genome.
- Added 1.1 archive/API/security tests and a release regression runner:
  `python verify_release.py` (Node.js is optional for JS static checks).
- Old Basic/Advanced behavior remains unchanged: both call exactly the same
  computation pipeline. GUI only changes visibility and configurable settings.

### Limits

This is **production-oriented research software**, not a formally qualified
industrial product. We have not validated browser rendering on all browsers,
thread/process crash recovery across operating systems, security hardening for
untrusted remote clients, nonlinear FEM convergence or physical piezoelectric
accuracy. Bind the server to localhost (the default); do not expose the
FastAPI service on the public internet without authentication and deployment
hardening. The STL is a conceptual overlapping assembly, not a certified
single solid. See `RESEARCH_AND_VALIDATION.md` for rigorous release and
physical validation criteria and prior art.

### Repeatable verification

```
python -m unittest discover -s tests -q
node tests/test_deformation.js
python verify_release.py --smoke-evolution
```

The final command intentionally executes a real three-second evolution and
saves it under `runs/` so it can be reopened from the GUI.

## NEW — v1.2 genuine mechanical simulation

**See [FEM_README.md](FEM_README.md)**. The GUI and CLI now support 3D continuum linear HEX8 FEM for Top-3 candidate audit (enabled in GUI/CLI), a real nodal-displacement/stress 3D viewer, and an independent VTK/NPZ export. The quick screening and some electrical responses remain surrogates. Voxel mesh-convergence is a known limitation and cannot be assumed to hold.

## v1.3 — high-resolution mechanical FEM and smooth structural members

See [FINE_MESH_RELEASE.md](FINE_MESH_RELEASE.md). Version 1.3 defaults to a real 3D space-frame **beam FEM** at 0.25 mm pitch (5× finer axial segmentation than v1.2's 1.25 mm), offers .3125 mm (4×) and .15625 mm (8×), and allows explicit volumetric HEX8 selection. The contact-patch fallback is retained, and smooth variable-radius members replace visibly joined cylinders. The fine beam FEM is **not** 8× volumetric HEX8. Full 4× solid HEX8 was verified for one representative crown; full 8× solid was meshed but not solved to completion in the available time.


## v1.5 hardware adaptation
See [WORKSTATION_HP_Z840.md](WORKSTATION_HP_Z840.md) and [RELEASE_NOTES_v15.md](RELEASE_NOTES_v15.md). `python hardware_profile.py --json` profiles this machine; `--cores auto` on server and CLI selects a conservative physical-core recommendation; `hardware_benchmark.py` measures CPU and optional Pascal-compatible CUDA12 solver on identical FEM meshes. Large 4x/8x meshes stay CPU matrix-free.

## v1.5.1 Windows Python 3.14 / Pascal CuPy hotfix

The optional CUDA 12 package in v1.5 mistakenly pinned CuPy 13, which does
not provide Windows Python 3.14 wheels. In v1.5.1, use:

```powershell
python -m pip install -r requirements.txt
python gpu_selftest.py
python hardware_benchmark.py --family quadrant --pitch 1.25 --out gpu_vs_cpu.json
```

CuPy 14 CG requires `rtol`/`atol` rather than `tol`, fixed in the application.
Your Quadro P1000 is Pascal compute capability 6.1 and requires CUDA 12.x code.
`nvidia-smi` reporting CUDA 13.0 refers to driver compatibility, not an installed
CUDA 13 Toolkit requirement. Keep CPU as the default solver until you benchmark.