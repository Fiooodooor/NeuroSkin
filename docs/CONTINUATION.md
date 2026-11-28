# Continuing saved evolution

Open **Runs**, select an experiment, and click **Open**. Select a saved generation or leave **Final run result** selected. Click **Load selected snapshot for evolution**. The application returns to Overview with a continuation panel and the saved controls loaded.

Edit the controls and click **Continue with these controls**. This creates a separate run; the source run and its results remain unchanged. Cancel continuation discards the preparation without starting a run. A normal Evolve starts a fresh experiment.

The continuation panel checks edited controls automatically. It shows how many saved geometries fit the chosen search scope, which controls differ from the loaded configuration, whether the saved random stream will be restored, and which inherited geometry receives the first full audit. Older archives may load documented defaults; the comparison therefore uses **Loaded** and **Selected** columns. The source champion's birth generation is displayed separately from the chosen snapshot's generation.

Continue is enabled only after the preview for the current controls succeeds. Incompatible scopes or invalid parameters leave the source untouched and do not start a run. Delayed responses from older control selections are ignored. This is a configuration/compatibility preview, not a FEM simulation or prediction of the resulting fitness.

## What carries forward

- The chosen snapshot's generation number. A snapshot at generation 40 continues with generation 41, even if its best candidate was discovered in generation 12.
- Compatible saved geometries, prioritising the selected champion when it fits the scope, followed by population-checkpoint geometries or saved finalists/family champions/gallery entries. Duplicate source genomes are removed. Smaller populations retain the first eligible seeds; remaining slots use local mutations and fresh designs.
- Saved controls: search scope, objective, population, exploration, precision, seed, CPU budget, FEM settings and validation grids. The duration is an additional search budget, not the parent's cumulative elapsed time.
- Population checkpoints also preserve the random-generator state. This is restored when the requested seed matches the saved seed; changing the seed starts a new random stream.

Every inherited genome is scored under the new controls. In the first branch generation, the first compatible inherited geometry is guaranteed one full-audit slot, even when its fast proxy score is poor. This is the saved champion when it fits the selected scope. Other slots follow the existing nomination policy; the total remains at most three distinct finalists. Later generations use ordinary nomination and promotion. Receiving an audit slot does not guarantee feasibility, promotion or a retained historical score.

Old fitness, audited champions, novelty/QD archives and audit caches are not reused as current evidence. Changing the objective or FEM settings cannot silently retain a historical high score as the new incumbent.

An incompatible search scope excludes incompatible source genomes. If no saved geometry fits, starting is rejected before replacing the live state. The original genomes are not silently converted into another architecture.

## Checkpoints and older archives

At a completed generation boundary, the engine atomically publishes:

1. `stages/stage_NNNNNN.json`: audited finalists, champion, decision, controls and lineage.
2. `stages/population_NNNNNN.json`: the next population, PRNG state, controls, provenance and checksum.
3. `results.json`: the discoverable snapshot of the latest completed boundary.

If a process fails later, the last published boundary can be reopened after restart. A partially evaluated generation is not resumed. A stage that lacks its population checkpoint falls back to its saved elite geometries.

Older archives did not record the full population or all controls. The preparation panel explicitly reports missing controls and loads defaults for them. CPU workers may be reduced to the available hardware. Review those controls before starting.

This is **branch continuation with fresh evaluation**, not exact process replay. Population and PRNG checkpoints do not restore the old novelty archive, QD archive, audit cache or timing history. Old candidate birth labels remain unchanged; new evolved candidates and stage files consistently use one-based generation numbering.

## Traceability and User bests

Each child run stores `lineage`: parent run, selected generation, source digest/provenance/score, seed counts, exclusions, PRNG restoration and changed controls. The workspace identifies the parent. Parent and child histories remain separate because scores may use different assumptions.

The existing User bests rule applies independently to the child run: only its final audited champion can enroll, strictly above 90. Intermediate checkpoints do not enroll. Qualifying entries preserve the child's lineage and controls.

## API

- `GET /api/archives/{run_id}/continuation?generation=G`: prepare a selected stage; omit `generation` for the final/latest published snapshot. Returns controls, source kind, warnings and `source_digest`.
- `POST /api/archives/{run_id}/continuation/preview`: validate the selected controls and report inheritance counts, excluded geometries, first audit seed, PRNG restoration and settings changes. Accepts the same body fields as continuation; it does not create an evolution instance or acquire a heavy-compute slot.
- `POST /api/archives/{run_id}/continue`: start a child. Body accepts `generation`, `source_digest` and ordinary Start controls. Omitted controls inherit saved values. A mismatched digest returns 409, preventing a prepared source from silently changing before execution.
- Invalid controls, unsupported source data or an incompatible scope return 422. Missing source files return 404. An active evolution/analysis retains the existing compute reservation and rejects a conflicting start with 409.

Malformed JSON collections/settings are rejected with descriptive 422 responses. Optional legacy null collections are treated as absent. Invalid PRNG state is rejected before a branch replaces the live state; no pickled executable state is loaded.

Related: [architecture](ARCHITECTURE.md), [sensing model](SENSING_MODEL.md), [verification](VERIFICATION.md).
