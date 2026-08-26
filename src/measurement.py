"""
measurement.py — how precise is every dimension we publish, and what would fix it.

THE QUESTION THIS ANSWERS
The drawing JDA supplied carries no dimension entities. Every width, offset, chainage and
detour in this pipeline is therefore SCALED off georeferenced linework, and a number
scaled off linework and printed to one decimal place looks exactly like a number that was
measured. This module makes the difference visible: for each published dimension, how it
was derived, how repeatable that derivation is, and what a field survey would resolve.

THE TEST THAT MATTERS IS THE METHOD AGAINST ITSELF
An estimate whose value depends on an arbitrary choice inside the method is not a
measurement of the road, it is a measurement of the choice. The transect method walks the
alignment at a fixed step and takes the median of what it finds near each junction, so the
step is exactly such a choice. Re-running across steps says whether the answer has
converged or is still moving.

WHAT IT FOUND, AND WHY capacity.py CHANGED
At a 25 m step the whole corridor yields 18 usable transects - one to three per junction -
and the median of two numbers is not a width. TMC-01 read 11.7 m there and 15.7 m at every
finer step, a 33% difference that flows straight into lanes, capacity, v/c and design life.
The step is now 5 m, inside the converged region, and the convergence table is published
so the choice can be checked rather than trusted.

Run:  uv run python src/measurement.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.atlas import longest_alignment, read_geometry
from src.capacity import DXF, WIDE_TRANSECT_M, measure_widths
from src.config import JUNCTION_COORDS, OUT_DATA

# Steps to test, coarse to fine. The published step must sit where the answer has stopped
# moving, and "stopped" is defined below rather than judged by eye.
STEPS = (25.0, 10.0, 5.0, 2.0)
PUBLISHED_STEP = 5.0

# Two consecutive steps agreeing to within this are treated as converged. 0.3 m is a
# third of a lane marking's width - well inside anything that changes a lane count.
CONVERGED_M = 0.3

BOOTSTRAP = 2000
SEED = 20260511


def convergence():
    """Per-junction width at each step, and where it stops moving."""
    rows = {}
    for s in STEPS:
        w, st, _ = measure_widths(step=s)
        rows[s] = dict(widths={k: v[0] for k, v in w.items()},
                       counts={k: v[1] for k, v in w.items()}, stations=len(st))
    out = []
    for code in JUNCTION_COORDS:
        seq = [rows[s]["widths"].get(code) for s in STEPS]
        # the first step whose value agrees with the NEXT finer one
        conv = None
        for i in range(len(STEPS) - 1):
            a, b = seq[i], seq[i + 1]
            if a is not None and b is not None and abs(a - b) <= CONVERGED_M:
                conv = STEPS[i]
                break
        # A list of records, not a dict keyed by the step. The step is a VALUE here, and
        # keying on it puts "25.0" and "2.0" into the published schema as if they were
        # field names - which is exactly how the data dictionary read them.
        out.append(dict(junction=code, jda_name=JUNCTION_COORDS[code][2].strip(),
                        by_step=[dict(step_m=s, width_m=rows[s]["widths"].get(code),
                                      transects=rows[s]["counts"].get(code))
                                 for s in STEPS],
                        converged_at_step=conv,
                        spread_m=(round(max(x for x in seq if x is not None)
                                        - min(x for x in seq if x is not None), 2)
                                  if any(x is not None for x in seq) else None)))
    return out, rows


def bootstrap_width(step=PUBLISHED_STEP, band=400.0):
    """
    Confidence interval on each junction's median width, from its own transects.

    The estimator is a median over the transects within `band` of the junction, so the
    interval is a resample of exactly those. It measures how much the answer depends on
    WHICH transects happened to land, which is the sampling error - it says nothing about
    whether the kerb linework is in the right place. That is the registration check below.
    """
    from pyproj import Transformer
    _w, stations, _t = measure_widths(step=step)
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    rng = np.random.default_rng(SEED)
    out = []
    for code, (lat, lon, *_r) in JUNCTION_COORDS.items():
        jx, jy = to_utm.transform(lon, lat)
        near = np.array([w for _c, p, w in stations
                         if (p[0] - jx) ** 2 + (p[1] - jy) ** 2 <= band ** 2])
        if len(near) == 0:
            out.append(dict(junction=code, n=0, median_m=None, ci_m=None, unquantified=
                            "no transect within the band; width not measurable here"))
            continue
        boot = [float(np.median(rng.choice(near, len(near)))) for _ in range(BOOTSTRAP)]
        lo, hi = np.percentile(boot, [2.5, 97.5])
        out.append(dict(junction=code, n=int(len(near)),
                        median_m=round(float(np.median(near)), 2),
                        ci_m=[round(float(lo), 2), round(float(hi), 2)],
                        ci_width_m=round(float(hi - lo), 2),
                        min_m=round(float(near.min()), 2), max_m=round(float(near.max()), 2),
                        above_wide_threshold=bool(np.median(near) > WIDE_TRANSECT_M)))
    return out


def registration(step=25.0):
    """
    Do JDA's KML centreline and JDA's CAD drawing agree about where the road is?

    Two independently produced descriptions of the same corridor. Neither is checked
    against ground truth here - what is measured is whether they are consistent, and by
    how much. A systematic offset would mean every chainage and every transect is placed
    against a centreline the drawing does not share.
    """
    geom = read_geometry(DXF)
    align = longest_alignment(geom)
    segs = []
    for cat in ("median", "carriageway"):
        for layer, kind, vs in geom.get(cat, []):
            if kind == "line" and len(vs) > 1:
                segs.extend(((vs[i], vs[i + 1], cat) for i in range(len(vs) - 1)))

    cell = 60.0
    grid = {}
    for a, b, cat in segs:
        for gx in {int(a[0] // cell), int(b[0] // cell)}:
            for gy in {int(a[1] // cell), int(b[1] // cell)}:
                grid.setdefault((gx, gy), []).append((a, b, cat))

    def seg_dist(p, a, b):
        ax, ay, bx, by = a[0], a[1], b[0], b[1]
        ex, ey = bx - ax, by - ay
        L2 = ex * ex + ey * ey
        if L2 == 0:
            return math.dist(p, a)
        t = max(0.0, min(1.0, ((p[0] - ax) * ex + (p[1] - ay) * ey) / L2))
        return math.dist(p, (ax + t * ex, ay + t * ey))

    d_med, d_kerb = [], []
    for i in range(len(align) - 1):
        a, b = align[i], align[i + 1]
        L = math.dist(a, b)
        for k in range(max(1, int(L // step))):
            t = k / max(1, int(L // step))
            p = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
            gx, gy = int(p[0] // cell), int(p[1] // cell)
            near = [s for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    for s in grid.get((gx + dx, gy + dy), ())]
            m = [seg_dist(p, s[0], s[1]) for s in near if s[2] == "median"]
            c = [seg_dist(p, s[0], s[1]) for s in near if s[2] == "carriageway"]
            if m:
                d_med.append(min(m))
            if c:
                d_kerb.append(min(c))

    def stat(v, label):
        if not v:
            return dict(feature=label, n=0, unquantified="no linework within reach")
        a = np.array(v)
        return dict(feature=label, n=int(len(a)),
                    median_m=round(float(np.median(a)), 2),
                    p90_m=round(float(np.percentile(a, 90)), 2),
                    max_m=round(float(a.max()), 2))
    return [stat(d_med, "nearest median/divider line"),
            stat(d_kerb, "nearest carriageway kerb line")]


def register(conv, boot, reg):
    """
    Every published dimension, with its method and its uncertainty.

    A dimension with a number and no uncertainty is the failure this table exists to
    prevent, so one that cannot be quantified says so and says why, rather than being
    left out.
    """
    ci = [r["ci_width_m"] for r in boot if r.get("ci_width_m") is not None]
    med_reg = next((r for r in reg if r["feature"].startswith("nearest median")), {})
    return [
        dict(dimension="Carriageway width per direction",
             used_for="lane count, approach capacity, v/c, design life, queue length",
             method=f"perpendicular transects every {PUBLISHED_STEP:.0f} m, median within "
                    f"400 m of the junction; total kerb-to-kerb less the median, halved",
             uncertainty=(f"95% bootstrap interval {min(ci):.1f} to {max(ci):.1f} m wide "
                          f"across the six junctions") if ci else "not quantified",
             resolved_by="total station cross-sections at each junction and mid-block"),
        dict(dimension="Transect step",
             used_for="every width above",
             method=f"{PUBLISHED_STEP:.0f} m, chosen where the answer stops moving",
             uncertainty=(f"convergence tested at {', '.join(f'{s:g}' for s in STEPS)} m; "
                          f"junctions converged: "
                          f"{sum(1 for c in conv if c['converged_at_step'])} of {len(conv)}"),
             resolved_by="not applicable - this is a property of the method, not the road"),
        dict(dimension="Corridor chainage and length",
             used_for="junction ordering, U-turn detours, pier siting stations",
             method="cumulative distance along JDA's KML centreline in EPSG:32643",
             uncertainty="the KML carries 14 vertices over 4,625 m, so curvature between "
                         "vertices is cut off; the polyline is a lower bound on true length",
             resolved_by="a surveyed centreline string, or the CAD alignment once its "
                         "layer is identified"),
        dict(dimension="KML against CAD registration",
             used_for="the assumption that chainage and transects share one geometry",
             method="distance from each centreline station to the nearest CAD linework",
             uncertainty=(f"median {med_reg.get('median_m')} m to the nearest divider line, "
                          f"90th percentile {med_reg.get('p90_m')} m"
                          if med_reg.get("median_m") is not None else "not quantified"),
             resolved_by="a common control point in both, or a stated CAD georeference"),
        dict(dimension="Median opening width",
             used_for="whether a U-turn is physically possible at an opening",
             method="gap between consecutive DIVIDER runs, measured along the alignment",
             uncertainty="not quantified per opening - the DIVIDER layer is a single "
                         "polyline set with no separate edge, so an opening's width has "
                         "no second reading to compare against",
             resolved_by="total station at each opening: nose to nose, and the receiving "
                         "carriageway width opposite"),
        dict(dimension="U-turn detour distance",
             used_for="vehicle-km imposed by the scheme",
             method="junction chainage to the nearest U-turn-capable opening, doubled",
             uncertainty="carries the chainage uncertainty above, doubled; and 3 of 12 "
                         "bays lie beyond the drawing so their detour is not measured "
                         "at all rather than estimated",
             resolved_by="the seven proposed bay chainages from JDA"),
        dict(dimension="Constraint offsets in the atlas",
             used_for="pier siting, clear-run identification",
             method="perpendicular distance from the alignment to each constraint feature",
             uncertainty="inherits the registration figure above; feature positions are "
                         "CAD vertices with no stated survey accuracy",
             resolved_by="the drawing's own survey control sheet, if one exists"),
    ]


def _main():
    conv, by_step = convergence()
    boot = bootstrap_width()
    reg = registration()
    rows = register(conv, boot, reg)

    print("=== Measurement register ===")
    print("  The DWG carries no dimension entities. Every dimension below is scaled off")
    print("  georeferenced linework, so each one is published with how it was derived.\n")

    print("--- Does the width estimate depend on the transect step? ---")
    hdr = "".join(f"{s:>9g} m" for s in STEPS)
    print(f"  {'junction':<10}{'name':<13}{hdr}{'spread':>9}{'converges':>11}")
    print("  " + "-" * 76)
    for c in conv:
        vals = "".join(
            (f"{r['width_m']:>11.1f}" if r["width_m"] is not None else f"{'-':>11}")
            for r in c["by_step"])
        cv = f"{c['converged_at_step']:g} m" if c["converged_at_step"] else "NOT YET"
        print(f"  {c['junction']:<10}{c['jda_name']:<13}{vals}{c['spread_m']:>9.1f}{cv:>11}")
    print(f"\n  transects found: " +
          "  ".join(f"{s:g} m -> {by_step[s]['stations']}" for s in STEPS))
    print(f"  Published step is {PUBLISHED_STEP:g} m. At 25 m the corridor yields "
          f"{by_step[25.0]['stations']} transects in total,")
    print("  one to three per junction, and the median of two numbers is not a width.")

    print("\n--- How much does each width depend on which transects landed? ---")
    print(f"  {'junction':<10}{'n':>4}{'median':>9}{'95% interval':>18}"
          f"{'range seen':>18}{'wide?':>7}")
    print("  " + "-" * 68)
    for r in boot:
        if r.get("median_m") is None:
            print(f"  {r['junction']:<10}{0:>4}   {r['unquantified']}")
            continue
        print(f"  {r['junction']:<10}{r['n']:>4}{r['median_m']:>9.1f}"
              f"{r['ci_m'][0]:>11.1f}-{r['ci_m'][1]:<6.1f}"
              f"{r['min_m']:>11.1f}-{r['max_m']:<6.1f}"
              f"{'yes' if r['above_wide_threshold'] else 'no':>7}")
    wide = sum(1 for r in boot if r.get("above_wide_threshold"))
    print(f"\n  {wide} of {len(boot)} junctions measure over {WIDE_TRANSECT_M:.0f} m per")
    print("  direction, which is five running lanes each way or a service road being read")
    print("  as carriageway. Capacity scales linearly with the answer.")

    print("\n--- Do JDA's KML and JDA's CAD agree about where the road is? ---")
    for r in reg:
        if r.get("n"):
            print(f"  {r['feature']:<34}median {r['median_m']:>6.2f} m   "
                  f"p90 {r['p90_m']:>6.2f} m   max {r['max_m']:>7.2f} m   n={r['n']}")
        else:
            print(f"  {r['feature']:<34}{r['unquantified']}")

    print("\n--- Every published dimension ---")
    for r in rows:
        print(f"\n  {r['dimension']}")
        print(f"    used for    : {r['used_for']}")
        print(f"    method      : {r['method']}")
        print(f"    uncertainty : {r['uncertainty']}")
        print(f"    resolved by : {r['resolved_by']}")

    missing = [r["dimension"] for r in rows if not r["uncertainty"]]
    print(f"\n  GATE - published dimensions carrying a stated uncertainty: "
          f"**{len(rows) - len(missing)} of {len(rows)}**")
    if missing:
        raise SystemExit(f"dimension published with no uncertainty: {missing}")

    print("\n  None of this substitutes for a field survey. What to commission: a total")
    print("  station traverse on the corridor with cross-sections at each junction and at")
    print("  every median opening, tied to a stated control, delivering opening nose-to-")
    print("  nose widths, receiving carriageway widths, and the seven proposed bay")
    print("  chainages. Until then every width here is provisional and says so.")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "measurement.json").write_text(json.dumps(dict(
        source="JDA survey drawing (DWG converted to DXF); no dimension entities present",
        published_step_m=PUBLISHED_STEP, steps_tested=list(STEPS),
        converged_tolerance_m=CONVERGED_M,
        convergence=conv,
        transects_by_step=[dict(step_m=s, transects=by_step[s]["stations"])
                           for s in STEPS],
        bootstrap=boot, bootstrap_resamples=BOOTSTRAP,
        registration=reg,
        dimensions=rows,
        junctions_above_wide_threshold=wide,
        wide_threshold_m=WIDE_TRANSECT_M,
        status=("provisional: every dimension is scaled from georeferenced linework and "
                "a total station survey is required before design"),
    ), indent=1))
    print(f"\nwritten: {OUT_DATA/'measurement.json'}")


if __name__ == "__main__":
    _main()
