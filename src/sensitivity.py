"""
sensitivity.py — do the conclusions survive the assumptions they rest on?

Every headline in this project sits on top of at least one judgement:

    PCU correction        floor +14.9%, ceiling +74.8% - half unresolvable because the
                          survey lumps 48% of the stream into one column
    lane capacity         1,200 PCU/h/lane from IRC:106, a planning figure the corridor
                          demonstrably exceeds
    effective lanes       2 by geometry; Indian mixed traffic commonly runs more streams
                          than marked lanes
    critical gap          literature, calibrated elsewhere, not measured here
    growth to design year 4 / 6 / 8 percent

A conclusion that only holds at one corner of that space is not a finding, it is a
coincidence. This runs each headline across the whole space and reports which survive
everywhere, which are conditional, and which single assumption moves the answer most.

The test that matters is deliberately hostile: take the assumption set MOST FAVOURABLE to
the scheme being proposed, and see whether the conclusion still stands.

Run:  uv run python src/sensitivity.py
"""
import json
import sys
from itertools import product
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.analyse import NORTH, SOUTH, through_vs_turning
from src.capacity import ASSUMPTIONS as CAP_A
from src.config import OUT_DATA
from src.scheme_test import CRITICAL_GAP_S, FOLLOW_UP_S, NO_GAP_VC, gap_capacity, weighted_gap
from src.tmc_parse import parse_all

# The space. Each axis runs from most favourable to the proposed scheme, to least.
AXES = dict(
    pcu_uplift_pct=[14.9, 30.0, 44.0, 74.8],
    lane_capacity_pcu=[1200, 1500, 1800],       # IRC planning -> generous
    lanes_per_direction=[2, 3],                 # geometric -> observed stream count
    critical_gap=["optimistic", "conservative"],
    growth_pct=[4.0, 6.0, 8.0],
)


def uturn_verdict(bins, day, gap_choice):
    """How many corridor approaches the U-turn bays cannot serve, at one gap assumption."""
    idx = 0 if gap_choice == "optimistic" else 1
    fu = FOLLOW_UP_S[0] if gap_choice == "optimistic" else FOLLOW_UP_S[1]
    mv = bins[(bins.kind == "movement") & (bins.date == day)]
    fails = total = 0
    for _code, g in mv.groupby("junction"):
        share = g.groupby("veh_class")["count"].sum()
        share = (share / share.sum()).to_dict()
        tc = weighted_gap(share, idx)
        tot = g.groupby("bin_start")["count"].sum().sort_index()
        i = max(range(len(tot) - 3), key=lambda k: tot.iloc[k:k + 4].sum())
        win = tot.index[i:i + 4]
        pk = g[g.bin_start.isin(win)]
        for arm in (NORTH, SOUTH):
            rt = pk[(pk.arm_from == arm) & (pk.movement == "Right")]["count"].sum()
            opp = SOUTH if arm == NORTH else NORTH
            thru = pk[(pk.arm_from == opp) & (pk.movement == "Straight")]["count"].sum()
            if rt <= 0:
                continue
            total += 1
            if rt / gap_capacity(thru, tc, fu) >= 1.0:
                fails += 1
    return fails, total


def elevated_verdict(bins, day, uplift_pct, lane_cap, lanes):
    """How many corridor approaches the elevated option returns under capacity."""
    tv = through_vs_turning(bins, day).set_index("junction")
    mv = bins[(bins.kind == "movement") & (bins.date == day)]
    cap = lane_cap * lanes
    ok = total = 0
    for code, g in mv.groupby("junction"):
        thr = float(tv.loc[code, "through_pct"]) / 100
        for arm in (NORTH, SOUTH):
            a = g[g.arm_from == arm]
            if a.empty:
                continue
            s = a.groupby("bin_start")["count"].sum().sort_index()
            i = max(range(len(s) - 3), key=lambda k: s.iloc[k:k + 4].sum())
            veh = float(s.iloc[i:i + 4].sum())
            # veh -> PCU via the uplift being tested, applied to the surveyed baseline
            pcu = veh * 0.874 * (1 + uplift_pct / 100)   # 0.874 = surveyed PCU/veh ratio
            total += 1
            if (pcu * (1 - thr)) / cap < 1.0:
                ok += 1
    return ok, total


