"""
profiles.py — the corridor across the whole day, not at one hour.

WHY
Every figure published so far describes the peak hour. That is the convention and it
hides the finding: these approaches are over capacity for eight to twelve hours, so a
peak-hour number understates the problem by most of the day. Three exhibits fix that,
all built from the 96 fifteen-minute bins already parsed.

  Level of service by approach and hour   the A-F grid, so the shape of the day is visible
  Peak spreading                          where the peak has already flattened into a plateau
  Cumulative arrival-departure            Newell's diagram: queue is a vertical gap, delay
                                          an area, and both are read off the same picture

THE CUMULATIVE DIAGRAM IS THE ONE THAT MATTERS
Plot cumulative arrivals A(t) against cumulative departures D(t). Where demand exceeds
capacity the curves separate: the vertical distance is the queue at that instant, the
horizontal distance is the delay to a vehicle arriving then, and the enclosed area is
total delay. A bar chart of "mean delay" asserts a number; this shows the whole mechanism
and lets a reader check it with a ruler.

Run:  uv run python src/profiles.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.capacity import LOS_BANDS, los
from src.config import JUNCTION_COORDS, OUT_DATA

BIN_HOURS = 0.25
LOS_ORDER = ["A", "B", "C", "D", "E", "F"]


def hourly_pcu(bins, day, junction, arm):
    """Rolling-hour PCU on one approach, one value per 15-minute step."""
    from src.pcu import factor_band, SURVEYED
    mv = bins[(bins.kind == "movement") & (bins.date == day) &
              (bins.junction == junction)]
    share = mv.groupby("veh_class")["count"].sum()
    share = share / share.sum()
    a = mv[mv.arm_from == arm]
    if a.empty:
        return None
    per_bin = a.groupby(["bin_start", "veh_class"])["count"].sum().unstack(fill_value=0)
    w = {}
    for cls in per_bin.columns:
        b = factor_band(cls, float(share[cls]))
        w[cls] = b[1] if b[1] is not None else SURVEYED[cls]
    ser = sum(per_bin[c] * w[c] for c in per_bin.columns).sort_index()
    return pd.Series([float(ser.iloc[i:i + 4].sum()) for i in range(len(ser) - 3)],
                     index=ser.index[:len(ser) - 3])


def los_grid(bins, day, capacities):
    """
    LOS for every approach at every hour of the surveyed day.

    capacities: {(junction, arm_label): PCU/hr}
    """
    from src.analyse import NORTH, SOUTH
    rows = []
    for (code, label), cap in capacities.items():
        arm = NORTH if "Mansarover" in label else SOUTH
        ser = hourly_pcu(bins, day, code, arm)
        if ser is None:
            continue
        for t, v in ser.items():
            rows.append(dict(junction=code, approach=label,
                             hour=t.strftime("%H:%M"),
                             pcu=round(v), vc=round(v / cap, 3), los=los(v / cap)))
    return pd.DataFrame(rows)


def cumulative(bins, day, junction, arm, capacity, band=(0.85, 1.20)):
    """
    Newell's cumulative arrival-departure curves for one approach.

    Departures are capped at capacity, which is what makes the curves separate. The
    queue never discharges below zero: once a queue exists, departures run AT capacity
    until it clears, which is the whole behaviour a mean-delay figure throws away.

    ARRIVALS ARE MEASURED. DEPARTURES ARE ASSUMED.
    A(t) is a running sum of counted vehicles. D(t) needs a discharge rate, which a
    classified count does not contain - it is the one contestable line on the figure. So
    it is drawn as a BAND across a capacity range rather than a single line, which puts
    the assumption on the page where a reader can argue with it instead of burying it
    inside an averaged delay figure. Same discipline as the PCU bands.
    """
    ser = hourly_pcu(bins, day, junction, arm)
    if ser is None:
        return None
    # A rolling-hour rate divided by four is the PCU that actually arrive in one bin.
    per_bin = ser / 4.0
    arrivals = per_bin.cumsum()

    # Capacity must be expressed in the SAME unit. capacity is PCU per HOUR, so a
    # fifteen-minute bin can discharge a quarter of it. Comparing a per-bin arrival
    # against an hourly capacity lets everything through and reports no queue at all,
    # which is what this did on an approach running at v/c 2.41.
    def discharge(mult):
        cap_bin = capacity * mult * BIN_HOURS
        dep, queue, carried = [], [], 0.0
        for v in per_bin:
            want = v + carried
            served = min(want, cap_bin)
            carried = want - served
            dep.append(served)
            queue.append(carried)
        return (pd.Series(dep, index=per_bin.index).cumsum(), queue)

    mid, q_mid = discharge(1.0)
    lo, q_lo = discharge(band[0])          # slower discharge: longer queue
    hi, q_hi = discharge(band[1])          # faster discharge: shorter queue
    return pd.DataFrame(dict(t=[t.strftime("%H:%M") for t in per_bin.index],
                             arrivals=arrivals.round(0).values,
                             departures=mid.round(0).values,
                             dep_low=lo.round(0).values,
                             dep_high=hi.round(0).values,
                             queue=[round(q) for q in q_mid],
                             queue_low=[round(q) for q in q_hi],
                             queue_high=[round(q) for q in q_lo]))


if __name__ == "__main__":
    from src.tmc_parse import parse_all

    cap = json.loads((OUT_DATA / "capacity.json").read_text())
    bins, _ = parse_all()
    day = sorted(bins.date.unique())[0]
    capacities = {(j["junction"], j["approach"]): j["capacity"] for j in cap["junctions"]}

    grid = los_grid(bins, day, capacities)
    print("=== Level of service by approach and hour ===")
    print("  Every published v/c so far is the peak hour. This is the whole day.\n")
    dist = grid.los.value_counts().reindex(LOS_ORDER).fillna(0).astype(int)
    total = int(dist.sum())
    for g in LOS_ORDER:
        bar = "#" * round(40 * dist[g] / total)
        print(f"  LOS {g}  {dist[g]:>5} of {total}  {100*dist[g]/total:>5.1f}%  {bar}")
    f_share = 100 * dist["F"] / total
    print(f"\n  GATE - approach-hours at LOS F: **{dist['F']} of {total}** ({f_share:.0f}%)")

    worst = grid.groupby("junction")["vc"].max().sort_values(ascending=False)
    print(f"\n  worst approach-hour v/c by junction:")
    for code, v in worst.items():
        print(f"    {code}  {JUNCTION_COORDS[code][2]:<14}{v:>6.2f}")

    print("\n=== Peak spreading ===")
    over = grid[grid.vc > 1.0].groupby(["junction", "approach"]).size() / 4
    print(f"  hours per day above capacity, mean {over.mean():.1f}, max {over.max():.1f}")
    print("  A corridor with a genuine peak has a spike. A corridor whose peak has")
    print("  already spread has a plateau, and no amount of peak-hour capacity fixes it.")

    # cumulative curves for the binding approach
    binding = cap["junctions"][max(range(len(cap["junctions"])),
                                   key=lambda i: cap["junctions"][i]["vc_pt"])]
    from src.analyse import NORTH, SOUTH
    arm = NORTH if "Mansarover" in binding["approach"] else SOUTH
    cum = cumulative(bins, day, binding["junction"], arm, binding["capacity"])
    print(f"\n=== Cumulative arrivals vs departures, {binding['junction']} "
          f"{binding['approach']} ===")
    print(f"  capacity {binding['capacity']:,} PCU/hr\n")
    print(f"  {'time':<8}{'arrived':>10}{'departed':>10}{'queued':>9}")
    print("  " + "-" * 37)
    for i in range(0, len(cum), 12):
        r = cum.iloc[i]
        print(f"  {r.t:<8}{r.arrivals:>10,.0f}{r.departures:>10,.0f}{r.queue:>9,.0f}")
    peak_q = cum["queue"].max()
    print(f"\n  peak queue {peak_q:,.0f} PCU, band {cum['queue_low'].max():,.0f} to "
          f"{cum['queue_high'].max():,.0f}; final unserved {cum['queue'].iloc[-1]:,.0f} PCU")
    print("  Arrivals are MEASURED. The departure curve is the one assumption on this")
    print("  figure, so it is drawn as a band across a discharge range rather than a")
    print("  line - the assumption goes on the page instead of inside an averaged number.")
    print("  The vertical gap between the curves is the queue at that moment, the")
    print("  horizontal gap is the delay to a vehicle arriving then, and the area")
    print("  between them is total delay. All three are read off one picture.")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "profiles.json").write_text(json.dumps(dict(
        los_grid=grid.to_dict("records"),
        los_distribution={g: int(dist[g]) for g in LOS_ORDER},
        approach_hours_total=total, approach_hours_F=int(dist["F"]),
        f_share_pct=round(f_share, 1),
        hours_over_capacity={f"{k[0]}|{k[1]}": float(v) for k, v in over.items()},
        mean_hours_over=round(float(over.mean()), 2),
        cumulative=dict(junction=binding["junction"], approach=binding["approach"],
                        capacity=binding["capacity"], peak_queue_pcu=int(peak_q),
                        peak_queue_band=[int(cum["queue_low"].max()),
                                         int(cum["queue_high"].max())],
                        discharge_band=[0.85, 1.20],
                        series=cum.to_dict("records")),
    ), indent=1))
    print(f"\nwritten: {OUT_DATA/'profiles.json'}")
