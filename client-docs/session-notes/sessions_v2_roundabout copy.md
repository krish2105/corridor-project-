# Session Prompts v2 — Mahima / Vande Mataram Circle
### 6-arm free-flow roundabout, Giriraj Nagar / Dholai, Jaipur

**Supersedes Sessions 2 and 3 in the earlier plan.** Sessions 1 and 4 are unchanged
in shape but now carry real coordinates.

**Junction:** ~26.8478 N, 75.7436 E — *confirm with an exact pin before Session 2*
**Names in use:** Mahima Circle / Vande Mataram Circle
**Type:** free-flow roundabout, 6+ arms, India (clockwise circulation)

---

# Add these to CLAUDE.md

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

---

# SESSION 1 — Scaffold and environment

*(unchanged from v1, with real coordinates baked in)*

> Set up the repo per the layout in CLAUDE.md.
>
> - Directory structure, plus a `.gitignore` excluding `data/raw/`, `out/`,
>   `*.mp4`, `*.pt`, `__pycache__`
> - `pyproject.toml` via `uv`, Python 3.11, with the stack in CLAUDE.md.
>   Pin `osmnx>=2.0`, `shapely>=2.0`, `numpy<2.2`
> - Create `src/config.py` holding the junction constants:
>   `JUNCTION_NAME = "Mahima / Vande Mataram Circle"`,
>   `JUNCTION_LATLON = (26.8478, 75.7436)`, `JUNCTION_TYPE = "roundabout"`,
>   `CIRCULATION = "clockwise"`, `CRS_WORK = "EPSG:32643"`, `CRS_GEO = "EPSG:4326"`
> - Create `src/geo.py` with a `TO_UTM` / `TO_WGS84` transformer pair,
>   `sanity_check_jaipur(x, y)` raising if a UTM coordinate is more than 50 km from
>   Jaipur centre, and `bearing(p1, p2)` returning a compass bearing
> - Tests for all three in `tests/test_geo.py`
>
> **Success:** `uv run pytest` passes. `sanity_check_jaipur` accepts
> (578000, 2976000) and rejects (378000, 2976000). `bearing((0,0),(0,1))` → 0.0,
> `bearing((0,0),(1,0))` → 90.0. Converting `JUNCTION_LATLON` to UTM passes the
> sanity check.

---

# SESSION 2 — Roundabout network ingest and ring collapse

*(replaces v1 Session 2 — this is the version that handles a roundabout)*

> Build `src/network.py`. Read Phase 2 of `docs/jaipur_corridor_study.md` for the
> general noding approach, but note this junction is a **roundabout**, which that
> phase does not cover. The roundabout handling below is the new part.
>
> - `fetch_osm(lat, lon, radius_m=600)` — drivable network via osmnx, projected
>   immediately to EPSG:32643
> - `detect_roundabout(G)` — find edges tagged `junction=roundabout` or
>   `junction=circular`. Return the ordered ring of nodes forming the circulatory
>   carriageway. **If OSM has not tagged it, fall back to detecting a small cycle
>   of one-way edges near the target coordinate, and warn me clearly** — I may need
>   to identify the ring manually
> - `find_arms(G, ring_nodes)` — every edge leaving the ring is an arm. For each,
>   record: the ring node it attaches to, the bearing away from the ring centre,
>   the street name from OSM, and a compass label (N, NE, E, SE, S, SW, W, NW)
> - `collapse_ring(G, ring_nodes)` — build a logical junction: one synthetic node at
>   the ring centroid, with each arm attached. **Keep the original ring geometry
>   in a separate attribute** — it is needed later for circulating-flow zones and
>   for weaving-length calculation
> - `order_arms_clockwise(arms, centre)` — sort arms by bearing in clockwise order,
>   which is the direction of circulation in India. Assign each an index 0..n-1
> - Export: arms table to CSV, ring geometry and network to GeoJSON, graph to GraphML
>
> **Success:** the ring is detected and reported with its radius and circumference.
> The arms table lists **6 or more arms**, each with a street name where OSM has one,
> a bearing, and a clockwise index. Print the arm count prominently — if it comes
> back as 4, the detection is wrong and I need to know immediately rather than have
> it silently proceed.
>
> Also print the **weaving length between each pair of adjacent arms** (arc distance
> along the ring). On a 6-arm roundabout several of these will be short, and that is
> the finding, not a bug.

---

# SESSION 3 — Roundabout movement enumeration

*(replaces v1 Session 3)*

> Build `src/movements.py`. Note the roundabout rules in CLAUDE.md — this is not a
> conventional junction.
>
> - `turn_delta(theta_in, theta_out)` — signed angle normalised to (-180, 180]
> - `classify_turn(delta)` — geometric label using the India left-hand-drive rules
>   in CLAUDE.md. This is the **secondary** label
> - `exit_number(entry_idx, exit_idx, n_arms)` — clockwise offset from the entry
>   arm. Entry arm to itself is a full circulation, labelled `UTURN`. Adjacent
>   clockwise arm is `EXIT_1`, and so on. This is the **primary** label
> - `enumerate_movements(arms)` — every (entry arm, exit arm) pair, carrying both
>   labels plus bearings and delta
> - `circulating_segments(ring, arms)` — the ring arc between each pair of adjacent
>   arms, for later circulating-flow counting
> - Export the movement table to CSV with columns:
>   `entry_arm, entry_name, exit_arm, exit_name, exit_number, geometric_turn,
>   bearing_in, bearing_out, delta`
>
> **Success:** with 6 arms the table contains **exactly 36 rows**, of which 6 are
> U-turns. Assert this against the detected arm count rather than a hardcoded number.
> Unit tests cover a 4-arm and a 6-arm case, plus the boundary values at
> delta = ±45 and ±135.
>
> Print a readable summary I can sanity-check by eye — for each arm, list where its
> traffic can go, by street name. If "Vande Mataram Marg → 100 Feet Rd" comes out
> as the 3rd exit and that matches the map, the logic is right.

---

# SESSION 4 — Constraint atlas

*(unchanged in shape from v1, extended for the roundabout)*

> Build `src/atlas.py`.
>
> - Pull building footprints, land use, waterways and green space from OSM for a
>   600 m radius
> - Render: the ring and all arms, arms labelled with street names and clockwise
>   index, constraint layers beneath
> - Produce an interactive `folium` HTML and a print-quality matplotlib PDF with
>   north arrow, scale bar and legend
> - Add a metadata block: CRS, sources, generation date, arm count, movement count,
>   ring radius, and the weaving length table from Session 2
>
> **Success:** a PDF in `out/` that reads as a professional deliverable. All arms
> labelled and legible. The weaving-length table is on the sheet — it is the first
> quantitative finding in the whole project and it costs nothing to produce.

---

# What changes later (Sessions 5–8)

Not needed yet, but worth knowing so nothing surprises you:

- **Zone counting gets simpler, not harder.** Entry zone on each approach before the
  give-way line, exit zone on each exit. No need to trace the circulating path — the
  entry/exit pair fully determines the movement.
- **One extra measurement:** a zone on each circulatory arc between adjacent arms,
  giving circulating flow. Roundabout entry capacity depends on it, so it is not
  optional.
- **Capacity method** is IRC:65 weaving and Indo-HCM roundabout gap acceptance.
  No signal timing, no saturation flow, no cycle length.
- **U-turn volumes may be substantial.** U-turns are trivially easy at a roundabout
  compared with a divided carriageway, so do not assume they are negligible.
