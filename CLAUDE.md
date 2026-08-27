# CORRIDOR — Mansarovar Corridor Junction Intelligence

## What this is

A traffic analysis pipeline for a **six-junction corridor in Jaipur**, running between
**Mansarover Metro** (north) and **Sanganer Stadium** (south).

The primary input is a JDA-supplied classified turning movement survey: 12 workbooks,
six intersections (TMC-01 … TMC-06) counted over a full 24 hours on two consecutive
days (11 and 12 May 2026). The pipeline parses it, audits it, corrects what can be
defensibly corrected, and publishes the result.

A video/CV counting stage is **built and self-tested but unverified**: detection,
tracking, homography, zone counting, critical-gap estimation and a two-stage training
chain all exist and pass their own gates against synthetic data. None has seen real
footage, so no accuracy figure is claimed and the validation report (D8) stands as a
pro forma with its gates published ahead of the measurement.

## Goal

A credibility artefact for a JDA Jaipur conversation. Success is a **validated,
corrected corridor result with a stated error rate** — not feature coverage.

The audit is the point. Showing the survey's own defects, quantified, with the
correction and its magnitude, is what makes an engineer trust the rest.

## Scope discipline

Six junctions, handled as six. No plugin architecture, no multi-corridor config
system, no PostGIS, no auth, no backend API, no real-time anything. Static JSON is
enough. When a second corridor exists we generalise deliberately, not speculatively.

---

## The junctions

All six share a `Mansarover Metro` (N) and `Sanganer Stadium` (S) arm — they are
consecutive junctions on one corridor. The E/W arms are the cross-streets.

| Code | N arm | E arm | S arm | W arm |
|---|---|---|---|---|
| TMC-01 | Mansarover Metro | Patrika Gate | Sanganer Stadium | Sumer Nagar |
| TMC-02 | Mansarover Metro | Durgapur | Sanganer Stadium | Mohanpura |
| TMC-03 | Mansarover Metro | Patel Marg Crossing | Sanganer Stadium | Sumer Nagar |
| TMC-04 | Mansarover Metro | VT Road | Sanganer Stadium | Dholai |
| TMC-05 | Mansarover Metro | Rajatpath | Sanganer Stadium | Mangyawas |
| TMC-06 | Mansarover Metro | New Aatish Market | Sanganer Stadium | Mansarover |

Arm order in the table is **clockwise**, which is how the survey sheets order them.
Physical ordering of the six junctions along the corridor is **derived from the counts**
(southbound outflow at junction *n* against Mansarover-Metro inflow at *n+1*), not assumed.

---

## Non-negotiable rules

### Coordinates
- **All spatial data is EPSG:32643 (UTM Zone 43N), metres.** No exceptions.
- Lat/long (EPSG:4326) exists only at ingest and display boundaries. Convert immediately.
- Never compute distance, area, or bearing in degrees.
- Jaipur sanity check: WGS84 `26.9124N, 75.7873E` → UTM43N `E≈578000, N≈2976000`.
  If a coordinate is far from this, something is wrong. Fail loudly.

### Traffic domain
- **India drives on LEFT.** The RIGHT turn crosses opposing traffic and is the
  critical, capacity-limiting movement. Never import right-hand-drive assumptions.
- **Left turn = the next arm clockwise from the approach.** Verified against the JDA
  Summary sheets, which are internally consistent with this and with the flow diagrams.
- Turn classification by signed delta bearing, range (-180, 180]:
  - `|d| <= 45` → THROUGH
  - `-135 <= d < -45` → LEFT
  - `45 < d <= 135` → RIGHT
  - `|d| > 135` → UTURN
- **This dataset counts 12 movements per junction: 4 arms × (LEFT / STRAIGHT / RIGHT).**
  **U-turns were not surveyed.** Do not synthesise them, do not assume they are zero —
  report their absence as a gap.

### The survey's class scheme, and what can be corrected

