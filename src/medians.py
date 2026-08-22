"""
medians.py — where a U-turn is physically possible on the corridor.

The survey counted twelve movements per junction and no U-turns at all, so U-turn
demand is unmeasured rather than zero. The drawing settles the other half of the
question: a U-turn needs a physical opening in the median, and the DIVIDER linework
says exactly where those are.

Method follows Phase 3.2 of the methodology, with the erratum applied — gaps are
measured between median pieces that are ADJACENT along the corridor, not by taking
a maximum over all pairs, which reports the distance between the two furthest-apart
fragments and passes almost unconditionally.

Run:  uv run python src/medians.py
"""
import json
import math
import sys
from pathlib import Path

from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.atlas import longest_alignment, read_geometry
from src.config import CRS_GEO, CRS_WORK, OUT_DATA, ROOT

DXF = next((ROOT / "00_source" / "dxf").glob("*.dxf"), None)
TO_WGS = Transformer.from_crs(CRS_WORK, CRS_GEO, always_xy=True)

CORRIDOR_BAND_M = 30.0   # median linework further out belongs to a cross-street
# IRC guidance and Indian practice: below ~4 m nothing can turn; typical notified
# median openings run 8-15 m. Anything much wider is usually a junction mouth.
MIN_TURNABLE_M = 4.0
TYPICAL_LO, TYPICAL_HI = 8.0, 15.0


def chainage(alignment):
    """Return f(x, y) -> (chainage_m, perpendicular_offset_m) against the alignment."""
    segs, acc = [], 0.0
    for i in range(len(alignment) - 1):
        a, b = alignment[i], alignment[i + 1]
        L = math.dist(a, b)
        if L:
            segs.append((a, b, L, acc))
            acc += L

    def f(x, y):
        best = (float("inf"), 0.0, 0.0)
        for (ax, ay), (bx, by), L, s0 in segs:
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (L * L)))
            px, py = ax + t * dx, ay + t * dy
            d = math.dist((x, y), (px, py))
            if d < best[0]:
                # sign the offset so left and right of the alignment separate
                side = math.copysign(1.0, dx * (y - ay) - dy * (x - ax))
                best = (d, s0 + t * L, d * side)
        return best[1], best[2], best[0]
    return f, acc


def median_runs(geom, alignment):
    """Each DIVIDER polyline reduced to the stretch of corridor it occupies."""
    f, total = chainage(alignment)
    runs = []
    for layer, kind, vs in geom.get("median", []):
        if kind != "line" or len(vs) < 2:
            continue
        ch = [f(x, y) for x, y in vs]
        near = [c for c in ch if c[2] <= CORRIDOR_BAND_M]
        if len(near) < 2:
            continue                       # median of a cross-street, not this corridor
        lo = min(c[0] for c in near)
        hi = max(c[0] for c in near)
        if hi - lo < 1.0:
            continue                       # a stub, not a run
        runs.append((lo, hi, len(vs)))
    runs.sort()

    # merge overlapping runs: a median is often drawn as several polylines
    merged = []
    for lo, hi, n in runs:
        if merged and lo <= merged[-1][1] + 0.5:
            merged[-1][1] = max(merged[-1][1], hi)
            merged[-1][2] += n
        else:
            merged.append([lo, hi, n])
    return merged, total


def openings(merged):
    """Gaps between ADJACENT median runs. This is the erratum'd version."""
    gaps = []
    for i in range(len(merged) - 1):
        start, end = merged[i][1], merged[i + 1][0]
        gaps.append((start, end - start))
    return gaps


def classify(width):
    if width < MIN_TURNABLE_M:
        return "too narrow"
    if width < TYPICAL_LO:
        return "marginal"
    if width <= TYPICAL_HI:
        return "typical opening"
    return "wide / junction mouth"


if __name__ == "__main__":
    if DXF is None:
        raise SystemExit("No DXF in 00_source/dxf/ — convert the DWG first.")
    geom = read_geometry(DXF)
    align = longest_alignment(geom)
    merged, total = median_runs(geom, align)
    gaps = openings(merged)

    covered = sum(hi - lo for lo, hi, _ in merged)
    print(f"corridor length          : {total/1000:.2f} km")
    print(f"DIVIDER polylines        : {len(geom.get('median', []))}")
    print(f"median runs on corridor  : {len(merged)}  "
          f"(within {CORRIDOR_BAND_M:.0f} m of the alignment)")
    print(f"corridor with a median   : {covered:,.0f} m ({100*covered/total:.0f}%)")
    print(f"gaps between runs        : {len(gaps)}\n")

    buckets = {}
    for ch, w in gaps:
        buckets.setdefault(classify(w), []).append((ch, w))
    print(f"{'CLASS':<24}{'COUNT':>7}   what it means")
    print("-" * 78)
    MEANING = {
        "too narrow": "no vehicle can turn; median is effectively continuous",
        "marginal": "a 2W or auto may turn; a car or bus cannot",
        "typical opening": "a notified median opening: U-turns and right turns",
        "wide / junction mouth": "a junction, or an unusually long break",
    }
    for k in ("too narrow", "marginal", "typical opening", "wide / junction mouth"):
        v = buckets.get(k, [])
        print(f"{k:<24}{len(v):>7}   {MEANING[k]}")

    turnable = [(c, w) for c, w in gaps if w >= MIN_TURNABLE_M]
    print(f"\nlocations where a U-turn is physically possible: **{len(turnable)}**")
    if turnable:
        per_km = len(turnable) / (total / 1000)
        print(f"that is {per_km:.1f} per km of corridor\n")
        print(f"  {'chainage':>10}{'width':>8}   class")
        for c, w in sorted(turnable)[:20]:
            print(f"  {c:>9,.0f}m{w:>7.1f}m   {classify(w)}")
        if len(turnable) > 20:
            print(f"  ... and {len(turnable)-20} more")

    feats = []
    f, _ = chainage(align)
    # place each opening at the alignment point of its chainage
    stations = {}
    acc = 0.0
    for i in range(len(align) - 1):
        a, b = align[i], align[i + 1]
        L = math.dist(a, b)
        if L:
            stations[acc] = (a, b, L)
            acc += L
    def point_at(ch):
        for s0, (a, b, L) in sorted(stations.items()):
            if s0 <= ch <= s0 + L:
                t = (ch - s0) / L
                return a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
        return align[-1]
    for c, w in gaps:
        x, y = point_at(c + w / 2)
        lon, lat = TO_WGS.transform(x, y)
        feats.append(dict(type="Feature",
                          geometry=dict(type="Point", coordinates=[round(lon, 7), round(lat, 7)]),
                          properties=dict(chainage_m=round(c, 1), width_m=round(w, 1),
                                          classification=classify(w),
                                          uturn_possible=w >= MIN_TURNABLE_M)))
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    path = OUT_DATA / "median_openings.geojson"
    path.write_text(json.dumps(dict(type="FeatureCollection", features=feats), indent=1))
    print(f"\nwritten: {path}")

    print("\nWhy this matters: the survey recorded LEFT, STRAIGHT and RIGHT only.")
    print(f"Every one of these {len(turnable)} openings is a place where U-turn demand")
    print("exists and was never measured. At a median opening the U-turn competes with")
    print("the right turn for the same gap, so the movement the survey does count is")
    print("understated in its effect on capacity, not just incomplete.")
