"""
atlas.py — Corridor Constraint Atlas from the JDA survey drawing.

The methodology calls this "the pier-siting constraint set": everything an elevated
structure would have to be threaded between. Buildings, trees, and the buried and
overhead services that determine whether a pier can physically go somewhere.

The analytical output is the constraint profile — walking the corridor alignment and
counting what sits inside a pier footprint at every station. A map shows where things
are; the profile says where a pier cannot go, which is the question actually being asked.

Run:  uv run python src/atlas.py
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import CRS_GEO, CRS_WORK, OUT, OUT_DATA, ROOT

DXF = next((ROOT / "00_source" / "dxf").glob("*.dxf"), None)
TO_WGS = Transformer.from_crs(CRS_WORK, CRS_GEO, always_xy=True)

# DXF layer -> constraint category. Grouped by who owns the diversion, because that
# is what determines cost and lead time, not what the object is made of.
CATEGORIES = {
    "structures": ["BUILDING"],
    "vegetation": ["TREES"],
    "drainage":   ["NALA-", "nali-", "CULVERT", "CHAMBAR-", "MAIN HOLE"],
    "electrical": ["TRANSFORMER", "LT_LINE", "EP_LINE", "ELECTRIC PANEL BOARD",
                   "HI MAX LIGHT", "LAMP POST"],
    "telecom":    ["OFC LINE", "T_LINE", "TELEPHONE TOWER"],
    "gas":        ["GAS STONE"],
    "geotech":    ["BORING-"],
    "water":      ["WELL-", "HAND PUMP", "WATER TANK"],
    "religious":  ["TEMPLE-"],
    "carriageway": ["BT ROAD", "CC ROAD", "w.b.m. road", "SP.ROAD & TAIL", "FOOTPATH"],
    "median":     ["DIVIDER"],
    "rail":       ["RAILWAY TRACK"],
    "alignment":  ["kml road"],
}
LAYER_CAT = {lay: cat for cat, lays in CATEGORIES.items() for lay in lays}

# A pier for an elevated corridor occupies roughly 2-3 m; anything within 8 m of the
# centre has to be diverted, protected or the pier moved. Deliberately generous.
PIER_RADIUS_M = 8.0
STATION_M = 25.0        # profile sampling interval along the alignment

# Diversion difficulty, worst first. A stated judgement, not a measurement.
SEVERITY = {"structures": 5, "religious": 5, "rail": 5, "gas": 4, "drainage": 3,
            "electrical": 3, "telecom": 2, "water": 2, "geotech": 1, "vegetation": 1,
            "median": 0, "carriageway": 0, "alignment": 0}

# HARD constraints stop a pier outright: you demolish, or you move the pier. Everything
# else is street furniture that gets relocated as a matter of course, and lumping the
# two together lets 2,300 lamp posts outrank a building. Both profiles are reported.
HARD = {"structures", "religious", "rail", "gas"}


def read_geometry(path):
    """Stream the DXF, returning {category: [(layer, kind, [(x, y), ...]), ...]}."""
    out = defaultdict(list)
    section = ent = layer = None
    verts, pend, extra = [], {}, {}

    def emit():
        if section != "ENTITIES" or layer not in LAYER_CAT or not verts:
            return
        kind = "point" if ent in ("INSERT", "POINT", "CIRCLE") else "line"
        out[LAYER_CAT[layer]].append((layer, kind, list(verts)))

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
                emit()
                ent, layer, verts, pend, extra = v, None, [], {}, {}
                if v == "ENDSEC":
                    section = None
            elif c == "2" and ent == "SECTION":
                section = v
            elif section == "ENTITIES":
                if c == "8":
                    layer = v
                elif c == "10":
                    pend["x"] = float(v)
                elif c == "20" and "x" in pend:
                    verts.append((pend.pop("x"), float(v)))
                elif c == "11":
                    extra["x2"] = float(v)
                elif c == "21" and "x2" in extra:
                    verts.append((extra.pop("x2"), float(v)))
    emit()
    return out


def longest_alignment(geom):
    """The corridor centreline: the longest imported alignment in the drawing."""
    def length(p):
        return sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))
    lines = [v for _, kind, v in geom.get("alignment", []) if kind == "line" and len(v) > 1]
    if not lines:
        raise SystemExit("No 'kml road' alignment found in the drawing.")
    return max(lines, key=length)


def densify(line, step):
    """Stations every `step` metres along a polyline, with chainage."""
    pts, acc = [], 0.0
    for i in range(len(line) - 1):
        a, b = line[i], line[i + 1]
        seg = math.dist(a, b)
        if seg == 0:
            continue
        n = max(1, int(seg // step))
        for k in range(n):
            t = k / n
            pts.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), acc + t * seg))
        acc += seg
    pts.append((line[-1][0], line[-1][1], acc))
    return pts


def profile(geom, alignment, radius=PIER_RADIUS_M, step=STATION_M):
    """At each station, what sits inside a pier footprint."""
    obstacles = []
    for cat, items in geom.items():
        if SEVERITY.get(cat, 0) == 0:
            continue                        # roads and medians are not obstacles
        for layer, _, vs in items:
            for p in vs:
                obstacles.append((p[0], p[1], cat, layer))

    stations = densify(alignment, step)
    # bucket obstacles onto a coarse grid so this is not O(stations x obstacles)
    cell = 50.0
    grid = defaultdict(list)
    for x, y, cat, layer in obstacles:
        grid[(int(x // cell), int(y // cell))].append((x, y, cat, layer))

    rows = []
    r2 = radius ** 2
    for sx, sy, ch in stations:
        gx, gy = int(sx // cell), int(sy // cell)
        hits = defaultdict(int)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for x, y, cat, layer in grid.get((gx + dx, gy + dy), ()):
                    if (x - sx) ** 2 + (y - sy) ** 2 <= r2:
                        hits[cat] += 1
        score = sum(SEVERITY[c] * n for c, n in hits.items())
        hard = sum(n for c, n in hits.items() if c in HARD)
        rows.append(dict(chainage_m=round(ch, 1), x=sx, y=sy,
                         constraints=dict(hits), n=sum(hits.values()),
                         score=score, hard=hard))
    return rows, len(obstacles)


def to_geojson(geom):
    feats = []
    for cat, items in geom.items():
        for layer, kind, vs in items:
            if kind == "point":
                lon, lat = TO_WGS.transform(vs[0][0], vs[0][1])
                g = dict(type="Point", coordinates=[round(lon, 7), round(lat, 7)])
            else:
                if len(vs) < 2:
                    continue
                coords = [[round(a, 7), round(b, 7)]
                          for a, b in (TO_WGS.transform(x, y) for x, y in vs)]
                g = dict(type="LineString", coordinates=coords)
            feats.append(dict(type="Feature", geometry=g,
                              properties=dict(category=cat, layer=layer)))
    return dict(type="FeatureCollection", features=feats)


def render_pdf(geom, alignment, rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    STYLE = {
        "structures": ("#9E2B25", 0.9, 2.4), "religious": ("#6B2D8C", 1.0, 16),
        "rail":       ("#14181A", 1.0, 2.6),  "gas":        ("#C8791A", 0.9, 10),
        "drainage":   ("#1B6E8F", 0.7, 4),   "electrical": ("#B08A00", 0.6, 2.2),
        "telecom":    ("#2C6249", 0.7, 5),   "water":      ("#3B7FA8", 0.9, 12),
        "geotech":    ("#5C6663", 0.8, 9),   "vegetation": ("#3E7A3E", 0.45, 1.6),
        "median":     ("#8B938E", 0.8, 1.0), "carriageway": ("#C2C7C1", 0.9, 0.7),
    }
    fig, (ax, axp) = plt.subplots(
        2, 1, figsize=(11.7, 16.5), height_ratios=[3.1, 1],
        gridspec_kw=dict(hspace=0.20))
    fig.patch.set_facecolor("#FAFBF8")

    for cat in ("carriageway", "median", "vegetation", "electrical", "structures",
                "drainage", "telecom", "geotech", "water", "gas", "rail", "religious"):
        col, alpha, size = STYLE[cat]
        for layer, kind, vs in geom.get(cat, []):
            if kind == "line" and len(vs) > 1:
                xs, ys = zip(*vs)
                ax.plot(xs, ys, color=col, lw=size, alpha=alpha, solid_capstyle="round")
            elif kind == "point":
                ax.plot(vs[0][0], vs[0][1], ".", color=col, ms=math.sqrt(size) * 2.2,
                        alpha=alpha)

    ax_x, ax_y = zip(*alignment)
    ax.plot(ax_x, ax_y, color="#FAFBF8", lw=6.5, alpha=.95, zorder=5,
            solid_capstyle="round")
    ax.plot(ax_x, ax_y, color="#14181A", lw=2.2, alpha=1, zorder=6,
            solid_capstyle="round")
    ax.set_aspect("equal")
    ax.set_facecolor("#FAFBF8")
    for s in ax.spines.values():
        s.set_color("#D5D9D4")
    ax.tick_params(labelsize=7, colors="#5C6663")
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.set_xlabel("Easting, EPSG:32643 (m)", fontsize=8, color="#5C6663")
    ax.set_ylabel("Northing, EPSG:32643 (m)", fontsize=8, color="#5C6663")
    ax.set_title("Corridor Constraint Atlas — pier-siting constraint set",
                 fontsize=15, color="#14181A", loc="left", pad=14, fontweight="bold")

    # north arrow and scale bar, both required on a survey sheet
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    nx, ny = x1 - (x1 - x0) * .07, y1 - (y1 - y0) * .10
    ax.annotate("N", xy=(nx, ny + (y1 - y0) * .045), xytext=(nx, ny),
                ha="center", fontsize=11, color="#14181A", fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color="#14181A", lw=1.6))
    bar = 500.0
    bx, by = x0 + (x1 - x0) * .06, y0 + (y1 - y0) * .05
    ax.plot([bx, bx + bar], [by, by], color="#14181A", lw=3, solid_capstyle="butt")
    ax.text(bx + bar / 2, by + (y1 - y0) * .009, f"{bar:.0f} m", ha="center",
            fontsize=8, color="#14181A")

    ax.legend(handles=[Line2D([], [], color=STYLE[c][0], lw=2.4, label=c)
                       for c in STYLE] +
                      [Line2D([], [], color="#14181A", lw=2.2, label="alignment")],
              loc="center left", fontsize=7.5, frameon=True, facecolor="#FAFBF8",
              edgecolor="#D5D9D4", framealpha=.94, ncol=1, handlelength=1.5,
              labelspacing=.55, borderpad=.7)

    ch = [r["chainage_m"] / 1000 for r in rows]
    sc = [r["score"] for r in rows]
    hd = [r["hard"] for r in rows]
    axp.fill_between(ch, sc, color="#8B938E", alpha=.30, label="all constraints (weighted)")
    axp.plot(ch, sc, color="#8B938E", lw=.9)
    axp.fill_between(ch, [h * 5 for h in hd], color="#9E2B25", alpha=.55,
                     label="hard only: buildings, temples, rail, gas")
    clear = [c for c, h in zip(ch, hd) if h == 0]
    axp.plot(clear, [0] * len(clear), "|", color="#2C6249", ms=7, mew=1.4,
             label=f"no hard constraint ({len(clear)} of {len(rows)} stations)")
    axp.set_facecolor("#FAFBF8")
    axp.set_xlabel("chainage along alignment (km)", fontsize=9, color="#5C6663")
    axp.set_ylabel("constraint score", fontsize=9, color="#5C6663")
    axp.set_title(f"Constraint profile — what sits within a {PIER_RADIUS_M:.0f} m pier "
                  f"footprint, every {STATION_M:.0f} m",
                  fontsize=10.5, loc="left", color="#14181A", pad=8)
    axp.tick_params(labelsize=8, colors="#5C6663")
    for s in axp.spines.values():
        s.set_color("#D5D9D4")
    axp.legend(fontsize=8, frameon=True, facecolor="#FAFBF8", edgecolor="#D5D9D4",
               loc="upper right", framealpha=.94)

    fig.text(0.5, 0.012,
             "Source: JDA survey drawing 'mansrover road final.dwg', converted to DXF "
             "and read directly.  CRS EPSG:32643 (UTM 43N).  "
             "Severity weighting is a stated judgement, not a measurement.",
             ha="center", fontsize=7.5, color="#5C6663")
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    if DXF is None:
        raise SystemExit("No DXF in 00_source/dxf/ — convert the DWG first.")
    print(f"reading {DXF.name} ...")
    geom = read_geometry(DXF)

    print(f"\n{'CATEGORY':<14}{'LAYERS':<8}{'FEATURES':>10}{'VERTICES':>10}")
    print("-" * 44)
    for cat in sorted(geom, key=lambda c: -len(geom[c])):
        items = geom[cat]
        print(f"{cat:<14}{len({l for l,_,_ in items}):<8}{len(items):>10,}"
              f"{sum(len(v) for _,_,v in items):>10,}")
    print("-" * 44)
    print(f"{'TOTAL':<14}{'':<8}{sum(len(v) for v in geom.values()):>10,}")

    align = longest_alignment(geom)
    rows, n_obs = profile(geom, align)
    length_km = rows[-1]["chainage_m"] / 1000

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "atlas.geojson").write_text(json.dumps(to_geojson(geom)))
    # full inventory, distinct from what the profile counts near the alignment
    (OUT_DATA / "atlas_summary.json").write_text(json.dumps(dict(
        alignment_km=round(length_km, 2),
        categories={cat: dict(features=len(items),
                              layers=sorted({l for l, _, _ in items}))
                    for cat, items in sorted(geom.items())})))
    (OUT_DATA / "constraint_profile.json").write_text(json.dumps(
        [{k: r[k] for k in ("chainage_m", "constraints", "n", "score", "hard")} for r in rows]))

    clear = [r for r in rows if r["hard"] == 0]
    worst = sorted(rows, key=lambda r: -r["score"])[:8]
    print(f"\nalignment length : {length_km:.2f} km, {len(rows)} stations at {STATION_M:.0f} m")
    print(f"obstacles tested : {n_obs:,}")
    any_clear = [r for r in rows if r["score"] == 0]
    print(f"stations with nothing at all inside a {PIER_RADIUS_M:.0f} m pier footprint : "
          f"{len(any_clear)}/{len(rows)} ({100*len(any_clear)/len(rows):.0f}%)")
    print(f"stations with no HARD constraint (building/temple/rail/gas)      : "
          f"{len(clear)}/{len(rows)} ({100*len(clear)/len(rows):.0f}%)")

    print(f"\nmost constrained stations:")
    print(f"  {'chainage':>10}{'score':>7}   what is in the way")
    for r in worst:
        what = ", ".join(f"{k} x{v}" for k, v in sorted(r["constraints"].items(),
                                                        key=lambda kv: -kv[1]))
        print(f"  {r['chainage_m']:>9,.0f}m{r['score']:>7}   {what}")

    runs, cur = [], None
    for r in rows:
        if r["hard"] == 0:
            cur = cur or r["chainage_m"]
        elif cur is not None:
            runs.append((cur, r["chainage_m"] - cur)); cur = None
    if cur is not None:
        runs.append((cur, rows[-1]["chainage_m"] - cur))
    runs.sort(key=lambda t: -t[1])
    print(f"\nlongest runs free of hard constraints (candidate pier zones):")
    for start, ln in runs[:6]:
        print(f"  ch {start:>7,.0f} m  for {ln:>5,.0f} m")

    pdf = OUT / "corridor_constraint_atlas.pdf"
    render_pdf(geom, align, rows, pdf)
    print(f"\nwritten: {pdf}")
    print(f"written: {OUT_DATA/'atlas.geojson'}")
    print(f"written: {OUT_DATA/'constraint_profile.json'}")