**The scheme is not the contractor's invention.** It is IRC:SP:41-1994 Table 3.1,
"Intersection Design Data" — the standard proforma for an intersection survey, including
its ten classes and its static PCU factors. That matters twice over: the factors are
defensible as a starting point, and Table 3.1 also carries a **PEDESTRIAN Nos.** row that
this survey left empty. Clause 3.1(iv) requires it in urban areas with substantial
pedestrian movement. The omission is at clause level, not a matter of judgement.

The JDA sheets use a 10-column scheme that does **not** map cleanly onto IRC:106.
Five columns are composites mixing classes with different PCU values. Correct only what
maps 1:1; publish a sensitivity band for the rest. Never invent a point estimate for a
composite.

| Col | JDA label | PCU used | Maps to | Correctable |
|---|---|---|---|---|
| B | Car, Taxi, Tempo, Auto Rickshaw & Pick up | 1.0 | CAR + AUTO + LCV | **No — band** |
| C | Motar Cycle, Scooter | 0.5 | 2W | **Yes** |
| D | Agriculture Tractor, LCV Mini Bus | 1.5 | TRACTOR + LCV + BUS | **No — band** |
| E | Three Wheeler (Auto) Axle Truck, Buses | 3.0 | AUTO + TRUCK + BUS | **No — band** |
| F | Tractor Trailor, Truck Trailor Units (3 Axle & MAV) | 4.5 | MAV + TRACTOR | Partly |
| H | Cycle | 0.5 | CYCLE | **Yes** |
| I | Cycle Rickshaw | 1.5 | CYCLE_RIK | **Yes** |
| J | Hand Cart | 3.0 | HAND_CART, IRC:106-1990 Table 1 at 2.0 (5%) / 3.0 (10%+) | **Yes** |
| K | Horse Drawn | 4.0 | ANIMAL | **Yes** |
| L | Bullock Corts | 8.0 | ANIMAL | **Yes** — 142 counted (TMC-03/04/05), not zero |

**There is no E-rickshaw column.** The label exists in the workbook string table but no
column carries it. Flag this as a stated gap in every output — e-rickshaws are a
material share of Jaipur traffic and their absence biases the count downward.

### PCU
- PCU factors are **share-dependent** (IRC:106). Interpolate linearly between the 5% and
  10% values based on that class's share of the stream. Do not hardcode a single value.
- The survey used **static** factors. That is the central audit finding: 2W is carried at
  0.50 while 2W is ~49% of the stream, where IRC:106 requires 0.75.
- E_RIK has no official PCU. Use 1.0/1.2 and **flag it as an assumption in output**.
- Corrections run both ways. 2W is understated; Cycle (0.50 vs IRC 0.40) and the MAV
  bucket (4.5 vs IRC 3.7) are mildly overstated. Report the net, not just the favourable half.

### Never trust a stored total
Every `Total Fast`, `Total Slow`, `Grand Total (Nos.)` and `Grand Total (PCU's)` in the
workbooks is **re-derived from its components**. Some are wrong — `Total Slow` returns 0
on movement sheet V-1 when its components sum to 58, breaking conservation against the
approach total. Mismatches are **recorded in a register, never silently corrected**.

---

## Verification gates

Every stage has a numeric acceptance threshold. Do not proceed past a failed gate —
report the failure instead of working around it.

### Survey data stages (current work)

| Stage | Gate |
|---|---|
| Parse | Every stored total re-derived; count of silently-absorbed discrepancies = **0** |
| Conservation | Σ(3 movements from arm *i*) vs IN_*i* reported per arm, per junction, per day |
| Movements | Exactly **12** per junction (4 arms × L/S/R). No U-turns in this dataset |
| PCU evidence | Implied factor per class constant across all 96 intervals, else the "static PCU" claim is withdrawn |
| Peak hour | Re-derived from 15-min bins matches the workbook's own rolling-hour sheets |
| Corridor order | Continuity-derived ordering agrees with map pins, or the disagreement is reported. Continuity was inconclusive at a 1.2% margin; chainage along the surveyed alignment resolved it |

### Assessment stages

