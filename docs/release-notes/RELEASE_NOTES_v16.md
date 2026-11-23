# NeuroSkin Evolution Lab 1.6 — 20 scientific and conceptual seed designs

## Key functions

- 20 documented initial candidates: 10 original conceptual architectures + 10 literature-inspired geometry motifs. One source is provided for each literature-inspired concept. **Not a faithful CAD reproduction or a novelty/patent clearance assessment.**
- A **10-criterion, 0–10-per-criterion, maximum-100 expert-prior rubric**, plus a minimum-two-per-family diversity constraint, determines the 10 initial shortlist concepts. Expert priors **do not count as physical FEM results**.
- The 10 shortlisted genotypes are inserted into the *actual initial evolutionary population* (filtered by the chosen family). They are evaluated by the normal quick screening, then Top-3/full audit/FEM promotion pipeline. Random mutations and other candidates remain part of the population.
- `seed_library.py` stores the 20 designs and scoring rules. `archetype_geometry.py` implements differentiable, endpoint-constrained 3D centerline modifications and selected network cross-members, used by both `detail_mesh()` and the mechanical solver.
- `seed_models_v16/` includes all 20 conceptual overlapping-component STL assemblies, genome JSON, coarse FEM test summaries and a 20×10 score CSV. All 20 were successfully solved with a coarse HEX8 model in the development environment. **This is not proof of mesh convergence, fatigue life, manufacturability, piezoelectric coupling, negative Poisson's ratio, or electronic accuracy**.
- PVDF configurations: 1/2/3/4 films for a four-leg Quadrant, and 1/2/3/4/6/8 films for designs with enough structural members. Wiring: independent, charge sum, X differential, Y differential, alternating polarity. The optional count/wiring preview overrides never rewrite the archived genotype or its historical fitness.
- `recovery_sim.py` implements an **assumed single-mode standard-linear-solid (SLS) creep-compliance unloading calculation**. It reports a predicted residual vs time after removing force, plus a strain-risk gate. It modifies Top-3 promotion and the unified audit score. **This is NOT a nonlinear viscoelastic solid FEM, real hysteresis/permanent-set prediction or a fatigue-life test.** Both modulus ratio and relaxation time are assumed constants until real material measurements are available.
- GUI now opens in Basic with two primary actions: `▶ Evolve` and `◆ Evaluate All`. The Advanced panels remain available for inspecting results, but their previous separate run buttons have been hidden to reduce clutter. Pause/Stop remain run-control buttons.
- New runs use randomized seeds. The server generates one if omitted; the GUI also generates a fresh seed on each Evolve click; the CLI defaults to randomized and accepts `--seed N` for explicit replay. The used seed is stored in experiment archives.
- A hardware-aware CUDA 12 / Python 3.14 backend remains optional, with Xeon CPU FEM as the default. The user's Quadro P1000 passed the CuPy 14.2.0 sparse-CG smoke test; this does not demonstrate a performance win for real FEM.

## Running

```powershell
python -m pip install -r requirements.txt
python server.py --cores auto --open --port 8765
```

Open `http://127.0.0.1:8765`. Expand the **20 starting geometries** panel, Preview a candidate, click **Evaluate All**. The audit may take significant time when HEX8 is enabled at 0.3125 or 0.15625 mm. For fast exploration use `3D beam` or `HEX8 pitch=1.25` and revalidate shortlisted variants with fine HEX8. The GUI and generated STL are conceptual, not certified printable CAD. 

```powershell
python evolve_cli.py --cores 32 --seconds 120 --population 128 --mode all --no-fem --out runs_headless
# Or use --fem --fem-pitch 0.3125 for significantly more expensive multi-fidelity validation.
python export_seed_catalog.py --out seed_models_v16
python -m pytest -q tests/test_library_v16.py tests/test_pvdf_array_v14.py
```

Optional GPU:

```powershell
python -m pip install -r requirements.txt
python gpu_selftest.py
python hardware_benchmark.py --family quadrant --pitch 1.25
```

## Ten scored criteria (0–10 each, expert priors)

1. Normal: sensitivity to normal contact force
2. Shear: separation of lateral/shear load
3. Location: identifiability of contact position
4. Dynamic: potential piezoelectric transient signal
5. Recovery: expected reversible recovery (not simulated material data)
6. Stretch: compatibility with substrate deformation
7. Fabrication: plausible low-cost manufacture
8. Fatigue: geometry-related fatigue-risk prior
9. Electronics: energy/readout simplicity
10. Numerical: parameterization, solver stability and geometry robustness

Final score range: 0–100. The 10 starting motifs are selected by expert score **with a minimum of two concepts per major mechanical family** to preserve exploration diversity (the result is not strictly the raw ten largest scores). Every field is disclosed in `seed_models_v16/scores_20x10.csv`. These are **judgment-based proposal priorities**, not calibrated measurements or FEM-derived scores. Top-3 evolutionary promotion uses the separate actual evaluation pipeline; it does not replace physical testing.

## Recovery physics

For `E∞/E0=0.55`, `τ=0.8 s`, force held for `1 s`, the assumed creep compliance is

`J(t) = 1/E∞ − (1/E∞ − 1/E0) exp(−t/τ)`.

When force is removed after `t_hold`, the recoverable deflection is proportional to `J(t_hold + Δt) − J(Δt)`. The test screens strain against a conservative **assumed** 8% strain limit. Every linear solid returns to zero displacement after unloading by construction; that fact alone cannot support a materials claim about permanent set or fatigue. Future work needs experimental loading/unloading loops and visco-hyperelastic FEM.

## Verification and legacy interoperability

- 20 parametric designs exported as STL and JSON; all 20 pass the coarse HEX8 0.1 N numerical smoke test.
- The focused compatibility suite checks the historical v1.4 single-film archive behavior, the expanded valid PVDF layout and the unified API.
- Save original archives. Changing code/geometry changes the provenance hash and earlier fitness results must be treated as **noncomparable** without reevaluation.
- Plotly uses local bundled library; no cloud services required. CuPy is optional; CUDA support is limited by 4 GB VRAM.

## Boundaries

This is a research application, not a safety-certified robotic tactile sensor design tool. It does not model coupled PVDF/adhesive mechanical stiffness, fully coupled electrical fields, nonlinear hyperelasticity, dynamic contact/friction or real fatigue. Resistive/capacitive readouts remain synthetic. Full physical validation requires sample fabrication, measured stress–strain/creep parameters, electronics characterization and mesh-convergence analysis.
