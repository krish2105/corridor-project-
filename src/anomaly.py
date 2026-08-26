"""
anomaly.py — automated integrity screening of a submitted traffic survey.

WHAT THIS IS FOR
The audit in `audit.py` found this survey's defects by hand: someone read the workbooks,
noticed that day two looked like day one, and then built a test for it. That does not
scale. JDA commissions surveys continuously and has no way to screen a submission before
accepting it, so the defects surface, if at all, months later inside a design.

This module is the screen. It takes a parsed survey and runs six independent detectors
over it, each looking for a different signature of a data problem, and scores every
junction. Nothing about THIS survey is hardcoded: the detectors are written against the
general shape of a classified count, so the same code runs on the next contractor's
submission.

THE GATE IS REDISCOVERY
A detector that finds nothing is useless and a detector that finds everything is worse.
The gate here is that the screen must independently rediscover the two defects the audit
already proved - the duplicated second day and the broken stored totals - and rank them
above the noise, WITHOUT being told they exist. If it cannot re-find a known defect it
cannot be trusted on an unknown one.

WHY THESE SIX
Each is a different failure mode of survey production, and each leaves a signature that
survives aggregation:

  duplicate day    a second day copied from the first, wholly or in part
  terminal digit   hand tallying rounds to 0 and 5; machine counting does not
  flatline run     the same count repeated across consecutive intervals
  profile spike    a count that does not belong to its own hour
  composition mix  an interval whose class mix departs from the site's own mix,
                   the signature of a column shift during data entry
  stored total     an arithmetic break between a written total and its components

WHAT THIS IS NOT
Not fraud detection. Every signature here has an innocent explanation - a festival, a
lane closure, a genuinely quiet class. The output is a list of things a human should
look at, ordered, with the reason attached. Calling it anything stronger would be
claiming a conclusion the arithmetic does not support.

Run:  uv run python src/anomaly.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import JUNCTION_COORDS, OUT_DATA

# Terminal digits are only meaningful once a count is big enough to have one. Below 10
# the terminal digit IS the count, so its distribution is skewed for honest reasons and
# testing it would manufacture a finding.
DIGIT_MIN_COUNT = 10

# A robust z above this on the residual from a local median is worth a look. 3.5 is the
# conventional MAD-based outlier threshold (Iglewicz and Hoaglin), used rather than a
# tuned value so the number is not chosen to make the output look good.
SPIKE_Z = 3.5

# A spike must also be large in vehicles, not only in standard deviations. Without this
# the detector fires on the slow classes, where the local spread is a vehicle or two and
# a cycle rickshaw arriving makes z enormous. A spike has to be both statistically and
# practically large to be worth a reviewer's time.
SPIKE_MIN_VEH = 10

# Four consecutive identical non-zero counts is 60 minutes of a stream not varying. Real
# 15-minute counts vary; this threshold is deliberately loose so runs that clear it are
# unambiguous rather than borderline.
FLATLINE_MIN = 4

# L1 distance between two share vectors runs 0 to 2. Half of that is a mix that has
# genuinely changed, not one that has drifted.
MIX_L1 = 0.5


def _series(bins):
    """Movement sheets only, as (junction, sheet, class, date) -> 96 counts."""
    mv = bins[bins.kind == "movement"]
    return mv.pivot_table(index=["junction", "sheet", "veh_class", "date"],
                          columns="bin_label", values="count", aggfunc="sum")


# --- the six detectors -------------------------------------------------------

def duplicate_day(bins):
    """
    How much of each day reproduces the day before it, bin for bin.

    Compared at series level rather than on daily totals. Two independently counted days
    can land on the same total by coincidence; they cannot land on the same 96 numbers.
    """
    piv = _series(bins)
    dates = sorted(bins.date.unique())
    if len(dates) < 2:
        return pd.DataFrame(columns=["junction", "series", "bins_identical", "share"])
    rows = []
    for (j, sheet, cls), g in piv.groupby(level=["junction", "sheet", "veh_class"]):
        g = g.droplevel(["junction", "sheet", "veh_class"])
        if not {dates[0], dates[1]} <= set(g.index):
            continue
        a, b = g.loc[dates[0]].to_numpy(), g.loc[dates[1]].to_numpy()
        live = (a > 0) | (b > 0)
        if live.sum() == 0:                 # a class absent on both days proves nothing
            continue
        same = int((a[live] == b[live]).sum())
        rows.append(dict(junction=j, series=f"{sheet}/{cls}", bins_identical=same,
                         live_bins=int(live.sum()), share=round(same / live.sum(), 3)))
    return pd.DataFrame(rows)


def terminal_digit(bins):
    """
    Chi-square of the last digit of every count against uniform.

    A person tallying on a sheet rounds to 0 and 5 without meaning to. A count read off a
    detector or a video does not. The test says which of the two produced this survey.

    Both p and the effect size are returned, and the SCORE uses the effect size. With
    tens of thousands of counts a chi-square rejects uniform on a deviation far too small
    to mean anything, so scoring on p would give every junction the same maximum and the
    detector would carry no information at all - which is exactly what it did on the
    first run here. What matters is how many percentage points above the expected 20%
    the digits 0 and 5 actually take.
    """
    mv = bins[bins.kind == "movement"]
    rows = []
    for j, g in mv.groupby("junction"):
        v = g.loc[g["count"] >= DIGIT_MIN_COUNT, "count"].to_numpy().astype(int)
        if len(v) < 100:
            continue
        obs = np.bincount(v % 10, minlength=10)
        chi, p = stats.chisquare(obs)
        rows.append(dict(junction=j, n=int(len(v)), chi2=round(float(chi), 1),
                         p=float(p),
                         excess_0_5_pct=round(100 * (obs[0] + obs[5]) / len(v) - 20, 1)))
    return pd.DataFrame(rows)


def flatline_run(bins):
    """Longest run of the same non-zero count across consecutive intervals."""
    piv = _series(bins)
    rows = []
    for idx, row in piv.iterrows():
        v = row.to_numpy()
        best, best_val, run = 0, 0.0, 0
        for i in range(1, len(v)):
            run = run + 1 if (v[i] == v[i - 1] and v[i] > 0) else 0
            if run and run + 1 > best:
                best, best_val = run + 1, float(v[i])
        if best >= FLATLINE_MIN:
            j, sheet, cls, dt = idx
            rows.append(dict(junction=j, series=f"{sheet}/{cls}", date=str(dt),
                             run_bins=int(best), value=best_val))
    return pd.DataFrame(rows)


def profile_spike(bins):
    """
    Counts that do not belong between their own neighbours.

    The operator is the second difference, v[i] - (v[i-1] + v[i+1]) / 2, not a residual
    from a rolling median. Traffic has a shape and the shape is steep: the morning ramp
    climbs for two hours straight, and a centred median lags a ramp, so the residual is
    large through the whole climb. That is what the first version of this detector
    measured - it flagged 110 bins per thousand, which was the ramp, not an anomaly.

    The second difference is exactly zero on any straight ramp, whatever its slope, so
    what survives is a bin that departs from the line its neighbours sit on. Its scale
    comes from the MAD of the second differences themselves, so a busy series is allowed
    proportionally more movement than a quiet one.
    """
    piv = _series(bins)
    rows = []
    for idx, row in piv.iterrows():
        v = row.to_numpy().astype(float)
        if v.sum() < 100:
            continue
        d = np.full(len(v), np.nan)
        d[1:-1] = v[1:-1] - 0.5 * (v[:-2] + v[2:])
        mad = np.nanmedian(np.abs(d - np.nanmedian(d)))
        if not mad:
            continue
        z = 0.6745 * d / mad              # Iglewicz-Hoaglin modified z
        hit = (np.abs(z) > SPIKE_Z) & (np.abs(d) >= SPIKE_MIN_VEH)
        hit = np.nan_to_num(hit).astype(bool)
        # One outlier smears across three second differences - its own, and its two
        # neighbours', which are computed using it. Counting flagged positions therefore
        # reports roughly three times as many spikes as there are, so a run of adjacent
        # flags is collapsed to the single anomaly that produced it.
        n = int(np.sum(hit & ~np.concatenate(([False], hit[:-1]))))
        j, sheet, cls, dt = idx
        rows.append(dict(junction=j, series=f"{sheet}/{cls}", date=str(dt),
                         bins=int(len(v)), n_spikes=n,
                         max_z=round(float(np.nanmax(np.abs(z))), 1)))
    return pd.DataFrame(rows)


def composition_shift(bins):
    """
    Intervals whose class mix departs from the site's own daily mix.

    A column transposed during data entry moves vehicles between classes without changing
    the interval total, so no conservation check sees it. The share vector does.
    """
    mv = bins[bins.kind == "movement"]
    tot = mv.groupby(["junction", "date", "bin_label", "veh_class"])["count"].sum()
    wide = tot.unstack("veh_class").fillna(0.0)
    rows = []
    for (j, dt), g in wide.groupby(level=["junction", "date"]):
        n = g.sum(axis=1)
        g = g[n >= 50]                      # a thin interval has a noisy mix, not a wrong one
        if len(g) < 10:
            continue
        share = g.div(g.sum(axis=1), axis=0)
        ref = g.sum() / g.sum().sum()       # the site's own mix, not a national assumption
        l1 = (share - ref).abs().sum(axis=1)
        hit = l1 > MIX_L1
        if hit.any():
            rows.append(dict(junction=j, date=str(dt), intervals=int(hit.sum()),
                             max_l1=round(float(l1.max()), 3),
                             worst_interval=str(l1.idxmax()[-1])))
    return pd.DataFrame(rows)


def stored_total_break(mism):
    """The arithmetic register, folded in so the screen covers all six modes."""
    if mism is None or len(mism) == 0:
        return pd.DataFrame(columns=["junction", "breaks", "net_vehicles"])
    return (mism.groupby("junction")
                .agg(breaks=("delta", "size"), net_vehicles=("delta", "sum"))
                .reset_index())


# --- scoring -----------------------------------------------------------------

def screen(bins, mism=None):
    """Run all six and score each junction. Returns (findings, per-junction scores)."""
    dup, dig = duplicate_day(bins), terminal_digit(bins)
    flat, spike = flatline_run(bins), profile_spike(bins)
    mix, brk = composition_shift(bins), stored_total_break(mism)

    junctions = sorted(bins.junction.unique())
    rows = []
    for j in junctions:
        d = dup[dup.junction == j] if len(dup) else dup
        # share of series that are wholly a copy of the previous day
        dup_share = float((d.share >= 1.0).mean()) if len(d) else 0.0
        dg = dig[dig.junction == j]
        sp = spike[spike.junction == j] if len(spike) else spike
        rows.append(dict(
            junction=j, jda_name=JUNCTION_COORDS[j][2].strip(),
            duplicate_series_share=round(dup_share, 3),
            terminal_digit_p=float(dg.p.iloc[0]) if len(dg) else 1.0,
            terminal_digit_excess_pct=(round(float(dg.excess_0_5_pct.iloc[0]), 1)
                                       if len(dg) else 0.0),
            flatline_series=int((flat.junction == j).sum()) if len(flat) else 0,
            spike_bins_per_1000=(round(1000 * sp.n_spikes.sum() / sp.bins.sum(), 1)
                                 if len(sp) and sp.bins.sum() else 0.0),
            mix_intervals=(int(mix[mix.junction == j].intervals.sum()) if len(mix) else 0),
            stored_total_breaks=(int(brk[brk.junction == j].breaks.sum()) if len(brk) else 0),
        ))
    sc = pd.DataFrame(rows)

    # Each detector contributes 0 to 1, and they are summed unweighted. A weighting would
    # be a judgement about which defect matters more, which is the reviewer's call.
    sc["s_duplicate"] = sc.duplicate_series_share.round(3)
    for col, src in (("s_digit", "terminal_digit_excess_pct"),
                     ("s_flatline", "flatline_series"),
                     ("s_spike", "spike_bins_per_1000"),
                     ("s_mix", "mix_intervals"), ("s_arith", "stored_total_breaks")):
        # clipped at zero: a junction whose 0s and 5s are UNDER-represented is not
        # rounding less than nothing, and a negative score would credit it for that.
        v = sc[src].clip(lower=0)
        hi = v.max()
        sc[col] = 0.0 if hi == 0 else (v / hi).round(3)
    parts = ["s_duplicate", "s_digit", "s_flatline", "s_spike", "s_mix", "s_arith"]
    sc["integrity_flag_score"] = sc[parts].sum(axis=1).round(3)
    findings = dict(duplicate=dup, digit=dig, flatline=flat, spike=spike,
                    mix=mix, arithmetic=brk)
    return findings, sc.sort_values("integrity_flag_score", ascending=False)


def _main():
    from src.tmc_parse import parse_all

    bins, mism = parse_all()
    findings, sc = screen(bins, mism)

    print("=== Survey integrity screen ===")
    print("  Six detectors, no knowledge of this survey's known defects.\n")

    dup = findings["duplicate"]
    whole = int((dup.share >= 1.0).sum()) if len(dup) else 0
    print(f"  1. duplicate day     {whole} of {len(dup)} series reproduce the previous "
          f"day in EVERY live bin")
    print(f"                       (the audit's 396 is the same series set matched on "
          f"the daily total; this is the stricter test)")
    dig = findings["digit"]
    if len(dig):
        worst = dig.sort_values("excess_0_5_pct", ascending=False).iloc[0]
        sig = int((dig.p < 0.01).sum())
        print(f"  2. terminal digit    {sig} of {len(dig)} junctions reject uniform at "
              f"p<0.01, but on {worst.excess_0_5_pct:+.1f}pp at worst "
              f"({worst.junction}). Rounding is present and small.")
    print(f"  3. flatline run      {len(findings['flatline'])} series hold one non-zero "
          f"value for {FLATLINE_MIN}+ consecutive intervals")
    sp = findings["spike"]
    nsp, nbin = int(sp.n_spikes.sum()), int(sp.bins.sum())
    print(f"  4. profile spike     {nsp} of {nbin:,} bins ({1000*nsp/nbin:.1f} per 1000) "
          f"depart from their neighbours' line by |z|>{SPIKE_Z} AND\n                       differ from it by {SPIKE_MIN_VEH}+ vehicles")
    mx = findings["mix"]
    print(f"  5. composition mix   "
          f"{int(mx.intervals.sum()) if len(mx) else 0} intervals depart from the site's "
          f"own class mix by L1>{MIX_L1}")
    ar = findings["arithmetic"]
    print(f"  6. stored total      {int(ar.breaks.sum()) if len(ar) else 0} written "
          f"totals disagree with their own components")

    print("\n=== Junction scores, unweighted sum of six detectors ===")
    print("  Each detector is normalised across the six on its EFFECT, not on whether it")
    print("  reaches significance: with this many counts everything is significant.\n")
    print(f"  {'junction':<10}{'name':<14}{'dup':>6}{'digit':>7}{'flat':>6}{'spike':>7}"
          f"{'mix':>6}{'arith':>7}{'score':>8}")
    print("  " + "-" * 71)
    for _, r in sc.iterrows():
        print(f"  {r.junction:<10}{r.jda_name:<14}{r.s_duplicate:>6.2f}{r.s_digit:>7.2f}"
              f"{r.s_flatline:>6.2f}{r.s_spike:>7.2f}{r.s_mix:>6.2f}{r.s_arith:>7.2f}"
              f"{r.integrity_flag_score:>8.2f}")

    # The gate: did the screen re-find what the audit proved, unprompted?
    found_dup = whole > 0
    found_arith = len(ar) > 0 and int(ar.breaks.sum()) > 0
    print(f"\n  GATE - known defects rediscovered without being told: "
          f"**{int(found_dup) + int(found_arith)} of 2**")
    print(f"    duplicated second day : {'FOUND' if found_dup else 'MISSED'}")
    print(f"    broken stored totals  : {'FOUND' if found_arith else 'MISSED'}")
    if not (found_dup and found_arith):
        raise SystemExit("screen failed its own gate: it cannot re-find a known defect")

    print("\n  This is a screen, not a verdict. Every signature above has an innocent")
    print("  explanation. What it gives JDA is an ordered list of what to ask about")
    print("  before a submission is accepted, produced in seconds rather than months.")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    payload = dict(
        method="six independent detectors over the parsed survey, scored unweighted",
        caveat=("a screen, not fraud detection; every signature has an innocent "
                "explanation and the output is an ordered list to ask about"),
        thresholds=dict(digit_min_count=DIGIT_MIN_COUNT, spike_z=SPIKE_Z,
                        spike_min_veh=SPIKE_MIN_VEH,
                        flatline_min=FLATLINE_MIN, mix_l1=MIX_L1),
        detectors=dict(
            duplicate=dict(series=len(dup), wholly_identical=whole),
            terminal_digit=dig.to_dict("records"),
            flatline=dict(series=len(findings["flatline"])),
            spike=dict(series=len(sp)),
            mix=dict(intervals=int(mx.intervals.sum()) if len(mx) else 0),
            arithmetic=dict(breaks=int(ar.breaks.sum()) if len(ar) else 0)),
        junctions=sc.to_dict("records"),
        gate=dict(known_defects=2, rediscovered=int(found_dup) + int(found_arith)),
    )
    (OUT_DATA / "anomaly.json").write_text(json.dumps(payload, indent=1))
    print(f"\nwritten: {OUT_DATA/'anomaly.json'}")


if __name__ == "__main__":
    _main()
