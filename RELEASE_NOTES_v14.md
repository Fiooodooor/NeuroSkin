# NeuroSkin 1.4 — balanced PVDF arrays (23 November 2026)

## Root cause

NeuroSkin 1.3 rendered and evaluated the PVDF ribbon on the first structural member returned by `structural_struts(...)`. This hard-coded selection was responsible for the always-one-sided orange film, regardless of the rest of the geometry.

More importantly, the previous PVDF electrical surrogate sampled strain from the same first member only. The continuum HEX8 and beam FEM currently DO NOT include PVDF film, glue, electrodes, or leads as mechanically distinct material layers, so there was *no* structural penalty in FEM even if the displayed film geometry was physically asymmetric.

## Changes

- **New genotypes default to four angularly balanced films (80% of initial candidates), or an opposed pair (20%).** All films follow actual primary strut centerlines. For Crown and Chiral, 2- or 4-fold primary strut arrangements are favored in the genotype for exact placement balance at the base.
- Added genes `piezo_count` (categorical 2/4), `piezo_azimuth_rad` and `piezo_wiring` (0 independent, 1 signed sum, 2 differential-X). They are included in crossover, mutation, transmutation and optimization.
- `pvdf_array.py`: deterministic member selection and a geometric imbalance metric. **This balance only checks PVDF placement centroid, not symmetry of the whole mechanism or bonded composite stiffness.**
- `piezoelectric.py`: independent per-film charge/voltage/strain readouts, wiring-dependent signal aggregation, per-channel strain limit and a simple readout-cost penalty. The displayed `peak_V` refers to a single strongest channel when independently wired, never a fictitious RSS of voltages. The `dynamic_snr_proxy` for independent channels uses an RSS of assumed uncorrelated-noise channel SNRs; this is NOT a measured SNR.
- In the GUI, **PVDF configuration → As saved / Balanced pair / Balanced quartet** allows an explicit, temporary change to a displayed or archived candidate, including its electrical characterization and STL export. Archive genotypes without `piezo_count` still retain their **original one-film configuration** to avoid silently changing historical results. A clear warning explains that override does NOT update archived fitness.
- Added **Genome JSON** export for reproducing a preview override as a derived genotype. Use `fem_cli.py --genome FILE` to run the mechanical portion of the validation.
- Added tests for distribution, zero-load behavior, legacy stability, API override behavior and wiring.

## Limitations / required research

The 3D FEM **still does not represent PVDF or adhesive stiffness, electrode mass, shear lag, material poling, or electrical field coupling**. A symmetric arrangement of four films prevents the obvious one-sided layout but does **not prove** that an assembled sensor has perfectly balanced forces. Different leg stiffness, bond conditions, trace routing and electrical grounding can still create asymmetries. For mechanical prediction, implement laminated shell/solid bonded-film FEM or an equivalent calibrated beam section *and* rerun all finalists.

The new PVDF signal model is a parameterized linear surrogate, not a validated piezoelectric constitutive solver. It is especially inappropriate for indefinite static force measurement. Full FEM and archive fitness values are not directly comparable between v1.3 and v1.4 until the model is reevaluated.

## Run

```
python -m pip install -r requirements.txt
python server.py --cores 8 --open --port 8765
```

Select a new candidate and leave **PVDF configuration: As saved**, or select a legacy candidate and explicitly preview **Balanced quartet**. Export `Genome JSON` and run:

```
python fem_cli.py --family quadrant --genome new_genome.json --backend hex8 --pitch 0.3125 --force 0.1 --out fem_candidate
```

Do not compare an altered historical genotype's old fitness to a new one; re-evaluate the new design under the same validated protocol.

## Literature relevance

- [Flexible Piezoelectric Tactile Sensor Array for Dynamic Three-Axis Force Measurement, Sensors 2016](https://doi.org/10.3390/s16060819), multi-channel PVDF force readout.
- [Screen-Printed Flexible Piezoelectric Force Sensor Array with Electromagnetic Interference Shielding, 2026](https://doi.org/10.1002/adem.202502361), physical arrangement and differential signal issues.
- [Research on a novel wide-frequency response self-decoupling PVDF piezoelectric film array four-dimensional force/moment sensor (2026)](https://www.sciencedirect.com/science/article/pii/S0263224126021329), multi-element force/moment decoupling precedent.
- [Interface Electronics for PVDF Based Tactile Sensor (2025)](https://ieeexplore.ieee.org/abstract/document/11336158), instrumentation is crucial for actual signal quality.
