# Jaipur Corridor Study — End-to-End Methodology
### From AutoCAD sheets to classified turning movement counts to a calibrated simulation model

**Scope:** Full corridor study — geometry extraction, movement definition, primary data collection, automated counting, capacity analysis, simulation.

**Assumptions stated up front (correct me where wrong):**
1. The corridor is an urban arterial in Jaipur with signalised and unsignalised at-grade junctions.
2. CAD sheets are JDA/PWD survey or town-planning drawings, likely 2D, possibly unreferenced.
3. No existing traffic data — all primary collection.
4. Left-hand traffic (India), mixed heterogeneous flow, weak lane discipline.
5. Design horizon 20 years, standard for elevated corridor justification.

---

# PHASE 0 — Coordinate System Discovery

You don't know the CRS. This is the single highest-risk unknown in the project: **every downstream metre depends on getting it right.** Solve it before anything else.

## 0.1 Diagnose by coordinate magnitude

Open the DXF and look at the raw extents. The magnitude tells you almost everything.

| Observed X, Y | Almost certainly | EPSG |
|---|---|---|
| `75.78, 26.91` | WGS84 geographic (degrees) | 4326 |
| `578000, 2976000` | UTM Zone 43N | 32643 |
| `2900000, 950000` | Kalianpur 1975 / India Zone IIA (metres) | 24378 |
| `1150000, 780000` (odd origin) | Local JDA / municipal grid | none — needs fitting |
| `0–5000, 0–5000` | **Drawing-local / paper space — no georeference at all** | none — needs fitting |
| Anything × 3.28 off | Values are in **feet**, not metres | — |

**Jaipur reference values — memorise these as your sanity check:**
- WGS84: `26.9124° N, 75.7873° E`
- UTM 43N (EPSG:32643): `E ≈ 578,000 m, N ≈ 2,976,000 m`
- UTM zone for all of Jaipur district: **43N**, central meridian 75° E
- Indian Grid zone for Rajasthan: **India Zone IIA** (EPSG:24378, Kalianpur 1975 datum)

> The single most common failure: a JDA sheet in a local grid gets assumed to be UTM, and the whole corridor lands 400 km into the Arabian Sea. Always plot one test point on satellite imagery before proceeding.

## 0.2 Diagnostic script

```python
"""
crs_probe.py — Determine what coordinate system a DXF is in.
Run this FIRST on every sheet you receive.
"""
import ezdxf
import numpy as np

def probe_dxf(path):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()

    # Collect every vertex from every geometric entity in modelspace
    pts = []
    for e in msp:
        t = e.dxftype()
        if t == "LINE":
            pts.append((e.dxf.start.x, e.dxf.start.y))
            pts.append((e.dxf.end.x, e.dxf.end.y))
        elif t == "LWPOLYLINE":
            pts.extend([(p[0], p[1]) for p in e.get_points("xy")])
        elif t == "POLYLINE":
            pts.extend([(v.dxf.location.x, v.dxf.location.y) for v in e.vertices])
        elif t in ("CIRCLE", "ARC"):
            pts.append((e.dxf.center.x, e.dxf.center.y))

    if not pts:
        raise ValueError("No geometry found — is the drawing all in blocks or paper space?")

    a = np.array(pts)
    xmin, ymin = a.min(axis=0)
    xmax, ymax = a.max(axis=0)

    print(f"DXF version : {doc.dxfversion}")
    # $INSUNITS: 0=unitless 1=inches 2=feet 4=mm 5=cm 6=metres
    print(f"$INSUNITS   : {doc.header.get('$INSUNITS', 'not set')}")
    print(f"X range     : {xmin:,.2f}  ->  {xmax:,.2f}   (span {xmax-xmin:,.2f})")
    print(f"Y range     : {ymin:,.2f}  ->  {ymax:,.2f}   (span {ymax-ymin:,.2f})")
    print(f"Vertices    : {len(a):,}")

    # Heuristic classification
    if 60 < xmin < 100 and 5 < ymin < 40:
        print(">>> WGS84 geographic degrees (EPSG:4326)")
    elif 100_000 < xmin < 1_000_000 and 2_000_000 < ymin < 4_000_000:
        print(">>> Projected UTM-like. For Jaipur this is EPSG:32643 (UTM 43N).")
    elif xmax - xmin < 20_000 and xmin < 50_000:
        print(">>> Drawing-local / unreferenced. Needs GCP fitting (Phase 0.3).")
    else:
        print(">>> Unrecognised — likely a local municipal grid. Needs GCP fitting.")

    # Unit check: a real corridor is kilometres long. If the span is ~3.28x
    # what you expect in metres, the drawing is in feet.
    print(f"\nSpan sanity: if this corridor is ~5 km, expect span ~5000 (m) "
          f"or ~16400 (ft). Observed: {max(xmax-xmin, ymax-ymin):,.0f}")

if __name__ == "__main__":
    probe_dxf("corridor_sheet_01.dxf")
```

**Verify:** the reported span must match the real-world corridor length you know. If your corridor is 5 km and the span reads 5,000 → metres. If it reads 16,400 → feet. If it reads 5,000,000 → millimetres.

## 0.3 Georeferencing an unreferenced drawing (Ground Control Points)

When the CAD has no CRS — which is the likely case for JDA sheets — you fit a transform from drawing coordinates to real-world coordinates using **Ground Control Points**.

**Choosing GCPs — this determines your accuracy:**
- Pick **sharp, permanent, unambiguous** features: building corners, road intersection kerb corners, bridge abutment ends, boundary wall corners, culvert headwalls.
- **Never** use tree canopies, painted road markings, parked vehicles, or anything that has moved since the survey.
- Spread them across the **full extent** of the drawing — corners and centre, not clustered. Clustered GCPs give a transform that's excellent locally and wildly wrong at the edges.
- Minimum 4. Use 6–8 so you can compute residuals and drop bad ones.
- Get real-world coordinates from: **Bhuvan** (ISRO, free, Indian imagery, good for this), Google Earth Pro (right-click → copy coordinates), or a handheld GNSS if you can site-visit.

**Which transform to fit:**

| Transform | DOF | Use when |
|---|---|---|
| **Similarity (Helmert)** | 4 — rotation, uniform scale, 2× translation | **Default.** Survey-grade CAD. Preserves shape and angles. |
| Affine | 6 — adds shear + non-uniform scale | Only if the drawing was distorted (scanned/stretched). Shear will silently absorb your errors and hide a bad fit. |
| Polynomial / TPS | many | Never for vector CAD. Only for warped scanned rasters. |

**Use Similarity by default.** If similarity gives a bad fit but affine looks great, that's not a win — it means shear is masking a systematic problem (wrong GCP identification, or the drawing genuinely being in a different projection).

```python
"""
georeference.py — Fit CAD drawing coordinates to UTM 43N using GCPs.
Fit in a PROJECTED system (metres), never in lat/long degrees —
degrees are not uniformly scaled and a similarity fit is meaningless there.
"""
import numpy as np
import cv2
from pyproj import Transformer

# Jaipur -> UTM Zone 43N. always_xy=True means (lon, lat) input order.
TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)

# --- YOUR GCP TABLE ---------------------------------------------------------
# (cad_x, cad_y)  paired with  (longitude, latitude) read off Bhuvan/Google Earth
GCPS = [
    ((1240.55,  880.12), (75.78730, 26.91240)),
    ((4870.20, 1355.44), (75.82115, 26.91680)),
    ((2015.88, 4402.77), (75.79402, 26.94510)),
    ((5560.31, 4890.05), (75.82760, 26.94955)),
    ((3390.14, 2650.60), (75.80680, 26.92880)),
    ((880.42,  3120.95), (75.78400, 26.93330)),
]
# ----------------------------------------------------------------------------

def fit_similarity(gcps):
    """Fit a 2x3 similarity matrix mapping CAD coords -> UTM metres."""
    src = np.array([[g[0][0], g[0][1]] for g in gcps], dtype=np.float64)
    dst = np.array([TO_UTM.transform(g[1][0], g[1][1]) for g in gcps],
                   dtype=np.float64)

    # estimateAffinePartial2D fits rotation + UNIFORM scale + translation.
    # method=cv2.LMEDS is robust to one or two badly-identified GCPs.
    M, inliers = cv2.estimateAffinePartial2D(src, dst, method=cv2.LMEDS)
    if M is None:
        raise RuntimeError("Fit failed — check that GCP pairs are correctly ordered.")

    # Residuals: how far each GCP lands from where it should
    src_h = np.hstack([src, np.ones((len(src), 1))])
    pred = src_h @ M.T
    resid = np.linalg.norm(pred - dst, axis=1)

    # Recover the implied scale and rotation as a sanity check
    scale = np.hypot(M[0, 0], M[0, 1])
    rot_deg = np.degrees(np.arctan2(M[1, 0], M[0, 0]))

    print(f"Implied scale    : {scale:.6f}  (CAD units per metre)")
    print(f"Implied rotation : {rot_deg:+.4f}°")
    print(f"RMSE             : {np.sqrt((resid**2).mean()):.3f} m")
    print(f"Max residual     : {resid.max():.3f} m")
    for i, r in enumerate(resid):
        flag = "  <-- DROP THIS ONE" if r > 3 * np.median(resid) else ""
        print(f"  GCP {i}: {r:6.3f} m{flag}")
    return M

def apply(M, xy):
    """Transform an (N,2) array of CAD coords to UTM 43N metres."""
    xy = np.asarray(xy, dtype=np.float64)
    return np.hstack([xy, np.ones((len(xy), 1))]) @ M.T

if __name__ == "__main__":
    M = fit_similarity(GCPS)
    np.save("cad_to_utm43n.npy", M)   # reuse for every sheet in the same drawing set
```

**Acceptance criteria — do not proceed past this gate:**

| RMSE | Verdict |
|---|---|
| < 1.0 m | Survey-grade. Proceed. |
| 1.0 – 3.0 m | Acceptable for planning-level corridor work. Proceed, document it. |
| 3.0 – 10 m | Marginal. Re-check GCP identification before proceeding. |
| > 10 m | Something is structurally wrong — wrong sheet, wrong units, misordered pairs, or the drawing isn't a plan view. Stop and diagnose. |

