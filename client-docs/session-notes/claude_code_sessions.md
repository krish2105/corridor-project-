# Claude Code — 8 Session Build Plan
### Single-junction pilot, Jaipur. Copy each prompt into a fresh Claude Code session.

**Sessions 1–4 need no video and no JDA data.** Start today. Sessions 5–8 need one
video file. That split is deliberate — it means you can have half the pipeline working
before you ever go to site.

---

## SESSION 1 — Scaffold and environment

> Set up the repo per the layout in CLAUDE.md.
>
> - Create the directory structure and a `.gitignore` that excludes `data/raw/`,
>   `out/`, `*.mp4`, `*.pt`, and `__pycache__`
> - Create a `pyproject.toml` using `uv`, Python 3.11, with the stack listed in
>   CLAUDE.md. Pin `osmnx>=2.0`, `shapely>=2.0`, `numpy<2.2` for ultralytics compat
> - Create `src/geo.py` with: a `TO_UTM` / `TO_WGS84` transformer pair for
>   EPSG:4326 ↔ EPSG:32643, a `sanity_check_jaipur(x, y)` function that raises if a
>   UTM coordinate is more than 50 km from Jaipur city centre, and a `bearing(p1, p2)`
>   function returning a compass bearing
> - Write tests for all three in `tests/test_geo.py`
>
> **Success:** `uv run pytest` passes. `sanity_check_jaipur` correctly accepts
> (578000, 2976000) and rejects (378000, 2976000). `bearing((0,0),(0,1))` returns 0.0
> and `bearing((0,0),(1,0))` returns 90.0.

---

## SESSION 2 — Network ingest and noding

> Build `src/network.py`. Read Phase 2 of `docs/jaipur_corridor_study.md` first.
>
> - `fetch_osm(lat, lon, radius_m)` — pull the drivable network with osmnx, project
>   immediately to EPSG:32643
> - `node_network(lines, snap_tol=1.0)` — the noding pipeline: snap near-coincident
>   endpoints, split at intersections via `unary_union`, recombine with `linemerge`,
>   build a `networkx.MultiDiGraph`
> - `classify_nodes(G)` — tag each node by undirected degree: terminus / midblock /
>   T_junction / cross_junction / complex_junction
> - `snap_tolerance_sweep(lines)` — report node count at tol = 0.1, 0.5, 1.0, 2.0,
>   5.0 m so I can see where the count stabilises
> - Export to GeoJSON and GraphML
>
> **Success:** running on my junction coordinates produces a connected graph. The
> tolerance sweep prints a table. No degree-1 nodes appear in the interior of the
> network — only at the edge of the fetch radius. Print node and edge counts.

---

## SESSION 3 — Movement enumeration

> Build `src/movements.py`. Read Phase 3 of the methodology doc.
>
> - `turn_delta(theta_in, theta_out)` — signed angle normalised to (-180, 180]
> - `classify_turn(delta)` — India left-hand-drive rules exactly as specified in CLAUDE.md
> - `enumerate_movements(G, node)` — every (approach, exit) pair at a node, with
>   bearings, delta, movement type, and a TMC code like NBL / EBT / SBR / WBU
> - Handle the case where a >135° turn onto a *different* link is a sharp turn, not a
>   U-turn. Only a return onto the same link is a true U-turn
> - Export the movement table to CSV
>
> **Success:** a 4-arm junction yields exactly 16 movements — 4 THROUGH, 4 LEFT,
> 4 RIGHT, 4 UTURN. A 3-arm T-junction yields 9. Unit tests cover both, plus the
> boundary cases at delta = ±45 and ±135.

---

## SESSION 4 — Constraint atlas from open data

> Build `src/atlas.py`.
>
> - Pull building footprints, land use, waterways, and green space from OSM for the
>   junction area
> - Render a layered map: network coloured by junction type, movement arrows at the
>   pilot junction, constraint layers beneath
> - Produce both an interactive `folium` HTML and a print-quality matplotlib PDF with
>   a north arrow, scale bar, and legend
> - Include a metadata block on the PDF: CRS, data sources, generation date, and the
>   node/edge/movement counts
>
> **Success:** a PDF in `out/` that looks like a professional deliverable, not a
> script output. The junction is legible. Every layer is in the legend.
>
> *This is the artefact you can show JDA before you have any video.*

---

## SESSION 5 — Detection and tracking