| Stage | Gate |
|---|---|
| Capacity | Widths **measured** from transects, never assumed. v/c reported as a band because half the PCU correction is unresolvable |
| Design life | Relief reported for the **horizon**, not the opening year. 0 of 12 approaches survive to 2046 |
| Scheme test | v/c above **3.0** reported as "no viable gaps", never as a number — gap acceptance has degenerated by then |
| Queue and delay | No queue reported longer than the road can physically hold. Past spillback the deterministic model is out of its regime and says so |
| Economics | Every rupee figure **banded**; value of time declared a policy input, not a result. Excluded items named |
| Sensitivity | Every published conclusion re-run across the full assumption grid, and the grid size stated |

### Video/CV stages (built, unverified until footage exists)

| Stage | Gate |
|---|---|
| Homography | reprojection RMSE < 0.5 m near junction centre |
| Detection, stage 1 | mAP@0.5 ≥ 0.80 overall, ≥ 0.70 per class on IDD |
| Detection, stage 2 | train/val split by contiguous **time block**, never random — adjacent frames are the same scene and a random split inflates mAP past its own gate |
| Tracking | > 90% of tracks resolve to a movement |
| Counts | manual-vs-auto MAPE < 10% total, < 15% per major class |
| Critical gap | ≥ 25 head-of-queue drivers, else not reportable and the literature values stand |
| Pipeline | Stops at the first failed gate. A run that completes on a bad homography emits a normal-looking matrix nothing downstream flags |

---

## Code style
- Minimum code that solves the problem. No speculative flexibility.
- Every module runnable standalone with a `__main__` that demonstrates it.
- Print the verification metric at the end of every stage. Silent success is not success.
- Comment the *why*, especially for domain decisions (why footpoint not centroid,
  why 15 m zone offset, why LMEDS not RANSAC, why share-dependent PCU).
- No placeholder values, no TODO stubs in delivered code.

## Stack

Only what is actually imported. This list is asserted against `pyproject.toml` and the
import graph by a test, because an earlier version named six libraries the project does
not use — including one it had evaluated and deliberately rejected.

- Python 3.11, `uv` for env and lockfile
- `pandas`, `numpy`, `openpyxl` — survey ingest and analysis
- `pyarrow`, `tabulate` — Parquet and markdown tables, via pandas rather than imported
- `shapely` 2.x — geometry
- `pyproj` — projections
- `scipy` — statistics for the audit tests
- `opencv-python` — homography, video IO, frame handling
- `ultralytics` + `torch` — YOLO detection and fine-tuning
- `supervision` — ByteTrack tracking
- `matplotlib` — the constraint atlas PDF
- `reportlab` — the meeting pack PDF and the reviewer question sheet
- `pyyaml` — dataset manifests
- Next.js + React, MapLibre GL, Recharts — dashboard, static JSON, no backend

**Deliberately NOT used, and why:**

- **`ezdxf`** — the converted DXF is 198 MB of ASCII and `ezdxf.readfile` is not practical
  on it. `dxf_inventory.py` streams group-code pairs instead: whole file in seconds, no
  meaningful memory. Do not reintroduce it.
- **`sahi`** — the slicing technique is used and implemented directly in `detect.py`
  (`slices`, `iou`, `merge`), which keeps the tile geometry and the merge rule under our
  own tests. Describe it as sliced inference, never as SAHI the library.
- **`osmnx`, `geopandas`, `networkx`, `folium`** — the survey supplies movements and the
  CAD supplies geometry, so no OSM ingest, no graph topology and no folium output was
  ever needed.

## Hardware split

- **MacBook M4 Pro**: all development, survey analysis, geometry, topology, outputs.
  Ultralytics inference runs on MPS (`device='mps'`).
- **Windows PC (RTX 3060 12GB)**: YOLO fine-tuning and batch video inference.
  CUDA is meaningfully faster than MPS for training. Move video processing there.

## Layout