**Also check the implied scale.** If it comes out at `1.000` your CAD is in metres. `0.3048` means feet. `0.001` means millimetres. A scale of `3.28` means you've inverted the direction. These are free diagnostics — read them.

**Verify visually, always:** export the transformed centreline to GeoJSON, drop it on satellite imagery in QGIS, and look at it. Numbers can be right and the result still wrong.

---

# PHASE 1 — DXF Ingest

## 1.1 Getting from DWG to DXF

I cannot read `.dwg` (proprietary binary). Convert first:

- **In AutoCAD:** `SAVEAS` → *AutoCAD 2018 DXF (\*.dxf)*. Choose **ASCII**, not binary.
- **Free converter:** ODA File Converter (Open Design Alliance) — batch converts folders of DWG → DXF.
- **QGIS:** can read DWG directly via the DWG/DXF import if built with ODA support.

Ask JDA for DXF explicitly when you request the sheets. Also ask for:
- The **survey report** — it names the datum and projection, solving Phase 0 outright
- The **benchmark / control point schedule** — gives you ready-made GCPs with real coordinates
- The **layer legend** — saves hours of guessing

## 1.2 Inventory the layers before parsing anything

Never assume layer names. Indian road sheets vary wildly between consultants.

```python
"""
layer_inventory.py — What's actually in this drawing?
Always run this before writing any extraction logic.
"""
import ezdxf
from collections import Counter

doc = ezdxf.readfile("corridor_sheet_01.dxf")
msp = doc.modelspace()

counts = Counter((e.dxf.layer, e.dxftype()) for e in msp)

print(f"{'LAYER':<32} {'TYPE':<14} {'COUNT':>7}")
print("-" * 56)
for (layer, etype), n in sorted(counts.items(), key=lambda kv: -kv[1]):
    print(f"{layer:<32} {etype:<14} {n:>7,}")

print(f"\nTotal layers: {len({l for l, _ in counts})}")
print("Layers defined in table (incl. empty):")
for lyr in doc.layers:
    print(f"  {lyr.dxf.name:<32} color={lyr.dxf.color:<4} "
          f"{'FROZEN' if lyr.is_frozen() else ''} {'OFF' if lyr.is_off() else ''}")
```

**Layer names you'll typically hit on JDA/PWD road sheets:**

| Likely name | Contains | Need it? |
|---|---|---|
| `CL`, `CENTRELINE`, `C_L`, `ROAD_CL` | Road centreline | **Critical** |
| `KERB`, `CURB`, `EDGE`, `ROAD_EDGE` | Carriageway edges | **Critical** — gives width |
| `MEDIAN`, `DIVIDER`, `CENTRAL_VERGE` | Median | **Critical** — gaps = U-turns |
| `ROW`, `BOUNDARY`, `ROAD_BOUNDARY` | Right of way | Critical for corridor feasibility |
| `EXISTING`, `PROPOSED` | Scheme state | Yes — separate them |
| `BUILDING`, `STRUCTURE`, `PLOT` | Frontage | Yes — constraint atlas |
| `UTIL_*`, `SEWER`, `WATER`, `HT_LINE`, `OFC` | Buried/overhead services | **Yes — these kill elevated pier locations** |
| `TREE`, `PLANTATION` | Trees | Yes — felling permissions |
| `TEXT`, `MTEXT`, `DIM`, `HATCH`, `GRID` | Annotation | Usually skip, but chainages live here |
| `DEFPOINTS` | AutoCAD internal | Always skip |

## 1.3 Extraction, with the traps handled

Four things break naive DXF parsers. Handle all of them:

1. **Curves aren't polylines.** `ARC`, `SPLINE`, `ELLIPSE` must be flattened to vertex chains.
2. **Blocks hide geometry.** An `INSERT` entity is a reference — its contents live in the block table and carry a transform (position, scale, rotation). Naive parsers see zero geometry in block-heavy drawings.
3. **Bulge in LWPOLYLINE.** A polyline vertex can carry a bulge factor making that segment an arc. Ignoring it straightens curves.
4. **Z is not always zero.** Road sheets may carry levels. For an *elevated* corridor this matters enormously — see Phase 2.3.

```python
"""
extract_geometry.py — DXF -> shapely LineStrings in UTM 43N.
Handles blocks, curves, and bulges.
"""
import ezdxf
from ezdxf import path as ezpath
from shapely.geometry import LineString
import numpy as np

FLATTEN_TOL = 0.05      # metres of sagitta error allowed when flattening curves

def entity_to_coords(e):
    """
    Convert any geometric DXF entity to a list of (x, y, z) vertices.
    ezdxf's path module handles ARC/SPLINE/ELLIPSE/bulges uniformly.
    Returns None for entities with no path representation (TEXT, POINT, ...).
    """
    try:
        p = ezpath.make_path(e)
    except (TypeError, ValueError):
        return None
    pts = [(v.x, v.y, v.z) for v in p.flattening(distance=FLATTEN_TOL)]
    return pts if len(pts) >= 2 else None

def extract(dxf_path, layers, M=None):
    """
    layers : set of layer names to pull
    M      : 2x3 CAD->UTM matrix from Phase 0, or None if already georeferenced
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    out = []

    # virtual_entities() explodes INSERTs, applying the block's
    # position/scale/rotation transform. Without this you lose block geometry.
    def walk(container):
        for e in container:
            if e.dxftype() == "INSERT":
                yield from walk(e.virtual_entities())
            else:
                yield e

    for e in walk(msp):
        # ERRATUM: entities inside a block usually sit on layer "0" and inherit the
        # INSERT's layer at draw time. Filtering on e.dxf.layer here therefore drops
        # exactly the block geometry that walk() exists to recover. Carry the parent
        # INSERT's layer down through walk() and test against that instead.
        if e.dxf.layer not in layers:
            continue
        pts = entity_to_coords(e)
        if pts is None:
            continue

        xy = np.array([(p[0], p[1]) for p in pts])
        z = np.array([p[2] for p in pts])

        if M is not None:
            xy = np.hstack([xy, np.ones((len(xy), 1))]) @ M.T

        out.append({
            "geom": LineString(xy),
            "layer": e.dxf.layer,
            "dxftype": e.dxftype(),
            "z_mean": float(z.mean()),
            "handle": e.dxf.handle,     # keeps traceability back to the CAD entity
        })
    return out

if __name__ == "__main__":
    M = np.load("cad_to_utm43n.npy")
    feats = extract("corridor_sheet_01.dxf", {"CL", "CENTRELINE"}, M)
    print(f"{len(feats)} centreline features, "
          f"total length {sum(f['geom'].length for f in feats):,.1f} m")
```

**Verify:** total centreline length should roughly match the known corridor length. If it's 3× too long, you're picking up duplicated layers or both carriageways. If it's a fraction, you're missing block geometry.

---

# PHASE 2 — Building Network Topology

**This is the conceptual heart of the CAD half of the project, and where most people fail.**

A CAD drawing contains *dumb geometry*. Two lines crossing on screen are just two lines — the drawing has no idea they form a junction. There is no connectivity, no direction of travel, no notion that turning from one onto the other is possible. A traffic model needs a **graph**: nodes (junctions) and directed edges (links) that know how they connect.

Converting one into the other is called **noding**.

## 2.1 The noding pipeline

```
raw CAD linework
   ↓  1. filter to centrelines only
   ↓  2. snap near-coincident endpoints (CAD has gaps)
   ↓  3. split every line at every intersection
   ↓  4. merge collinear fragments back into maximal links
   ↓  5. build a directed graph
   ↓  6. classify nodes by degree
noded network graph
```

```python
"""
build_topology.py — CAD centrelines -> a routable network graph.
"""
from shapely.geometry import LineString, Point, MultiLineString
from shapely.ops import unary_union, linemerge, snap
import networkx as nx

SNAP_TOL = 1.0   # metres. CAD centrelines rarely meet exactly.

def build_network(centrelines):
    """centrelines: list of shapely LineStrings, in metres."""

    # --- Step 1: snap endpoints that are close but not coincident -----------
    # CAD drawings routinely have 5-50 cm gaps at junctions. Without snapping,
    # unary_union won't node them and you get a disconnected network.
    merged = unary_union(centrelines)
    snapped = snap(merged, merged, SNAP_TOL)   # <-- see ERRATUM below

    # --- Step 2: node at all intersections ---------------------------------
    # unary_union on a collection of lines splits every line wherever it
    # crosses another. This is the actual noding operation.
    noded = unary_union(snapped)

    # --- Step 3: merge collinear fragments ---------------------------------
    # Noding over-fragments. linemerge recombines runs that pass through
    # degree-2 points into single links.
    links = linemerge(noded)
    links = list(links.geoms) if isinstance(links, MultiLineString) else [links]

    # --- Step 4: build the graph -------------------------------------------
    G = nx.MultiDiGraph()

    def node_id(pt):
        # Round to centimetre so float noise doesn't create duplicate nodes
        return (round(pt[0], 2), round(pt[1], 2))

    for ls in links:
        coords = list(ls.coords)
        u, v = node_id(coords[0]), node_id(coords[-1])
        if u == v:
            continue                      # degenerate loop, discard
        G.add_node(u, x=u[0], y=u[1])
        G.add_node(v, x=v[0], y=v[1])
        # Two directed edges — a two-way road. Adjust for one-ways in Phase 2.4.
        G.add_edge(u, v, geometry=ls, length=ls.length, direction="fwd")
        G.add_edge(v, u, geometry=LineString(coords[::-1]),
                   length=ls.length, direction="rev")
    return G

def classify_nodes(G):
    """Degree in the UNDIRECTED sense tells you what kind of node this is."""
    U = G.to_undirected()
    kinds = {}
    for n in G.nodes:
        deg = len(set(U.neighbors(n)))    # distinct neighbours, not parallel edges
        kinds[n] = {
            1: "terminus",       # corridor end or dangling stub (check these!)
            2: "midblock",       # not a junction — just a geometry break
            3: "T_junction",
            4: "cross_junction",
        }.get(deg, "complex_junction")    # 5+ legs — common in old Jaipur
        G.nodes[n]["kind"] = kinds[n]
        G.nodes[n]["degree"] = deg
    return G
```

