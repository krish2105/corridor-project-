"""
uturn_framework.py — deciding where a U-turn bay belongs, and where it does not.

WHAT THIS ADDS TO scheme_test.py
`scheme_test` answers one question: does JDA's published scheme work? It does not - all
twelve bays fail on gap acceptance, and on every basis tested. That is a verdict, and a
verdict is not a decision. The next question is the one an engineer has to answer:
given a location, what decides whether a U-turn bay is the right treatment there, which
constraint binds, and what would have to change for the answer to flip?

THE LADDER
Five criteria, evaluated IN ORDER, first failure binding:

  1 gap capacity   can the bay serve its demand from gaps in the opposing stream?
  2 median width   does the design vehicle physically fit the turning path?
  3 storage        does the queue fit the bay without blocking the through lane?
  4 weaving        is there room to cross to the left before the next junction?
  5 detour burden  what does the diversion cost the traffic it diverts?

Order matters and is not arbitrary. A bay that cannot find a gap will not be rescued by a
wider median, so evaluating geometry first would produce a list of geometric fixes for a
problem geometry cannot reach. Criteria below the binding one are reported as NOT REACHED
rather than as passes, because they were not tested.

WHAT IT DOES WITH MISSING DATA
Three of the twelve bays sit beyond the CAD drawing's extent and seven proposed bay
chainages have never been supplied, so several criteria cannot be evaluated at all. Those
return CANNOT EVALUATE with the specific measurement named. That is the deliverable: a
decision framework whose output includes what to go and measure, rather than one that
fills the hole with an assumption and returns a number.

THE BACK-SOLVE
For every failing bay the framework solves the binding criterion backwards - what
conflicting flow would let this bay work? - because that is what converts a verdict into
a design brief. A bay needing the opposing stream to fall by 80% is telling you the
opposing stream is the thing to treat, not the bay.

Run:  uv run python src/uturn_framework.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import OUT_DATA
from src.scheme_test import (FOLLOW_UP_S, NO_GAP_VC, breakpoint_gap, gap_capacity)

# Design-vehicle turning requirement, as a BAND and declared a policy input.
#
# The turning path width a U-turn needs is roughly twice the vehicle's minimum turning
# radius, less whatever receiving carriageway is available on the far side. The radii
# below are the figures in general Indian design use; they are carried as a band and as
# an assumption, not quoted as a clause, because the governing clause in the current
# print of IRC:SP:41 and IRC:86 has not been checked against this text. Confirm before
# design. What the framework needs from them is which vehicle a measured width admits,
# and that question survives the uncertainty in the radii.
DESIGN_VEHICLE = {
    "car":        (5.5, 6.0),
    "bus_truck":  (12.0, 13.0),
    "articulated": (13.0, 14.0),
}
# A U-turn swept path needs about 2R plus a working allowance either side.
SWEPT_ALLOWANCE_M = 1.5

# Deceleration and storage length a bay needs before it starts blocking the through
# lane. Stated as an assumption: no bay geometry has been supplied.
BAY_STORAGE_M = 45.0

# Metres a vehicle needs to cross one lane after re-entering the opposing carriageway.
# A U-turn that lands 4 m short of the junction it is meant to serve has none.
WEAVE_PER_LANE_M = 60.0

# Detour imposed on a diverted vehicle, above which the diversion is itself the problem.
# Not a standard: a stated threshold, published so it can be argued with.
DETOUR_TOLERABLE_M = 400.0

CRITERIA = ["gap capacity", "median width", "storage", "weaving", "detour burden"]

PASS, FAIL, BLOCKED, NOT_REACHED = "pass", "fail", "cannot evaluate", "not reached"


def _swept_need():
    """Turning-path width each design vehicle needs, as a band."""
    return {k: (2 * lo + 2 * SWEPT_ALLOWANCE_M, 2 * hi + 2 * SWEPT_ALLOWANCE_M)
            for k, (lo, hi) in DESIGN_VEHICLE.items()}


def admits(width_m):
    """Largest design vehicle a measured turning-path width admits, on the band."""
    if width_m is None:
        return None, None
    need = _swept_need()
    for v in ("articulated", "bus_truck", "car"):
        lo, hi = need[v]
        if width_m >= hi:
            return v, "clears the whole band"
        if width_m >= lo:
            return v, "inside the band - depends which radius governs"
    return None, "below the car band"


def gap_criterion(u):
    """Can the bay serve its demand from gaps? Optimistic case, so a fail is a fail."""
    vc = u["vc_optimistic"]
    if vc > NO_GAP_VC:
        return dict(status=FAIL, value=round(vc, 1),
                    detail=(f"v/c {vc:.1f} exceeds {NO_GAP_VC}. Reported as no viable "
                            f"gaps, not as a capacity number: past this ratio gap "
                            f"acceptance has degenerated and the model is out of regime."))
    if vc >= 1.0:
        return dict(status=FAIL, value=round(vc, 2),
                    detail=f"v/c {vc:.2f} at the optimistic gap. Demand exceeds capacity.")
    return dict(status=PASS, value=round(vc, 2),
                detail=f"v/c {vc:.2f} at the optimistic gap.")


def median_criterion(u, opening):
    """Does the design vehicle fit? Blocked where no opening has been measured."""
    if opening is None:
        return dict(status=BLOCKED, value=None,
                    detail=("no median opening measured at this bay. Needs: opening "
                            "width and receiving carriageway width at the bay chainage, "
                            "from the total station survey."))
    w = opening["width_m"]
    veh, how = admits(w)
    if veh is None:
        return dict(status=FAIL, value=w,
                    detail=f"{w:.1f} m turning path is below even the car band.")
    return dict(status=PASS if veh != "car" else FAIL, value=w,
                detail=f"{w:.1f} m admits {veh.replace('_', '/')} ({how}).")


def storage_criterion(u):
    """
    Does the queue fit the bay?

    Only meaningful where the bay can serve its demand at all. Where it cannot, the queue
    is not a length, it is unbounded within the hour, and quoting a metre figure for it
    would be a number with no regime behind it.
    """
    vc = u["vc_optimistic"]
    if vc >= 1.0:
        return dict(status=BLOCKED, value=None,
                    detail=("queue is unbounded within the peak hour at this v/c, so it "
                            "has no length to compare against storage."))
    return dict(status=BLOCKED, value=None,
                detail=(f"no bay geometry supplied. Needs: deceleration and storage "
                        f"length at the bay, against an assumed {BAY_STORAGE_M:.0f} m."))


def weave_criterion(u, detour, lanes):
    """Room to cross to the left after re-entering the opposing carriageway."""
    if detour is None or detour.get("one_way_m") is None:
        return dict(status=BLOCKED, value=None,
                    detail=("bay chainage not supplied or beyond the drawing. Needs: "
                            "the proposed bay's chainage on JDA's alignment."))
    d = detour["one_way_m"]
    need = WEAVE_PER_LANE_M * max(1, lanes - 1)
    if d < need:
        return dict(status=FAIL, value=d,
                    detail=(f"{d} m from bay to junction against {need:.0f} m needed to "
                            f"cross {max(1, lanes - 1)} lane(s). A vehicle re-entering "
                            f"here is changing lane inside the junction."))
    return dict(status=PASS, value=d,
                detail=f"{d} m available against {need:.0f} m needed.")


def detour_criterion(detour):
    if detour is None or detour.get("detour_m") is None:
        return dict(status=BLOCKED, value=None,
                    detail="bay chainage not supplied or beyond the drawing.")
    d = detour["detour_m"]
    if d > DETOUR_TOLERABLE_M:
        return dict(status=FAIL, value=d,
                    detail=(f"{d:,} m round trip, {detour['veh_km_per_hour']:,.0f} "
                            f"veh-km/hour imposed at the peak."))
    return dict(status=PASS, value=d,
                detail=f"{d:,} m round trip, within the {DETOUR_TOLERABLE_M:.0f} m tolerance.")


def bay_ceiling(t_f):
    """
    The most a single U-turn bay can ever pass, at zero opposing traffic.

    As the conflicting flow goes to zero the HCM form tends to 3600 / t_f: with nothing
    to yield to, throughput is set by the follow-up headway alone. It is the ceiling no
    amount of signal timing, median width or opposing-flow relief can lift, and it is
    what separates a bay that is badly sited from one that is the wrong instrument.
    """
    return 3600.0 / t_f


def back_solve(u):
    """
    What would have to change for the binding criterion to clear?

    Three answers, solved rather than asserted: the conflicting flow at which the bay
    would exactly serve its demand, the demand it could serve at today's flow, and
    whether the demand is above the bay's ceiling at all.

    The ceiling check has to come first. Without it a bisection over conflicting flow
    walks down to its lower bound and reports "the opposing stream must fall 100%", which
    reads as an extreme version of a solvable problem. It is not one: those bays are
    asking a single opening to pass more vehicles than any opening passes.
    """
    dem, qc, t_c, t_f = (u["uturn_demand"], u["conflicting_flow"], u["t_c_lo"],
                         FOLLOW_UP_S[0])
    ceiling = bay_ceiling(t_f)
    served = gap_capacity(qc, t_c, t_f)
    out = dict(
        conflicting_now=round(qc), demand_now=round(dem),
        demand_servable=round(served),
        demand_reduction_pct=round(100 * (1 - served / dem), 1) if dem else None,
        bay_ceiling_veh_hr=round(ceiling),
        above_bay_ceiling=bool(dem > ceiling),
        gap_needed_s=round(breakpoint_gap(dem, qc, t_f), 2), gap_ours_s=round(t_c, 2))
    if dem > ceiling:
        out.update(conflicting_needed=None, conflicting_reduction_pct=None,
                   note=(f"demand {dem:,.0f} exceeds the {ceiling:,.0f} veh/h a single "
                         f"bay passes at zero opposing traffic. No reduction in the "
                         f"opposing stream can make this bay work."))
        return out
    lo, hi = 1.0, qc
    for _ in range(200):                      # capacity falls monotonically with q_c
        mid = (lo + hi) / 2
        if gap_capacity(mid, t_c, t_f) < dem:
            hi = mid
        else:
            lo = mid
    q_need = (lo + hi) / 2
    out.update(conflicting_needed=round(q_need),
               conflicting_reduction_pct=round(100 * (1 - q_need / qc), 1) if qc else None,
               note=None)
    return out


# The ladder of what to do instead, ordered by what it costs. Which rungs are LIVE is
# decided per bay from the back-solve, not asserted: a rung that cannot move the binding
# term is not an option, however cheap it is.
ALTERNATIVES = [
    ("keep the signal", "no capital cost",
     "The junction already meters the opposing stream. Removing the signal is what "
     "creates the gap problem in the first place."),
    ("relocate the bay", "low",
     "Move it to a chainage where the opposing through flow is lower. Only helps if such "
     "a chainage exists within a tolerable detour."),
    ("signalise the U-turn", "moderate",
     "A metered U-turn manufactures the gap the stream will not offer. It reintroduces "
     "the signal the scheme exists to remove, on the corridor rather than at the junction."),
    ("widen the median, add an acceleration lane", "moderate",
     "Raises capacity by lowering the follow-up headway and letting vehicles merge rather "
     "than cross. A second-order effect on a first-order shortfall."),
    ("grade separate the through movement", "high",
     "The only measure that changes the binding term: it removes the conflicting flow "
     "rather than asking the U-turn to find gaps in it."),
]


def assess(uturns, detours, openings, lanes_by_junction):
    """One verdict per bay, with the binding criterion and the back-solve."""
    det = {(d["junction"], d["bay"]): d for d in detours}
    rows = []
    for u in uturns:
        d = det.get((u["junction"], u["bay"]))
        opening = None
        if d and d.get("bay_chainage_m") is not None:
            opening = min(openings, key=lambda o: abs(o["chainage_m"] - d["bay_chainage_m"]),
                          default=None)
            if opening and abs(opening["chainage_m"] - d["bay_chainage_m"]) > 50:
                opening = None            # the nearest measured opening is not this one
        lanes = lanes_by_junction.get(u["junction"], 3)

        checks = {
            "gap capacity": gap_criterion(u),
            "median width": median_criterion(u, opening),
            "storage": storage_criterion(u),
            "weaving": weave_criterion(u, d, lanes),
            "detour burden": detour_criterion(d),
        }
        binding = next((c for c in CRITERIA if checks[c]["status"] == FAIL), None)
        # Recorded BEFORE the not-reached pass overwrites them. A criterion below the
        # binding one is not blocked TODAY - the verdict is already reached without it -
        # but it is what would need data the moment the binding criterion were cleared.
        # Losing that distinction made the framework report nothing left to measure while
        # its own advice section listed two surveys.
        blocked_now = [c for c in CRITERIA if checks[c]["status"] == BLOCKED]
        if binding:
            i = CRITERIA.index(binding)
            blocked_after = [c for c in blocked_now if CRITERIA.index(c) > i]
            blocked_now = [c for c in blocked_now if CRITERIA.index(c) < i]
            # everything after the binding criterion was not tested, and saying it passed
            # would be a claim about a test that never ran
            for c in CRITERIA[i + 1:]:
                checks[c] = dict(status=NOT_REACHED, value=checks[c]["value"],
                                 detail=f"not reached: {binding} binds first.")
        else:
            blocked_after = []
        rows.append(dict(
            junction=u["junction"], jda_name=u["jda_name"].strip(), bay=u["bay"],
            uturn_demand=round(u["uturn_demand"]),
            verdict=("fails" if binding else
                     "undecided" if blocked_now else "viable"),
            binding_criterion=binding,
            blocked_on=blocked_now,
            blocked_if_binding_cleared=blocked_after,
            checks=checks,
            back_solve=back_solve(u) if binding == "gap capacity" else None,
        ))
    return rows


def live_alternatives(rows):
    """Which rungs of the ladder can actually move the binding term, corridor-wide."""
    gap_bound = [r for r in rows if r["binding_criterion"] == "gap capacity"]
    if not gap_bound:
        return [dict(measure=m, cost=c, note=n, live=True) for m, c, n in ALTERNATIVES]

    over_ceiling = [r for r in gap_bound if r["back_solve"]["above_bay_ceiling"]]
    cuts = [r["back_solve"]["conflicting_reduction_pct"] for r in gap_bound
            if r["back_solve"]["conflicting_reduction_pct"] is not None]
    worst = max(cuts) if cuts else 100.0
    ceiling = gap_bound[0]["back_solve"]["bay_ceiling_veh_hr"]

    def reason(threshold):
        if over_ceiling:
            n = len(over_ceiling)
            return (f" It cannot help the {n} bay(s) whose demand is above the "
                    f"{ceiling:,} veh/h a single opening passes at zero opposing "
                    f"traffic, and for the rest the opposing flow would have to fall "
                    f"{worst:.0f}%.")
        return f" It cannot close a {worst:.0f}% shortfall."

    out = []
    for measure, cost, note in ALTERNATIVES:
        if measure == "relocate the bay":
            live = not over_ceiling and worst < 50
            note += "" if live else reason(50)
        elif measure == "widen the median, add an acceleration lane":
            live = not over_ceiling and worst < 25
            note += "" if live else reason(25)
        elif measure == "signalise the U-turn":
            # metering manufactures gaps, but it cannot lift the follow-up ceiling
            live = len(over_ceiling) < len(gap_bound)
            if over_ceiling:
                note += (f" It still cannot serve the {len(over_ceiling)} bay(s) above "
                         f"the {ceiling:,} veh/h ceiling: metering creates gaps, it does "
                         f"not shorten the follow-up headway.")
        elif measure == "grade separate the through movement" and over_ceiling:
            live = True
            note += (f" For the {len(over_ceiling)} bay(s) above the ceiling it works by "
                     f"removing the NEED for a U-turn - with the through movement "
                     f"elevated the junction can keep a signalised right turn - not by "
                     f"making the bay work. A single opening still cannot pass their "
                     f"demand.")
        else:
            live = True
        out.append(dict(measure=measure, cost=cost, note=note, live=live))
    return out


def _main():
    sch = json.loads((OUT_DATA / "scheme_test.json").read_text())
    cap = json.loads((OUT_DATA / "capacity.json").read_text())
    openings = [f["properties"] for f in json.loads(
        (OUT_DATA / "median_openings.geojson").read_text())["features"]]
    lanes = {k: v["lanes_per_dir"] for k, v in cap["widths"].items()}

    rows = assess(sch["uturns"], sch["uturn_detour"], openings, lanes)
    alts = live_alternatives(rows)

    print("=== U-turn decision framework ===")
    print("  Five criteria in order, first failure binding. A criterion below the")
    print("  binding one is NOT REACHED, not passed: it was never tested.\n")
    print(f"  {'bay':<22}{'demand':>8}   {'verdict':<11}{'binds on':<15}blocked on")
    print("  " + "-" * 92)
    for r in rows:
        b = ", ".join(r["blocked_on"]) or "-"
        print(f"  {r['junction']} {r['bay']:<11}{r['uturn_demand']:>8,}   "
              f"{r['verdict']:<11}{str(r['binding_criterion'] or '-'):<15}{b[:32]}")

    fails = [r for r in rows if r["verdict"] == "fails"]
    print(f"\n  {len(fails)} of {len(rows)} bays fail. Binding criterion:")
    for c in CRITERIA:
        n = sum(1 for r in fails if r["binding_criterion"] == c)
        if n:
            print(f"    {c:<16}{n} of {len(rows)}")

    over = [r for r in fails if (r["back_solve"] or {}).get("above_bay_ceiling")]
    if over:
        ceil = over[0]["back_solve"]["bay_ceiling_veh_hr"]
        print(f"\n  {len(over)} of those are above the ceiling of the instrument itself.")
        print(f"  A single opening passes at most {ceil:,} veh/h - 3600 / the follow-up")
        print(f"  headway - and that is with NO opposing traffic at all. These bays are")
        print(f"  not badly sited. They are the wrong instrument for the demand:")
        for r in over:
            print(f"    {r['junction']} {r['bay']:<11}"
                  f"{r['back_solve']['demand_now']:>7,} veh/h against a "
                  f"{ceil:,} veh/h ceiling")

    print("\n=== What would have to change ===")
    print("  Solved backwards from the binding criterion, not asserted. A dash in the")
    print("  q_c columns is a bay above the ceiling: no opposing-flow relief reaches it.\n")
    print(f"  {'bay':<22}{'q_c now':>9}{'q_c needed':>12}{'cut':>7}"
          f"{'servable':>10}{'gap needed':>12}{'ours':>7}")
    print("  " + "-" * 81)
    for r in fails:
        s = r["back_solve"]
        if not s:
            continue
        need = f"{s['conflicting_needed']:,}" if s["conflicting_needed"] else "-"
        cut = (f"{s['conflicting_reduction_pct']:.0f}%"
               if s["conflicting_reduction_pct"] is not None else "-")
        print(f"  {r['junction']} {r['bay']:<11}{s['conflicting_now']:>9,}{need:>12}"
              f"{cut:>7}{s['demand_servable']:>10,}{s['gap_needed_s']:>11.2f}s"
              f"{s['gap_ours_s']:>6.2f}s")

    print("\n=== The ladder, and which rungs are live here ===")
    for a in alts:
        print(f"  [{'LIVE' if a['live'] else 'DEAD'}] {a['measure']}  ({a['cost']})")
        print(f"         {a['note']}")

    now = sorted({c for r in rows for c in r["blocked_on"]})
    later = sorted({c for r in rows for c in r["blocked_if_binding_cleared"]})
    n_blocked = sum(1 for r in rows if r["verdict"] == "undecided")
    print("\n=== What to measure ===")
    if not now:
        print("  Nothing, to reach today's verdict, and that is itself the finding.")
        print(f"  {len(rows)} of {len(rows)} bays fail on the gap criterion, which binds "
              f"on the counts and")
        print("  the opposing flows we already hold. No survey changes the answer, so")
        print("  there is no measurement to wait for before deciding against the scheme.")
    else:
        print(f"  {n_blocked} of {len(rows)} bays are undecided on data we do not hold,")
        print("  blocked on: " + ", ".join(now))
    if later:
        print("\n  It matters the moment the binding criterion is cleared. If the")
        print("  opposing flow were treated, these could not then be evaluated: "
              + ", ".join(later) + ".")
        print("  Two items unblock them:")
        print("    1. The seven proposed bay chainages on JDA's alignment. Unblocks")
        print("       weaving and detour, and lets a measured opening be matched to a bay.")
        print("    2. A total station survey of median opening and receiving carriageway")
        print("       width at each bay. The DWG carries no dimension entities, so every")
        print("       width in this pipeline is scaled off linework and is provisional.")

    unresolved = [r for r in rows if r["verdict"] == "undecided" and not r["blocked_on"]]
    print(f"\n  GATE - bays reaching a verdict or naming what blocks them: "
          f"**{len(rows) - len(unresolved)} of {len(rows)}**")
    if unresolved:
        raise SystemExit("a bay was left undecided without naming what would decide it")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "uturn_framework.json").write_text(json.dumps(dict(
        method="ordered criteria ladder, first failure binding, binding term back-solved",
        criteria=CRITERIA,
        assumptions=dict(
            design_vehicle_turning_radius_m=DESIGN_VEHICLE,
            swept_allowance_m=SWEPT_ALLOWANCE_M,
            swept_width_needed_m={k: [round(a, 1), round(b, 1)]
                                  for k, (a, b) in _swept_need().items()},
            bay_storage_m=BAY_STORAGE_M, weave_per_lane_m=WEAVE_PER_LANE_M,
            detour_tolerable_m=DETOUR_TOLERABLE_M, no_gap_vc=NO_GAP_VC,
            radii_note=("design-vehicle radii are a policy input carried as a band; the "
                        "governing clause in the current IRC:SP:41 and IRC:86 print has "
                        "not been checked against this text and must be before design")),
        bays=rows,
        n_bays=len(rows),
        n_fail=len(fails),
        binding_counts={c: sum(1 for r in fails if r["binding_criterion"] == c)
                        for c in CRITERIA},
        alternatives=alts,
        blocked_criteria_now=now,
        blocked_criteria_once_binding_cleared=later,
        n_undecided=n_blocked,
        bay_ceiling_veh_hr=(over[0]["back_solve"]["bay_ceiling_veh_hr"] if over else None),
        bays_above_bay_ceiling=len(over),
        measurement_status=("provisional: the DWG carries no dimension entities, so every "
                            "width here is scaled from georeferenced linework and a total "
                            "station survey is required before design"),
    ), indent=1))
    print(f"\nwritten: {OUT_DATA/'uturn_framework.json'}")


if __name__ == "__main__":
    _main()
