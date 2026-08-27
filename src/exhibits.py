"""
exhibits.py — the figures a traffic engineer looks for, and one nobody else publishes.

Four datasets, all from the classified count and the measured widths. Nothing here needs
speed, trajectory or signal-timing data, because we do not have any and will not imply it.

  volume flow      the twelve-arrow junction schematic. The exhibit an Indian engineer
                   looks for FIRST; a matrix is a substitute they may not accept as
                   equivalent, and its absence is more conspicuous than its presence.
  tornado          how far each PCU assumption moves corridor demand, sorted. The audit
                   finding as one picture, showing both directions - two-wheelers are
                   understated, cycles and the MAV bucket are overstated.
  continuity       southbound outflow at junction n against Mansarover-Metro inflow at
                   n+1, per fifteen-minute bin. Volume balancing is standard practice;
                   PUBLISHING THE RESIDUAL is not, and it is the closest thing this
                   study has to a measured error rate on the source data.
  flow raster      distance along the corridor against time, coloured by through flow.

DELIBERATELY ABSENT
A time-space diagram, because bandwidth is defined as time inside a green phase and this
corridor is being made signal-free - there would be nothing to read, and an engineer who
knows that discounts every exhibit next to it. A speed-flow fundamental diagram, because
a classified count contains no speed or density and a fitted curve would be decoration
with axes.

Run:  uv run python src/exhibits.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import JUNCTIONS, JUNCTION_COORDS, OUT_DATA
from src.routes import route
from src.pcu import EXACT, IRC106, SURVEYED, factor_band

TURN = {1: "Left", 2: "Straight", 3: "Right"}


def volume_flow(bins, day):
    """Every movement at every junction, peak hour, with its turn type."""
    mv = bins[(bins.kind == "movement") & (bins.date == day)]
    out = []
    for code, g in mv.groupby("junction"):
        arms = JUNCTIONS[code]
        idx = {a: i for i, a in enumerate(arms)}
        tot = g.groupby("bin_start")["count"].sum().sort_index()
        i = max(range(len(tot) - 3), key=lambda k: tot.iloc[k:k + 4].sum())
        win = tot.index[i:i + 4]
        pk = g[g.bin_start.isin(win)]
        rows = []
        for (fr, to), gg in pk.groupby(["arm_from", "arm_to"]):
            if fr not in idx or to not in idx:
                continue
            offset = (idx[to] - idx[fr]) % 4
            # What this movement actually does once the signals go, from routes.py so
            # the diagram and the capacity test cannot describe it differently.
            r = route(idx[fr], idx[to])
            rows.append(dict(from_arm=fr, to_arm=to,
                             from_i=idx[fr], to_i=idx[to],
                             turn=TURN.get(offset, "U-turn"),
                             veh=int(gg["count"].sum()),
                             permitted=r["permitted"], bay=r["bay"],
                             rejoins=r["rejoins"], legs=r["legs"]))
        out.append(dict(junction=code, jda_name=JUNCTION_COORDS[code][2],
                        arms=list(arms), peak_start=str(win[0])[11:16],
                        movements=sorted(rows, key=lambda r: (r["from_i"], r["to_i"]))))

    # Dimensions, so the diagram can be drawn to scale rather than as a cartoon.
    #
    # Only the CORRIDOR arms have a measured width: transects are cast along JDA's
    # centreline, which runs north-south, so nothing in this pipeline has ever measured a
    # cross street. The diagram says so rather than drawing all four arms alike and
    # letting a reader assume otherwise.
    cap = OUT_DATA / "capacity.json"
    widths = json.loads(cap.read_text())["widths"] if cap.exists() else {}
    sch = OUT_DATA / "scheme_test.json"
    det = json.loads(sch.read_text()).get("uturn_detour", []) if sch.exists() else []
    by_j = {}
    for d in det:
        by_j.setdefault(d["junction"], []).append(d)
    for j in out:
        w = widths.get(j["junction"], {})
        j["width_m"] = w.get("width_m")
        j["lanes_per_dir"] = w.get("lanes_per_dir")
        j["width_measured_on"] = "corridor arms only; cross streets are not measured"
        j["detours"] = [dict(bay=d["bay"], detour_m=d.get("detour_m"),
                             one_way_m=d.get("one_way_m"),
                             beyond=d["bay_beyond_drawing"],
                             at_junction_mouth=d.get("bay_is_junction_mouth"))
                        for d in by_j.get(j["junction"], [])]
    return out


def tornado(bins, day):
    """
    How far each PCU assumption moves corridor peak demand, in both directions.

    The survey used one static factor per class. IRC:106 makes the factor depend on that
    class's share of the stream. For classes that map 1:1 the correction is exact; for
    the composite columns it is a band, and a band is what gets published.
    """
    mv = bins[(bins.kind == "movement") & (bins.date == day)]
    counts = mv.groupby("veh_class")["count"].sum()
    share = counts / counts.sum()
    base = float((counts * counts.index.map(lambda c: SURVEYED[c])).sum())

    rows = []
    for cls, n in counts.items():
        lo, pt, hi = factor_band(cls, float(share[cls]))
        surveyed = SURVEYED[cls]
        swing_lo = float(n) * ((lo if lo is not None else surveyed) - surveyed)
        swing_hi = float(n) * ((hi if hi is not None else surveyed) - surveyed)
        rows.append(dict(veh_class=cls, share_pct=round(100 * float(share[cls]), 2),
                         surveyed_factor=surveyed,
                         irc_low=lo, irc_high=hi,
                         exact=cls in EXACT,
                         swing_low_pct=round(100 * swing_lo / base, 2),
                         swing_high_pct=round(100 * swing_hi / base, 2),
                         magnitude=round(100 * max(abs(swing_lo), abs(swing_hi)) / base, 2)))
    rows.sort(key=lambda r: -r["magnitude"])
    return dict(base_pcu=round(base), classes=rows,
                net_low_pct=round(sum(r["swing_low_pct"] for r in rows), 2),
                net_high_pct=round(sum(r["swing_high_pct"] for r in rows), 2))


def continuity(bins, day, order):
    """
    Southbound outflow at junction n vs Mansarover-Metro inflow at n+1, per bin.

    The residual is mid-block access, plus whatever the counts got wrong. Nobody
    publishes it, which is exactly why it is worth publishing: it is a measured error
    rate on someone else's data, derived from their own numbers.
    """
    from src.analyse import NORTH, SOUTH
    mv = bins[(bins.kind == "movement") & (bins.date == day)]
    out = []
    for a, b in zip(order, order[1:]):
        outflow = (mv[(mv.junction == a) & (mv.arm_to == SOUTH)]
                   .groupby("bin_start")["count"].sum())
        inflow = (mv[(mv.junction == b) & (mv.arm_from == NORTH)]
                  .groupby("bin_start")["count"].sum())
        j = pd.concat([outflow.rename("out"), inflow.rename("in")], axis=1).fillna(0)
        j["residual"] = j["in"] - j["out"]
        j["pct"] = 100 * j["residual"] / j[["in", "out"]].max(axis=1).replace(0, pd.NA)
        out.append(dict(north=a, south=b,
                        daily_out=int(j["out"].sum()), daily_in=int(j["in"].sum()),
                        mean_residual_pct=round(float(j["pct"].mean()), 1),
                        worst_residual_pct=round(float(j["pct"].abs().max()), 1),
                        series=[dict(t=str(t)[11:16], out=int(r["out"]),
                                     inn=int(r["in"]), residual=int(r["residual"]))
                                for t, r in j.iterrows()]))
    return out


def flow_raster(bins, day, order):
    """Through flow on each corridor link, per bin. Distance against time."""
    from src.analyse import NORTH, SOUTH
    mv = bins[(bins.kind == "movement") & (bins.date == day)]
    cells = []
    for k, code in enumerate(order):
        g = mv[(mv.junction == code) &
               (mv.arm_from.isin([NORTH, SOUTH])) & (mv.arm_to.isin([NORTH, SOUTH]))]
        per = g.groupby("bin_start")["count"].sum()
        for t, v in per.items():
            cells.append(dict(link=k, junction=code, t=str(t)[11:16], veh=int(v)))
    return cells


if __name__ == "__main__":
    from src.tmc_parse import parse_all

    bins, _ = parse_all()
    day = sorted(bins.date.unique())[0]
    cor = json.loads((OUT_DATA / "corridor.json").read_text())["corridor"]
    # chainage order, which the CAD resolved; the flow-derived order was inconclusive
    order = ["TMC-06", "TMC-05", "TMC-04", "TMC-03", "TMC-02", "TMC-01"]

    vf = volume_flow(bins, day)
    print("=== Intersection volume flow, peak hour ===")
    print("  The twelve-arrow schematic an engineer looks for first.\n")
    for j in vf[:2]:
        print(f"  {j['junction']}  {j['jda_name']}  peak {j['peak_start']}")
        for m in j["movements"]:
            print(f"    {m['from_arm']:<18} -> {m['to_arm']:<18} {m['turn']:<9}{m['veh']:>7,}")
        print()
    print(f"  ... {len(vf)-2} more junctions\n")

    t = tornado(bins, day)
    print("=== PCU assumptions, sorted by how far they move corridor demand ===")
    print(f"  {'class':<14}{'share':>8}{'survey':>8}{'IRC low':>9}{'IRC high':>10}"
          f"{'swing low':>11}{'swing high':>12}")
    print("  " + "-" * 72)
    for r in t["classes"]:
        if r["magnitude"] < 0.01:
            continue
        lo = f"{r['irc_low']:.2f}" if r["irc_low"] is not None else "band"
        hi = f"{r['irc_high']:.2f}" if r["irc_high"] is not None else "band"
        print(f"  {r['veh_class']:<14}{r['share_pct']:>7.1f}%{r['surveyed_factor']:>8.2f}"
              f"{lo:>9}{hi:>10}{r['swing_low_pct']:>10.1f}%{r['swing_high_pct']:>11.1f}%")
    print(f"\n  net effect on corridor PCU: {t['net_low_pct']:+.1f}% to {t['net_high_pct']:+.1f}%")
    print("  Both directions are shown. Two-wheelers are understated; cycles and the")
    print("  MAV bucket are overstated. Reporting only the favourable half would be")
    print("  the same error the survey made.")

    con = continuity(bins, day, order)
    print("\n=== Corridor continuity, published residual ===")
    print("  Southbound outflow at each junction against the next junction's inflow.")
    print("  The residual is mid-block access plus count error. Nobody publishes it.\n")
    print(f"  {'link':<20}{'daily out':>12}{'daily in':>11}{'mean resid':>12}{'worst':>9}")
    print("  " + "-" * 65)
    for c in con:
        print(f"  {c['north']} -> {c['south']:<10}{c['daily_out']:>12,}{c['daily_in']:>11,}"
              f"{c['mean_residual_pct']:>11.1f}%{c['worst_residual_pct']:>8.0f}%")

    ras = flow_raster(bins, day, order)
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "exhibits.json").write_text(json.dumps(dict(
        volume_flow=vf, tornado=t, continuity=con, flow_raster=ras,
        corridor_order=order,
        omitted=dict(
            time_space="bandwidth is time inside a green phase; this corridor is being "
                       "made signal-free, so there is nothing to read",
            speed_flow="a classified count contains no speed or density; a fitted "
                       "fundamental diagram would be decoration with axes"),
    ), indent=1))
    print(f"\n  GATE - exhibits built from the count alone: **4 of 4**")
    print(f"  deliberately omitted: time-space diagram, speed-flow diagram. Both need")
    print(f"  data this survey does not contain, and both would look authoritative.")
    print(f"\nwritten: {OUT_DATA/'exhibits.json'}")