> **ERRATUM — `snap(merged, merged, tol)` snaps a geometry to itself.** That is close
> to a no-op: it cannot pull the endpoint of line A onto line B, which is the entire
> reason snapping appears in this pipeline. The gaps stay open and the network
> fragments, exactly the failure the step exists to prevent.
>
> Use GEOS precision reduction, which nodes and snaps in one pass:
>
> ```python
> import shapely
>
> def node_lines(centrelines, tol=SNAP_TOL):
>     merged = unary_union(centrelines)
>     # set_precision snaps every vertex to a grid of size `tol` and re-nodes,
>     # which closes sub-tolerance gaps between *different* lines.
>     return shapely.node(shapely.set_precision(merged, tol))
> ```

**Tuning `SNAP_TOL` — this is a real judgement call:**
- **Too small (0.1 m):** junctions stay disconnected, your network fragments, routing fails.
- **Too large (5 m):** distinct nodes merge. A staggered T-junction — extremely common in Jaipur where two side roads meet an arterial 15 m apart — collapses into a single crossroads, and you lose the entire reason the junction behaves badly.
- **Start at 1.0 m.** Then inspect: count nodes at each tolerance and look for the value where the count stabilises. Sudden drops mean you're over-merging.

**Verify:** the node count should be close to the number of junctions you can count by eye on satellite imagery. Every `terminus` node in the middle of the corridor is a bug — it means a gap that snapping missed.

## 2.2 Extracting lane counts and carriageway width

The centreline tells you where the road is. The kerb lines tell you how big it is.

```python
"""
For each link, measure carriageway width by casting perpendicular
transects from the centreline to the nearest kerb on each side.
"""
import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points

def measure_width(centreline, kerbs_union, n_samples=20, probe=40.0):
    """
    Returns median carriageway width in metres.
    probe: how far to cast the transect — must exceed the widest expected road.
    """
    widths = []
    for s in np.linspace(0.05, 0.95, n_samples):
        pt = centreline.interpolate(s, normalized=True)
        # local heading, then its perpendicular
        ahead = centreline.interpolate(min(s + 0.01, 1.0), normalized=True)
        dx, dy = ahead.x - pt.x, ahead.y - pt.y
        norm = np.hypot(dx, dy)
        if norm == 0:
            continue
        px, py = -dy / norm, dx / norm     # unit perpendicular

        hits = []
        for sign in (1, -1):
            ray = LineString([(pt.x, pt.y),
                              (pt.x + sign * px * probe, pt.y + sign * py * probe)])
            inter = ray.intersection(kerbs_union)
            if inter.is_empty:
                continue
            # nearest intersection point to the centreline
            near = nearest_points(pt, inter)[1]
            hits.append(pt.distance(near))
        if len(hits) == 2:
            widths.append(sum(hits))
    return float(np.median(widths)) if widths else None

def lanes_from_width(width_m, divided):
    """
    IRC lane widths for urban roads:
      3.5 m standard lane; 3.0 m acceptable in constrained urban sections.
    Subtract shoulder/kerb shy distance before dividing.
    """
    if width_m is None:
        return None
    usable = width_m - 1.0            # kerb shy distance both sides
    per_dir = usable / (2 if divided else 1)
    return max(1, round(per_dir / 3.5))
```

> **ERRATUM — the divided/undivided test is inverted.** `measure_width` casts its
> transects from **one** centreline. On a divided road OSM and CAD both carry one
> centreline *per carriageway*, so the measured width already describes a single
> direction and must not be halved. On an undivided road the one measured width
> carries both directions and must be. The correct line is:
>
> ```python
> per_dir = usable if divided else usable / 2
> ```
>
> As written, a divided arterial reports half its real lane count and an undivided
> road reports double.

**Caveat, and state it in your report:** width-derived lane counts are an *estimate*. In Jaipur, marked lanes and used lanes diverge sharply — a 10.5 m carriageway nominally carries 3 lanes but in practice carries 4–5 streams of mixed traffic. Validate against video (Phase 6) and report the *observed* stream count, not just the geometric one. This is exactly why the sublane simulation model in Phase 8 matters.

## 2.3 Grade separation — critical for your project specifically

`unary_union` splits lines wherever they cross **in plan**. But a flyover crossing a road below does *not* form a junction. If you node it naively, your model will let vehicles turn off the flyover onto the road beneath it.

For an elevated corridor study this is not an edge case — it's the entire subject matter.

**Handle it by:**
1. Reading the Z values from Phase 1 (`z_mean`) and refusing to node where the vertical separation exceeds ~3 m.
2. Where the CAD is flat 2D, using **layer names** as the level signal (`FLYOVER`, `EL_CORRIDOR`, `ROB`, `UNDERPASS`, `EXISTING_GRADE`).
3. Failing both, tagging crossings manually. There won't be many.

```python
def should_node(feat_a, feat_b, z_tol=3.0):
    """Two crossing centrelines form a real junction only if at the same level."""
    ELEVATED = {"FLYOVER", "EL_CORRIDOR", "ROB", "RUB", "UNDERPASS", "VUP"}
    if (feat_a["layer"] in ELEVATED) != (feat_b["layer"] in ELEVATED):
        return False                                    # different levels
    return abs(feat_a["z_mean"] - feat_b["z_mean"]) < z_tol
```

**Verify:** every grade-separated crossing you know exists on the corridor should appear as two *unconnected* edges. Check each one by hand — there are typically only a handful and getting one wrong invalidates the model.

## 2.4 One-way and restricted links

Jaipur's walled city and several arterial sections operate one-way, some of them time-varying. The CAD will not tell you this. Sources:
- Jaipur Traffic Police notifications
- Site observation during the Phase 5 survey (record it explicitly on the field form)
- OpenStreetMap `oneway=yes` tags as a first draft — **verify, don't trust**

Store as an edge attribute and drop the reverse edge where it applies.

---

# PHASE 3 — Movement Definition

Now the part you specifically asked about: **who can go left, right, straight, U-turn, and how.**

## 3.1 The geometry of a turning movement

At a junction node with *n* legs, a **movement** is an ordered pair (approach leg → exit leg). A 4-arm junction has 4 approaches × 4 exits = 16 pairs, of which 4 are U-turns, giving the familiar **12 through/left/right movements plus 4 U-turns**.

Classify each pair by the **turn angle**:

- `θ_in` = compass bearing of travel *into* the node, taken from the last two vertices of the approach link
- `θ_out` = compass bearing of travel *out of* the node, from the first two vertices of the exit link
- `Δ = normalise(θ_out − θ_in)` into the range (−180°, +180°]

**India (drive on left) classification:**

| Δ (degrees) | Movement | Code | Character |
|---|---|---|---|
| −45 to +45 | **Through** | T | Straight across |
| −135 ≤ Δ < −45 | **Left turn** | L | *Near-side* turn. No conflict with opposing flow. Often free/uncontrolled. |
| +45 < Δ ≤ +135 | **Right turn** | R | *Far-side* turn. **Crosses opposing traffic** — the critical, conflicting movement. |
| \|Δ\| > 135 | **U-turn** | U | Requires a median opening |

> **Left and right are opposite to US/EU practice.** In India the *right* turn is the difficult, conflicting, capacity-limiting one — it's what needs a protected phase, a dedicated pocket, or grade separation. If you carry over a US methodology unmodified, you will optimise the wrong movement.

```python
"""
movements.py — Enumerate and classify every turning movement at every junction.
"""
import math
from itertools import permutations

def bearing(p1, p2):
    """Compass bearing p1->p2 in degrees. 0=North, 90=East, clockwise."""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    return math.degrees(math.atan2(dx, dy)) % 360

def turn_delta(theta_in, theta_out):
    """Signed turn angle in (-180, 180]. Negative = left, positive = right."""
    return ((theta_out - theta_in + 180) % 360) - 180

def classify_turn(delta):
    """India / left-hand traffic."""
    if abs(delta) <= 45:
        return "THROUGH"
    if -135 <= delta < -45:
        return "LEFT"
    if 45 < delta <= 135:
        return "RIGHT"
    return "UTURN"

def approach_bearing(G, u, v):
    """Bearing of travel arriving at node v along edge u->v."""
    coords = list(G[u][v][0]["geometry"].coords)
    return bearing(coords[-2], coords[-1])

def exit_bearing(G, v, w):
    """Bearing of travel departing node v along edge v->w."""
    coords = list(G[v][w][0]["geometry"].coords)
    return bearing(coords[0], coords[1])

DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

def compass_octant(bearing_deg):
    return DIRS[int(((bearing_deg + 22.5) % 360) // 45)]

def enumerate_movements(G, node):
    """
    Return every (approach, exit) movement at `node`, classified.
    Movement code follows standard TMC notation: NBL = northbound left, etc.
    'Northbound' = the direction the vehicle is TRAVELLING, not where it came from.
    """
    preds = [u for u in G.predecessors(node)]
    succs = [w for w in G.successors(node)]
    out = []

    for u in preds:
        th_in = approach_bearing(G, u, node)
        travel_dir = compass_octant(th_in)          # NB / SB / EB / WB ...
        for w in succs:
            th_out = exit_bearing(G, node, w)
            d = turn_delta(th_in, th_out)
            kind = classify_turn(d)

            # A "U-turn" back onto the same physical link is the real U-turn.
            # A 170-degree turn onto a DIFFERENT link is a sharp turn, not a U-turn.
            if kind == "UTURN" and u != w:
                kind = "LEFT" if d < 0 else "RIGHT"

            out.append({
                "node": node,
                "from_leg": u,
                "to_leg": w,
                "bearing_in": round(th_in, 1),
                "bearing_out": round(th_out, 1),
                "delta": round(d, 1),
                "movement": kind,
                "code": f"{travel_dir}B{kind[0]}",   # e.g. NBL, EBT, SBR, WBU
                "permitted": None,                   # filled in by Phase 3.2
            })
    return out
```