if __name__ == "__main__":
    bins, _ = parse_all()
    day = sorted(bins.date.unique())[0]

    print("=== The assumption space ===")
    for k, v in AXES.items():
        print(f"  {k:<24} {v}")
    n = 1
    for v in AXES.values():
        n *= len(v)
    print(f"\n  {n} combinations. Each conclusion is evaluated across all of them.\n")

    # --- conclusion 1: can the U-turn bays serve the demand? ---------------
    print("=== Conclusion 1 — the U-turn bays cannot carry the demand ===")
    print("  Only the critical-gap assumption bears on this one.\n")
    print(f"  {'critical gap':<18}{'approaches unservable':>24}")
    print("  " + "-" * 42)
    u = {}
    for choice in AXES["critical_gap"]:
        f, t = uturn_verdict(bins, day, choice)
        u[choice] = (f, t)
        print(f"  {choice:<18}{f:>13} of {t:<8}")
    best = u["optimistic"]
    print(f"\n  MOST FAVOURABLE assumption to the scheme: {best[0]} of {best[1]} still fail.")
    print(f"  ROBUST: the conclusion holds across the entire space." if best[0] > best[1] / 2
          else "  CONDITIONAL: the conclusion depends on the gap assumption.")

    # --- conclusion 2: does grade separation fix the corridor? ------------
    print("\n=== Conclusion 2 — an elevated through-carriageway restores the approaches ===")
    print("  PCU uplift, lane capacity and lane count all bear on this one.\n")
    rows = []
    for up, lc, ln in product(AXES["pcu_uplift_pct"], AXES["lane_capacity_pcu"],
                              AXES["lanes_per_direction"]):
        ok, tot = elevated_verdict(bins, day, up, lc, ln)
        rows.append(dict(uplift=up, lane_cap=lc, lanes=ln, ok=ok, total=tot,
                         frac=ok / tot))
    df = pd.DataFrame(rows)
    worst = df.loc[df.frac.idxmin()]
    print(f"  {'PCU uplift':>11}{'lane cap':>10}{'lanes':>7}{'approaches OK':>16}")
    print("  " + "-" * 46)
    for _, r in df.sort_values("frac").head(6).iterrows():
        print(f"  {r.uplift:>10.1f}%{r.lane_cap:>10,}{r.lanes:>7}{r.ok:>10} of {r.total:<4}")
    print(f"  ... {len(df) - 6} more combinations")
    print(f"\n  LEAST FAVOURABLE combination: {worst.ok:.0f} of {worst.total:.0f} approaches "
          f"return under capacity")
    print(f"  ({worst.uplift:.1f}% uplift, {worst.lane_cap:,.0f} PCU/lane, "
          f"{worst.lanes:.0f} lanes/direction)")
    allpass = int((df.frac == 1.0).sum())
    print(f"  Combinations where ALL approaches return under capacity: "
          f"**{allpass} of {len(df)}**")

    # --- which assumption matters most ------------------------------------
    print("\n=== Which assumption moves the answer most ===")
    print("  One-at-a-time, holding the others at the middle of their range.\n")
    base = dict(uplift=30.0, lane_cap=1500, lanes=2)
    b_ok, b_tot = elevated_verdict(bins, day, base["uplift"], base["lane_cap"], base["lanes"])
    print(f"  baseline: {b_ok} of {b_tot} approaches OK\n")
    print(f"  {'assumption':<24}{'low end':>12}{'high end':>12}{'swing':>9}")
    print("  " + "-" * 58)
    swings = []
    for axis, key in (("pcu_uplift_pct", "uplift"), ("lane_capacity_pcu", "lane_cap"),
                      ("lanes_per_direction", "lanes")):
        vals = AXES[axis]
        cfg_lo = {**base, key: vals[0]}
        cfg_hi = {**base, key: vals[-1]}
        lo, _ = elevated_verdict(bins, day, cfg_lo["uplift"], cfg_lo["lane_cap"], cfg_lo["lanes"])
        hi, _ = elevated_verdict(bins, day, cfg_hi["uplift"], cfg_hi["lane_cap"], cfg_hi["lanes"])
        swings.append((axis, lo, hi, abs(hi - lo)))
        print(f"  {axis:<24}{lo:>8} of {b_tot:<3}{hi:>8} of {b_tot:<3}{abs(hi-lo):>9}")
    swings.sort(key=lambda t: -t[3])
    if swings[0][3] == 0:
        print("\n  **No single assumption changes the conclusion.** Every axis swings the")
        print("  result by zero approaches across its full range, so naming a most-")
        print("  influential assumption would be meaningless here. The finding is not")
        print("  assumption-driven; it is driven by the size of the through movement.")
    else:
        print(f"\n  Most influential: **{swings[0][0]}** "
              f"(swings the result by {swings[0][3]} approaches)")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    p = OUT_DATA / "sensitivity.json"
    p.write_text(json.dumps(dict(
        axes=AXES, combinations=n,
        uturn={k: dict(fails=v[0], of=v[1]) for k, v in u.items()},
        uturn_robust=bool(best[0] > best[1] / 2),
        elevated=[{k: (v if not hasattr(v, "item") else v.item()) for k, v in r.items()}
                  for r in df.to_dict("records")],
        elevated_all_pass_combinations=allpass, elevated_total_combinations=len(df),
        most_influential=(swings[0][0] if swings[0][3] > 0 else None),
        swing=swings[0][3], assumption_driven=bool(swings[0][3] > 0),
    ), indent=1))
    print(f"\nwritten: {p}")
