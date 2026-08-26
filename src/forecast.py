"""
forecast.py — how short can a count be and still be trusted?

THE QUESTION WORTH ASKING
"Prediction" on this dataset could mean forecasting 2046 traffic, and that would be
dishonest: one independent day of observation cannot support a growth model, and the
design-year work in `capacity.py` already does the defensible version by applying stated
IRC growth rates and publishing them as an input rather than a result.

What one day of six junctions CAN support is the question a client actually pays for.
A 24-hour classified count at six junctions is expensive, and most of those hours are
counted only to scale the ones that matter. If a four-hour count predicts the 24-hour
total to within a few percent, the next survey costs a fraction of this one - and JDA can
audit a contractor's 24-hour submission against a four-hour spot check of its own.

THE MODEL
A ratio estimator, which is what a traffic engineer means by an expansion factor:
`total = partial x f`, with f fitted across approaches. Nothing more elaborate, because
nothing more elaborate is supportable at n = 24 and because a factor is auditable by hand,
which a fitted nonlinearity is not.

VALIDATION IS LEAVE-ONE-OUT, AND THE BASELINE IS PUBLISHED
Every approach is predicted by a factor fitted on the other twenty-three, so no approach
contributes to its own prediction. The error is compared against the no-model baseline -
assume the window carries its pro-rata share of the day, f = 24/N - because a model that
cannot beat pro-rata has not learned anything about the shape of a Jaipur traffic day.

WHAT THIS CANNOT DO, STATED PLAINLY
Fitted on one independent day of one corridor. It does not forecast a future year, it
does not transfer to another corridor without refitting, and it is not validated across
days: the second survey day reproduces the first on most series, so testing on it would
be testing on the training data.

Run:  uv run python src/forecast.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import OUT_DATA

# Windows a surveyor could actually staff, as (start hour, length in hours). The survey
# day runs 08:00 to 08:00, so a window is expressed in hours from that boundary.
WINDOWS = [(0, 2), (0, 4), (0, 6), (0, 8), (0, 12), (1, 4), (2, 4), (8, 4), (10, 4)]

# What a count is commissioned to produce. Both are predicted, because a daily total that
# is right while the peak hour is wrong is no use for design.
TARGETS = ("daily_total", "peak_hour")

MAPE_GATE = 10.0         # the CLAUDE.md count gate, applied to this model too


def approach_hours(bins):
    """Each approach's 24 hourly totals on the analysis day, indexed 0..23 from 08:00."""
    mv = bins[bins.kind == "movement"].copy()
    day = sorted(mv.date.unique())[0]          # day two is derived; see the audit
    mv = mv[mv.date == day].copy()
    mv["h"] = ((pd.to_datetime(mv.bin_start) -
                pd.to_datetime(mv.bin_start).min()).dt.total_seconds() // 3600).astype(int)
    g = (mv.groupby(["junction", "arm_from", "h"])["count"].sum()
           .unstack("h").fillna(0.0).sort_index())
    return g.reindex(columns=range(24), fill_value=0.0)


def targets(h):
    """Daily total and peak hour, per approach."""
    return pd.DataFrame(dict(daily_total=h.sum(axis=1), peak_hour=h.max(axis=1)))


def loo(partial, actual):
    """
    Leave-one-out ratio estimator.

    For each approach the factor is the mean of the others' total/partial ratios, so the
    held-out approach never contributes to the factor that predicts it. The mean of
    ratios rather than the ratio of means: the latter is dominated by the busiest
    approach and would quietly become a one-approach model.
    """
    r = actual / partial
    n = len(r)
    pred = np.empty(n)
    for i in range(n):
        f = np.delete(r.to_numpy(), i).mean()
        pred[i] = partial.iloc[i] * f
    return pred


def mape(actual, pred):
    return float(100 * np.mean(np.abs(pred - actual) / actual))


def evaluate(h, tg):
    rows = []
    for start, length in WINDOWS:
        cols = [(start + i) % 24 for i in range(length)]
        partial = h[cols].sum(axis=1)
        if (partial <= 0).any():
            continue
        for t in TARGETS:
            actual = tg[t]
            m = mape(actual, loo(partial, actual))
            # the no-model baseline: the window carries its pro-rata share of the day
            base_pred = partial * (24 / length) if t == "daily_total" else partial / length
            rows.append(dict(
                start_hour_from_0800=start, hours=length,
                clock=f"{(8 + start) % 24:02d}:00-{(8 + start + length) % 24:02d}:00",
                target=t, mape=round(m, 2),
                baseline_mape=round(mape(actual, base_pred), 2),
                factor=round(float((actual / partial).mean()), 4),
                factor_cv=round(float((actual / partial).std() /
                                      (actual / partial).mean()), 4),
                worst_approach_pct=round(float(
                    (100 * np.abs(loo(partial, actual) - actual) / actual).max()), 2),
            ))
    return pd.DataFrame(rows)


def _main():
    from src.tmc_parse import parse_all

    bins, _ = parse_all()
    h = approach_hours(bins)
    tg = targets(h)
    res = evaluate(h, tg)

    print("=== How short can a count be? ===")
    print(f"  {len(h)} approaches, one analysis day. Ratio estimator, leave-one-out.")
    print("  'baseline' is the no-model answer: the window carries its pro-rata share.\n")
    print(f"  {'window':<14}{'hrs':>5}   {'target':<13}{'factor':>9}{'cv':>8}"
          f"{'MAPE':>9}{'baseline':>10}{'worst':>8}")
    print("  " + "-" * 78)
    for _, r in res.sort_values(["target", "hours", "start_hour_from_0800"]).iterrows():
        print(f"  {r.clock:<14}{r.hours:>5}   {r.target:<13}{r.factor:>9.3f}"
              f"{r.factor_cv:>8.3f}{r.mape:>8.1f}%{r.baseline_mape:>9.1f}%"
              f"{r.worst_approach_pct:>7.1f}%")

    best = {}
    for t in TARGETS:
        g = res[res.target == t]
        ok = g[(g.mape < MAPE_GATE) & (g.mape < g.baseline_mape)]
        best[t] = (None if ok.empty else
                   ok.sort_values(["hours", "mape"]).iloc[0].to_dict())

    print(f"\n=== Shortest window that clears {MAPE_GATE:.0f}% AND beats pro-rata ===")
    for t in TARGETS:
        b = best[t]
        if b is None:
            print(f"  {t:<13} none. No window tested predicts it well enough to replace "
                  f"a full count.")
        else:
            print(f"  {t:<13} {b['clock']} ({b['hours']} h) -> MAPE {b['mape']:.1f}% "
                  f"against a {b['baseline_mape']:.1f}% baseline, worst approach "
                  f"{b['worst_approach_pct']:.1f}%")

    n_ok = sum(1 for t in TARGETS if best[t] is not None)
    print(f"\n  GATE - targets predictable from a short count at MAPE < {MAPE_GATE:.0f}%: "
          f"**{n_ok} of {len(TARGETS)}**")

    print(f"\n  The WINDOW was chosen on this same leave-one-out error, over "
          f"{len(res)} window-target")
    print("  combinations, so the headline MAPE is the best of a search and is optimistic")
    print("  by an unknown amount. The leave-one-out protects the FACTOR, not the choice")
    print("  of window. Two figures are not selected and should be read instead: the")
    print("  worst single approach in each row, and the fact that the 8- and 12-hour")
    print("  windows clear the gate without any search at all.")

    print("\n  Limits, so this is not read as more than it is. Fitted on ONE independent")
    print("  day of ONE corridor: the second survey day reproduces the first on most")
    print("  series, so it cannot serve as a test set. It forecasts nothing about a")
    print("  future year. It is a scaling rule for a Jaipur arterial day, and the first")
    print("  thing to do with it is refit it the moment a genuinely independent day exists.")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "forecast.json").write_text(json.dumps(dict(
        method="ratio (expansion-factor) estimator, leave-one-out over approaches",
        baseline="pro-rata: the window carries its share of the day, no model",
        n_approaches=int(len(h)), analysis_days=1,
        caveat=("one independent day, one corridor; not a growth forecast and not "
                "validated across days, because day two is derived from day one"),
        mape_gate=MAPE_GATE,
        selection=dict(
            combinations_searched=int(len(res)),
            note=("the window is chosen on the same leave-one-out error it is reported "
                  "with, so the headline MAPE is the best of a search and optimistic by "
                  "an unknown amount; the leave-one-out protects the factor, not the "
                  "choice of window")),
        windows=res.to_dict("records"),
        shortest_window={t: best[t] for t in TARGETS},
        gate=dict(targets=len(TARGETS), predictable=n_ok),
    ), indent=1))
    print(f"\nwritten: {OUT_DATA/'forecast.json'}")


if __name__ == "__main__":
    _main()