**Verify:** at a clean 4-arm crossroads you should get exactly 16 movements — 4 T, 4 L, 4 R, 4 U. If you get 12, your U-turn edges are missing. If you get 20+, you have duplicate parallel edges from bad noding — go back to Phase 2.

## 3.2 Permitted vs prohibited — reading restrictions off the CAD

Geometry says a movement is *possible*. Signage, medians and channelisers say whether it's *allowed*. The CAD encodes more of this than people realise.

| Restriction | CAD evidence | Detection |
|---|---|---|
| **U-turn allowed** | Gap in the `MEDIAN` polyline | Find discontinuities in the median linework within ~50 m of the node. No gap → no U-turn. |
| **Free left turn** | Short curved link + triangular channeliser island bypassing the node | A curved edge connecting two legs whose length is far shorter than going via the node centre |
| **Right turn banned** | No median opening on the approach; or a `SIGN`/`TEXT` layer entity reading "NO RIGHT TURN" | Median continuity + text search |
| **Right-turn pocket** | Median tapers, carriageway locally widens | Width measurement (2.2) shows a local bulge near the node |
| **One-way** | Arrow blocks on a `TRAFFIC`/`SIGN` layer | Block name inspection — often unreliable, verify on site |

```python
def uturn_permitted(node_pt, median_geoms, search_r=50.0, min_gap=4.0):
    """
    A U-turn needs a physical opening in the median.
    Look for a discontinuity of at least min_gap metres within search_r of the node.
    Typical Indian median openings are 8-15 m; below ~4 m nothing can turn.
    """
    from shapely.geometry import Point
    from shapely.ops import unary_union
    area = Point(node_pt).buffer(search_r)
    local = unary_union([g for g in median_geoms if g.intersects(area)])
    if local.is_empty:
        return True          # no median at all -> undivided road, U-turn possible
    clipped = local.intersection(area)
    pieces = list(clipped.geoms) if hasattr(clipped, "geoms") else [clipped]
    if len(pieces) < 2:
        return False         # continuous median, no opening
    # measure the largest gap between consecutive median pieces
    gaps = [pieces[i].distance(pieces[j])
            for i in range(len(pieces)) for j in range(i + 1, len(pieces))]
    return max(gaps) >= min_gap
```

> **ERRATUM — `max()` over all pairs is the wrong statistic.** The docstring says
> "largest gap between *consecutive* median pieces", but the code takes the maximum
> over *every* pair. With three or more median fragments that returns the distance
> between the two furthest-apart pieces, not the size of any opening, so the function
> reports "U-turn permitted" almost unconditionally.
>
> Order the pieces along the median and measure only adjacent gaps:
>
> ```python
> ref = local if local.geom_type == "LineString" else max(local.geoms, key=lambda g: g.length)
> pieces.sort(key=lambda g: ref.project(g.centroid))
> gaps = [pieces[i].distance(pieces[i + 1]) for i in range(len(pieces) - 1)]
> return max(gaps, default=0.0) >= min_gap
> ```

**Reality check:** whatever the CAD says, **verify every restriction on site during the Phase 5 survey.** Signage changes, medians get broken open informally, and enforcement varies by time of day. The CAD gives you a hypothesis; the field visit confirms it. Build a "restriction verification" column into your field form.

## 3.3 The movements the CAD will never show you

You mentioned reversing. Reversing isn't a turning movement — it's a *manoeuvre*, and it belongs to a category of behaviour that dominates Indian junction performance but appears in no drawing and in no standard TMC form:

| Irregular manoeuvre | Why it matters | How to capture |
|---|---|---|
| **Wrong-way / contraflow** | Endemic on Jaipur arterials, especially 2W and auto near median openings. Consumes capacity and creates conflicts. | Trajectory heading opposes link bearing by >150° for a sustained run |
| **Kerbside stopping** — autos, buses, e-rickshaws picking up | Blocks the near-side lane. Frequently the *actual* cause of a bottleneck. | Track velocity → near-zero within the kerb buffer |
| **Reversing** out of frontage plots / parking | Blocks a lane briefly but repeatedly | Sustained negative velocity along the link axis |
| **Straddling / lane-sharing by 2W** | Why lane-based capacity models fail in India | Lateral occupancy analysis; feeds the sublane model in Phase 8 |
| **Pedestrian crossing mid-block** | Forces braking waves | Person-class tracks crossing the carriageway polygon |

**Recommendation:** log these as a separate `irregular_manoeuvres` table, counted per hour per junction. Do not fold them into the TMC — that corrupts the count. Instead use them as *evidence*: "the northbound approach loses an effective 0.8 lanes for 40% of the peak hour to kerbside auto stopping" is a far stronger argument for grade separation than a raw volume number.

```python
def detect_wrongway(track_world, link_bearing, min_pts=15, thresh=150):
    """
    track_world: list of (x, y) in metres, one per frame, from Phase 6.
    Returns True if the track sustains a heading opposing the link.
    """
    import numpy as np
    if len(track_world) < min_pts:
        return False
    a = np.array(track_world)
    headings = [bearing(a[i], a[i + 1]) for i in range(len(a) - 1)]
    opposed = [abs(turn_delta(link_bearing, h)) > thresh for h in headings]
    return sum(opposed) > 0.7 * len(opposed)
```

---

# PHASE 4 — Vehicle Classification

## 4.1 Classes and PCU factors (IRC:106-1990)

**PCU (Passenger Car Unit)** converts heterogeneous traffic into a common denominator. A bus doesn't just occupy more space than a car — it accelerates slower, needs bigger gaps, and blocks sight lines. PCU captures all of that in one number.

| # | Class | PCU (share ≤ 5%) | PCU (share ≥ 10%) | Detectable off-the-shelf? |
|---|---|---|---|---|
| 1 | Two-wheeler (motorcycle, scooter) | 0.5 | 0.75 | Yes (COCO `motorcycle`) |
| 2 | Auto-rickshaw (3W passenger) | 1.2 | 2.0 | **No — must train** |
| 3 | Car / Jeep / Van (LMV) | 1.0 | 1.0 | Yes (COCO `car`) |
| 4 | LCV (light commercial, tempo, pickup) | 1.4 | 2.0 | Partly — confused with car/truck |
| 5 | Bus | 2.2 | 3.7 | Yes (COCO `bus`) |
| 6 | Truck (2-axle) | 2.2 | 3.7 | Yes (COCO `truck`) |
| 7 | Multi-axle vehicle (3+ axle, articulated) | 3.7 | 4.0 | **No — must train** |
| 8 | Bicycle | 0.4 | 0.5 | Yes (COCO `bicycle`) |
| 9 | Cycle-rickshaw | 1.5 | 2.0 | **No — must train** |
| 10 | Tractor / tractor-trailer | 4.0 | 4.0 | **No — must train** |
| 11 | Animal-drawn cart | 4.0 | 8.0 | **No — must train** |
| 12 | **E-rickshaw** | *not in IRC:106* | — | **No — must train** |

**Two things people get wrong here — get them right and it shows:**

**(a) PCU is share-dependent, not fixed.** The two columns are not alternatives to pick between. IRC:106 gives the lower value when that class is ≤5% of the stream and the higher when it's ≥10%, and you **interpolate linearly in between**. On a Jaipur arterial where two-wheelers are 55% of traffic, you use 0.75, not 0.5. Using the wrong column changes your PCU volume by 20%+ and can flip your Level of Service grade.

```python
def pcu_factor(vehicle_class, class_share):
    """
    class_share : this class as a fraction of total vehicle count (0-1).
    Linear interpolation between the IRC:106 5% and 10% values.
    """
    TABLE = {   # class: (pcu_at_5pct, pcu_at_10pct)
        "2W":        (0.50, 0.75),
        "AUTO":      (1.20, 2.00),
        "CAR":       (1.00, 1.00),
        "LCV":       (1.40, 2.00),
        "BUS":       (2.20, 3.70),
        "TRUCK":     (2.20, 3.70),
        "MAV":       (3.70, 4.00),
        "CYCLE":     (0.40, 0.50),
        "CYCLE_RIK": (1.50, 2.00),
        "TRACTOR":   (4.00, 4.00),
        "ANIMAL":    (4.00, 8.00),
        "E_RIK":     (1.00, 1.20),   # ASSUMPTION — see note below
    }
    lo, hi = TABLE[vehicle_class]
    if class_share <= 0.05:
        return lo
    if class_share >= 0.10:
        return hi
    t = (class_share - 0.05) / 0.05
    return lo + t * (hi - lo)
```

**(b) The e-rickshaw problem.** IRC:106 dates from 1990. E-rickshaws did not exist. They are now a substantial and growing share of Jaipur's traffic, particularly on feeder routes and around markets and stations. There is **no officially notified PCU value.** 

You have three defensible options — pick one and *document it as an explicit assumption in the report*, because a reviewing engineer will ask:
1. Treat as auto-rickshaw (PCU 1.2/2.0) — conservative, defensible, simplest
2. Use CSIR-CRRI study values (~1.0–1.2) — better justified, cite the specific study
3. **Measure it yourself** from your own data using the speed-area or headway method — this is the strongest position and, for a study of this scale, worth doing

Option 3 turns a weakness into a contribution. If you derive a locally-measured e-rickshaw PCU for Jaipur, that is genuinely publishable and it makes the whole study harder to dismiss.

**Also note:** Indo-HCM (2017, CSIR-CRRI) supersedes IRC:106 for capacity analysis and uses a dynamic PCU concept that varies with traffic composition and speed. Cite Indo-HCM as primary and IRC:106 as the fallback. For a ₹5,000 crore project, using the 1990 table alone will draw criticism.

## 4.2 Detection classes for the CV model

Map the IRC classes to what your detector actually outputs. **Off-the-shelf COCO-trained YOLO covers roughly 55% of Jaipur's traffic stream and misses the auto-rickshaw and e-rickshaw entirely — which together can be 20–30% of vehicles.** Fine-tuning is mandatory, not optional.

