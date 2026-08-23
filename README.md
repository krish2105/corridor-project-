# Corridor — JDA survey audit, Jaipur

An independent re-derivation of a classified turning movement survey commissioned by the Jaipur Development Authority: 6 junctions on **New Sanganer Road**, counted over 24 hours and issued as twelve Excel workbooks.

The pipeline parses every cell, recomputes every stored total from its components, and reports what disagrees. It then reads the accompanying CAD survey drawing to establish what is physically on the corridor, tests the scheme being built on that data, and prices the delay the corridor is already carrying.

## What it found

| Finding | Evidence |
|---|---|
| The second survey day was **not independently observed** | 396 of 555 movement-class series reproduce day one to the exact vehicle; of those that move, 154 rise and 5 fall. p ≈ 2×10⁻³⁹ |
| The scheme's key movement was **never counted** | JDA is converting this road to signal-free operation with seven U-turn bays. No U-turn column exists anywhere in the survey. The drawing shows 27 median gaps wide enough to turn through |
| PCU **understated by at least 14.9%** | Static factors against a composition-dependent standard; two-wheelers at 49% of the stream carried at IRC:106's sub-5% value |
| The flow diagram **reports the wrong classes** | 20-class header over 10-class data, shifted; two-wheelers appear under "Taxi"; 960 `#REF!` cells |
| **223 stored totals** disagree with their components | 180 understate, 43 overstate; all recorded, none silently corrected |
| **JDA's U-turn bays cannot carry the demand** | A right turn becomes a U-turn under signal-free running, so the bays inherit the recorded right-turn volume. At a composition-weighted critical gap: 11 of 12 approaches unservable, 9 even optimistically. 3,781 veh/hr would force across opposing traffic |
| An elevated through-carriageway **is justified on opening** | Through movements 57–79%; carrying them over the junctions returns all 12 corridor approaches to acceptable operation |
| **…and does not last its own design horizon** | Growing residual turning demand at 6%, the first approach is back over capacity in 2032 and 0 of 12 still hold at 2046. This argues against our own recommendation and is reported anyway |
| **The corridor does not queue, it locks** | 6 of 12 approaches queue past the junction behind them inside the peak hour. A through trip takes 72.1 minutes against 8.0 at free flow — an effective 4.4 km/h |
| **The delay already has a measurable annual cost** | Approaches are over capacity 8.3 hours a day, counted from the survey's own intervals. Valued at an occupancy-weighted value of time that is ₹176–417 crore a year |

Design rule throughout: **never trust a stored total.** Everything is recomputed, and discrepancies go to a register rather than being absorbed.

Every conclusion is re-run across its own assumption grid before publication — 144 combinations for the capacity and scheme conclusions, 27 for the queue conclusion.

## Running it

Source data is not in this repo — the workbooks and CAD are the client's. Place them under `00_source/` and:

```bash
uv sync
uv run pytest                     # 194 tests
uv run python src/inspect_tmc.py   # raw workbook structure, no reshaping
uv run python src/audit.py         # -> out/audit_report.md
uv run python src/atlas.py         # -> out/corridor_constraint_atlas.pdf
uv run python src/medians.py       # U-turn feasibility from the DIVIDER linework
uv run python src/capacity.py      # measured widths, v/c, design life
uv run python src/scheme_test.py   # does the JDA U-turn scheme work?
uv run python src/delay.py         # queue, spillback, corridor journey time
uv run python src/economics.py     # cost of delay, banded
uv run python src/sensitivity.py   # every conclusion across its assumption grid
uv run python src/export.py        # -> out/data/corridor.json
uv run python src/reports.py       # -> D6, D8, D9
uv run python src/dictionary.py    # -> docs/data_dictionary.md
uv run python src/service_docs.py  # -> out/service/ and README.md
uv run python src/build_page.py    # -> out/corridor_audit.html
npm run dev --prefix web          # dashboard on :3210
```

Every module runs standalone and prints its own verification metric. A module that fails its gate reports the failure rather than continuing.

## Layout

- `src/` — 31 modules. `tmc_parse` and `audit` are the core; `atlas`, `medians` and `dxf_inventory` read the CAD survey; `capacity`, `scheme_test`, `delay` and `economics` carry the findings.
- `web/` — Next.js dashboard, reading the same `corridor.json` as the static report.
- `docs/data_dictionary.md` — every field in every published file, with units. Generated, so a field added without a description fails a test.
- `docs/jaipur_corridor_study.md` — the methodology, with inline `ERRATUM` blocks correcting 9 defects in its own worked code.

**Documents are generated, not written.** Reports, the data dictionary, the commercial pack and this README all build from pipeline output, because hand-written figures go stale silently — this file claimed 26 tests while the suite held 194.

## Caveats, stated

3 junction positions are fixed by an exact name match against JDA's scheme and confirmed by chainage along the survey drawing; 3 are placed by position in that sequence and labelled inferred throughout.

The severity weighting in the constraint atlas is a judgement, not a measurement. Half the PCU correction is unresolvable because the survey's class scheme lumps roughly half the stream into one column, so those figures are published as bands.

Critical-gap values are from literature rather than measured here; they are Raff-derived and so likely biased high, which makes the U-turn finding conservative. Detection accuracy is unverified until footage exists — the pipeline and its gates are built and self-tested, and no accuracy figure is claimed.

Rupee figures are banded and the value of time is a policy input, not a measurement. Substituting the authority's own approved rates changes one table.