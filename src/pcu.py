"""
pcu.py — IRC:106 share-dependent PCU, and an honest band where the data won't allow a point.

IRC:106 gives two factors per class: one for when that class is <=5% of the stream,
one for when it is >=10%, interpolating linearly between. PCU is a function of
composition, not a constant. The JDA survey used constants.

The survey's 10-column scheme does not map cleanly onto IRC:106. Four columns map 1:1
and can be corrected outright. Six are composites mixing IRC classes with different
factors; those cannot be disaggregated from this data, so they get a low/high band
rather than a fabricated point estimate.

Run:  uv run python src/pcu.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.tmc_parse import CLASS_LABELS, parse_all

# --- IRC:106-1990 Table 2, (pcu at share <=5%, pcu at share >=10%) -----------
IRC106 = {
    "2W":        (0.50, 0.75),
    "AUTO":      (1.20, 2.00),
    "CAR":       (1.00, 1.00),
    "LCV":       (1.40, 2.00),
    "BUS":       (2.20, 3.70),
    "TRUCK":     (2.20, 3.70),
    "MAV":       (3.70, 4.00),
    "CYCLE":     (0.40, 0.50),
    "CYCLE_RIK": (1.50, 2.00),
    "TRACTOR":   (4.00, 4.00),
    "ANIMAL":    (4.00, 8.00),
    "E_RIK":     (1.00, 1.20),   # ASSUMPTION — IRC:106 predates the e-rickshaw
}

# What the survey actually used, back-solved from its own Total(Veh)/Total(PCU) rows.
SURVEYED = {
    "CAR_BUCKET": 1.0, "TWO_W": 0.5, "AGRI_LCV": 1.5, "AUTO_TRK_BUS": 3.0,
    "TRL_MAV": 4.5, "CYCLE": 0.5, "CYCLE_RIK": 1.5, "HAND_CART": 3.0,
    "HORSE_DRAWN": 4.0, "BULLOCK": 8.0,
}

# Survey column -> the IRC classes it contains. One entry = a clean 1:1 map.
MAPPING = {
    "TWO_W":        ["2W"],
    "CYCLE":        ["CYCLE"],
    "CYCLE_RIK":    ["CYCLE_RIK"],
    "HORSE_DRAWN":  ["ANIMAL"],
    "CAR_BUCKET":   ["CAR", "AUTO", "LCV"],
    "AGRI_LCV":     ["TRACTOR", "LCV", "BUS"],
    "AUTO_TRK_BUS": ["AUTO", "TRUCK", "BUS"],
    "TRL_MAV":      ["TRACTOR", "MAV"],
    "BULLOCK":      ["ANIMAL"],
    "HAND_CART":    [],          # no IRC:106 equivalent at all
}
EXACT = {k for k, v in MAPPING.items() if len(v) == 1}


def irc_factor(irc_class, share):
    """Share-dependent factor. share is the class's fraction of the stream (0-1)."""
    lo, hi = IRC106[irc_class]
    if share <= 0.05:
        return lo
    if share >= 0.10:
        return hi
    return lo + (share - 0.05) / 0.05 * (hi - lo)


def factor_band(code, share):
    """
    (low, point, high) for a survey column at an observed share.

    point is None for composites — we will not invent one. For a composite the band
    spans the cheapest and dearest constituent, evaluated at that same share, which
    is the widest defensible statement the data supports.
    """
    members = MAPPING[code]
    if not members:                                  # Hand Cart: outside IRC:106
        f = SURVEYED[code]
        return f, None, f
    vals = [irc_factor(m, share) for m in members]
    if code in EXACT:
        return vals[0], vals[0], vals[0]
    return min(vals), None, max(vals)


def convert(bins, day=None):
    """Per junction/day: PCU as surveyed, corrected on exact classes, and banded."""
    mv = bins[bins.kind == "movement"]
    if day is not None:
        mv = mv[mv.date == day]
    tot = mv.groupby(["junction", "date", "veh_class"], as_index=False)["count"].sum()
    tot["share"] = tot.groupby(["junction", "date"])["count"].transform(lambda s: s / s.sum())

    rows = []
    for (j, d), g in tot.groupby(["junction", "date"]):
        surveyed = exact = low = high = 0.0
        for _, r in g.iterrows():
            lo, pt, hi = factor_band(r.veh_class, r.share)
            surveyed += r["count"] * SURVEYED[r.veh_class]
            # "exact" corrects only the 1:1 classes and holds composites as surveyed —
            # the defensible floor.
            exact += r["count"] * (pt if pt is not None else SURVEYED[r.veh_class])
            low += r["count"] * lo
            high += r["count"] * hi
        rows.append(dict(junction=j, date=d, veh=g["count"].sum(),
                         pcu_surveyed=surveyed, pcu_corrected_floor=exact,
                         pcu_band_low=low, pcu_band_high=high,
                         uplift_floor_pct=100 * (exact - surveyed) / surveyed))
    return pd.DataFrame(rows), tot


if __name__ == "__main__":
    bins, _ = parse_all()
    res, tot = convert(bins)

    print("=== Factor comparison at observed corridor shares (day 1, TMC-01) ===\n")
    g = tot[(tot.junction == "TMC-01") & (tot.date == sorted(tot.date.unique())[0])]
    print(f"{'class':<52} {'share':>7} {'used':>6} {'IRC low':>8} {'IRC pt':>7} {'IRC high':>9}")
    print("-" * 94)
    for _, r in g.sort_values("count", ascending=False).iterrows():
        lo, pt, hi = factor_band(r.veh_class, r.share)
        print(f"{CLASS_LABELS[r.veh_class][:50]:<52} {100*r.share:>6.2f}% "
              f"{SURVEYED[r.veh_class]:>6.2f} {lo:>8.2f} "
              f"{(f'{pt:.2f}' if pt is not None else '  --'):>7} {hi:>9.2f}")
    print("\n'--' = composite column, no defensible point estimate. Band only.\n")

    print("=== Corridor PCU ===\n")
    show = res.copy()
    show["date"] = show.date.astype(str)
    print(show.to_string(index=False, float_format=lambda v: f"{v:,.0f}"))
    print()
    print(f"GATE — floor uplift (1:1 classes only): "
          f"{res.uplift_floor_pct.mean():.1f}% mean, "
          f"{res.uplift_floor_pct.min():.1f}%-{res.uplift_floor_pct.max():.1f}% range")
    lo_p = 100 * (res.pcu_band_low - res.pcu_surveyed).sum() / res.pcu_surveyed.sum()
    hi_p = 100 * (res.pcu_band_high - res.pcu_surveyed).sum() / res.pcu_surveyed.sum()
    print(f"GATE — full band vs surveyed: {lo_p:+.1f}% to {hi_p:+.1f}%")
    print("\nE_RIK is absent from the survey entirely. Its PCU (1.0/1.2) is stated here as")
    print("an assumption for completeness; no e-rickshaw count exists to apply it to.")