**Training data options, best first:**
1. **IDD (India Driving Dataset)** — IIIT Hyderabad. Indian road scenes, includes autorickshaw as a class. Free for research. Start here.
2. **Self-annotation** — extract ~2,000 frames from your own junction video, annotate in CVAT or Roboflow. ~15–20 hours of work. **Highest accuracy** because it matches your exact camera angle, height, and lighting.
3. Public traffic datasets from similar contexts (Bangladeshi/Sri Lankan sets have overlapping vehicle types).

**Practical recipe:** fine-tune YOLOv8m or YOLO11m starting from COCO weights on IDD, then fine-tune again on ~500 of your own annotated frames. The second stage is what takes you from "works okay" to "works on this junction."

**Target performance before you trust the counts:** mAP@0.5 ≥ 0.80 overall, and ≥ 0.70 for every individual class. Two-wheelers in dense clusters are your hardest case — they occlude each other heavily and travel in packs. Check that class specifically.

---

# PHASE 5 — Primary Data Collection Plan

You have no data. This phase is the one that costs money and time, so design it once and correctly.

## 5.1 Survey inventory

| Survey | Where | Duration | Standard |
|---|---|---|---|
| **Classified Turning Movement Count (TMC)** | Every junction on the corridor | 16 h (06:00–22:00) × 3 days | IRC:SP:41, IRC:102 |
| **Mid-block classified volume count** | Every link between junctions | 24 h × 3 days (7 preferred) | IRC:SP:19 |
| **Speed & delay (moving car method)** | Full corridor, both directions | 6 runs per direction per peak | IRC:SP:41 |
| **Queue length** | Signalised approaches | Peak hours, per cycle | Indo-HCM |
| **Origin–Destination** | Corridor screenlines | 12 h, 1 day | IRC:102 |
| **Pedestrian count & crossing behaviour** | All junctions + mid-block crossings | 16 h, 1 day | IRC:103 |
| **Parking & kerbside inventory** | Full corridor | 12 h, 1 day | IRC:SP:12 |
| **Junction geometric inventory** | Every junction | One pass | — |
| **Public transport boarding/alighting** | Bus stops on corridor | Peak periods | — |

For an elevated corridor specifically, **pedestrian counts and kerbside activity carry unusual weight** — they establish the at-grade impact of the scheme, which is where objections come from and where the environmental clearance scrutiny lands.

## 5.2 When to survey — Jaipur-specific

**3 days minimum:** one typical weekday (**Tuesday, Wednesday or Thursday** — never Monday or Friday, which carry distorted patterns), one Saturday, one Sunday.

**Avoid entirely:**
- **Monsoon** (roughly July–September) — flow patterns are not representative
- **Festivals:** Teej, Gangaur, Diwali week, Holi, Makar Sankranti. Jaipur's festival traffic is dramatically atypical, and Teej and Gangaur processions close major roads outright.
- **Jaipur Literature Festival** period if the corridor is anywhere near the Old City / Central Jaipur
- School and university exam periods, and school holidays — both shift the peak
- Any day with a VIP movement, political rally, or scheduled road closure — check with Jaipur Traffic Police in advance
- Market days if a weekly market abuts the corridor

**Best window:** **October–November** or **February–March**. Stable weather, schools in session, no major festival cluster.

**Check before finalising dates:** call Jaipur Traffic Police control room and JDA for any planned diversions, and check the Rajasthan government holiday calendar.

## 5.3 Video-based collection — the recommended approach

Manual counting of 16 hours × 12 movements × 12 vehicle classes at each junction is enormously labour-intensive and error-prone. Video gives you a permanent, re-analysable, auditable record. **This is the right choice for a corridor study of this size.**

**Camera placement:**
- **Height 8–12 m minimum.** Below 8 m, vehicles occlude each other badly and turning paths become ambiguous. Rooftops of adjacent buildings are ideal — negotiate access in advance.
- **All four approaches in frame** if possible from one elevated position; otherwise one camera per approach with synchronised clocks.
- **Sun angle:** avoid pointing east in the morning or west in the evening. Lens flare destroys detection for the exact hours you care about.
- **Resolution:** 1080p minimum, **4K strongly preferred** — two-wheeler and auto-rickshaw discrimination at the far side of a wide junction needs the pixels.
- **Frame rate:** 25–30 fps. Below 15 fps, tracking fails on fast two-wheelers.
- **Power and storage:** 16 hours × 4K is substantial. Plan battery/mains and card capacity. Test the full duration before survey day.

**Drone use — read this before planning any aerial work:**
- India requires **DGCA compliance** via the **Digital Sky** platform: drone registration (UIN), Remote Pilot Certificate, and airspace zone check.
- **Jaipur has significant restricted airspace.** Jaipur International Airport (Sanganer) generates a red zone. Areas around government buildings, and the Amber Fort / heritage zone, carry additional restrictions.
- **Check the Digital Sky airspace map for your exact corridor before assuming drone survey is viable.** Green zone: fly with registration. Yellow zone: ATC permission required. Red zone: prohibited without central government clearance.
- Practical guidance: use drones for **geometric survey and orthophoto capture** (short duration, high value), and **fixed cameras for the 16-hour counts**. Battery endurance makes long-duration drone counting impractical anyway.

**Ground Control Points for the video — the step that connects everything:**

Before recording, mark and survey **4–8 points visible in the camera frame** whose positions you also know in the CAD. Kerb corners, manhole covers, median nose tips, signal pole bases. These give you the homography in Phase 6. **You cannot add these afterwards** — if you finish the survey without them you must re-visit the site.

This is the single step that makes the CAD half and the counting half into one system instead of two disconnected exercises. Do not skip it.

## 5.4 Manual counting as ground truth

Even with full video automation, run manual counts on **2 × 15-minute samples per junction** — one in peak, one in off-peak. These are not redundant. They are how you prove your automated pipeline is accurate, and how you answer the reviewer who asks whether the numbers can be trusted.

**Field form structure** (one sheet per 15-min interval per approach):

```
Junction: __________  Approach: ____  Date: ______  Interval: __:__ – __:__
Enumerator: __________  Weather: ______  Incidents: ______________________

              |  LEFT  | THROUGH |  RIGHT  | U-TURN |
Two-wheeler   |        |         |         |        |
Auto-rickshaw |        |         |         |        |
E-rickshaw    |        |         |         |        |
Car/Jeep/Van  |        |         |         |        |
LCV           |        |         |         |        |
Bus           |        |         |         |        |
Truck (2-ax)  |        |         |         |        |
Multi-axle    |        |         |         |        |
Cycle         |        |         |         |        |
Cycle-rickshaw|        |         |         |        |
Tractor       |        |         |         |        |
Animal cart   |        |         |         |        |

Restrictions observed:  [ ] No right turn  [ ] No U-turn  [ ] One-way
                        [ ] Free left      [ ] Signal timing: ____ s cycle
Irregular activity:     Wrong-way count ____  Kerbside stops ____
```

## 5.5 Sample size and peak hour determination

- **Count interval: 15 minutes.** This is the standard and it is not arbitrary — you need it to compute the Peak Hour Factor.
- **Peak hour** = the four *consecutive* 15-minute intervals with the highest combined volume.
- **Peak Hour Factor (PHF)** = (hourly volume) ÷ (4 × highest single 15-min volume).
  - PHF near 1.0 → uniform flow within the hour
  - PHF of 0.85–0.92 → typical urban Indian arterial
  - PHF below 0.80 → sharply peaked; **design for the peak 15 minutes, not the hourly average**, or your junction will fail for a quarter of every hour

```python
def peak_hour(counts_15min):
    """
    counts_15min : list of (timestamp, volume) in chronological 15-min bins.
    Returns (start_index, hourly_volume, PHF).
    """
    best_i, best_v = 0, -1
    for i in range(len(counts_15min) - 3):
        v = sum(c[1] for c in counts_15min[i:i + 4])
        if v > best_v:
            best_i, best_v = i, v
    peak_15 = max(c[1] for c in counts_15min[best_i:best_i + 4])
    phf = best_v / (4 * peak_15) if peak_15 else 0
    return best_i, best_v, round(phf, 3)
```

## 5.6 Zero-budget bootstrap — build credibility before the contract

You have an active JDA opportunity and the "Corridor Constraint Atlas" identified as the credibility-establishing artifact. You do not need the full survey to produce it.

**What you can build for free, this month:**
1. **Network geometry** from OpenStreetMap — download the corridor with `osmnx`, already a topologically-correct graph
2. **A working georeference** from Bhuvan or Google satellite imagery
3. **Constraint layers** from open sources: land use, existing built-up frontage, water bodies, heritage buffers
4. **A pilot count** — one camera, one junction, one 3-hour peak period, using this exact pipeline
5. **The full methodology** — this document

That pilot count is disproportionately persuasive. A single junction with real classified turning movements, produced from your own pipeline with a validation table, demonstrates you can deliver the whole corridor. Walking in with a methodology *and* a working result is a completely different conversation from walking in with a proposal.

---

# PHASE 6 — Video to Turning Movement Counts

## 6.1 Pipeline architecture

```
video frames
   ↓  YOLO detection (fine-tuned, 12 Indian classes)
   ↓  ByteTrack multi-object tracking -> persistent track IDs
   ↓  footpoint extraction (bottom-centre of bbox)
   ↓  HOMOGRAPHY -> world coordinates in UTM 43N
   ↓  zone entry/exit test against CAD-derived approach polygons
   ↓  movement assignment (leg A -> leg C)
   ↓  15-minute × class × movement aggregation
classified TMC matrix
```

## 6.2 Homography — the bridge between CAD and video

The camera sees a perspective view. You need plan-view world coordinates. Since road surfaces are effectively planar over a junction, a single **homography matrix** maps image pixels to ground coordinates.

**Two details that determine whether this works:**

**(a) Use the bounding box footpoint, not the centroid.** The homography is only valid for points *on the ground plane*. A bbox centroid sits at roughly half the vehicle's height, so projecting it introduces an error proportional to vehicle height — which means a bus gets displaced several metres more than a motorcycle. Use the bottom-centre of the box.

**(b) Fit in world metres, using the same GCPs you surveyed in Phase 5.3.** This puts video output and CAD geometry in one coordinate system automatically.

