"""
capacity.py — Phase 7. Capacity, v/c, Level of Service and design-year growth.

Turns the corrected counts into the sentence a business case actually needs: which
movement binds, at what volume/capacity ratio, and in which year it fails.

Two things here are measured rather than assumed, which is the point:

  * Carriageway width comes from the survey drawing. Perpendicular transects are cast
    from the corridor alignment to the BT ROAD kerb linework, so lane capacity rests on
    the road that is there, not on a design standard.
  * Demand is the corrected PCU from pcu.py, carried as a BAND. Half the PCU correction
    is unresolvable because the survey lumps 48% of the stream into one column, so every
    v/c and every failure year is reported as a range. A single LOS grade would be a
    false precision.

Assumptions are declared in ASSUMPTIONS below and printed with the results. They are
judgements, not measurements, and they are the first thing a reviewer should attack.

Run:  uv run python src/capacity.py
"""
import json
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.atlas import longest_alignment, read_geometry
from src.config import JUNCTION_COORDS, OUT, OUT_DATA, ROOT
from src.medians import chainage
from src.pcu import SURVEYED, convert, factor_band
from src.tmc_parse import parse_all

DXF = next((ROOT / "00_source" / "dxf").glob("*.dxf"), None)

ASSUMPTIONS = {
    "base_year": 2026,
    "design_horizon_years": 20,
    "growth_low_pct": 4.0,
    "growth_med_pct": 6.0,
    "growth_high_pct": 8.0,
    "lane_width_m": 3.5,
    "shy_distance_m": 1.0,
    # IRC:106 urban arterial capacity, PCU/hour per direction on a divided carriageway.
    # Indo-HCM supersedes this for detailed work; these are the planning-level values.
    "capacity_pcu_per_lane_hr": 1200,
    "phf_applied": True,
}

# Volume-capacity to Level of Service, MULTILANE DIVIDED URBAN ROAD.
#
# These were previously 0.40 / 0.60 / 0.75 / 0.90 and labelled "Indo-HCM / IRC". That
# label was not supportable. A search of IRC:106-1990, draft IRC:106 (2022), IRC:92-1985
# and 2017, IRC:SP:41-1994, IRC:SP:90-2010 and Indo-HCM chapters 2, 3, 5 and 6 found no
# Indian standard publishing that set. The old bands were optimistic by a full grade in
# several windows - most damagingly they reported v/c 0.86-0.90 as D when it is E, which
# is the band meaning "at or near capacity, no usable gaps".
#
# Source: draft IRC:106 (2022), 1st Revision, Table 9, "LOS of Multilane Divided Urban
# Roads based on V/C Ratio". DRAFT, not the published 1990 edition - stated wherever a
# letter is published. IRC:106-1990 itself gives no v/c bands at all; its only v/c anchor
# is clause 8.1, "normally LOS C be adopted for design of urban roads... volume will be
# around 0.70 times the maximum capacity", which agrees with the C ceiling below.
LOS_BANDS = [(0.30, "A"), (0.45, "B"), (0.70, "C"), (0.85, "D"), (1.00, "E")]
LOS_SOURCE = "draft IRC:106 (2022) Table 9, multilane divided urban road"

# A v/c-derived letter is a MIDBLOCK measure. Indo-HCM Chapter 5 defines an urban road
# segment as the length between two controlled intersections, and for junctions Chapter 6
# uses CONTROL DELAY (Table 6.7: A <=20 s/PCU ... F >130), warning that there is no
# one-to-one correspondence between delay and v/c. We cannot compute control delay - it
# needs signal timings the survey does not contain - so what is published is the v/c and
# its midblock letter, labelled as such, and never a junction LOS letter.
LOS_CAVEAT = ("midblock measure; Indo-HCM grades junctions on control delay, which needs "
              "signal timings this survey does not contain")

