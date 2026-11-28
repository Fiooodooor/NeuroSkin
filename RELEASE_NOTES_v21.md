# NeuroSkin Evolution Lab v2.1 — Search Space / Relative Rotation Update

## Problem resolved

The v2.0 GUI exposed only `all`, `crown`, `chiral`, and `quadrant`, even though ten
curated hybrid geometries were available in the generator. A restricted run
could not intentionally select hybrids or a particular two-stage architecture.

## Search modes (live server-supplied catalogue)

- `all`: single-stage structures, curated hybrids, and newly procedural hybrids
- `single:all`: single-stage only
- `hybrid:all`: the 10 curated combinations **plus** procedural hybrids
- `crown`, `chiral`, `quadrant`: one upper family, single + matching curated
- `single:<family>`: explicit single-stage only
- `hybrid:<family>`: matching curated and procedural hybrids
- `hybrid:<hybrid_id>`: locked to one curated two-stage architecture
- `procedural:all` or `procedural:<family>`: combinations of independently selected
  upper/lower stage families and their compatible flexure topologies.

The engine validates the scope after **every** mutation, crossover, transmutation,
immigrant generation and stage-local refinement. The UI populates its Search space
options dynamically from `/api/search_spaces`; CLI consumes the same catalogue.

## Search strategies

- `adaptive` default: global exploration, a bounded MAP-Elites-lite archive,
  engineering-guided mutations, and local trust-region refinement.
- `explore`: favors structural jumps, diversity and random immigrants.
- `precision`: stronger local exploitation of audited feasible finalists, but
  retains global escape operators.
- `--search-precision 0.8` controls the normalized mutation step near elites.
- All new genes are actually used by geometry, structural proxy and (for Top-3)
  the corresponding actual HEX8 model.

## Expanded procedural genotype

For the special `hybrid_id=procedural`:

- `hybrid_upper_family` (equal to `family`),
- `hybrid_lower_family` (crown/chiral/quadrant),
- `hybrid_upper_topology`, `hybrid_lower_topology`,
- `hybrid_opposed_chirality` (boolean),
- `hybrid_phase` (angular offset),
- existing separate scale, split, thickness, PVDF, adhesive and electrode genes.

The rotation search interval is now approximately -180°..180°; stage thickness
multipliers are also extended. The middle plate keeps a connected series path.

## Are the stages supposed to be rotated?

They can be, but they do not have to be. A 45° upper-stage phase shift may
interleave supports and alter directional stiffness. An aligned 0° stage is a
valid baseline and sometimes mechanically better. With ideal C4 symmetry,
90° may be equivalent to 0°, but actual struts, electrodes, adhesive and
boundary constraints can break that equivalence. **A phase rotation does NOT
reverse helix handedness.** For opposed helices, signed twist is the
independent gene and must be verified separately.

`orientation_study.py` tests 0°, 22.5°, 45°, 67.5°, and 90° using the same
force and spatial screening protocol. `--fem-pitch 1.25` optionally runs 3D HEX8
on each orientation. GUI `Evaluate All` includes the fast rotation study for
hybrid candidates. Results are explicitly synthetic screening predictions.

## Workstation usage

```powershell
python -m pip install -r requirements.txt
python server.py --cores auto --open --port 8765
```

Explore all hybrids:

```powershell
python evolve_cli.py --mode hybrid:all --search-strategy adaptive --search-precision 0.85 --population 120 --cores 20 --seconds 300 --fem --fem-pitch 0.3125
```

Study exactly one hybrid:

```powershell
python evolve_cli.py --mode hybrid:h01_serpentine_quadrant --search-strategy precision --search-precision 0.9 --population 120 --cores 20 --seconds 300 --fem --fem-pitch 0.3125
```

Search *novel procedural combinations*:

```powershell
python evolve_cli.py --mode procedural:all --search-strategy explore --population 120 --cores 20 --seconds 300 --fem --fem-pitch 0.3125
```

Compare relative rotations of the same candidate:

```powershell
python orientation_study.py --hybrid-id h01_serpentine_quadrant --out h01_rotation.json
python orientation_study.py --hybrid-id h10_dual_chiral --out h10_rotation.json
python orientation_study.py --genome selected_genome.json --hybrid-id h01_serpentine_quadrant --fem-pitch 0.625 --out detailed_rotation.json
```

The 0.625-mm FEM orientation sweep may require significant CPU time.

## Numerical honesty

- New modes change the **space being searched**, not the fidelity of physical
  evaluation. All candidates still use fast surrogate screening; Top-3 receive
  the chosen full audit and FEM where enabled.
- Geometry remains a voxelized, small-strain linear-elastic solid with approximate
  PVDF bonding and reduced shell post-processing. Nonlinear contact, hyperelasticity,
  electrode electrostatics and fatigue require further validation.
- The intermediate plate is structurally included; generated variants can still
  be invalid under high-resolution meshing or manufacturing constraints.
- Existing saved experiments remain readable, but their scores are not directly
  comparable to newly evolved phenotypes without re-evaluation.