```
corridor/
├── CLAUDE.md
├── 00_source/
│   ├── dwg/          # as received from JDA
│   ├── dxf/          # converted, ASCII
│   └── extracted/    # the 12 TMC workbooks
├── docs/
│   ├── jaipur_corridor_study.md      # full methodology — the reference
│   ├── data_dictionary.md            # generated — every published field, with units
│   ├── sessions_v2_roundabout.md     # SUPERSEDED — roundabout plan, provenance only
│   ├── inputs_models_stack.md        # SUPERSEDED except Parts 3 and 5 (camera, stack)
│   └── setup_runbook.md              # environment setup; its PROMPT ORDER is superseded
├── data/
│   ├── raw/          # video, downloaded OSM
│   ├── gcps/         # ground control points — NOT YET CREATED; arrives with the
│   │                 #   GCP stills, which are still outstanding
│   └── processed/    # geojson, graphml, parquet
├── src/                # every module runs standalone and prints its own metric
│   ├── config.py       # corridor + junction constants, incl. coordinates
│   ├── dwg_probe.py    # Phase 0 — CRS discovery from the DWG header
│   ├── dxf_inventory.py# Phase 1 — layer inventory, junction candidates
│   ├── inspect_tmc.py  # raw workbook structure probe, no reshaping
│   ├── tmc_parse.py    # workbooks -> tidy frames; never trusts a stored total
│   ├── spelling.py     # corrected labels at display; source spelling preserved
│   ├── audit.py        # integrity audit -> out/audit_report.md
│   ├── pcu.py          # IRC:106 share-dependent PCU, bands for composites
│   ├── analyse.py      # peak hour, TMC matrices, through/turning split
│   ├── atlas.py        # constraint atlas + pier-siting profile
│   ├── medians.py      # U-turn feasibility from DIVIDER linework
│   │
│   ├── capacity.py     # measured widths, v/c, design life of the relief
│   ├── measurement.py  # every published dimension: method, uncertainty, what fixes it
│   ├── routes.py       # every path through a signal-free junction, enumerated
│   ├── scheme_test.py  # gap acceptance — does the JDA U-turn scheme work?
│   ├── uturn_framework.py # where a bay belongs: criteria ladder, binding term
│   ├── delay.py        # queue, spillback, delay, corridor journey time
│   ├── economics.py    # cost of delay, banded; value of time is a policy input
│   ├── sensitivity.py  # every conclusion re-run across the assumption grid
│   ├── safety.py       # conflict points from geometry; exposure, not crash prediction
│   ├── profiles.py     # LOS by approach-hour, peak spreading, cumulative queue
│   ├── exhibits.py     # volume-flow, tornado, continuity, flow raster
│   ├── standards.py    # the corridor against the codes it is built under
│   │
│   ├── anomaly.py      # survey integrity screen; gate is rediscovering known defects
│   ├── cluster.py      # approach typology; gate is a held-out corridor/cross label
│   ├── forecast.py     # shortest trustworthy count, leave-one-out expansion factors
│   │
│   ├── homography.py   # pixel -> world, float64 + local origin, plain least squares
│   ├── detect.py       # YOLO + SAHI slicing + ByteTrack
│   ├── count.py        # zones -> movements; resolves by radial velocity order
│   ├── critical_gap.py # Raff + Troutbeck MLE from a field event log
│   ├── annotate.py     # frame selection for labelling; CVAT/Roboflow/LS ingest
│   ├── train.py        # stage 1, IDD fine-tune
│   ├── finetune.py     # stage 2, this camera; block split, never random
│   ├── validate.py     # MAPE gates, accepted vs meets-target
│   ├── pipeline.py     # Phase 6 driver — fails at the first gate
│   │
│   ├── reports.py      # D6 capacity, D8 validation (pro forma), D9 method
│   ├── meeting_pack.py # -> out/Corridor_Meeting_Pack.pdf + reviewer_questions.md
│   ├── dictionary.py   # -> docs/data_dictionary.md; gates every published field
│   ├── service_docs.py # -> README.md and out/service/; owns PIPELINE_ORDER
│   ├── export.py       # -> out/data/corridor.json (both dashboards read this)
│   ├── masterdb.py     # -> out/Six_Junction_Master_Database.xlsx (D12)
│   ├── sync_web.py     # out/ -> web/public/; refuses the files export reshapes
│   ├── build_page.py   # -> out/corridor_audit.html
│   ├── build_pitch.py  # -> out/corridor_pitch.html
│   └── build_picker.py # local map for assigning TMC codes to candidates
│
│   NOT BUILT, and deliberately so — nothing in the deliverable needs them:
│     network.py    CAD -> noded graph. Corridor order came from chainage instead
│     movements.py  from CAD — the survey supplies movements directly
│     geo.py        superseded by pyproj use in dwg_probe/atlas/medians
├── web/              # Next.js dashboard
├── tests/
└── out/              # deliverables, audit report, static JSON
    └── service/      # generated — implementation plan, commercial pack, capability
```

