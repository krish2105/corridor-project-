# CORRIDOR — Junction Intelligence Pilot

## What this is

A single-junction traffic analysis pipeline for Jaipur. Takes an open-data road
network plus one video of one junction, and produces a validated classified
turning movement count.

**Scope discipline: this is ONE junction, not a corridor.** Do not build corridor-scale
abstractions. No multi-junction orchestration, no config systems for junctions that
don't exist yet, no plugin architectures. When this works for one junction we will
generalise deliberately, not speculatively.

## Goal

A credibility artefact for a JDA Jaipur conversation. Success is a working
result with a stated error rate — not feature coverage.

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
- Turn classification by signed delta bearing, range (-180, 180]:
  - `|d| <= 45` → THROUGH
  - `-135 <= d < -45` → LEFT
  - `45 < d <= 135` → RIGHT
  - `|d| > 135` → UTURN
- Vehicle classes: `2W, AUTO, E_RIK, CAR, LCV, BUS, TRUCK, MAV, CYCLE, CYCLE_RIK,
  TRACTOR, ANIMAL`
- PCU factors are **share-dependent** (IRC:106). Interpolate between the 5% and 10%
  values based on that class's share of the stream. Do not hardcode a single value.
- E_RIK has no official PCU. Use 1.0/1.2 and **flag it as an assumption in output**.

### Verification gates
Every stage has a numeric acceptance threshold. Do not proceed past a failed gate —
report the failure instead of working around it.

| Stage | Gate |
|---|---|
| Georeference | RMSE < 3 m |
| Topology | node count matches visual junction count; no unexpected degree-1 nodes |
| Movements | exactly 16 movements at a 4-arm junction (4 each T/L/R/U) |
| Homography | reprojection RMSE < 0.5 m near junction centre |
| Tracking | > 90% of tracks resolve to a movement |
| Counts | manual-vs-auto MAPE < 10% total, < 15% per major class |

### Code style
- Minimum code that solves the problem. No speculative flexibility.
- Every module runnable standalone with a `__main__` that demonstrates it.
- Print the verification metric at the end of every stage. Silent success is not success.
- Comment the *why*, especially for domain decisions (why footpoint not centroid,
  why 15 m zone offset, why LMEDS not RANSAC).
- No placeholder values, no TODO stubs in delivered code.

## Stack

- Python 3.11
- `osmnx` — network ingest
- `shapely` 2.x, `geopandas`, `networkx` — geometry and topology
- `pyproj` — projections
- `ezdxf` — DXF parsing (used only once JDA supplies drawings)
- `opencv-python` — homography, video IO
- `ultralytics` — YOLO detection
- `supervision` — ByteTrack tracking, zone utilities
- `pandas` — aggregation
- `matplotlib`, `folium` — output

## Hardware split

- **MacBook M4 Pro**: all development, geometry, topology, analysis, outputs.
  Ultralytics inference runs on MPS (`device='mps'`).
- **Windows PC (RTX 3060 12GB)**: YOLO fine-tuning and batch video inference.
  CUDA is meaningfully faster than MPS for training. Move video processing there.

## Layout

```
corridor/
├── CLAUDE.md
├── docs/
│   ├── jaipur_corridor_study.md      # full methodology — the reference
│   └── corridor_service_playbook.md  # engagement context
├── data/
│   ├── raw/          # video, downloaded OSM
│   ├── gcps/         # ground control points
│   └── processed/    # geojson, graphml
├── src/
│   ├── network.py    # OSM -> noded graph
│   ├── movements.py  # movement enumeration + classification
│   ├── geo.py        # projections, georeferencing
│   ├── detect.py     # YOLO + ByteTrack
│   ├── homography.py # pixel -> world
│   ├── count.py      # zones -> TMC
│   ├── pcu.py        # PCU conversion
│   └── atlas.py      # outputs
├── tests/
└── out/              # deliverables
```

## Reference

`docs/jaipur_corridor_study.md` contains the full methodology with worked code for
every stage. **Read the relevant phase before implementing a stage.** It documents
the domain traps — bulge in LWPOLYLINE, grade separation noding, footpoint vs
centroid, share-dependent PCU. Do not rediscover these.

## Working style

- Surface assumptions rather than guessing. If a junction's geometry is ambiguous, ask.
- If a simpler approach exists, say so before building the complex one.
- Match the existing style; don't refactor working code that wasn't part of the task.
