"""
delay.py — what a v/c ratio above 1.0 actually means on the ground.

WHY THIS EXISTS
"v/c 2.41" is not a finding anyone can act on. "The queue reaches the junction behind it
within nine minutes" is. This module turns the capacity results into queue length, delay,
and corridor journey time, which are the quantities an engineer and a committee both
understand.

WHY NOT AN HCM CONTROL-DELAY MODEL
The standard delay formulations - Webster, HCM d1 + d2 - need cycle length, effective
green and a progression factor. The survey records none of those, and there is no signal
data anywhere in the twelve workbooks. Using them would mean inventing their inputs and
then reporting the invention to three decimal places.

Deterministic oversaturation queueing needs none of that. When arrivals exceed capacity,
the queue grows at exactly the difference regardless of how the junction is controlled,
because control cannot discharge more than capacity. That makes it the right model for
this data: fewer assumptions, and every one of them stated.

  queue at time t      Q(t) = (lambda - mu) * t          [PCU]
  total delay over T   = 0.5 * (lambda - mu) * T^2       [PCU-hours]
  mean delay per veh   = 0.5 * T * (1 - 1/X)             [hours], X = v/c

WHERE IT STOPS BEING PHYSICS
A deterministic queue grows without bound. A real one cannot: it reaches the junction
behind it and blocks it. Once the computed queue exceeds the distance to the upstream
junction, the model has left the regime it is valid in, and a queue length in metres
would be a fiction dressed as a measurement. Past that point this module reports
SPILLBACK and names the junction that gets blocked - the same discipline as the
NO_GAP_VC guard in scheme_test.py, for the same reason.

STORAGE IS BY AREA, NOT BY CAR LENGTHS
Converting a queue to metres via "6.5 m per car" is wrong on this corridor. Two-wheelers
are 49% of the stream and queue two and three abreast in a lane, filling gaps a car
cannot. So the queue is converted to vehicles by class using the observed composition,
each class occupies its own footprint, and the total area is divided by the MEASURED
carriageway width. Packing is imperfect, so a jam packing efficiency is applied and
stated rather than buried.

Run:  uv run python src/delay.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import JUNCTION_COORDS, OUT_DATA
from src.capacity import ASSUMPTIONS, los

# Analysis period. The peak hour is what was surveyed and what capacity is quoted for.
T_HOURS = 1.0

# Jam footprint per vehicle, metres squared, from IRC:SP:41 and Indo-HCM static
# dimensions plus a working clearance. Width matters as much as length here: it is why
# two-wheelers store far more densely than a PCU conversion suggests.
JAM_FOOTPRINT_M2 = {
    "TWO_W":        1.8 * 0.8,      # queue 2-3 abreast in a 3.5 m lane
    "CAR_BUCKET":   4.5 * 1.8,      # car / taxi / tempo / auto / pickup, mixed
    "AGRI_LCV":     7.0 * 2.2,
    "AUTO_TRK_BUS": 9.0 * 2.4,      # the heavy end of the composite bucket
    "TRL_MAV":     14.0 * 2.5,
    "CYCLE":        1.8 * 0.6,
    "CYCLE_RIK":    2.4 * 1.0,
    "HAND_CART":    2.0 * 1.0,
    "HORSE_DRAWN":  3.5 * 1.5,
    "BULLOCK":      4.0 * 1.8,
}
# Vehicles do not tessellate. 0.75 is the usual working value for dense mixed queues;
# a higher number would shorten every queue reported here, so it is the conservative end.
JAM_PACKING = 0.75

# Free-flow speed for the corridor journey-time comparison. Urban arterial, IRC:106
# design speed band for a divided arterial in a built-up section.
FREE_FLOW_KMH = 40.0


def queue_and_delay(demand_pcu_hr, capacity_pcu_hr, t_hours=T_HOURS):
    """
    Deterministic oversaturation queueing. Returns PCU queued and mean delay in minutes.

    Under capacity there is no deterministic queue at all - what remains is random
    arrival delay, which this model does not claim to estimate. Returning zero there is
    honest: it says "this model finds no systematic queue", not "there is no delay".
    """
    x = demand_pcu_hr / capacity_pcu_hr
    if x <= 1.0:
        return dict(vc=x, queue_pcu=0.0, mean_delay_min=0.0,
                    total_delay_pcu_hr=0.0, oversaturated=False)
    excess = demand_pcu_hr - capacity_pcu_hr
    return dict(vc=x,
                queue_pcu=excess * t_hours,
                mean_delay_min=60 * 0.5 * t_hours * (1 - 1 / x),
                total_delay_pcu_hr=0.5 * excess * t_hours ** 2,
                oversaturated=True)


def queue_metres(queue_pcu, composition, pcu_per_vehicle, width_m):
    """
    Convert a PCU queue to a physical length using the observed class mix.

    composition: {veh_class: share of vehicles}, from the survey itself.
    pcu_per_vehicle: the stream's mean, so PCU can be turned back into vehicles.
    """
    if queue_pcu <= 0 or width_m <= 0:
        return 0.0, 0.0
    vehicles = queue_pcu / pcu_per_vehicle
    area = sum(vehicles * share * JAM_FOOTPRINT_M2.get(cls, 7.0)
               for cls, share in composition.items())
    return vehicles, area / (JAM_PACKING * width_m)


def spillback(queue_m, upstream_gap_m):
    """
    Whether the queue reaches the junction behind it.

    Returns the reported length, which is capped at the available storage, and a flag.
    Reporting an uncapped 3 km queue on a 400 m link would be quoting a number the road
    cannot physically hold.
    """
    if upstream_gap_m is None:
        return queue_m, False
    return min(queue_m, upstream_gap_m), queue_m > upstream_gap_m


def minutes_to_spillback(upstream_gap_m, queue_m, t_hours=T_HOURS):
    """How long into the peak the queue reaches the upstream junction."""
    if not queue_m or upstream_gap_m is None or queue_m <= upstream_gap_m:
        return None
    return 60 * t_hours * upstream_gap_m / queue_m


def corridor_spacing():
    """Distance between consecutive junctions, along the surveyed alignment."""
    from src.reports import chainage
    _, rows = chainage()
    out = {}
    for i, r in enumerate(rows):
        out[r["junction"]] = dict(
            chainage_m=r["chainage_m"],
            to_previous_m=None if i == 0 else r["chainage_m"] - rows[i - 1]["chainage_m"],
            to_next_m=None if i == len(rows) - 1 else rows[i + 1]["chainage_m"] - r["chainage_m"],
            previous=None if i == 0 else rows[i - 1]["junction"],
            next=None if i == len(rows) - 1 else rows[i + 1]["junction"])
    return out, rows


if __name__ == "__main__":
    from src.tmc_parse import parse_all
    from src.analyse import composition as comp_fn

    cap = json.loads((OUT_DATA / "capacity.json").read_text())
    bins, _ = parse_all()
    day = sorted(bins.date.unique())[0]
    comp = comp_fn(bins, day)
    spacing, ordered = corridor_spacing()

    print("=== Assumptions ===")
    print(f"  analysis period              {T_HOURS} hr (the surveyed peak)")
    print(f"  jam packing efficiency       {JAM_PACKING}")
    print(f"  free-flow speed              {FREE_FLOW_KMH} km/h")
    print(f"  model                        deterministic oversaturation queueing")
    print(f"  signal timings used          none - the survey records none\n")

    # mean PCU per vehicle per junction, needed to turn a PCU queue back into vehicles
    rows = []
    for j in cap["junctions"]:
        code = j["junction"]
        width = cap["widths"][code]["width_m"]
        cj = comp[comp.junction == code]
        shares = dict(zip(cj.veh_class, cj.share))
        veh_total = float(cj["count"].sum())
        # the survey's own PCU per vehicle, from the corrected point estimate
        pcu_per_veh = j["pcu_pt"] / max(1e-9, j.get("veh_pt", 0) or 0) if j.get("veh_pt") else None
        if not pcu_per_veh or pcu_per_veh <= 0:
            from src.pcu import SURVEYED
            pcu_per_veh = sum(shares.get(c, 0) * SURVEYED.get(c, 1.0) for c in shares) or 1.0

        q = queue_and_delay(j["pcu_pt"], j["capacity"])
        gap = spacing[code]["to_previous_m"] if "Mansarover" in j["approach"] \
            else spacing[code]["to_next_m"]
        upstream = spacing[code]["previous"] if "Mansarover" in j["approach"] \
            else spacing[code]["next"]
        veh, qm = queue_metres(q["queue_pcu"], shares, pcu_per_veh, width)
        shown, spills = spillback(qm, gap)
        t_spill = minutes_to_spillback(gap, qm)
        rows.append(dict(junction=code, approach=j["approach"], vc=round(q["vc"], 2),
                         # publish the capacity this queue was actually derived from.
                         # sensitivity.py rescales these rows, and without the real
                         # divisor it has to guess one - which it did, at a value
                         # capacity.py had already retired.
                         capacity_pcu_hr=round(j["capacity"]),
                         los=j["los_pt"], queue_pcu=round(q["queue_pcu"]),
                         queue_vehicles=round(veh), queue_m=round(qm),
                         storage_m=None if gap is None else round(gap),
                         upstream=upstream, spillback=bool(spills),
                         minutes_to_spillback=None if t_spill is None else round(t_spill, 1),
                         mean_delay_min=round(q["mean_delay_min"], 1),
                         total_delay_pcu_hr=round(q["total_delay_pcu_hr"])))

    df = pd.DataFrame(rows)
    print("=== Queue and delay at the surveyed peak ===")
    print(f"  {'junction':<9}{'approach':<20}{'v/c':>6}{'queue veh':>11}{'queue m':>9}"
          f"{'storage m':>11}{'delay min':>11}  blocks")
    print("  " + "-" * 86)
    for r in rows:
        block = f"{r['upstream']} at {r['minutes_to_spillback']:.0f} min" \
            if r["spillback"] else ("-" if r["storage_m"] else "leaves study area")
        store = f"{r['storage_m']:,}" if r["storage_m"] else "n/a"
        print(f"  {r['junction']:<9}{r['approach'].replace('from ',''):<20}{r['vc']:>6.2f}"
              f"{r['queue_vehicles']:>11,}{r['queue_m']:>9,}"
              f"{store:>11}{r['mean_delay_min']:>11.1f}  {block}")

    n_spill = int(df.spillback.sum())
    n_over = int((df.vc > 1).sum())
    print(f"\n  GATE - approaches whose peak-hour queue exceeds the distance to the")
    print(f"  junction behind them: **{n_spill} of {len(df)}**")
    if n_spill:
        soonest = df[df.spillback].nsmallest(1, "minutes_to_spillback").iloc[0]
        print(f"  soonest: {soonest.junction} {soonest.approach} blocks {soonest.upstream} "
              f"after {soonest.minutes_to_spillback:.0f} minutes of peak")

    # corridor journey time for a through vehicle
    length_km = (ordered[-1]["chainage_m"] - ordered[0]["chainage_m"]) / 1000
    free_min = 60 * length_km / FREE_FLOW_KMH
    # A through vehicle travels ONE way, so it meets one approach per junction, not the
    # worse of the two. Southbound enters every junction from Mansarover Metro;
    # northbound from Sanganer Stadium. Summing the max of both would describe a trip
    # nobody makes.
    dirs = {
        "southbound": sum(r["mean_delay_min"] for r in rows
                          if "Mansarover" in r["approach"]),
        "northbound": sum(r["mean_delay_min"] for r in rows
                          if "Sanganer" in r["approach"]),
    }
    delay_sum = max(dirs.values())
    worst_dir_name = max(dirs, key=dirs.get)
    print(f"\n=== Corridor journey time, {length_km:.2f} km through the six junctions ===")
    print(f"  free flow at {FREE_FLOW_KMH:.0f} km/h                    {free_min:>6.1f} min")
    for name, d in dirs.items():
        print(f"  {name} junction delay at peak    {d:>6.1f} min"
              f"   -> {free_min + d:>5.1f} min total, "
              f"{60 * length_km / (free_min + d):>4.1f} km/h")
    print(f"\n  worst direction: {worst_dir_name}, {free_min + delay_sum:.1f} min "
          f"({(free_min + delay_sum) / free_min:.1f}x free flow), "
          f"{60 * length_km / (free_min + delay_sum):.1f} km/h effective")
    if n_spill:
        print(f"\n  That total is a FLOOR, not a forecast. {n_spill} of {len(df)} queues")
        print("  reach the junction behind them inside the peak, so they stop being")
        print("  independent - blocked approaches meter the ones upstream and the real")
        print("  journey time is worse than the sum of the parts. Deterministic queueing")
        print("  cannot model that, and this module does not pretend to.")

    # after grade separation: through traffic leaves the at-grade junction entirely
    after = []
    for r in cap["relief"]:
        q = queue_and_delay(r["residual_pcu"], next(
            j["capacity"] for j in cap["junctions"]
            if j["junction"] == r["junction"] and j["approach"] == r["approach"]))
        after.append(dict(junction=r["junction"], approach=r["approach"],
                          vc=round(q["vc"], 2), mean_delay_min=round(q["mean_delay_min"], 1),
                          los=los(q["vc"])))
    after_sum = 0.0   # through traffic is grade separated, so it meets no at-grade delay
    print(f"\n=== With the through movement grade separated ===")
    print(f"  at-grade approaches still oversaturated: "
          f"{sum(1 for a in after if a['vc'] > 1)} of {len(after)}")
    print(f"  through journey time                     {free_min:>6.1f} min "
          f"(free flow - it does not enter the junctions)")
    print(f"  saving against the at-grade floor        {delay_sum:>6.1f} min per trip")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "delay.json").write_text(json.dumps(dict(
        assumptions=dict(t_hours=T_HOURS, jam_packing=JAM_PACKING,
                         free_flow_kmh=FREE_FLOW_KMH,
                         model="deterministic oversaturation queueing",
                         signal_data="none in the survey",
                         jam_footprint_m2=JAM_FOOTPRINT_M2),
        analysis_date=str(day), approaches=rows,
        spillback_count=n_spill, oversaturated_count=n_over, n_approaches=len(df),
        corridor_km=round(length_km, 2),
        free_flow_min=round(free_min, 1),
        peak_delay_min=round(delay_sum, 1),
        direction_delay_min={k: round(v, 1) for k, v in dirs.items()},
        worst_direction=worst_dir_name,
        peak_journey_min=round(free_min + delay_sum, 1),
        effective_kmh=round(60 * length_km / (free_min + delay_sum), 1),
        after_grade_separation=after,
        through_journey_min_after=round(free_min, 1),
        saving_min_per_trip=round(delay_sum, 1),
        spacing={k: v for k, v in spacing.items()},
    ), indent=1))
    print(f"\nwritten: {OUT_DATA/'delay.json'}")
