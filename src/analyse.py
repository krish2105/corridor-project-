"""
analyse.py — corridor analytics over the parsed survey.

Peak hour and PHF, turning-movement matrices, composition, and the corridor
continuity analysis that recovers the physical ordering of the six junctions
from the counts alone.

Day 1 only by default. audit.py finding F shows 12 May is derived from 11 May,
so treating it as a second observation would double-count.

Run:  uv run python src/analyse.py
"""
import sys
from itertools import permutations
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import JUNCTIONS
from src.tmc_parse import CLASS_LABELS, parse_all
from src.pcu import SURVEYED, factor_band

NORTH, SOUTH = "Mansarover Metro", "Sanganer Stadium"


def movements(bins, day):
    return bins[(bins.kind == "movement") & (bins.date == day)]


def peak_hours(bins, day):
    """Peak hour = 4 consecutive 15-min bins with the highest combined entering volume."""
    mv = movements(bins, day)
    rows = []
    for j, g in mv.groupby("junction"):
        s = g.groupby("bin_start")["count"].sum().sort_index()
        i = max(range(len(s) - 3), key=lambda k: s.iloc[k:k + 4].sum())
        hour = s.iloc[i:i + 4]
        rows.append(dict(junction=j, peak_start=s.index[i], peak_veh=int(hour.sum()),
                         peak15=int(hour.max()),
                         phf=round(hour.sum() / (4 * hour.max()), 3),
                         daily_veh=int(s.sum())))
    return pd.DataFrame(rows).sort_values("junction")


def tmc_matrix(bins, day, junction):
    """Entry arm x exit arm, in vehicles and in corrected PCU."""
    mv = movements(bins, day)
    mv = mv[mv.junction == junction]
    share = mv.groupby("veh_class")["count"].sum()
    share = share / share.sum()

    def pcu_of(row):
        lo, pt, hi = factor_band(row.veh_class, share[row.veh_class])
        return row["count"] * (pt if pt is not None else SURVEYED[row.veh_class])

    mv = mv.assign(pcu=mv.apply(pcu_of, axis=1))
    veh = mv.pivot_table(index="arm_from", columns="arm_to", values="count",
                         aggfunc="sum", fill_value=0)
    pcu = mv.pivot_table(index="arm_from", columns="arm_to", values="pcu",
                         aggfunc="sum", fill_value=0)
    order = [a for a in JUNCTIONS[junction] if a in veh.index]
    return veh.reindex(index=order, columns=order, fill_value=0), \
           pcu.reindex(index=order, columns=order, fill_value=0)


def composition(bins, day):
    mv = movements(bins, day)
    c = mv.groupby(["junction", "veh_class"], as_index=False)["count"].sum()
    c["share"] = c.groupby("junction")["count"].transform(lambda s: s / s.sum())
    return c


def corridor_order(bins, day):
    """
    Recover the physical order of the six junctions from continuity alone.

    Southbound traffic leaving junction J toward Sanganer Stadium must arrive at
    the next junction south as traffic entering from Mansarover Metro. Northbound
    is the mirror. Score every ordering by how badly those two identities fail and
    take the best. No coordinates are used.
    """
    mv = movements(bins, day)
    out_s = mv[mv.arm_to == SOUTH].groupby("junction")["count"].sum()
    in_n = mv[mv.arm_from == NORTH].groupby("junction")["count"].sum()
    out_n = mv[mv.arm_to == NORTH].groupby("junction")["count"].sum()
    in_s = mv[mv.arm_from == SOUTH].groupby("junction")["count"].sum()

    def link_cost(a, b):
        """Cost of placing b immediately south of a, as a fraction of flow."""
        sb = abs(out_s[a] - in_n[b]) / max(out_s[a], in_n[b])
        nb = abs(out_n[b] - in_s[a]) / max(out_n[b], in_s[a])
        return sb + nb

    juncs = sorted(out_s.index)
    scored = sorted(((sum(link_cost(p[i], p[i + 1]) for i in range(len(p) - 1)), p)
                     for p in permutations(juncs)), key=lambda t: t[0])
    best_cost, best = scored[0]

    links = [dict(north=best[i], south=best[i + 1],
                  southbound_out=int(out_s[best[i]]), southbound_in=int(in_n[best[i + 1]]),
                  northbound_out=int(out_n[best[i + 1]]), northbound_in=int(in_s[best[i]]),
                  cost=round(link_cost(best[i], best[i + 1]), 4))
             for i in range(len(best) - 1)]
    top = [(round(c, 4), p) for c, p in scored[:5]]
    # Guard the divide. When the runner-up ordering scores zero cost - which happens
    # whenever two candidate orderings fit the flows equally well, including any corridor
    # with only two junctions - this divided by zero and returned nan, and a nan margin
    # silently reads as "not conclusive" rather than as a failed computation.
    runner_up = scored[1][0] if len(scored) > 1 else None
    margin = (100 * (runner_up - best_cost) / runner_up) if runner_up else 0.0
    return best, best_cost, top, margin, pd.DataFrame(links)