```python
"""
homography.py — image pixels -> UTM 43N metres.
"""
import cv2
import numpy as np

# GCPs: pixel coordinates in the video frame, paired with UTM 43N metres
# (read the UTM values straight off your georeferenced CAD from Phase 0)
IMG_PTS = np.array([
    [ 412,  688],
    [1503,  651],
    [1788, 1002],
    [ 190, 1041],
    [ 951,  742],
    [ 967, 1180],
], dtype=np.float32)

WORLD_PTS = np.array([
    [578120.4, 2976040.1],
    [578168.9, 2976043.7],
    [578175.2, 2976012.3],
    [578112.7, 2976008.8],
    [578144.1, 2976031.5],
    [578143.6, 2976001.2],
], dtype=np.float32)

def fit_homography(img_pts, world_pts):
    H, mask = cv2.findHomography(img_pts, world_pts, cv2.RANSAC, 1.0)
    # Reprojection error tells you whether the fit is usable
    proj = cv2.perspectiveTransform(img_pts.reshape(-1, 1, 2), H).reshape(-1, 2)
    err = np.linalg.norm(proj - world_pts, axis=1)
    print(f"Homography RMSE : {np.sqrt((err**2).mean()):.3f} m")
    print(f"Max error       : {err.max():.3f} m")
    print(f"Inliers         : {int(mask.sum())}/{len(img_pts)}")
    return H

def to_world(H, pts):
    """pts: (N,2) array of pixel coords. Returns (N,2) in metres."""
    pts = np.asarray(pts, dtype=np.float32).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(pts, H).reshape(-1, 2)

def footpoint(bbox):
    """bbox = (x1, y1, x2, y2). Bottom-centre = where the vehicle meets the road."""
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, y2)
```

> **ERRATUM — `float32` will eat half your error budget.** `WORLD_PTS` above is
> declared `dtype=np.float32`. A UTM 43N northing near `2,976,040` needs eight
> significant figures; float32 carries about seven, so the coordinate is quantised to
> roughly **0.25 m before any real error is measured** — against a 0.5 m gate.
> `to_world` casts to float32 too, so every projected track point inherits it.
>
> Fix by subtracting a local origin and working in float64 metres:
>
> ```python
> ORIGIN = np.array([578_000.0, 2_976_000.0])      # junction-local, keeps values small
>
> def fit_homography(img_pts, world_pts, origin=ORIGIN):
>     img = np.asarray(img_pts, dtype=np.float64)
>     wld = np.asarray(world_pts, dtype=np.float64) - origin
>     # Plain least-squares over all points. NOT LMEDS and NOT RANSAC - see the
>     # correction below; robust estimators are worse at this sample size.
>     H, mask = cv2.findHomography(img, wld, 0)
>     proj = cv2.perspectiveTransform(img.reshape(-1, 1, 2), H).reshape(-1, 2)
>     err = np.linalg.norm(proj - wld, axis=1)
>     print(f"Homography RMSE : {np.sqrt((err**2).mean()):.3f} m")
>     return H, origin
> ```
>
> Add `origin` back when writing world coordinates out.
>
> **CORRECTION TO THIS ERRATUM, from measurement.** An earlier version of this note
> recommended `cv2.LMEDS` in place of the original `cv2.RANSAC`. That was wrong, and the
> original was closer to right. Tested over 40 random draws per condition in
> `src/homography.py`:
>
> | GCPs | noise | least-squares | LMEDS | RANSAC |
> |---|---|---|---|---|
> | 6 | 1.0 px | **0.025 / 0.038** | 0.119 / 1.328 | 0.025 / 0.038 |
> | 6 | 2.0 px | **0.054 / 0.080** | 0.240 / 2.004 | 0.054 / 0.080 |
> | 8 | 1.0 px | **0.034 / 0.049** | 0.052 / 0.174 | 0.034 / 0.049 |
>
> RMSE in metres, median / p90. With 5-8 hand-picked control points LMEDS is several
> times worse in the median and an order of magnitude worse in the tail, because it
> minimises the median residual over minimal subsets and there is not enough redundancy
> to stop it settling on a degenerate four-point fit. RANSAC matches least-squares only
> because, with no true outliers, it accepts every point and refines by least-squares
> anyway. **Use `method=0`.** Robust estimators belong on large automatically-matched
> point sets, not on control you picked by hand and trust.
>
> On the magnitude of the float32 problem: 0.25 m is the *quantisation step* at UTM
> northings, not the resulting error. Measured contribution to fitted RMSE is about
> **0.055 m** - roughly a ninth of the 0.5 m budget rather than half of it. Still worth
> fixing, and free to fix, but the original wording overstated it.

**Accept the homography only if RMSE < 0.5 m near the junction centre.** Accuracy degrades toward the frame edges and at shallow viewing angles — this is why camera height matters. If RMSE exceeds 1 m, re-survey GCPs or raise the camera.

## 6.3 Zone-based movement counting

**Why zones rather than counting lines:** a line-crossing counter tells you a vehicle passed, not where it came from or went. Turning movements need both. Define an **entry zone** and an **exit zone** on each leg; a track that enters through zone A and leaves through zone C is unambiguously movement A→C.

**Building the zones from the CAD — the payoff of Phases 0–3.** Because your video is now in UTM 43N and your CAD is too, you generate the zones automatically:

```python
"""
zones.py — Derive counting zones directly from the noded network graph.
"""
from shapely.geometry import Polygon, Point
from shapely.ops import substring

def leg_zone(G, node, neighbour, offset=15.0, depth=15.0, half_width=None):
    """
    Build a rectangular counting zone across a leg, starting `offset` metres
    from the junction and extending `depth` metres outward.

    offset : clear of the junction so stopped/queued vehicles don't
             oscillate in and out of the zone
    depth  : long enough that no vehicle can skip it between frames.
             At 60 km/h (16.7 m/s) and 25 fps a vehicle moves 0.67 m/frame,
             so 15 m is very safe.
    """
    edge = G[node][neighbour][0]["geometry"]
    if half_width is None:
        half_width = G[node][neighbour][0].get("width", 10.0) / 2.0 + 2.0

    seg = substring(edge, offset, min(offset + depth, edge.length))
    return seg.buffer(half_width, cap_style=2)   # cap_style=2 = flat ends

def build_zones(G, node):
    """One entry zone and one exit zone per leg at this junction."""
    zones = {}
    for nb in set(G.successors(node)) | set(G.predecessors(node)):
        zones[("entry", nb)] = leg_zone(G, node, nb, offset=15, depth=15)
        zones[("exit",  nb)] = leg_zone(G, node, nb, offset=15, depth=15)
    return zones
```

> **ERRATUM — this function as written cannot work.** The entry and exit zones are
> built with identical arguments, so they are the *same polygon*. `assign_movement`
> below takes the **first** matching zone via `next(...)`, so on every leg the entry
> zone wins and the exit zone is never reached. `exits` is always empty, every track
> returns `None`, and track resolution is 0% against a >90% gate.
>
> On a **divided** carriageway the two zones belong on opposite sides of the median:
> place them by the direction of travel, not on the shared centreline. On an
> **undivided** leg a single polygon genuinely serves both, and the movement must be
> resolved by the *order* the track passes through it rather than by zone identity:
>
> ```python
> def build_zones(G, node, offset=15.0, depth=15.0):
>     """Entry and exit zones per leg, separated across the median where one exists."""
>     zones = {}
>     for nb in set(G.successors(node)) | set(G.predecessors(node)):
>         base = leg_zone(G, node, nb, offset=offset, depth=depth)
>         if G[node][nb][0].get("divided"):
>             # offset each zone half a carriageway either side of the centreline
>             half = G[node][nb][0].get("width", 10.0) / 4.0
>             nx, ny = _leg_normal(G, node, nb)
>             zones[("entry", nb)] = affinity.translate(base,  nx * half,  ny * half)
>             zones[("exit",  nb)] = affinity.translate(base, -nx * half, -ny * half)
>         else:
>             zones[("entry", nb)] = zones[("exit", nb)] = base
>     return zones
> ```
>
> `assign_movement` must then collect **all** zones containing the point, not the
> first, and infer direction from the sign of travel along the leg axis.

**Assigning movements from tracks:**

```python
"""
count_movements.py — tracks -> classified TMC.
"""
from collections import defaultdict
from shapely.geometry import Point

def assign_movement(track_world, zones, min_dwell=3):
    """
    track_world : list of (frame_idx, x, y) in metres, one entry per frame.
    zones       : dict from build_zones()
    min_dwell   : frames a track must remain inside a zone to count.
                  Filters out tracks that clip a zone corner.

    Returns (from_leg, to_leg) or None if the track can't be resolved.
    """
    seq = []      # ordered list of (zone_key, frame) the track visited
    current, run = None, 0

    for f, x, y in track_world:
        p = Point(x, y)
        hit = next((k for k, poly in zones.items() if poly.contains(p)), None)
        if hit == current:
            run += 1
        else:
            if current is not None and run >= min_dwell:
                seq.append((current, f))
            current, run = hit, 1
    if current is not None and run >= min_dwell:
        seq.append((current, track_world[-1][0]))

    entries = [k[1] for k, _ in seq if k[0] == "entry"]
    exits   = [k[1] for k, _ in seq if k[0] == "exit"]
    if not entries or not exits:
        return None                      # partial track — vehicle left frame
    return (entries[0], exits[-1])       # first entry, last exit

def aggregate_tmc(tracks, zones, movement_table, fps, bin_minutes=15):
    """
    tracks : {track_id: {"class": str, "pts": [(frame, x, y), ...]}}
    movement_table : from enumerate_movements() — maps (from,to) -> LEFT/THROUGH/...
    Returns {(bin_index, vehicle_class, movement_code): count}
    """
    lookup = {(m["from_leg"], m["to_leg"]): m for m in movement_table}
    tmc = defaultdict(int)
    unresolved = 0

    for tid, t in tracks.items():
        od = assign_movement(t["pts"], zones)
        if od is None or od not in lookup:
            unresolved += 1
            continue
        mv = lookup[od]
        first_frame = t["pts"][0][0]
        bin_idx = int(first_frame / fps / 60 / bin_minutes)
        tmc[(bin_idx, t["class"], mv["code"])] += 1

    total = len(tracks)
    # ERRATUM: guard the division — an empty track set raised ZeroDivisionError,
    # which is the one case where you most want the diagnostic to print.
    pct = 100 * (total - unresolved) / total if total else 0.0
    print(f"Resolved {total - unresolved}/{total} tracks ({pct:.1f}%)")
    return tmc
```

