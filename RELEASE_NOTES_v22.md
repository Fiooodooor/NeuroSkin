# NeuroSkin 2.2 — Standardized Validation Engine (first production-quality module)

Based on v2.1.1 hotfix (2026-11-28). The included executable application remains an experimental engineering tool, **not an experimentally certified tactile sensor digital twin**.

## Added
- `validation_protocol_v30.json` validated through `validation_contract.py` (strict schema, SHA-256).
- `sensor_metrics.py` contact-position-disjoint train/validation/test evaluation for Fx/Fy/Fz and X/Y, assumed-noise Jacobian and Pareto selection.
- `evaluation_v30.py` deterministic synthetic force and location benchmark, 8-trial (configurable) uncertainty screen, failed-evaluation reports.
- `audit_combine.py` single standard FEM/recovery/laminate scoring pipeline shared by Top-3 and Evaluate All.
- `electronics_budget.py` explicit assumption-only readout latency, power/energy, bandwidth and channel count (including film count).
- `measured_import.py` local-only CSV importer for later hardware measurements; zero automatic T3 certification.
- `validation_cli.py`, `measurement_template.csv`, new API endpoints and GUI summary panels.
- Additional validation data in stage snapshots, the promotion decision and archive comparison.

## User actions

```powershell
python -m pip install -r requirements.txt
python server.py --cores auto --open --port 8765
```

In the GUI: **Evolve** -> Top-3 validation appears under the 3D model; **Evaluate All** -> dedicated Validation T0 report. The API also supports `/api/validation/protocol` and `/api/validation/status`.

Standalone validation:

```powershell
python validation_cli.py --family quadrant --genome selected_genome.json --out validation_report.json
python measured_import.py measurements.csv --out measurements_validation.json
```

## Validity / security
- **T0 only**: linear surrogate + synthetically assumed noise, not validated force accuracy.
- **T1 requires mesh-convergence evidence**, T2 verified nonlinear contact and held-out verification, T3 measured independent calibration and uncertainty.
- No automatic pass for missing solver test, no implicit promotion across fidelity/protocol hashes.
- Temperature, shape of actual indenter, fatigue and actual hysteresis remain *unsupported*, not fabricated.
- It is intentional for most random seeds to **fail**. A low score or no passing winner is valuable screening information.
- Run results from v2.1.1 or earlier can be opened but are **not comparable** to v2.2 standardized results without re-evaluation.

## Remaining scientific / engineering work

See `IMPLEMENTATION_PLAN.md`. Nonlinear continuum contact, geometry-conforming tetra meshing, measured electronics, and hardware calibration are **not implemented** in this release.
