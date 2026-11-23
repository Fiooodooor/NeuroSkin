# NeuroSkin Evolution Lab 1.9.1 — feasibility-guided sensing refinement

## Objectives and bug fixes

1. Fix contradictory reporting of “0% minimum coverage” when a 0.1 N scan passes 10/13 points: 25 mN low-force sensitivity is now a **separate diagnostic**, while operational coverage is reported individually at **0.1 and 0.4 N**.
2. Fix score-band mixing: a failed audit **always scores below 50/100** after all FEM, viscoelastic and shell terms, while a passing audit scores at least 50. Failed raw utilities are mapped monotonically into the lower band instead of flattening every failed design at 49.99. This is a *ranking policy*, not measured detection probability.
3. Fix a second feasibility inconsistency: novelty bonuses and partially audited FEM scores no longer allow known failed candidates to outrank feasible individuals in parent selection.
4. Give zero-coverage designs a **continuous progress metric** based on the assumed SNR, downward motion, tilt, lateral motion, reaction signs and a dielectric bottom-out check; the old flat zero score prevented useful gradient exploration.
5. Add bounded capacitive sensor genes (actual design assumptions, **not mutable noise**): electrode area, dielectric gap, relative permittivity, and mounting compliance. They affect both the surrogate electrical model and the FEM-derived ideal capacitor proxy.
6. Prefer four angularly balanced PVDF films in newly generated Quadrant models, while retaining two- and three-film experimentation and fully backward-compatible one-film archives.
7. Add a targeted guided mutation operator; it proposes plausible geometry/readout adjustments based on the current failure reasons and must still pass the same evaluations as other offspring.
8. Cache computationally expensive PVDF angular-subset selection by real support positions to accelerate repeated load-case studies.
9. Correct a misleading old unit test: arbitrary asymmetric random structures may have central tensile reactions; the centre-reaction test now uses a physically symmetric reference.
10. Keep the standardized 0.1 N laminate-shell result **independent of manual force settings**. A separate shell result drives the inspection graphic, so user interaction cannot alter promotion scores.
11. Keep the single complete requirements.txt, now including matplotlib for shipped preview generators, and retain v1.9 visual panels/Top-3/FEM/Evaluate All.

## Important engineering limitations

- The v1.9.1 pressure SNR score is computed using a **synthetic** capacitive transfer model and **assumed fixed 0.001 pF RMS noise**. Numerical SNR ≥3 does not certify hardware performance.
- The elastic mounting-compliance range (.10–.48 mm/N per foot) is a **hypothesis**. Large values should be verified with actual porous elastomer dielectric material, rate-dependence, travel limits, and electrode bonding. The new bottom-out flag guards a particularly obvious violation, not every failure mode.
- FEM is linear HEX8 with voxelization error. PVDF/adhesive reinforcement is embedded and the final ribbon-shell is a **post-process**, not a fully coupled shell/solid/multiphysics solve. Both require mesh convergence and material calibration.
- The optimizer can favor a stronger assumed signal because the capacitive response law changes with gap, area and compliance. A prototype and calibrated noise measurement remain necessary before ranking real devices.
- v1.9.1 fitness **is not numerically comparable** to v1.9/v1.8 archive scores. Every new run records source provenance and model version. Rerun Evaluate All on older models.

## Research context

The source of architectural inspiration is separated mechanical normal/shear paths and symmetric electrode layouts, as demonstrated in 2026 tactile-sensing research. These papers do NOT validate the specific NeuroSkin geometry or its scores:
- Geometry-mediated decoupling of multidimensional forces in flexible anisotropic tactile sensors: https://www.sciencedirect.com/science/article/pii/S1385894726085177
- A robust capacitive 3D tactile sensor with micro-frustum array dielectric and interfacial bonding optimization: https://www.sciencedirect.com/science/article/pii/S0924424726010046

## Run on Windows HP Z840

```powershell
python -m pip install -r requirements.txt
python -m pip check
python server.py --cores auto --open --port 8765
```

Suggested verification:

```powershell
python -m pytest -q tests/test_refinement_v191.py tests/test_laminate_shell_v19.py tests/test_laminate_v18.py
python refinement_benchmark.py --samples 48 --seed 2026 --out screening_v191.json
python render_refinement_preview.py
```

Use `--cores 16`/`20`/`32` benchmarks to find the most efficient affinity setup on the dual-Xeon hardware. CUDA on Quadro P1000 stays optional; the smallest FEM runs were far faster on CPU in the user's measured benchmark.