**Verify:** the resolved-track rate should exceed **90%**. Below that, diagnose:
- Zones too small or too far from the junction → tracks miss them
- Tracking fragmenting under occlusion → tune ByteTrack, raise the camera
- Vehicles entering/leaving mid-frame from driveways → legitimate, but quantify it

## 6.4 Validation — the section reviewers read first

Do not present counts without this table. It is what separates a defensible study from an unverified one.

| Junction | Interval | Manual total | Auto total | Error % | Manual 2W | Auto 2W | 2W error % |
|---|---|---|---|---|---|---|---|
| J1 | 09:00–09:15 | | | | | | |
| J1 | 14:00–14:15 | | | | | | |

**Acceptance thresholds:**

| Metric | Target | Minimum acceptable |
|---|---|---|
| Total vehicle count MAPE | < 5% | < 10% |
| Per-class MAPE (2W, car, auto) | < 10% | < 15% |
| Per-class MAPE (bus, truck, MAV) | < 10% | < 20% (low counts inflate percentage error) |
| Movement assignment accuracy | > 95% | > 90% |

If you miss these, fix the pipeline before proceeding. **A capacity analysis built on unvalidated counts is worthless**, and on a ₹5,000 crore scheme it is worse than worthless.

---

# PHASE 7 — Capacity and Level of Service Analysis

## 7.1 What the counts feed

For each junction, per movement, per 15-min interval, you now have volumes by class. Convert to PCU using the share-dependent factors from Phase 4.1, then:

**1. Saturation flow — measure it, don't assume it.** Indian saturation flow rates differ substantially from Western defaults because of mixed traffic and lateral movement. Measure from the video: count vehicles discharging during the saturated portion of green (after the first 4 seconds, before the last 2), convert to PCU, scale to an hourly rate. Report the measured value — it is one of the more valuable outputs of the whole exercise.

**2. Capacity and v/c ratio per movement.** The movement with the highest v/c is the junction's binding constraint. Identifying *which turning movement* fails — usually the right turn on the heaviest approach — is what justifies a specific alignment rather than a generic "the junction is congested."

**3. Level of Service.** Use **Indo-HCM (2017)** as primary — it is the Indian-context capacity manual and covers signalised, unsignalised, roundabout and mid-block sections with locally calibrated relationships. Cite IRC:106 and IRC:SP:41 alongside.

**4. Delay and queue.** Compare modelled delay against your field-measured queue lengths. Divergence means your saturation flow or arrival assumptions are off — fix them before proceeding to simulation.

## 7.2 Growth and design year

- **Historic growth:** obtain past count data from JDA, PWD, or NHAI for any station on or near the corridor. Even two historic years gives you a defensible CAGR.
- **Independent cross-check:** Rajasthan Transport Department vehicle registration data by district gives registered-vehicle growth. Traffic growth typically runs below registration growth — use it as an upper bound, not a direct substitute.
- **Elasticity method:** where count history is absent, apply an elasticity to Rajasthan GSDP growth. Typical urban traffic elasticity to GSDP is 1.0–1.4. State your assumed value explicitly.
- **Design horizon:** 20 years from commissioning for an elevated corridor, with intermediate check years at 5 and 10.

**Always present a range, not a single number.** Low/medium/high growth scenarios. A single-point 20-year forecast presented without a band invites, and deserves, challenge.

## 7.3 The argument the analysis needs to make

For an elevated corridor at this cost, the analysis must establish four things in sequence:

1. **The at-grade network fails** in the design year — v/c > 1.0 on critical movements, LOS E/F
2. **At-grade improvements are insufficient** — model signal optimisation, junction improvement, and widening within available ROW, and show they don't resolve it
3. **The specific alignment is justified** by the through-movement demand it removes — this is where your TMC data becomes irreplaceable, because it tells you exactly what proportion of traffic is *through* versus *turning*
4. **The at-grade impact is acceptable** — pedestrian severance, kerbside access, property frontage, tree felling, utility diversion

Point 3 is the one that only turning movement data can support. If through movements are 70% of the corridor volume, an elevated through-carriageway is well-founded. If they're 35%, the corridor's problem is local access and turning conflict, and a flyover will underperform its cost. **Your data is what decides this, and it is the most consequential finding in the study.**

---

# PHASE 8 — SUMO Simulation Model

## 8.1 Network export from your graph

Write SUMO XML directly from the Phase 2 graph. This gives you full control and avoids OSM import artefacts.

```python
"""
export_sumo.py — network graph -> SUMO .nod.xml / .edg.xml / .con.xml
Then: netconvert --node-files=corridor.nod.xml --edge-files=corridor.edg.xml \
                 --connection-files=corridor.con.xml --output-file=corridor.net.xml
"""
import xml.etree.ElementTree as ET

def write_nodes(G, path):
    root = ET.Element("nodes")
    for n, d in G.nodes(data=True):
        ET.SubElement(root, "node", {
            "id": f"n{abs(hash(n)) % 10**9}",
            "x": f"{d['x']:.2f}",
            "y": f"{d['y']:.2f}",
            # traffic_light for signalised, priority for give-way,
            # right_before_left is wrong for India — do not use it
            "type": "traffic_light" if d.get("signalised") else "priority",
        })
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)

def write_edges(G, path):
    root = ET.Element("edges")
    for u, v, k, d in G.edges(keys=True, data=True):
        e = ET.SubElement(root, "edge", {
            "id": f"e{abs(hash((u,v,k))) % 10**9}",
            "from": f"n{abs(hash(u)) % 10**9}",
            "to": f"n{abs(hash(v)) % 10**9}",
            "numLanes": str(d.get("lanes", 2)),
            "speed": str(d.get("speed_ms", 13.9)),   # 50 km/h urban default
        })
        # Preserve the real CAD alignment rather than a straight line
        pts = list(d["geometry"].coords)[1:-1]
        if pts:
            e.set("shape", " ".join(f"{x:.2f},{y:.2f}" for x, y, *_ in pts))
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
```

**Set `--lefthand` on netconvert.** SUMO defaults to right-hand traffic. Without this flag your entire model drives on the wrong side and every turning conflict is inverted.

## 8.2 Turn ratios from your TMC

This is the direct payoff of Phase 6. Convert counted movements into turn proportions and let `jtrrouter` generate routes:

```xml
<turns>
  <interval begin="0" end="900">
    <fromEdge id="e_north_in">
      <toEdge id="e_west_out"  probability="0.22"/>  <!-- left  -->
      <toEdge id="e_south_out" probability="0.61"/>  <!-- through -->
      <toEdge id="e_east_out"  probability="0.14"/>  <!-- right -->
      <toEdge id="e_north_out" probability="0.03"/>  <!-- U-turn -->
    </fromEdge>
  </interval>
</turns>
```

Probabilities per approach must sum to 1.0. Generate one interval per 15-minute bin so the model reproduces the real within-hour peaking your PHF captured.

## 8.3 Making SUMO behave like Indian traffic

Default SUMO models disciplined lane-following. Jaipur traffic does not do that. Three changes are essential:

**1. Enable the sublane model.** This is the single most important setting. It lets vehicles occupy lateral positions continuously rather than snapping to lane centres — which is how two-wheelers actually behave, filtering between larger vehicles and forming multiple streams within a marked lane.

```xml
<!-- in the sumocfg -->
<processing>
    <lateral-resolution value="0.8"/>   <!-- metres; enables sublane model -->
    <collision.action value="warn"/>
</processing>
```

**2. Define vehicle types with real dimensions and Indian lateral behaviour.**

```xml
<vType id="2W"    vClass="motorcycle"  length="1.9" width="0.7"  maxSpeed="16.7"
       accel="3.0" decel="5.0" sigma="0.6" minGap="0.8" minGapLat="0.25"
       latAlignment="arbitrary" laneChangeModel="SL2015"/>
<vType id="AUTO"  vClass="taxi"        length="2.6" width="1.4"  maxSpeed="13.9"
       accel="2.0" decel="4.0" sigma="0.7" minGap="1.0" minGapLat="0.35"
       latAlignment="arbitrary" laneChangeModel="SL2015"/>
<vType id="CAR"   vClass="passenger"   length="4.2" width="1.7"  maxSpeed="19.4"
       accel="2.6" decel="4.5" sigma="0.5" minGap="1.5" minGapLat="0.4"
       laneChangeModel="SL2015"/>
<vType id="BUS"   vClass="bus"         length="11.0" width="2.5" maxSpeed="16.7"
       accel="1.2" decel="3.5" sigma="0.4" minGap="2.5" minGapLat="0.6"
       laneChangeModel="SL2015"/>
<vType id="TRUCK" vClass="truck"       length="7.5" width="2.4"  maxSpeed="16.7"
       accel="1.1" decel="3.5" sigma="0.5" minGap="2.5" minGapLat="0.6"
       laneChangeModel="SL2015"/>
```

`latAlignment="arbitrary"` and a small `minGapLat` are what produce realistic two-wheeler filtering. `sigma` (driver imperfection) is set higher than European defaults to reflect greater speed variance.

**3. Calibrate against observed reality.** Do not present an uncalibrated model.

| Calibration target | Source | Acceptance |
|---|---|---|
| Link volumes | Your mid-block counts | GEH < 5 on 85% of links |
| Junction turning volumes | Your TMC | GEH < 5 on 85% of movements |
| Queue lengths | Field queue survey | Within 20% at peak |
| Corridor travel time | Moving car survey | Within 15% per direction per peak |

**GEH statistic** — the standard traffic model acceptance measure, designed because plain percentage error misbehaves across very different volume magnitudes:

```python
def geh(modelled, observed):
    """GEH < 5 = good fit. 5-10 = investigate. >10 = reject."""
    if modelled + observed == 0:
        return 0.0
    return ((2 * (modelled - observed) ** 2) / (modelled + observed)) ** 0.5
```

