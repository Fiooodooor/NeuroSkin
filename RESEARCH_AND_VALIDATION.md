# NeuroSkin: research-driven validation and release gates (2026-11-23)

This is an engineering research tool, **not** a physically validated digital twin.
Its numerical score is not calibrated sensor accuracy. It cannot claim clinical, industrial,
or safety-critical suitability; the STL files are overlapping visualization components.

## Evaluations that can be trusted today

1. Deterministic generation from an explicitly recorded seed and source-code hash.
2. Geometric and reduced-order mechanical *screening* across candidate families.
3. Assumed capacitive, Hall and PVDF transduction response *from the surrogate*.
4. For top-three finalists, identical pressure scans at three normal loads, lateral loads,
   torsion, strain nuisance, dynamic piezo tests, and held-out *synthetic* inverse-fitting.
5. Incumbent promotion only after the full surrogate audit, with feasibility-first rule.
6. Persistent, atomic per-generation archives, a replayable Top-3 audit and archived STL.

## Research converted into explicit test requirements

| Research evidence | What it motivates | Caveat |
|---|---|---|
| Customizing Tactile Sensors via Machine Learning-Driven Inverse Design (Advanced Science, Jan 2026) | Target-dependent objective profiles and parameter-space exploration | Inverse design does not itself validate the surrogate |
| Multiscale-structured miniaturized 3D force sensors (Nature Materials, 2026) | Whitened multiaxial identifiability and off-center pressure/shear confusion | Nanocomposite behavior is not present in our elasticity model |
| Geometry-mediated decoupling of multidimensional forces (Chemical Engineering Journal, Nov 2026) | Orthogonal response tests and substrate-deformation nuisance tests | Current rank test assumes modelled signals and noise |
| Kirigami-Cut Pattern Designs for the Enhancement of Sensing Performance (2026) | Out-of-plane strain amplification and PVDF placement as design variables | Strong voltage may imply destructive local strain |
| Kirigami-inspired, three-dimensional piezoelectric pressure sensors (npj Flexible Electronics, 2024) | Test both planar and folded PVDF, with dynamic and fatigue assays | Cannot infer dynamic sensitivity from the open-circuit peak alone |
| Tactile perception through fluid–solid interaction (Nature Communications, 2026) | Explore fluidic encoding as a future additional receptor family | The present code has no CFD/fluidic solver |

## Patent landscape: technical warnings, not legal conclusions

- US12196626B2 and US20210396605A1: normal/shear force differentiation using 3D tactile structures.
- US20210278300A1: capacitive/tactile sensing with multi-axis force response.
- US12152910B2: kirigami-based strain-sensor structures and applications.
- US20130119689A1: a piezoelectric shear sensor with a flexible supporting membrane.

These are examples of closely related prior art; status/claims require independent
professional examination in relevant jurisdictions. Combining known techniques is
not automatically patentable.

## Physical validation ladder

**Level 0: Software contract** — unit, API, archive, UI and regression checks; Python
assertions must not substitute for tests. Running basic/advanced view must produce
exactly the same backend configuration for identical settings.

**Level 1: surrogate screening** — all mechanics/electrical results have model version,
source hash, parameter assumptions, seed, objectives and 2D spatial contact tests.
A rejected design can have a high raw electrical signal yet zero reliable force identifiability.

**Level 2: mesh convergence and nonlinear mechanics** — actual meshed solid, large-
strain hyperelasticity (e.g. Ogden/Yeoh fitted from printed samples), unilateral
contact, self-contact, load location and cycle history. Require monotonic convergence
under mesh refinement; avoid fixed accuracy percentages unless measured.

**Level 3: coupled electromechanics** — deformed electrode geometry and parasitic
capacitances, mechanical loading of attached PVDF, electrode adhesion, RC front-end,
shielding, ADC/CDC throughput; compare predictions with measured signals.

**Level 4: build/prototype qualification** — calibrated XYZ force/torque reference,
normal and oblique loading including off-centre force and contact moment, multi-touch,
ambient temperature/humidity, 10k/100k cycles, drift and fatigue, delamination,
abrasion, power draw and BOM. Independent train/test split by physical specimen.

**Level 5: robotic utility** — closed-loop slip prevention, contact localization,
object compliance estimation, reproducible tasks and explicit performance vs baseline.

## Engineering release gate (non-regression)

- All previous-version tests **and** new archive/UI/API tests pass.
- The browser script passes JavaScript syntax checks, the API schemas are unchanged
  except additive backward-compatible properties.
- At least one end-to-end evolution finishes, persists results and reopens its Top-3
  and champion in the archive UI/API; status `completed` is not published before
  the terminal JSON is atomically committed.
- The program doesn't claim superiority if proxy scoring improves but feasibility,
  calibration, rank or held-out reconstruction worsens.
- Preserve prior champion in a run until a new finalist is fully audited. Across runs,
  different objective/assumptions/source hashes mean scores are **not directly comparable**.

This definition offers monotonic **release quality** under tested contracts; it is
not a proof that an optimizer's mathematical quality improves monotonically.

## Source links

- https://doi.org/10.1002/advs.202524250
- https://www.nature.com/articles/s41563-026-02508-7
- https://www.sciencedirect.com/science/article/abs/pii/S1385894726085177
- https://pmc.ncbi.nlm.nih.gov/articles/PMC13367109/
- https://www.nature.com/articles/s41528-024-00310-6
- https://www.nature.com/articles/s41467-026-72497-3
- https://patents.google.com/patent/US12196626B2/en
- https://patents.google.com/patent/US20210278300A1/en
- https://patents.google.com/patent/US12152910B2/en
- https://patents.google.com/patent/US20130119689A1/en