> Build `src/detect.py`. Read Phase 6 of the methodology doc.
>
> - Load YOLO via ultralytics; auto-select device (`mps` on Mac, `cuda` on the 3060)
> - Run detection + ByteTrack via `supervision` over a video file
> - Map COCO classes to our scheme where possible: `motorcycle→2W`, `car→CAR`,
>   `bus→BUS`, `truck→TRUCK`, `bicycle→CYCLE`
> - **Explicitly log every detection that cannot be mapped** — this is how we quantify
>   the auto-rickshaw and e-rickshaw gap before deciding on fine-tuning
> - Extract the bounding-box footpoint (bottom-centre) for each track, per frame
> - Persist tracks to Parquet: `track_id, frame, class, conf, foot_x, foot_y`
> - Write an annotated preview video for the first 60 seconds so I can eyeball quality
>
> **Success:** tracks persist across occlusion — spot-check that a vehicle crossing
> the junction keeps one ID. Print the class histogram and the unmapped-detection
> rate. Report FPS.

---

## SESSION 6 — Homography

> Build `src/homography.py`.
>
> - `fit_homography(img_pts, world_pts)` using `cv2.findHomography` with RANSAC,
>   reporting reprojection RMSE, max error, and inlier count
> - `to_world(H, pts)` for transforming track footpoints
> - A GCP picker: display a video frame, let me click points, and save pixel
>   coordinates to `data/gcps/`
> - Load the paired real-world coordinates from a CSV I supply
> - Fail loudly if RMSE > 0.5 m
>
> **Success:** RMSE under 0.5 m near the junction centre. Transformed track paths,
> when plotted over the Session 2 network, visibly follow the actual roads. That
> visual check is the real test — do not skip it.

---

## SESSION 7 — Zone counting and TMC

> Build `src/count.py` and `src/pcu.py`. Read Phase 6.3 and Phase 4.
>
> - `build_zones(G, node)` — generate entry/exit zones per leg directly from the
>   Session 2 graph, offset 15 m from the junction, 15 m deep
> - `assign_movement(track, zones, min_dwell=3)` — first entry zone, last exit zone
> - `aggregate_tmc(...)` — counts by 15-min bin × class × movement code
> - `pcu_factor(veh_class, share)` — share-dependent interpolation per IRC:106
> - `peak_hour(counts)` — four consecutive 15-min bins, returning volume and PHF
> - Output a TMC table as CSV and a spider diagram per junction
>
> **Success:** over 90% of tracks resolve to a movement. Report the unresolved rate
> and why. Print peak hour and PHF. The spider diagram is readable.

---

## SESSION 8 — Validation and deliverable

> Build the validation harness and final outputs.
>
> - A CSV template for manual counts matching the field form in Phase 5.4
> - `validate(manual, auto)` — MAPE overall and per class, against the thresholds
>   in CLAUDE.md, with a clear pass/fail per metric
> - A one-page validation report: georeference RMSE, homography RMSE, track
>   resolution rate, MAPE by class, and every stated assumption (especially the
>   e-rickshaw PCU)
> - Merge into a final PDF: constraint atlas, junction geometry, movement inventory,
>   TMC results, validation report
>
> **Success:** a single PDF I can hand to JDA. Every number in it traceable to a
> stage that reported its own error. If a threshold failed, the report says so
> rather than hiding it.

---

# What to attach in Claude Code

Drop these in before Session 1:

- `CLAUDE.md` at the repo root
- `docs/jaipur_corridor_study.md` — the methodology
- `docs/corridor_service_playbook.md` — context on why this exists
- Your `karpathy-guidelines` skill is already active and applies well here

Then `cd` into the repo and run `claude`.

---

# What I need from you

Only two things block Sessions 1–4:

- **Junction name and coordinates** — pick one. Best pilot junction: 4-arm,
  signalised, moderately busy, with a building nearby you can film from. Somewhere
  you can physically reach easily, because you'll go back more than once.
- **Corridor name** — so the atlas is labelled correctly.

For Sessions 5–8, once you shoot:

- **The video file** — 1080p minimum, 25–30 fps, 2–3 hours covering a peak. Camera
  8–12 m up. All four approaches in frame if possible.
- **4–8 GCPs** — points visible in the video frame whose real-world position you can
  read off Google Earth. Kerb corners, manhole covers, median nose tips, signal pole
  bases. Give me pixel coordinates and lat/long for each.
- **Two 15-minute manual counts** — one peak, one off-peak, using the field form.
  This is what makes the whole thing defensible.

**The GCPs are the one irreversible step.** You cannot add them after the fact — if
you film without identifying them, you go back to site. Mark them before you shoot.
