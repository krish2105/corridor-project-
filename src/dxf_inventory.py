"""
dxf_inventory.py — Phase 1.2 layer inventory and junction candidates.

The converted DXF is ~200 MB of ASCII, so this streams the group-code pairs rather
than loading a document. That reads the whole file in a few seconds and costs no
meaningful memory; ezdxf.readfile on this file is not practical.

Outputs
  - layer inventory (layer, entity type, count), contour layers folded up
  - traffic-signal clusters, which are candidate junction centres
  - named labels near each cluster, so a candidate can be identified by name
  - out/data/junction_candidates.geojson for the map

Run:  uv run python src/dxf_inventory.py
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import CRS_GEO, CRS_WORK, OUT_DATA, ROOT

DXF = next((ROOT / "00_source" / "dxf").glob("*.dxf"), None)
TO_WGS = Transformer.from_crs(CRS_WORK, CRS_GEO, always_xy=True)

# Contour layers are named ESMinor<level> / ESMajor<level>. There are ~90 of them
# and they carry the terrain model, not the road. Folded up so the inventory is legible.
CONTOUR = re.compile(r"^ES(Minor|Major)[\d.]+$")
NAME_LAYERS = {"TITEL TEXT", "NAME BOARD"}
CLUSTER_M = 80.0        # signals at one junction sit within a few tens of metres


def stream(path):
    """Yield (layer, entity_type, x, y, text) for every entity in ENTITIES."""
    section = ent = None
    cur = {}
    with open(path, "r", errors="ignore") as f:
        while True:
            c = f.readline()
            if not c:
                break
            v = f.readline()
            if not v:
                break
            c, v = c.strip(), v.strip()
            if c == "0":
                if ent and section == "ENTITIES":
                    yield (cur.get("layer", "?"), ent,
                           cur.get("x"), cur.get("y"), cur.get("text"))
                ent, cur = v, {}
                if v == "ENDSEC":
                    section = None
            elif c == "2" and ent == "SECTION":
                section = v
            elif section == "ENTITIES":
                if c == "8":
                    cur["layer"] = v
                elif c == "10" and "x" not in cur:
                    cur["x"] = float(v)
                elif c == "20" and "y" not in cur:
                    cur["y"] = float(v)
                elif c == "1" and "text" not in cur:
                    cur["text"] = v


def cluster(points, radius=CLUSTER_M):
    """Single-link clustering. Signals belonging to one junction merge into one group."""
    r2 = radius ** 2
    groups = []
    for p in points:
        for g in groups:
            if any((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < r2 for q in g):
                g.append(p)
                break
        else:
            groups.append([p])
    merged = True
    while merged:
        merged = False
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                if any((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 < r2
                       for a in groups[i] for b in groups[j]):
                    groups[i] += groups[j]
                    del groups[j]
                    merged = True
                    break
            if merged:
                break
    return sorted(groups, key=len, reverse=True)


def build():
    counts = Counter()
    signals, labels = [], []
    for layer, etype, x, y, text in stream(DXF):
        key = "ES*  (contours)" if CONTOUR.match(layer) else layer
        counts[(key, etype)] += 1
        if layer == "TRAFFIC SIGNAL" and etype == "INSERT" and x is not None and y is not None:
            signals.append((x, y))
        elif layer in NAME_LAYERS and text and x is not None and y is not None:
            labels.append((x, y, text))
    return counts, signals, labels


if __name__ == "__main__":
    if DXF is None:
        raise SystemExit("No DXF in 00_source/dxf/ — convert the DWG first (see src/dwg_probe.py).")
    print(f"reading {DXF.name} ({DXF.stat().st_size/1e6:,.0f} MB)\n")
    counts, signals, labels = build()

    by_layer = defaultdict(int)
    for (lay, _), n in counts.items():
        by_layer[lay] += n
    print(f"{'LAYER':<26}{'ENTITY TYPES':<34}{'TOTAL':>9}")
    print("-" * 72)
    for lay, tot in sorted(by_layer.items(), key=lambda kv: -kv[1]):
        types = ", ".join(f"{t}:{n:,}" for (l, t), n in
                          sorted(counts.items(), key=lambda kv: -kv[1]) if l == lay)
        print(f"{lay[:25]:<26}{types[:33]:<34}{tot:>9,}")
    print(f"\n{len(by_layer)} layers, {sum(by_layer.values()):,} entities")

    groups = cluster(signals)
    print(f"\n{len(signals)} traffic signals -> {len(groups)} clusters "
          f"(single-link at {CLUSTER_M:.0f} m)\n")
    print("Candidate junctions, largest first. A 4-arm signalised junction carries")
    print("roughly 8-16 heads, so the big clusters are the real junctions.\n")

    feats = []
    for i, g in enumerate(groups, 1):
        cx = sum(p[0] for p in g) / len(g)
        cy = sum(p[1] for p in g) / len(g)
        lon, lat = TO_WGS.transform(cx, cy)
        near = sorted((((x - cx) ** 2 + (y - cy) ** 2) ** .5, s)
                      for x, y, s in labels if (x - cx) ** 2 + (y - cy) ** 2 < 200 ** 2)
        name = near[0][1].replace("\\P", " / ") if near else ""
        if i <= 12:
            print(f"  C{i:<2} heads={len(g):>2}  {lat:.6f}, {lon:.6f}   {name[:46]}")
        feats.append(dict(type="Feature",
                          geometry=dict(type="Point", coordinates=[round(lon, 6), round(lat, 6)]),
                          properties=dict(cluster=f"C{i}", signal_heads=len(g),
                                          easting=round(cx, 2), northing=round(cy, 2),
                                          nearest_label=name[:80],
                                          nearest_label_m=round(near[0][0], 1) if near else None)))

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    path = OUT_DATA / "junction_candidates.geojson"
    path.write_text(json.dumps(dict(type="FeatureCollection", features=feats), indent=1))
    print(f"\nwritten: {path}  ({len(feats)} candidates)")
    print("\nThese are candidates, not the six surveyed junctions. The TMC workbooks")
    print("carry no coordinates and their arm labels are destinations rather than")
    print("junction names, so the match still needs confirming against the survey")
    print("location schedule or six map pins.")
