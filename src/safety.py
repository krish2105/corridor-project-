"""
safety.py — conflict points, exposure, and what the scheme does to both.

THE ARGUMENT THIS EXISTS TO TEST
A signal-free scheme is usually sold as safer: no signals, no red-light running, fewer
stops. The engineering question is narrower and answerable from geometry plus the counts
we already hold: does removing the signals REMOVE conflicts, or RELOCATE them?

Conflict points are counted geometrically rather than quoted from a textbook. Each of the
twelve movements is a chord across the junction from its entry to its exit, offset to the
left of the centreline because India drives on the left. Two chords conflict when they
cross; two movements sharing an exit merge; two sharing an entry diverge. The standard
four-arm result falls out of that construction rather than being asserted, which is the
point - the same construction then runs on the scheme's geometry, where nothing standard
applies.

EXPOSURE, NOT JUST COUNT
A conflict point where two streams of 30 veh/hr meet is not the same hazard as one where
two streams of 1,500 meet. Crash frequency in the literature goes broadly with the
product of the conflicting flows, so every point carries the product of the two movements
that create it. Counting points alone would make the scheme look better than it is,
because it removes many small conflicts and adds a few enormous ones.

WHAT THIS IS NOT
Not a crash prediction. There is no accident data for this corridor, and none is
invented. This is exposure - the opportunity for conflict - which is what geometry and
flow can honestly support. Reported as a ratio between schemes, never as an absolute
casualty figure.

Run:  uv run python src/safety.py
"""
import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import JUNCTIONS, JUNCTION_COORDS, OUT_DATA

# Arms are listed clockwise from north, so arm i sits at bearing 90*i degrees.
# India drives on the LEFT, so a vehicle enters on the left of its arm and leaves on the
# left of the exit arm. That offset is what decides which chords actually cross: without
# it, a left turn and the opposing right turn appear to conflict when they do not.
SIDE = -1.0          # left-hand traffic
OFFSET = 0.22        # lane offset as a fraction of the junction radius


def _endpoints(arm_index, entering):
    """
    Where a movement touches the junction circle, in unit coordinates.

    Entering and leaving on the same arm use opposite sides of the centreline.
    """
    import math
    a = math.radians(90 * arm_index)
    # outward unit vector along the arm, and the perpendicular
    ox, oy = math.sin(a), math.cos(a)
    px, py = math.cos(a), -math.sin(a)
    s = SIDE * OFFSET * (1 if entering else -1)
    return (ox + px * s, oy + py * s)


