# Corridor — JDA survey audit, Jaipur

An independent re-derivation of a classified turning movement survey commissioned by
the Jaipur Development Authority: six junctions on **New Sanganer Road**, counted over
24 hours and issued as twelve Excel workbooks.

The pipeline parses every cell, recomputes every stored total from its components, and
reports what disagrees. It then reads the accompanying CAD survey drawing to establish
what is physically on the corridor.

## What it found

| | |
|---|---|
| **The second survey day was not observed.** 396 of 555 movement-class series reproduce day one to the exact vehicle while their 15-minute bins differ. Of those that move, 154 rise and 5 fall — p ≈ 2×10⁻³⁹. | one usable day, not two |
| **The scheme's key movement was never counted.** JDA is converting this road to signal-free operation with seven U-turn bays. The survey has no U-turn column. The drawing shows 27 median gaps wide enough to turn through. | unmeasured, not zero |
| **PCU is understated.** Static factors against a composition-dependent standard: two-wheelers are 49% of the stream but carried at IRC:106's sub-5% value. | +14.9% floor |
| **The flow diagram reports the wrong classes.** A 20-class header sits over 10-class data, shifted. The two-wheeler count appears under "Taxi". | 960 `#REF!` cells |
| **223 stored totals disagree with their own components.** | all recorded, none silently corrected |

Design rule throughout: **never trust a stored total.** Everything is recomputed, and
discrepancies go to a register rather than being absorbed.

## Running it

Source data is not in this repo — the workbooks and CAD are the client's. Place them
under `00_source/` and:

```bash
uv sync
uv run pytest                    # 26 tests
uv run python src/inspect_tmc.py # raw workbook structure
uv run python src/audit.py       # -> out/audit_report.md
uv run python src/atlas.py       # -> out/corridor_constraint_atlas.pdf
uv run python src/medians.py     # U-turn feasibility
uv run python src/export.py      # -> out/data/corridor.json
npm run dev --prefix web         # dashboard on :3210
```

Every module runs standalone and prints its own verification metric.

## Layout

- `src/` — pipeline. `tmc_parse` and `audit` are the core; `atlas`, `medians` and
  `dxf_inventory` read the CAD survey.
- `web/` — Next.js dashboard, reading the same `corridor.json` as the static report.
- `docs/jaipur_corridor_study.md` — the methodology, with inline `ERRATUM` blocks
  correcting eight defects in its own worked code.

## Caveats, stated

Three junction positions are fixed by an exact name match against JDA's scheme; three
are placed by position in that sequence and labelled inferred. The severity weighting
in the constraint atlas is a judgement, not a measurement. Half the PCU correction is
unresolvable because the survey's class scheme lumps 48% of the stream into one column.