---

# PHASE 9 — Deliverables and Data Schema

## 9.1 PostGIS schema

```sql
-- Network geometry (all in EPSG:32643, UTM Zone 43N)
CREATE TABLE nodes (
    node_id      SERIAL PRIMARY KEY,
    geom         GEOMETRY(Point, 32643) NOT NULL,
    kind         TEXT,               -- T_junction / cross_junction / midblock
    degree       INT,
    signalised   BOOLEAN DEFAULT FALSE,
    cycle_time_s INT,
    name         TEXT
);
CREATE INDEX nodes_geom_idx ON nodes USING GIST (geom);

CREATE TABLE links (
    link_id      SERIAL PRIMARY KEY,
    from_node    INT REFERENCES nodes(node_id),
    to_node      INT REFERENCES nodes(node_id),
    geom         GEOMETRY(LineString, 32643) NOT NULL,
    length_m     NUMERIC(10,2),
    width_m      NUMERIC(6,2),
    lanes        INT,
    divided      BOOLEAN,
    oneway       BOOLEAN DEFAULT FALSE,
    grade_level  INT DEFAULT 0,      -- 0 = at grade, 1 = elevated, -1 = under
    dxf_handle   TEXT                -- traceability back to the CAD entity
);
CREATE INDEX links_geom_idx ON links USING GIST (geom);

-- Every possible movement at every junction
CREATE TABLE movements (
    movement_id  SERIAL PRIMARY KEY,
    node_id      INT REFERENCES nodes(node_id),
    from_link    INT REFERENCES links(link_id),
    to_link      INT REFERENCES links(link_id),
    turn_delta   NUMERIC(6,2),
    movement     TEXT CHECK (movement IN ('LEFT','THROUGH','RIGHT','UTURN')),
    code         TEXT,               -- NBL, EBT, SBR, WBU ...
    permitted    BOOLEAN,
    restriction_source TEXT,         -- 'cad_median' / 'field_signage' / 'assumed'
    UNIQUE (node_id, from_link, to_link)
);

-- The counts themselves
CREATE TABLE counts (
    count_id     BIGSERIAL PRIMARY KEY,
    movement_id  INT REFERENCES movements(movement_id),
    survey_date  DATE NOT NULL,
    bin_start    TIMESTAMPTZ NOT NULL,
    bin_minutes  INT DEFAULT 15,
    veh_class    TEXT NOT NULL,      -- 2W / AUTO / E_RIK / CAR / LCV / BUS / ...
    veh_count    INT NOT NULL,
    pcu_factor   NUMERIC(4,2),
    pcu_value    NUMERIC(8,2) GENERATED ALWAYS AS (veh_count * pcu_factor) STORED,
    source       TEXT,               -- 'video_auto' / 'manual' / 'validated'
    UNIQUE (movement_id, bin_start, veh_class, source)
);
CREATE INDEX counts_bin_idx ON counts (bin_start, movement_id);

-- Irregular manoeuvres, kept separate so they don't corrupt the TMC
CREATE TABLE irregular_manoeuvres (
    id           BIGSERIAL PRIMARY KEY,
    node_id      INT REFERENCES nodes(node_id),
    link_id      INT REFERENCES links(link_id),
    bin_start    TIMESTAMPTZ NOT NULL,
    manoeuvre    TEXT CHECK (manoeuvre IN
                   ('WRONG_WAY','KERBSIDE_STOP','REVERSING','PED_CROSSING')),
    veh_class    TEXT,
    event_count  INT NOT NULL,
    mean_dwell_s NUMERIC(6,2)
);
```

## 9.2 Project structure

```
corridor-study/
├── 00_source/
│   ├── dwg/                   # as received from JDA
│   ├── dxf/                   # converted
│   └── survey_reports/        # datum/projection documentation
├── 01_georeference/
│   ├── gcps.csv
│   ├── cad_to_utm43n.npy
│   └── residuals_report.md    # the accuracy evidence
├── 02_network/
│   ├── centrelines.geojson
│   ├── network.graphml
│   └── movements.csv          # every movement, classified, permitted flag
├── 03_survey/
│   ├── video/                 # raw, by junction and date
│   ├── field_forms/           # scanned manual counts
│   └── gcps_video/            # per-camera GCP surveys
├── 04_counts/
│   ├── tracks/                # raw detection+tracking output
│   ├── tmc/                   # aggregated counts
│   └── validation_report.md   # manual vs automated
├── 05_analysis/
│   ├── pcu_conversion.xlsx
│   ├── los_by_junction.xlsx
│   └── growth_scenarios.xlsx
├── 06_simulation/
│   ├── corridor.net.xml
│   ├── turns.xml
│   ├── vtypes.xml
│   └── calibration_report.md
├── 07_deliverables/
│   ├── corridor_constraint_atlas.pdf
│   ├── tmc_diagrams/
│   └── final_report.docx
└── src/                       # all the scripts in this document
```

## 9.3 Output artefacts

| Artefact | Content |
|---|---|
| **Corridor Constraint Atlas** | Georeferenced map series: ROW, utilities, structures, trees, heritage buffers, water bodies. The pier-siting constraint set. |
| **TMC diagrams** | Per junction: spider diagram with volume by movement, in vehicles and PCU, peak hour |
| **LOS map** | Corridor coloured by movement-level v/c, base year and design year |
| **Validation report** | Manual vs automated counts, MAPE by class, homography residuals, georeference RMSE |
| **Calibrated SUMO model** | Runnable base-year model plus with/without-scheme scenarios |
| **Method statement** | This document, adapted — establishes reproducibility |

---

# Critical Path and Sequencing

```
1. Get DXF from JDA          → verify: files open, layers legible
2. Determine CRS             → verify: georeference RMSE < 3 m, plots on satellite
3. Extract + node network    → verify: node count matches visual junction count
4. Enumerate movements       → verify: 16 movements at each 4-arm junction
5. Design survey             → verify: dates clear of festivals, GCPs planned
6. Pilot count, 1 junction   → verify: validation MAPE < 10%
7. Full survey               → verify: 3 days × all junctions captured
8. Process all video         → verify: >90% track resolution
9. Capacity analysis         → verify: LOS results consistent with observed queues
10. Simulate + calibrate     → verify: GEH < 5 on 85% of links
11. Deliverables
```

**Steps 1–6 are the critical path and they are also cheap.** Do them before committing survey budget. Step 6 in particular — a single-junction pilot with a validation table — is both your risk mitigation and your JDA credibility artefact. It proves the pipeline works before you spend money on a full survey, and it proves *you* work before JDA spends money on you.

**The two things most likely to sink this project:**
1. **A wrong or unverified coordinate system.** Everything downstream inherits the error, silently. Gate hard at Phase 0.
2. **GCPs not surveyed before the video shoot.** You cannot add them retrospectively. Plan them into the survey design.

---

# Viva / Review Q&A

**Q: Why is the right turn the critical movement in India, not the left?**
India drives on the left, so a right turn crosses the opposing traffic stream. It's the conflicting movement — it needs gap acceptance or a protected signal phase, and it's usually what limits junction capacity. In right-hand-drive countries the left turn plays this role. Carrying over a US methodology unmodified means protecting the wrong movement.

**Q: Why can't you just take lane counts from the CAD and use them?**
Because marked lanes and used lanes diverge sharply in mixed traffic. A 10.5 m carriageway is nominally three lanes but commonly carries four to five streams once two-wheelers filter. That's why the sublane simulation model is necessary and why observed stream counts should be reported alongside geometric ones.

**Q: How do you know your automated counts are correct?**
Manual ground truth on 15-minute samples per junction, reported as MAPE by vehicle class, with acceptance thresholds set in advance. Homography reprojection RMSE and georeference RMSE are reported alongside. The validation report is a deliverable, not an appendix.

**Q: Why zones instead of counting lines?**
A line crossing tells you a vehicle passed but not its origin or destination. Turning movements require both. Paired entry and exit zones resolve the movement unambiguously, and because the zones are generated from the georeferenced CAD network, they're geometrically consistent with the model rather than hand-drawn on a video frame.

**Q: What PCU did you use for e-rickshaws and why?**
IRC:106 predates them and has no value. State which of the three options you took — auto-rickshaw proxy, CRRI-derived value, or locally measured — and justify it. If you measured it from your own data, say so; that's the strongest answer available.

**Q: How does the CAD connect to the video?**
Through shared ground control points and a common coordinate system. GCPs surveyed on site appear both in the CAD and in the camera frame, giving a homography that puts vehicle trajectories into the same UTM 43N coordinates as the network. That's what makes automatic zone generation possible and what makes it one system rather than two.

**Q: How does the turning movement data justify the elevated alignment?**
By separating through movements from turning movements. An elevated through-carriageway only helps traffic that isn't turning. If through movements dominate, the scheme is well-founded; if turning and local access dominate, the corridor's real problem is junction conflict and a flyover will underperform its cost. No other dataset answers this.

**Q: What are the main limitations?**
Three days of survey may not capture seasonal variation. PCU values are largely from a 1990 standard with known gaps for newer vehicle types. Homography accuracy degrades toward frame edges. Growth forecasting over 20 years carries irreducible uncertainty — which is why scenarios are presented as a band rather than a point estimate. State these openly; a study that declares its limitations is more credible than one that doesn't.

---

# Standards Referenced

| Standard | Covers |
|---|---|
| **Indo-HCM (2017), CSIR-CRRI** | Indian Highway Capacity Manual — primary reference for capacity and LOS |
| **IRC:106-1990** | Capacity of urban roads in plain areas — PCU factors |
| **IRC:SP:41-1994** | Design of at-grade intersections |
| **IRC:SP:19** | Survey, investigation and preparation of road projects |
| **IRC:102** | Traffic studies for planning bypasses |
| **IRC:103** | Pedestrian facilities |
| **IRC:92** | Grade-separated intersections — **directly relevant to the elevated corridor** |
| **IRC:SP:12** | Parking |
| **DGCA Drone Rules 2021 / Digital Sky** | Aerial survey compliance |