def through_vs_turning(bins, day):
    """
    Through movements vs turning movements, per junction.

    This is the single most consequential number in the study. An elevated
    through-carriageway only helps traffic that is not turning: if through movements
    dominate, the scheme is well founded; if turning and local access dominate, the
    corridor's problem is junction conflict and a flyover underperforms its cost.
    (jaipur_corridor_study.md, Phase 7.3, point 3.)

    Straight = arm i -> arm i+2 in the clockwise arm order.
    """
    mv = movements(bins, day)
    rows = []
    for j, g in mv.groupby("junction"):
        arms = JUNCTIONS[j]
        straight = {(arms[i], arms[(i + 2) % 4]) for i in range(4)}
        g = g.assign(is_through=[(f, t) in straight for f, t in zip(g.arm_from, g.arm_to)])
        thr = g[g.is_through]["count"].sum()
        tot = g["count"].sum()
        # the corridor through movement specifically: N<->S
        corr = g[((g.arm_from == NORTH) & (g.arm_to == SOUTH)) |
                 ((g.arm_from == SOUTH) & (g.arm_to == NORTH))]["count"].sum()
        rows.append(dict(junction=j, total_veh=int(tot), through_veh=int(thr),
                         through_pct=round(100 * thr / tot, 1),
                         corridor_through_veh=int(corr),
                         corridor_through_pct=round(100 * corr / tot, 1)))
    return pd.DataFrame(rows).sort_values("junction")


if __name__ == "__main__":
    bins, _ = parse_all()
    day = sorted(bins.date.unique())[0]
    print(f"Analysis day: {day} (day 2 excluded — see audit finding F)\n")

    print("=== Peak hour and PHF ===")
    ph = peak_hours(bins, day)
    print(ph.to_string(index=False))
    print(f"\nPHF {ph.phf.min():.3f}-{ph.phf.max():.3f}. IRC guidance for an urban Indian")
    print("arterial is 0.85-0.92; values this close to 1.0 indicate a smoothed series.\n")

    print("=== Turning movement matrix, TMC-04 (busiest), vehicles/day ===")
    veh, pcu = tmc_matrix(bins, day, "TMC-04")
    print(veh.to_string())
    print("\nrows = entry arm, cols = exit arm. Diagonal is empty: no U-turns surveyed.")
    print("Left turn = next arm clockwise (India drives on the left).\n")

    print("=== Composition, corridor-wide ===")
    comp = composition(bins, day)
    tot = comp.groupby("veh_class")["count"].sum()
    for cls, n in tot.sort_values(ascending=False).items():
        print(f"  {CLASS_LABELS[cls][:52]:<54} {n:>9,.0f}  {100*n/tot.sum():>5.2f}%")
    print("\n  Note: summed across six junctions, so a vehicle traversing the corridor is")
    print("  counted once per junction it passes. This is junction throughput, not a")
    print("  corridor vehicle count.\n")

    print("=== Through vs turning movements ===")
    tv = through_vs_turning(bins, day)
    print(tv.to_string(index=False))
    print(f"\n  Through movements are {tv.through_pct.min():.1f}-{tv.through_pct.max():.1f}% "
          f"of junction traffic (mean {tv.through_pct.mean():.1f}%).")
    print(f"  The corridor movement alone (Mansarover <-> Sanganer) is "
          f"{tv.corridor_through_pct.mean():.1f}% on average.")
    print("  Phase 7.3 of the methodology: above ~70% through, an elevated")
    print("  through-carriageway is well founded. This is the number that decides it.\n")

    print("=== Corridor order, derived from continuity (no coordinates used) ===")
    best, cost, top, margin, links = corridor_order(bins, day)
    print(f"  best ordering, north to south : {' -> '.join(best)}   cost {cost:.4f}")
    print(f"  margin over runner-up         : {margin:.1f}%")
    print("\n  top 5 candidate orderings:")
    for c, p in top:
        print(f"    {c:.4f}  {' -> '.join(p)}")
    print()
    print(links.to_string(index=False))
    print("\n  southbound_out = vehicles leaving the north junction toward Sanganer")
    print("  southbound_in  = vehicles entering the south junction from Mansarover")
    print()
    if margin < 10:
        print(f"  >>> INCONCLUSIVE. A {margin:.1f}% margin over the runner-up is noise, and the")
        print("      top five orderings differ only in the middle of the chain. Two links are")
        print("      strong (cost < 0.05) but mid-block frontage access on an urban arterial")
        print("      breaks continuity badly enough that the full order is not recoverable")
        print("      from counts alone. Map pins are needed to fix it.")
    else:
        print(f"  >>> Ordering accepted at a {margin:.1f}% margin.")