## Reference

`docs/jaipur_corridor_study.md` contains the full methodology with worked code for
every stage. **Read the relevant phase before implementing a stage.** It documents the
domain traps — bulge in LWPOLYLINE, grade separation noding, footpoint vs centroid,
share-dependent PCU. Do not rediscover these.

**It also contains errata.** Several code samples have defects, marked inline with
`> **ERRATUM**` blocks. Read the erratum, not just the sample.

## Working style

- Surface assumptions rather than guessing. If a junction's geometry is ambiguous, ask.
- If a simpler approach exists, say so before building the complex one.
- Match the existing style; don't refactor working code that wasn't part of the task.

---

# SUPERSEDED — roundabout model

The block below is reproduced **verbatim** from `docs/sessions_v2_roundabout.md`. It
describes a single 6-arm free-flow roundabout (Mahima / Vande Mataram Circle) and was
the project's model before the JDA survey data arrived.

**It does not govern.** The supplied data is six 4-arm junctions with 12 movements each
and no roundabout. This section is kept for provenance and for the case where Mahima
Circle later becomes the video/CV pilot site. Where it conflicts with the rules above,
the rules above win.

```markdown
## Junction under study

Mahima / Vande Mataram Circle, Giriraj Nagar, Dholai, Jaipur.
Approx 26.8478 N, 75.7436 E (EPSG:4326) — confirm before use.
**Free-flow roundabout, 6+ arms. Not signalised.**

## Roundabout rules — these override the generic junction logic

- **India drives on the left, so circulation is CLOCKWISE.** Every generic
  roundabout reference you have seen assumes anticlockwise. Invert it.
- A roundabout is NOT a single node. OSM models it as a ring of one-way ways
  tagged `junction=roundabout`. The ring must be detected and collapsed into one
  logical junction before movements can be enumerated.
- **There is no opposed right turn.** All entries yield to circulating traffic.
  Capacity is gap acceptance and weaving, not signal phasing. Do not apply
  signalised-junction logic anywhere in this project.
- **Movements are named two ways, and both must appear in output:**
  - *Geometric*: LEFT / THROUGH / RIGHT / UTURN by bearing delta — useful for
    comparison with conventional TMC formats
  - *Exit number*: counting clockwise from the entry arm — 1st exit, 2nd exit,
    and so on, with a full circulation back to the entry arm being the U-turn.
    **This is how drivers and Indian engineers actually describe the movement,
    so it is the primary label.**
- **Circulating flow must be counted separately** from entry and exit flow.
  Roundabout entry capacity is a function of the circulating flow passing that
  entry, so a zone is needed on the circulatory carriageway between each pair of
  adjacent arms. This is an extra measurement a crossroads would not need.
- Governing standard is **IRC:65** (roundabout design) and the Indo-HCM
  roundabout chapter — **not IRC:SP:41**, which covers at-grade intersections.

## Movement count expectations

n arms → n² movement pairs, of which n are U-turns.
- 6 arms → **36 movements** (6 U-turns + 30 others)
- 7 arms → 49 movements (7 U-turns)

Do not hardcode 4 arms or 16 movements anywhere.
```