def _crosses(p1, p2, q1, q2):
    """Proper segment intersection, excluding shared endpoints."""
    def side(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2 = side(q1, q2, p1), side(q1, q2, p2)
    d3, d4 = side(p1, p2, q1), side(p1, p2, q2)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def movements_of(n_arms=4):
    """(entry, exit) for every movement except the U-turn, which is not surveyed."""
    return [(i, j) for i in range(n_arms) for j in range(n_arms) if i != j]


def conflict_points(movements, n_arms=4):
    """
    Classify every pair of movements as crossing, merging, diverging or none.

    Returns a list of dicts so each point can carry the flows that create it.
    """
    paths = {m: (_endpoints(m[0], True), _endpoints(m[1], False)) for m in movements}
    out = []

    # Crossing points: one per pair of paths that actually cross.
    for a, b in combinations(movements, 2):
        if a[0] == b[0] or a[1] == b[1]:
            continue                     # shares an entry or exit; handled below
        if _crosses(*paths[a], *paths[b]):
            out.append(dict(a=a, b=b, kind="crossing"))

    # Diverging and merging points are PHYSICAL LOCATIONS, not pairs.
    #
    # Three movements leaving one arm do not create three diverging points. The stream
    # splits one movement at a time, so n movements produce n-1 splits: the left turn
    # peels off first, then the straight separates from the right. Counting pairs gives
    # C(3,2)=3 per arm and a 40-point total; counting splits gives 2 per arm and the
    # 32 that every text on four-leg intersections reports. The textbook figure is the
    # check that caught this.
    #
    # Each split carries the two streams that separate AT it, so the exposure weighting
    # stays physical: the first point separates the left turn from everything still
    # together behind it.
    def _chain(group, key, kind):
        for arm in sorted({m[key] for m in group}):
            here = sorted([m for m in group if m[key] == arm],
                          key=lambda m: (m[1] - m[0]) % n_arms)
            for i in range(len(here) - 1):
                out.append(dict(a=here[i], b=tuple(here[i + 1:]), kind=kind,
                                arm=arm, order=i))

    _chain(movements, 0, "diverging")
    _chain(movements, 1, "merging")
    return out


def exposure(points, flows):
    """
    Weight each conflict point by the product of the two flows that create it.

    flows: {(entry, exit): veh/hr}. Returned in millions of vehicle-pairs per hour
    squared, which is meaningless as an absolute and meaningful as a ratio - which is
    the only way it is ever reported.
    """
    def side(x):
        # a crossing point has a single movement each side; a split or merge has one
        # movement separating from everything still travelling together
        if isinstance(x, tuple) and x and isinstance(x[0], tuple):
            return sum(flows.get(m, 0.0) for m in x)
        return flows.get(x, 0.0)

    total = {"crossing": 0.0, "merging": 0.0, "diverging": 0.0}
    for p in points:
        total[p["kind"]] += side(p["a"]) * side(p["b"])
    return {k: v / 1e6 for k, v in total.items()}


def scheme_conflicts(flows, n_arms=4):
    """
    The JDA scheme: right turns removed from the junction and re-made as U-turns.

    The right-turn demand does not vanish, so it is carried to a mid-block opening where
    it crosses the opposing through stream with nothing metering it. The junction gets
    safer; the link does not.
    """
    kept = [m for m in movements_of(n_arms) if (m[1] - m[0]) % n_arms != 3]
    junction = conflict_points(kept, n_arms)
    junction_exp = exposure(junction, flows)

    # each U-turn crosses the opposing through movement at its opening
    uturn = []
    for entry in range(n_arms):
        right = (entry, (entry + 3) % n_arms)
        opposing_through = ((entry + 2) % n_arms, entry)
        uturn.append(dict(a=right, b=opposing_through, kind="crossing",
                          where="mid-block U-turn opening"))
    uturn_exp = exposure(uturn, flows)
    return dict(junction=junction, junction_exposure=junction_exp,
                uturn=uturn, uturn_exposure=uturn_exp,
                total_exposure={k: junction_exp[k] + uturn_exp[k] for k in junction_exp})


if __name__ == "__main__":
    from src.tmc_parse import parse_all
    from src.analyse import movements as mv_frame

    bins, _ = parse_all()
    day = sorted(bins.date.unique())[0]
    mv = bins[(bins.kind == "movement") & (bins.date == day)]

    base = movements_of(4)
    pts = conflict_points(base)
    counts = {k: sum(1 for p in pts if p["kind"] == k)
              for k in ("crossing", "merging", "diverging")}

    print("=== Conflict points, four-arm junction, twelve movements ===")
    print("  Counted from geometry, not quoted. Chords are offset to the left of the")
    print("  centreline because India drives on the left.\n")
    for k, v in counts.items():
        print(f"  {k:<12}{v:>4}")
    print(f"  {'TOTAL':<12}{sum(counts.values()):>4}")
    ok = sum(counts.values()) == 32 and counts["crossing"] == 16
    print(f"\n  Every text on four-leg intersections reports 32: 16 crossing, 8 merging,")
    print(f"  8 diverging. This construction returns {sum(counts.values())} "
          f"({counts['crossing']}/{counts['merging']}/{counts['diverging']}). "
          f"{'It agrees.' if ok else 'IT DOES NOT AGREE - the geometry is wrong.'}\n")

    rows, corridor = [], {}
    for code, g in mv.groupby("junction"):
        arms = JUNCTIONS[code]
        idx = {a: i for i, a in enumerate(arms)}
        tot = g.groupby("bin_start")["count"].sum().sort_index()
        i = max(range(len(tot) - 3), key=lambda k: tot.iloc[k:k + 4].sum())
        peak = tot.index[i:i + 4]
        pk = g[g.bin_start.isin(peak)]
        flows = {}
        for (fr, to), gg in pk.groupby(["arm_from", "arm_to"]):
            if fr in idx and to in idx:
                flows[(idx[fr], idx[to])] = float(gg["count"].sum())

        today = exposure(pts, flows)
        scheme = scheme_conflicts(flows)
        rows.append(dict(
            junction=code, jda_name=JUNCTION_COORDS[code][2],
            peak_veh=round(sum(flows.values())),
            today_points=sum(counts.values()),
            today_crossing_exposure=round(today["crossing"], 1),
            scheme_junction_points=len(scheme["junction"]),
            scheme_crossing_exposure=round(scheme["total_exposure"]["crossing"], 1),
            uturn_crossing_exposure=round(scheme["uturn_exposure"]["crossing"], 1),
            change_pct=round(100 * (scheme["total_exposure"]["crossing"] - today["crossing"])
                             / today["crossing"], 1) if today["crossing"] else None))
        corridor[code] = rows[-1]

    print("=== Crossing-conflict exposure, today vs the signal-free scheme ===")
    print("  Exposure is the product of the two conflicting flows, summed. An absolute")
    print("  value means nothing; the ratio between two schemes is the finding.\n")
    print(f"  {'junction':<10}{'name':<14}{'points now':>11}{'points after':>13}"
          f"{'exposure now':>14}{'after':>10}{'change':>9}")
    print("  " + "-" * 82)
    for r in rows:
        print(f"  {r['junction']:<10}{r['jda_name']:<14}{r['today_points']:>11}"
              f"{r['scheme_junction_points']:>13}{r['today_crossing_exposure']:>14,.0f}"
              f"{r['scheme_crossing_exposure']:>10,.0f}{r['change_pct']:>8.0f}%")

    worse = sum(1 for r in rows if r["change_pct"] and r["change_pct"] > 0)
    mean_change = sum(r["change_pct"] for r in rows if r["change_pct"]) / len(rows)
    print(f"\n  GATE - junctions where crossing exposure RISES under the scheme: "
          f"**{worse} of {len(rows)}**")
    print(f"  mean change in crossing exposure: {mean_change:+.0f}%")
    print("\n  The scheme removes right turns from the junction, which genuinely removes")
    print("  conflict points there. It does not remove the demand. Every one of those")
    print("  vehicles reappears at a mid-block opening, crossing the opposing through")
    print("  stream with no signal to meter it and no junction geometry to slow it.")
    print("  Conflicts are relocated from a controlled place to an uncontrolled one.")

    print("\n=== Pedestrians ===")
    print("  The survey contains no pedestrian column. Not a low count - no column.")
    print("  On a corridor whose signals are being removed this is the sharpest gap in")
    print("  the dataset: the red phase is the only protected crossing opportunity a")
    print("  pedestrian currently has, and the scheme removes it without ever having")
    print("  measured who uses it.")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "safety.json").write_text(json.dumps(dict(
        method="geometric conflict-point construction, flow-weighted exposure",
        caveat="exposure, not crash prediction; no accident data exists for this corridor",
        base_counts=counts, base_total=sum(counts.values()),
        junctions=rows, junctions_worse=worse, mean_change_pct=round(mean_change, 1),
        pedestrian_column_present=False,
    ), indent=1))
    print(f"\nwritten: {OUT_DATA/'safety.json'}")