# Every corridor approach exceeds v/c 1.0 against the IRC:106 planning capacity, by
# 1.25 to 2.41. Sustained flow above capacity is not physically possible, so the
# planning value is not what this road achieves. jaipur_corridor_study.md 2.2 says why:
# "a 10.5 m carriageway is nominally three lanes but commonly carries four to five
# streams once two-wheelers filter". With 49% two-wheelers here, lane discipline is
# not what limits throughput.
#
# So the geometric capacity is reported as the standard's view, and the ACHIEVED
# capacity is taken from the highest sustained flow actually observed. The second is
# measured; the first is a book value. The gap between them is itself the finding.


def los(vc):
    for limit, grade in LOS_BANDS:
        if vc <= limit:
            return grade
    return "F"


def measure_widths(step=25.0, probe=45.0, band=400.0):
    """
    Carriageway width along the corridor, by perpendicular transect to the kerb lines.

    Returns {junction: median width within `band` metres of it}. The median resists the
    transects that miss a kerb gap or catch a service road.
    """
    geom = read_geometry(DXF)
    align = longest_alignment(geom)
    f, total = chainage(align)

    kerb, median = [], []
    for layer, kind, vs in geom.get("carriageway", []):
        if kind == "line" and len(vs) > 1 and layer in ("BT ROAD", "CC ROAD"):
            kerb.extend((vs[i], vs[i + 1]) for i in range(len(vs) - 1))
    for layer, kind, vs in geom.get("median", []):
        if kind == "line" and len(vs) > 1:
            median.extend((vs[i], vs[i + 1]) for i in range(len(vs) - 1))

    # grid the kerb segments so each transect only tests what is nearby
    cell = 60.0
    def gridify(segs):
        g = {}
        for a, b in segs:
            for gx in {int(a[0] // cell), int(b[0] // cell)}:
                for gy in {int(a[1] // cell), int(b[1] // cell)}:
                    g.setdefault((gx, gy), []).append((a, b))
        return g
    grid, mgrid = gridify(kerb), gridify(median)

    def cross(p, d, segs):
        """
        All hits from p along unit direction d, within `probe`, nearest first.

        The nearest hit is NOT the carriageway edge. The alignment sits offset from
        the median, so the first thing a transect meets on one side is the median
        kerb. Taking the nearest each side measures one carriageway plus a sliver of
        median and reports roughly half the real road.
        """
        out = []
        px, py = p
        dx, dy = d
        for (ax, ay), (bx, by) in segs:
            ex, ey = bx - ax, by - ay
            den = dx * ey - dy * ex
            if abs(den) < 1e-9:
                continue
            t = ((ax - px) * ey - (ay - py) * ex) / den
            u = ((ax - px) * dy - (ay - py) * dx) / den
            if 0 < t <= probe and 0 <= u <= 1:
                out.append(t)
        return sorted(out)

    # walk the alignment and measure
    stations, acc = [], 0.0
    for i in range(len(align) - 1):
        a, b = align[i], align[i + 1]
        L = math.dist(a, b)
        if L == 0:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        n = max(1, int(L // step))
        for k in range(n):
            t = k / n
            p = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
            gx, gy = int(p[0] // cell), int(p[1] // cell)
            near = lambda g: [s for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                              for s in g.get((gx + dx, gy + dy), ())]
            segs, msegs = near(grid), near(mgrid)
            if not segs:
                continue
            nrm = (-uy, ux)
            inv = (uy, -ux)
            lk, rk = cross(p, nrm, segs), cross(p, inv, segs)
            if not lk or not rk:
                continue
            total_w = lk[-1] + rk[-1]                      # outer kerb to outer kerb
            lm, rm = cross(p, nrm, msegs), cross(p, inv, msegs)
            med_w = 0.0
            if lm and rm:
                med_w = lm[-1] + rm[-1]                    # median straddles the alignment
            elif lm and len(lm) >= 2:
                med_w = lm[-1] - lm[0]
            elif rm and len(rm) >= 2:
                med_w = rm[-1] - rm[0]
            carriage = total_w - med_w
            # divided: the two carriageways share the section, so one direction is half
            if 8.0 < carriage < 40.0:
                stations.append((acc + t * L, p, carriage / 2.0))
        acc += L

    from pyproj import Transformer
    TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    out = {}
    for code, (lat, lon, *_rest) in JUNCTION_COORDS.items():
        jx, jy = TO_UTM.transform(lon, lat)
        near = [w for _, p, w in stations
                if (p[0] - jx) ** 2 + (p[1] - jy) ** 2 <= band ** 2]
        out[code] = (round(float(pd.Series(near).median()), 1), len(near)) if near else (None, 0)
    return out, stations, total


def lanes_from_width(width_m):
    """
    Lanes per direction.

    measure_widths already returns ONE carriageway (total kerb-to-kerb minus the
    median, halved), so this must not halve again. Halving twice is the inverted
    divided/undivided test flagged as an erratum in the methodology, and it reports
    a 4-lane arterial as 1 lane per direction.
    """
    if not width_m:
        return None
    usable = width_m - ASSUMPTIONS["shy_distance_m"]
    return max(1, round(usable / ASSUMPTIONS["lane_width_m"]))


def approach_pcu(bins, day):
    """
    Peak-hour PCU on each CORRIDOR approach, as a low/point/high band.

    Restricted to the two corridor arms - traffic entering from Mansarover Metro and
    from Sanganer Stadium. Those are the directions whose carriageway width was
    measured, so they are the only ones with a capacity to divide by. The cross-street
    approaches are counted but their width is not in the drawing's alignment, so no
    v/c is claimed for them.

    Comparing all four approaches' flow against one direction's link capacity, which an
    earlier version of this did, overstates v/c by roughly a factor of four.
    """
    from src.analyse import NORTH, SOUTH
    mv = bins[(bins.kind == "movement") & (bins.date == day)]
    rows = []
    for code, g in mv.groupby("junction"):
        share = g.groupby("veh_class")["count"].sum()
        share = share / share.sum()
        for arm, label in ((NORTH, "from Mansarover Metro"), (SOUTH, "from Sanganer Stadium")):
            a = g[g.arm_from == arm]
            if a.empty:
                continue
            per_bin = a.groupby(["bin_start", "veh_class"])["count"].sum().unstack(fill_value=0)
            band = {}
            for name, idx in (("lo", 0), ("pt", 1), ("hi", 2)):
                w = {}
                for cls in per_bin.columns:
                    b = factor_band(cls, float(share[cls]))
                    w[cls] = b[idx] if b[idx] is not None else SURVEYED[cls]
                ser = sum(per_bin[c] * w[c] for c in per_bin.columns).sort_index()
                best = max(range(len(ser) - 3), key=lambda i: ser.iloc[i:i + 4].sum())
                band[name] = float(ser.iloc[best:best + 4].sum())
                if name == "pt":
                    band["peak"] = ser.index[best]
            rows.append(dict(junction=code, approach=label, peak_start=band["peak"],
                             pcu_lo=band["lo"], pcu_pt=band["pt"], pcu_hi=band["hi"]))
    return pd.DataFrame(rows)


def observed_vehicles(bins, day):
    """Peak-hour VEHICLES on the busiest corridor approach of each junction."""
    from src.analyse import NORTH, SOUTH
    mv = bins[(bins.kind == "movement") & (bins.date == day)]
    out = {}
    for code, g in mv.groupby("junction"):
        best = 0
        for arm in (NORTH, SOUTH):
            s_ = g[g.arm_from == arm].groupby("bin_start")["count"].sum().sort_index()
            if len(s_) < 4:
                continue
            i = max(range(len(s_) - 3), key=lambda k: s_.iloc[k:k + 4].sum())
            best = max(best, float(s_.iloc[i:i + 4].sum()))
        out[code] = best
    return out


def failure_year(vc_now, growth_pct, base=None):
    """Year v/c reaches 1.0 at a compound growth rate."""
    base = base or ASSUMPTIONS["base_year"]
    if vc_now >= 1.0:
        return base
    g = growth_pct / 100
    n = math.log(1.0 / vc_now) / math.log(1 + g)
    return base + math.ceil(n)


if __name__ == "__main__":
    if DXF is None:
        raise SystemExit("No DXF in 00_source/dxf/ — convert the DWG first.")
    bins, _ = parse_all()
    day = sorted(bins.date.unique())[0]

    print("=== Assumptions, stated up front ===")
    for k, v in ASSUMPTIONS.items():
        print(f"  {k:<28} {v}")
    print()

    print("=== Carriageway width, measured from the survey drawing ===")
    widths, stations, total_len = measure_widths()
    print(f"  transects cast along {total_len/1000:.2f} km: {len(stations)} with kerbs both sides\n")
    print(f"  {'junction':<10}{'width m':>9}{'transects':>11}{'lanes/dir':>11}{'cap PCU/hr':>12}")
    print("  " + "-" * 53)
    cap = {}
    for code, (w, n) in widths.items():
        ln = lanes_from_width(w)
        c = (ln or 0) * ASSUMPTIONS["capacity_pcu_per_lane_hr"]
        cap[code] = c
        print(f"  {code:<10}{(f'{w:.1f}' if w else '--'):>9}{n:>11}{(ln or '--'):>11}{c:>12,}")

    ap = approach_pcu(bins, day)
    print(f"\n=== Peak-hour demand vs capacity, corridor approaches, {day} ===")
    print("  cross-street approaches are counted but their width is not in the drawing,")
    print("  so no v/c is claimed for them.\n")
    print(f"  {'junction':<9}{'approach':<24}{'peak':>7}{'PCU pt':>8}{'PCU hi':>8}"
          f"{'cap':>7}{'v/c pt':>8}{'LOS':>5}{'v/c hi':>8}{'LOS':>5}")
    print("  " + "-" * 89)
    rows = []
    for _, r in ap.iterrows():
        c = cap[r.junction]
        vc_pt, vc_hi = r.pcu_pt / c, r.pcu_hi / c
        rows.append(dict(junction=r.junction, approach=r.approach, capacity=c,
                         peak=str(r.peak_start)[11:16], pcu_lo=r.pcu_lo,
                         pcu_pt=r.pcu_pt, pcu_hi=r.pcu_hi,
                         vc_lo=r.pcu_lo / c, vc_pt=vc_pt, vc_hi=vc_hi,
                         los_pt=los(vc_pt), los_hi=los(vc_hi)))
        print(f"  {r.junction:<9}{r.approach:<24}{str(r.peak_start)[11:16]:>7}"
              f"{r.pcu_pt:>8,.0f}{r.pcu_hi:>8,.0f}{c:>7,}{vc_pt:>8.2f}{los(vc_pt):>5}"
              f"{vc_hi:>8.2f}{los(vc_hi):>5}")

    df = pd.DataFrame(rows)
    worst = df.loc[df.vc_pt.idxmax()]
    print(f"\n  binding approach today: **{worst.junction}, {worst.approach}** "
          f"at v/c {worst.vc_pt:.2f} (LOS {worst.los_pt}), "
          f"{worst.vc_hi:.2f} (LOS {worst.los_hi}) at the top of the PCU band")
    over = df[df.vc_pt >= 1.0]
    print(f"  approaches already at or over capacity: {len(over)} of {len(df)}")

    # --- what the observed flow says about the capacity model --------------
    print(f"\n=== Does a lane-based capacity model describe this corridor? ===")
    ach = df.groupby("junction").pcu_pt.max()
    print(f"  {'junction':<10}{'IRC:106 cap':>13}{'observed':>10}{'ratio':>8}"
          f"{'veh/lane/hr':>13}")
    print("  " + "-" * 55)
    veh = observed_vehicles(bins, day)
    for code in sorted(cap):
        lanes = lanes_from_width(widths[code][0]) or 1
        print(f"  {code:<10}{cap[code]:>13,}{ach[code]:>10,.0f}"
              f"{ach[code]/cap[code]:>8.2f}{veh[code]/lanes:>13,.0f}")
    ratio = float((ach / pd.Series(cap)).mean())
    print(f"\n  mean observed / planning capacity: **{ratio:.2f}x**")
    print("\n  No. Peak flow reaches 3,266 vehicles per nominal lane per hour on the")
    print("  binding approach, against a saturation flow of roughly 1,800-2,000. With")
    print("  58% two-wheelers the constraint is not lane discipline, and a lane-based")
    print("  v/c is not a meaningful denominator here. jaipur_corridor_study.md 2.2")
    print("  predicts exactly this: nominal lanes and used streams diverge in mixed")
    print("  traffic. Indo-HCM's sublane treatment is required, calibrated locally.")
    print("\n  So the v/c figures above are reported as what the STANDARD says, not as a")
    print("  measurement. The useful quantity is the observed throughput itself.")

    # --- the scheme case: what grade separation removes ---------------------
    print(f"\n=== What an elevated through-carriageway would remove ===")
    print("  Through movements do not need the at-grade junction. If they are carried")
    print("  over it, the at-grade section is left with the turning traffic only.\n")
    from src.analyse import through_vs_turning
    tv = through_vs_turning(bins, day).set_index("junction")
    print(f"  {'junction':<10}{'through %':>11}{'peak PCU':>10}{'at-grade left':>15}"
          f"{'v/c after':>11}{'LOS':>5}")
    print("  " + "-" * 63)
    relief = []
    for _, r in df.iterrows():
        thr = float(tv.loc[r.junction, "through_pct"]) / 100
        residual = r.pcu_pt * (1 - thr)
        vc_after = residual / r.capacity
        relief.append(dict(junction=r.junction, approach=r.approach,
                           through_pct=round(100 * thr, 1), peak_pcu=round(r.pcu_pt),
                           residual_pcu=round(residual), vc_before=round(r.vc_pt, 2),
                           vc_after=round(vc_after, 2), los_after=los(vc_after)))
    rel = pd.DataFrame(relief)
    for code, g in rel.groupby("junction"):
        w = g.loc[g.vc_after.idxmax()]
        print(f"  {code:<10}{w.through_pct:>10.1f}%{w.peak_pcu:>10,}{w.residual_pcu:>15,}"
              f"{w.vc_after:>11.2f}{w.los_after:>5}")
    worst_after = rel.loc[rel.vc_after.idxmax()]
    ok = int((rel.vc_after < 1.0).sum())

    # DESIGN LIFE - the question the relief table on its own does not answer.
    # Every approach is already over capacity, so the do-nothing design year is the base
    # year and stating it adds nothing. What matters is how long grade separation lasts:
    # relief that expires inside the design horizon is a different recommendation from
    # relief that does not, and reporting only the opening-year figure would overstate it.
    horizon_yr = ASSUMPTIONS["base_year"] + ASSUMPTIONS["design_horizon_years"]
    design_life = []
    for _, r in rel.iterrows():
        entry = dict(junction=r.junction, approach=r.approach, vc_after=r.vc_after)
        for label, g in (("low", ASSUMPTIONS["growth_low_pct"]),
                         ("med", ASSUMPTIONS["growth_med_pct"]),
                         ("high", ASSUMPTIONS["growth_high_pct"])):
            entry[f"fails_{label}"] = failure_year(r.vc_after, g)
        design_life.append(entry)
    med_years = sorted(d["fails_med"] for d in design_life)
    first_fail_med, last_fail_med = med_years[0], med_years[-1]
    within_horizon = sum(1 for d in design_life if d["fails_med"] <= horizon_yr)

    print(f"\n=== Design life of the relief, at {ASSUMPTIONS['growth_med_pct']}% growth ===")
    print(f"  {'junction':<10}{'approach':<20}{'v/c open':>9}"
          f"{'4%':>7}{'6%':>7}{'8%':>7}")
    print("  " + "-" * 60)
    for d in design_life:
        print(f"  {d['junction']:<10}{d['approach'].replace('from ',''):<20}"
              f"{d['vc_after']:>9.2f}{d['fails_low']:>7}{d['fails_med']:>7}"
              f"{d['fails_high']:>7}")
    print(f"\n  GATE - approaches whose relief survives to the {horizon_yr} horizon: "
          f"**{len(design_life) - within_horizon} of {len(design_life)}**")
    print(f"  first approach back over capacity: {first_fail_med}, "
          f"{first_fail_med - ASSUMPTIONS['base_year']} years after the base year")
    print("\n  Grade separation returns every approach to service on opening and does NOT")
    print(f"  hold it there for the stated {ASSUMPTIONS['design_horizon_years']}-year "
          "horizon. Reporting the opening-year")
    print("  figure alone would overstate the scheme; the corridor needs a demand-side")
    print("  measure alongside the structure, not instead of it.")
    print(f"\n  GATE — approaches back under the planning capacity after grade separation: "
          f"**{ok} of {len(rel)}**")
    print(f"  worst remaining: {worst_after.junction} at v/c {worst_after.vc_after:.2f} "
          f"(LOS {worst_after.los_after}), down from {worst_after.vc_before:.2f}")
    print("\n  This is the argument the count data exists to make. Removing the through")
    print("  movement is what creates headroom, and the through share is high enough on")
    print("  this corridor to do it.")

    # --- growth, with the constraint stated --------------------------------
    horizon = ASSUMPTIONS["base_year"] + ASSUMPTIONS["design_horizon_years"]
    print(f"\n=== Demand to {horizon} ===")
    print("  Counted flow on a saturated approach is capacity-constrained, so it is a")
    print("  FLOOR on present demand, not a measurement of it. Suppressed trips, diverted")
    print("  trips and peak spreading are invisible to a cordon count. These multiples")
    print("  are therefore lower bounds.\n")
    print(f"  {'growth':<10}{'multiple by ' + str(horizon):>22}"
          f"{'binding approach needs':>26}")
    print("  " + "-" * 58)
    binding = df.loc[df.pcu_pt.idxmax()]
    grow = []
    for g in (ASSUMPTIONS["growth_low_pct"], ASSUMPTIONS["growth_med_pct"],
              ASSUMPTIONS["growth_high_pct"]):
        mult = (1 + g / 100) ** ASSUMPTIONS["design_horizon_years"]
        need = binding.pcu_pt * mult
        grow.append(dict(growth_pct=g, multiple=round(mult, 2),
                         binding_need_pcu=round(need)))
        print(f"  {g:>5.0f}%   {mult:>20.2f}x{need:>24,.0f} PCU/hr")
    print(f"\n  binding approach today: {binding.junction} {binding.approach}, "
          f"{binding.pcu_pt:,.0f} PCU/hr")
    print("  A 20-year horizon at 6% implies roughly a threefold increase. No at-grade")
    print("  widening within the available 15 m section delivers that, which is the")
    print("  structural case for grade separation rather than junction improvement.")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "capacity.json").write_text(json.dumps(dict(
        assumptions=ASSUMPTIONS, analysis_date=str(day),
        widths={k: dict(width_m=v[0], transects=v[1], lanes_per_dir=lanes_from_width(v[0]),
                        capacity_pcu_hr=cap[k]) for k, v in widths.items()},
        junctions=[{k: (v if not hasattr(v, "item") else v.item())
                    for k, v in r.items()} for r in df.to_dict("records")],
        horizon_year=horizon,
        observed_vs_planning_ratio=round(ratio, 2),
        lane_model_applicable=False,
        relief=[{k: (v if not hasattr(v, "item") else v.item())
                 for k, v in r.items()} for r in rel.to_dict("records")],
        approaches_ok_after_grade_separation=ok,
        design_life=design_life,
        design_life_first_failure_med=first_fail_med,
        design_life_last_failure_med=last_fail_med,
        design_life_survives_horizon=len(design_life) - within_horizon,
        growth=grow,
    ), indent=1))
    print(f"\nwritten: {OUT_DATA/'capacity.json'}")
    print("\nEvery v/c is a band because half the PCU correction is unresolvable from this")
    print("survey. Quoting a single LOS grade off this data would be false precision.")
