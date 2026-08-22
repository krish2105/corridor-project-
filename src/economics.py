"""
economics.py — what the congestion costs, per year, and what relieving it is worth.

WHY THIS IS BANDED AND NOT A SINGLE NUMBER
Every figure here is delay (measured, from the survey) multiplied by a value of time
(a policy input, not a measurement). The delay side is defensible. The value-of-time side
is not ours to fix: authorities appraise against their own approved rates, and quoting a
single rupee figure derived from a rate JDA has not adopted would be presenting a policy
choice as an engineering result.

So the whole calculation runs as a band, the rates are declared in one place at the top,
and the method is written so that substituting JDA's own rates is a one-line change. That
is the honest form for this number: the METHOD is the deliverable, the rupees are
indicative until the authority supplies its rates.

HOW LONG THE CONGESTION LASTS IS MEASURED, NOT ASSUMED
Annual cost is very sensitive to how many hours a day an approach is over capacity, and
assuming "two peak hours" would drive the answer as much as the value of time does. The
survey counted all 96 fifteen-minute intervals, so the oversaturated duration is counted
directly: the number of rolling hours in which corrected PCU demand exceeds the measured
capacity of that approach.

WHAT IS DELIBERATELY NOT COUNTED
Vehicle operating cost in stop-start conditions, fuel, emissions, accident cost and
reliability. All are real, all would increase the figure, and none can be estimated from
a classified count without further assumptions. Leaving them out keeps this a lower bound.

Run:  uv run python src/economics.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import OUT_DATA

# Indicative occupancy-weighted value of time, rupees per vehicle-hour, 2026 prices.
# Bands, not points. Replace with JDA's approved rates before any appraisal is submitted:
# these are the only numbers in the whole project that are a policy input rather than a
# measurement, and they are collected here so that substitution is trivial.
VOT_INR_PER_VEH_HR = {
    "TWO_W":        (90, 180),      # ~1.3 occupants
    "CAR_BUCKET":   (250, 500),     # car / taxi / tempo / auto / pickup, ~2.5 occupants
    "AGRI_LCV":     (300, 600),
    "AUTO_TRK_BUS": (600, 1500),    # bus occupancy dominates this bucket
    "TRL_MAV":      (400, 900),
    "CYCLE":        (40, 90),
    "CYCLE_RIK":    (60, 130),
    "HAND_CART":    (40, 90),
    "HORSE_DRAWN":  (40, 90),
    "BULLOCK":      (40, 90),
}
WORKING_DAYS = (280, 330)    # band: the corridor is urban, so weekend load is not zero
CRORE = 1e7


def oversaturated_hours(bins, day, capacity_by_approach):
    """
    Hours per day each corridor approach is over its measured capacity.

    Counted from the survey's own 15-minute intervals as rolling hours, not assumed from
    a nominal peak period. This is the single most influential input after the value of
    time, so it is measured.
    """
    from src.analyse import NORTH, SOUTH
    from src.pcu import factor_band, SURVEYED

    mv = bins[(bins.kind == "movement") & (bins.date == day)]
    out = {}
    for code, g in mv.groupby("junction"):
        share = g.groupby("veh_class")["count"].sum()
        share = share / share.sum()
        for arm, label in ((NORTH, "from Mansarover Metro"),
                           (SOUTH, "from Sanganer Stadium")):
            a = g[g.arm_from == arm]
            if a.empty:
                continue
            cap = capacity_by_approach.get((code, label))
            if not cap:
                continue
            per_bin = a.groupby(["bin_start", "veh_class"])["count"].sum().unstack(fill_value=0)
            w = {}
            for cls in per_bin.columns:
                b = factor_band(cls, float(share[cls]))
                w[cls] = b[1] if b[1] is not None else SURVEYED[cls]
            ser = sum(per_bin[c] * w[c] for c in per_bin.columns).sort_index()
            # rolling hour = 4 consecutive 15-minute bins, expressed as PCU/hr
            hourly = [float(ser.iloc[i:i + 4].sum()) for i in range(len(ser) - 3)]
            over = [h for h in hourly if h > cap]
            # each rolling window advances 15 min, so n windows over capacity is n/4 hours
            out[(code, label)] = dict(hours_over=len(over) / 4,
                                      excess_pcu=sum(h - cap for h in over) / 4,   # PCU of excess ARRIVALS
                                      max_pcu_hr=max(hourly) if hourly else 0.0)
    return out


def annual_cost(excess_pcu_hr_per_day, composition, pcu_per_veh, days, vot):
    """
    Rupees per year of delay, for one bound of the band.

    excess_pcu_hr_per_day is PCU-HOURS of accumulated delay per day - that is, the excess
    arrivals already multiplied by half the analysis period. The caller applies that
    factor, so passing raw excess arrivals here would overstate the cost by the duration.
    """
    veh_hr = excess_pcu_hr_per_day / max(pcu_per_veh, 1e-9)
    per_day = sum(veh_hr * share * vot.get(cls, 200) for cls, share in composition.items())
    return per_day * days


if __name__ == "__main__":
    from src.tmc_parse import parse_all
    from src.analyse import composition as comp_fn
    from src.pcu import SURVEYED

    cap = json.loads((OUT_DATA / "capacity.json").read_text())
    dly = json.loads((OUT_DATA / "delay.json").read_text())
    bins, _ = parse_all()
    day = sorted(bins.date.unique())[0]
    comp = comp_fn(bins, day)

    cap_by = {(j["junction"], j["approach"]): j["capacity"] for j in cap["junctions"]}
    over = oversaturated_hours(bins, day, cap_by)

    print("=== Assumptions, and which of them are policy rather than measurement ===")
    print(f"  {'oversaturated duration':<30} MEASURED from the 96 survey intervals")
    print(f"  {'delay model':<30} MEASURED - deterministic oversaturation queueing")
    print(f"  {'vehicle composition':<30} MEASURED from the survey")
    print(f"  {'value of time':<30} POLICY - indicative band, replace with JDA rates")
    print(f"  {'working days per year':<30} POLICY - band {WORKING_DAYS[0]}-{WORKING_DAYS[1]}")
    print(f"  {'vehicle operating cost':<30} NOT COUNTED - would increase the figure")
    print(f"  {'fuel, emissions, accidents':<30} NOT COUNTED - would increase the figure\n")

    print("=== Hours per day over capacity, counted from the survey ===")
    print(f"  {'junction':<9}{'approach':<20}{'hrs over':>10}{'excess PCU-hr/day':>20}")
    print("  " + "-" * 60)
    rows = []
    for (code, label), d in sorted(over.items()):
        print(f"  {code:<9}{label.replace('from ',''):<20}{d['hours_over']:>10.2f}"
              f"{d['excess_pcu']:>20,.0f}")
        rows.append(dict(junction=code, approach=label, **d))
    total_excess = sum(d["excess_pcu"] for d in over.values())
    mean_hours = sum(d["hours_over"] for d in over.values()) / len(over)
    print(f"\n  corridor total excess demand: {total_excess:,.0f} PCU per day")
    print(f"  mean oversaturated duration:  {mean_hours:.1f} hours per approach per day")

    # composition and mean PCU per vehicle, corridor-wide
    cc = comp.groupby("veh_class")["count"].sum()
    shares = (cc / cc.sum()).to_dict()
    pcu_per_veh = sum(shares.get(c, 0) * SURVEYED.get(c, 1.0) for c in shares)

    # Deterministic queueing over a period T: delay = 0.5 * excess * T. T is taken as one
    # hour, matching delay.py, which means each oversaturated hour is treated as if its
    # queue clears before the next begins.
    #
    # That is certainly optimistic. The table above shows approaches over capacity for
    # eight to twelve CONTINUOUS hours, so queues plainly carry from one hour into the
    # next and real delay compounds. Modelling the carry-over would need the spillback
    # behaviour that delay.py already shows breaks the deterministic model, so the
    # conservative choice is taken and stated: this is a lower bound, not an estimate.
    from src.delay import T_HOURS
    delay_veh_hr_day = 0.5 * total_excess * T_HOURS / pcu_per_veh

    print(f"\n=== Delay, and what it costs ===")
    print(f"  mean PCU per vehicle          {pcu_per_veh:.3f}")
    print(f"  delay accumulated per day     {delay_veh_hr_day:,.0f} vehicle-hours")
    lo = annual_cost(0.5 * total_excess * T_HOURS, shares, pcu_per_veh, WORKING_DAYS[0],
                     {k: v[0] for k, v in VOT_INR_PER_VEH_HR.items()})
    hi = annual_cost(0.5 * total_excess * T_HOURS, shares, pcu_per_veh, WORKING_DAYS[1],
                     {k: v[1] for k, v in VOT_INR_PER_VEH_HR.items()})
    print(f"\n  {'annual cost of delay, do nothing':<38}"
          f"Rs {lo/CRORE:,.0f} - {hi/CRORE:,.0f} crore")

    # with the through movement grade separated, only the residual turning delay remains
    thr = {r["junction"]: r["through_pct"] / 100 for r in cap["relief"]}
    residual_excess = 0.0
    for (code, label), d in over.items():
        c = cap_by[(code, label)]
        # through traffic leaves the at-grade stream entirely
        residual_excess += max(0.0, d["excess_pcu"] * (1 - thr.get(code, 0)))
    r_lo = annual_cost(0.5 * residual_excess * T_HOURS, shares, pcu_per_veh, WORKING_DAYS[0],
                       {k: v[0] for k, v in VOT_INR_PER_VEH_HR.items()})
    r_hi = annual_cost(0.5 * residual_excess * T_HOURS, shares, pcu_per_veh, WORKING_DAYS[1],
                       {k: v[1] for k, v in VOT_INR_PER_VEH_HR.items()})
    print(f"  {'annual cost after grade separation':<38}"
          f"Rs {r_lo/CRORE:,.0f} - {r_hi/CRORE:,.0f} crore")
    print(f"  {'annual benefit':<38}"
          f"Rs {(lo-r_lo)/CRORE:,.0f} - {(hi-r_hi)/CRORE:,.0f} crore")

    first_fail = cap.get("design_life_first_failure_med")
    base = cap["assumptions"]["base_year"]
    life = (first_fail - base) if first_fail else None
    if life:
        print(f"\n  Over the {life} years before the first approach returns to capacity,")
        print(f"  undiscounted benefit is Rs {life*(lo-r_lo)/CRORE:,.0f} - "
              f"{life*(hi-r_hi)/CRORE:,.0f} crore. That window, not the nominal")
        print(f"  {cap['assumptions']['design_horizon_years']}-year horizon, is the "
              "period the scheme actually delivers over.")

    print(f"\n  GATE - every rupee figure is a band and the value of time is declared")
    print(f"  as a policy input: **{len(VOT_INR_PER_VEH_HR)} classes, all banded**")
    print("\n  These are lower bounds. Vehicle operating cost, fuel, emissions, accident")
    print("  cost and journey-time reliability are all excluded because a classified")
    print("  count cannot support them without further assumptions.")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "economics.json").write_text(json.dumps(dict(
        assumptions=dict(vot_inr_per_veh_hr=VOT_INR_PER_VEH_HR,
                         working_days=list(WORKING_DAYS),
                         vot_status="policy input - indicative, replace with JDA rates",
                         excluded=["vehicle operating cost", "fuel", "emissions",
                                   "accident cost", "reliability"],
                         queue_carryover="not modelled - each oversaturated hour treated "
                                         "independently, so the figure is a lower bound"),
        analysis_date=str(day),
        approaches=rows,
        total_excess_pcu_day=round(total_excess),
        mean_hours_over=round(mean_hours, 2),
        pcu_per_vehicle=round(pcu_per_veh, 3),
        delay_veh_hr_day=round(delay_veh_hr_day),
        annual_cost_crore=[round(lo / CRORE), round(hi / CRORE)],
        annual_cost_after_crore=[round(r_lo / CRORE), round(r_hi / CRORE)],
        annual_benefit_crore=[round((lo - r_lo) / CRORE), round((hi - r_hi) / CRORE)],
        benefit_to_first_failure_crore=None if not life else
            [round(life * (lo - r_lo) / CRORE), round(life * (hi - r_hi) / CRORE)],
        years_to_first_failure=life,
    ), indent=1))
    print(f"\nwritten: {OUT_DATA/'economics.json'}")
